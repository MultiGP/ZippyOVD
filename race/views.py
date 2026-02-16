import json
import time
from typing import Any, Optional

from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from .logo_store import assign_logo, delete_logo, get_team_logo_urls, list_data, resolve_logo_path, upload_logo
from .state import (
    get_current_state,
    get_machine_ip,
    get_payload,
    normalize_state,
    set_machine_ip,
    set_payload,
)
from .velocidrone import client


def home(request: HttpRequest) -> HttpResponse:
    return redirect("race_admin")


def race_admin(request: HttpRequest) -> HttpResponse:
    return render(request, "race/admin.html")


def race_bug(request: HttpRequest) -> HttpResponse:
    compact = str(request.GET.get("compact", "0")).strip().lower() in {"1", "true", "yes"}
    return render(request, "race/race_bug.html", {"compact": compact})


@csrf_exempt
def api_config(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        status = client.status()
        return JsonResponse(
            {
                "machineIp": get_machine_ip(),
                "wsConnected": status.get("connected", False),
                "wsLastError": status.get("lastError", ""),
                "wsWorkerAlive": status.get("workerAlive", False),
                "wsLastMessageTs": status.get("lastMessageTs", 0),
            }
        )

    if request.method == "POST":
        data = _json_body(request)
        machine_ip = str(data.get("machineIp", "")).strip()
        set_machine_ip(machine_ip)
        client.configure(machine_ip)
        return JsonResponse({"ok": True, "machineIp": machine_ip})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def api_action(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = _json_body(request)
    action = str(data.get("action", "")).strip()
    uid = _to_int_or_none(data.get("uid", None))
    camera_number = _to_int_or_none(data.get("number", None))

    payload = _build_command(action, uid, camera_number)
    if payload is None:
        return JsonResponse({"error": f"Unsupported action: {action}"}, status=400)

    queued = client.send_command(payload)
    return JsonResponse(
        {
            "ok": True,
            "queued": queued,
            "action": action,
            "payload": payload,
            "machineIp": get_machine_ip(),
        }
    )


@csrf_exempt
def api_telemetry(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = _json_body(request)
    payload = data if isinstance(data, dict) else {"players": []}
    set_payload(payload)
    return JsonResponse({"ok": True})


def api_state(request: HttpRequest) -> JsonResponse:
    score_mode = _parse_score_mode(request)
    return JsonResponse(_build_state(score_mode))


def api_stream(request: HttpRequest) -> StreamingHttpResponse:
    score_mode = _parse_score_mode(request)

    def event_generator() -> Any:
        last_payload = ""
        last_heartbeat_ts = 0.0

        while True:
            state = _build_state(score_mode)
            serialized = json.dumps(state, separators=(",", ":"), sort_keys=True)

            if serialized != last_payload:
                yield f"event: state\ndata: {serialized}\n\n"
                last_payload = serialized
                last_heartbeat_ts = time.time()
            else:
                now = time.time()
                if now - last_heartbeat_ts >= 15.0:
                    yield ": keepalive\n\n"
                    last_heartbeat_ts = now

            time.sleep(0.25)

    response = StreamingHttpResponse(event_generator(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@csrf_exempt
def api_logos(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    discovered_colors = _extract_discovered_team_colors(_build_state("sum"))
    return JsonResponse(list_data(discovered_colors))


@csrf_exempt
def api_logo_upload(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    file_obj = request.FILES.get("file")
    team_color = str(request.POST.get("teamColor", "")).strip()

    try:
        result = upload_logo(file_obj, team_color)
        return JsonResponse({"ok": True, **result})
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)


@csrf_exempt
def api_logo_assign(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = _json_body(request)
    team_color = str(data.get("teamColor", "")).strip()
    logo_id = str(data.get("logoId", "")).strip()

    try:
        assign_logo(team_color, logo_id)
        return JsonResponse({"ok": True})
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)


@csrf_exempt
def api_logo_delete(request: HttpRequest, logo_id: str) -> JsonResponse:
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        delete_logo(logo_id)
        return JsonResponse({"ok": True})
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)


def api_logo_file(request: HttpRequest, logo_id: str) -> HttpResponse:
    file_path = resolve_logo_path(logo_id)
    if file_path is None:
        return JsonResponse({"error": "Logo not found"}, status=404)

    return FileResponse(file_path.open("rb"))


def _build_state(score_mode: str) -> dict[str, Any]:
    ws_state = get_current_state()
    fallback_state = normalize_state(get_payload())
    status = client.status()

    if ws_state.get("players"):
        merged = ws_state
    else:
        merged = {
            "players": fallback_state.get("players", []),
            "teamScores": fallback_state.get("teamScores", {}),
            "teamScoresCompleted": fallback_state.get("teamScoresCompleted", {}),
            "raw": {},
        }

    if score_mode == "completed":
        merged["teamScores"] = dict(merged.get("teamScoresCompleted", {}))

    discovered_colors = _extract_discovered_team_colors(merged)
    merged["teamLogos"] = get_team_logo_urls(discovered_colors)

    merged["scoreMode"] = score_mode
    merged["ws"] = {
        "connected": status.get("connected", False),
        "lastError": status.get("lastError", ""),
        "lastMessageTs": status.get("lastMessageTs", 0),
        "machineIp": status.get("machineIp", ""),
        "workerAlive": status.get("workerAlive", False),
    }
    return merged


def _extract_discovered_team_colors(state: dict[str, Any]) -> list[str]:
    colors: set[str] = set()

    team_scores = state.get("teamScores", {})
    if isinstance(team_scores, dict):
        for key in team_scores.keys():
            color = str(key).strip()
            if color:
                colors.add(color)

    players = state.get("players", [])
    if isinstance(players, list):
        for player in players:
            if not isinstance(player, dict):
                continue
            color = str(player.get("color", "")).strip()
            if color:
                colors.add(color)

    return sorted(colors)


def _parse_score_mode(request: HttpRequest) -> str:
    score_mode = str(request.GET.get("teamMode", "sum")).strip().lower()
    if score_mode not in {"sum", "completed"}:
        return "sum"
    return score_mode


def _json_body(request: HttpRequest) -> dict[str, Any]:
    try:
        raw = request.body.decode("utf-8")
        if not raw:
            return {}
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return {}


def _build_command(action: str, uid: Optional[int], camera_number: Optional[int]) -> Optional[dict[str, Any]]:
    if action == "start_race":
        return {"command": "startrace"}
    if action == "abort_race":
        return {"command": "abortrace"}
    if action == "all_spectate":
        return {"command": "allspectate"}
    if action == "camera_spectate":
        return {"command": "cameramode", "mode": "spectate"}
    if action == "camera_fpv":
        return {"command": "cameramode", "mode": "fpv"}
    if action == "camera_player":
        if uid is None:
            return None
        return {"command": "cameraplayer", "uid": uid}
    if action == "camera_select":
        if camera_number is None:
            return None
        return {"command": "cameraselect", "number": camera_number}
    if action == "camera_reset":
        return {"command": "camerareset"}
    return None


def _to_int_or_none(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
