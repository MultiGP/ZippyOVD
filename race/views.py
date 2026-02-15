import json
from typing import Any, Optional

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

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
    ws_state = get_current_state()
    fallback_state = normalize_state(get_payload())
    status = client.status()

    score_mode = str(request.GET.get("teamMode", "sum")).strip().lower()
    if score_mode not in {"sum", "completed"}:
        score_mode = "sum"

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

    merged["scoreMode"] = score_mode
    merged["ws"] = {
        "connected": status.get("connected", False),
        "lastError": status.get("lastError", ""),
        "lastMessageTs": status.get("lastMessageTs", 0),
        "machineIp": status.get("machineIp", ""),
    }

    return JsonResponse(merged)


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
