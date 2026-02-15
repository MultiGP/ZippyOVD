from threading import Lock
from typing import Any

_lock = Lock()
_machine_ip = ""
_last_payload: dict[str, Any] = {"players": []}


def set_machine_ip(machine_ip: str) -> None:
    global _machine_ip
    with _lock:
        _machine_ip = machine_ip.strip()


def get_machine_ip() -> str:
    with _lock:
        return _machine_ip


def set_payload(payload: dict[str, Any]) -> None:
    global _last_payload
    with _lock:
        _last_payload = payload


def get_payload() -> dict[str, Any]:
    with _lock:
        return dict(_last_payload)


def normalize_state(payload: dict[str, Any]) -> dict[str, Any]:
    players = payload.get("players", [])
    normalized_players: list[dict[str, Any]] = []
    team_scores: dict[str, int] = {}

    for entry in players:
        name = str(entry.get("name", "Unknown"))
        color = str(entry.get("color", "#888888"))
        lap = int(entry.get("lap", 0))
        normalized_players.append(
            {
                "name": name,
                "color": color,
                "lap": lap,
            }
        )
        team_scores[color] = team_scores.get(color, 0) + lap

    return {
        "players": normalized_players,
        "teamScores": team_scores,
    }
