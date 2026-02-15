from threading import Lock
from typing import Any

_lock = Lock()
_machine_ip = ""
_last_payload: dict[str, Any] = {"players": []}
_current_state: dict[str, Any] = {
    "players": [],
    "teamScores": {},
    "teamScoresCompleted": {},
    "raw": {},
}
_uid_laps: dict[str, int] = {}
_completed_team_scores: dict[str, int] = {}


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


def get_current_state() -> dict[str, Any]:
    with _lock:
        return {
            "players": list(_current_state.get("players", [])),
            "teamScores": dict(_current_state.get("teamScores", {})),
            "teamScoresCompleted": dict(_current_state.get("teamScoresCompleted", {})),
            "raw": dict(_current_state.get("raw", {})),
        }


def ingest_velocidrone_event(event: dict[str, Any]) -> None:
    global _current_state

    with _lock:
        raw = dict(_current_state.get("raw", {}))
        for key, value in event.items():
            raw[key] = value

        race_status = raw.get("racestatus", {})
        if isinstance(race_status, dict):
            race_action = str(race_status.get("raceAction", "")).strip().lower()
            if race_action in {"started", "aborted", "finished", "reset"}:
                _uid_laps.clear()
                _completed_team_scores.clear()

        racedata = raw.get("racedata", {})
        players: list[dict[str, Any]] = []
        team_scores: dict[str, int] = {}

        if isinstance(racedata, dict):
            for player_name, details in racedata.items():
                if not isinstance(details, dict):
                    continue

                color = _normalize_color(str(details.get("colour", "#888888")))
                lap = _to_int(details.get("lap", 0))
                uid = str(details.get("uid", "")).strip()

                players.append(
                    {
                        "name": str(player_name),
                        "color": color,
                        "lap": lap,
                        "uid": uid,
                    }
                )

                team_scores[color] = team_scores.get(color, 0) + lap

                if uid:
                    previous_lap = _uid_laps.get(uid, 0)
                    if lap < previous_lap:
                        previous_lap = 0
                    if lap > previous_lap:
                        lap_gain = lap - previous_lap
                        _completed_team_scores[color] = _completed_team_scores.get(color, 0) + lap_gain
                    _uid_laps[uid] = lap

        _current_state = {
            "players": players,
            "teamScores": team_scores,
            "teamScoresCompleted": dict(_completed_team_scores),
            "raw": raw,
        }


def normalize_state(payload: dict[str, Any]) -> dict[str, Any]:
    players = payload.get("players", [])
    normalized_players: list[dict[str, Any]] = []
    team_scores: dict[str, int] = {}

    for entry in players:
        name = str(entry.get("name", "Unknown"))
        color = _normalize_color(str(entry.get("color", "#888888")))
        lap = _to_int(entry.get("lap", 0))
        uid = str(entry.get("uid", "")).strip()

        normalized_players.append(
            {
                "name": name,
                "color": color,
                "lap": lap,
                "uid": uid,
            }
        )
        team_scores[color] = team_scores.get(color, 0) + lap

    return {
        "players": normalized_players,
        "teamScores": team_scores,
        "teamScoresCompleted": {},
    }


def _normalize_color(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("#"):
        return cleaned
    if len(cleaned) in (6, 8):
        return f"#{cleaned}"
    return "#888888"


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
