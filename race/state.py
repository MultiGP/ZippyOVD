import json
from pathlib import Path
from threading import Lock
from typing import Any

_lock = Lock()
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "race_config.json"
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
_player_meta_by_name: dict[str, dict[str, str]] = {}


def set_machine_ip(machine_ip: str) -> None:
    global _machine_ip
    with _lock:
        _machine_ip = machine_ip.strip()
        _save_config_locked()


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

        session_update = event.get("session", {})
        if isinstance(session_update, dict):
            session_player_name = str(session_update.get("playerName", "")).strip()
            if session_player_name:
                meta = _player_meta_by_name.get(session_player_name, {})
                _player_meta_by_name[session_player_name] = {
                    "name": session_player_name,
                    "color": str(meta.get("color", "")).strip(),
                    "uid": str(meta.get("uid", "")).strip(),
                }

        player_update = event.get("player", {})
        if isinstance(player_update, dict):
            player_name = str(player_update.get("PlayerName", "")).strip()
            if player_name:
                color = _normalize_color(str(player_update.get("playerColour", "")))
                meta = _player_meta_by_name.get(player_name, {})
                _player_meta_by_name[player_name] = {
                    "name": player_name,
                    "color": color if color else str(meta.get("color", "")).strip(),
                    "uid": str(meta.get("uid", "")).strip(),
                }

        race_status = raw.get("racestatus", {})
        if isinstance(race_status, dict):
            race_action = str(race_status.get("raceAction", "")).strip().lower()
            if race_action in {"started", "aborted", "finished", "reset"}:
                _uid_laps.clear()
                _completed_team_scores.clear()

        racedata = raw.get("racedata", {})
        race_rows: dict[str, dict[str, Any]] = {}
        team_scores: dict[str, int] = {}

        if isinstance(racedata, dict):
            for player_name, details in racedata.items():
                if not isinstance(details, dict):
                    continue

                normalized_name = str(player_name)
                color = _normalize_color(str(details.get("colour", "")))
                lap = _to_int(details.get("lap", 0))
                uid = str(details.get("uid", "")).strip()
                gate = _to_int(details.get("gate", 0))

                finished_value = str(details.get("finished", "")).strip().lower()
                is_finished = finished_value in {"true", "1", "yes"}

                race_rows[normalized_name] = {
                    "name": normalized_name,
                    "color": color,
                    "lap": lap,
                    "gate": gate,
                    "uid": uid,
                    "finished": is_finished,
                }

                if color:
                    team_scores[color] = team_scores.get(color, 0) + lap

                meta = _player_meta_by_name.get(normalized_name, {})
                _player_meta_by_name[normalized_name] = {
                    "name": normalized_name,
                    "color": color,
                    "uid": uid if uid else str(meta.get("uid", "")).strip(),
                }

                if uid:
                    previous_lap = _uid_laps.get(uid, 0)
                    if lap < previous_lap:
                        previous_lap = 0
                    if lap > previous_lap:
                        lap_gain = lap - previous_lap
                        _completed_team_scores[color] = _completed_team_scores.get(color, 0) + lap_gain
                    _uid_laps[uid] = lap

        players: list[dict[str, Any]] = list(race_rows.values())

        for player_name, meta in _player_meta_by_name.items():
            if player_name in race_rows:
                continue
            players.append(
                {
                    "name": player_name,
                    "color": _normalize_color(str(meta.get("color", ""))),
                    "lap": 0,
                    "gate": 0,
                    "uid": str(meta.get("uid", "")).strip(),
                    "finished": False,
                }
            )

        players.sort(key=lambda row: row.get("name", "").lower())

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
        color = _normalize_color(str(entry.get("color", "")))
        lap = _to_int(entry.get("lap", 0))
        uid = str(entry.get("uid", "")).strip()
        gate = _to_int(entry.get("gate", 0))

        finished = bool(entry.get("finished", False))

        normalized_players.append(
            {
                "name": name,
                "color": color,
                "lap": lap,
                "gate": gate,
                "uid": uid,
                "finished": finished,
            }
        )
        if color:
            team_scores[color] = team_scores.get(color, 0) + lap

    return {
        "players": normalized_players,
        "teamScores": team_scores,
        "teamScoresCompleted": {},
    }


def _normalize_color(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("#"):
        return cleaned
    if len(cleaned) in (6, 8):
        return f"#{cleaned}"
    return ""


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _save_config_locked() -> None:
    try:
        payload = {"machineIp": _machine_ip}
        _CONFIG_PATH.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass


def _load_config() -> None:
    global _machine_ip

    try:
        if not _CONFIG_PATH.exists():
            return

        parsed = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            _machine_ip = str(parsed.get("machineIp", "")).strip()
    except (OSError, json.JSONDecodeError):
        return


_load_config()
