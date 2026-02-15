import json
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from .state import get_machine_ip, get_payload, normalize_state, set_machine_ip, set_payload


def home(request: HttpRequest) -> HttpResponse:
    return redirect("race_admin")


def race_admin(request: HttpRequest) -> HttpResponse:
    return render(request, "race/admin.html")


def race_bug(request: HttpRequest) -> HttpResponse:
    return render(request, "race/race_bug.html")


def api_config(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"machineIp": get_machine_ip()})

    if request.method == "POST":
        data = _json_body(request)
        machine_ip = str(data.get("machineIp", "")).strip()
        set_machine_ip(machine_ip)
        return JsonResponse({"ok": True, "machineIp": machine_ip})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def api_action(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = _json_body(request)
    action = data.get("action", "")
    pilot = data.get("pilot", None)

    # TODO: Implement actual websocket command relay to Velocidrone.
    return JsonResponse(
        {
            "ok": True,
            "queued": True,
            "action": action,
            "pilot": pilot,
            "machineIp": get_machine_ip(),
            "note": "Command relay stubbed in initial scaffold.",
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
    payload = get_payload()
    return JsonResponse(normalize_state(payload))


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
