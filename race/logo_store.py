import json
import uuid
from pathlib import Path
from threading import Lock
from typing import Any, Optional

_STORE_LOCK = Lock()
_BASE_DIR = Path(__file__).resolve().parent.parent
_STORE_PATH = _BASE_DIR / "team_logo_store.json"
_LOGO_DIR = _BASE_DIR / "team_logos"


def list_data(discovered_colors: list[str]) -> dict[str, Any]:
    with _STORE_LOCK:
        store = _load_store_locked()

    assignments = dict(store.get("teamAssignments", {}))
    logos = store.get("logos", {})

    logo_items: list[dict[str, Any]] = []
    assigned_ids = set(assignments.values())
    for logo_id, info in logos.items():
        logo_items.append(
            {
                "id": logo_id,
                "name": str(info.get("originalName", logo_id)),
                "url": f"/race/api/logos/file/{logo_id}/",
                "inUse": logo_id in assigned_ids,
            }
        )

    teams: list[dict[str, Any]] = []
    for color in sorted({c for c in discovered_colors if c}):
        logo_id = assignments.get(color, "")
        teams.append(
            {
                "color": color,
                "logoId": logo_id,
                "logoUrl": f"/race/api/logos/file/{logo_id}/" if logo_id else "",
            }
        )

    return {
        "teams": teams,
        "logos": sorted(logo_items, key=lambda item: str(item.get("name", "")).lower()),
        "teamAssignments": assignments,
    }


def get_team_logo_urls(colors: list[str]) -> dict[str, str]:
    with _STORE_LOCK:
        store = _load_store_locked()

    assignments = store.get("teamAssignments", {})
    result: dict[str, str] = {}
    for color in colors:
        if not color:
            continue
        logo_id = str(assignments.get(color, "")).strip()
        if logo_id:
            result[color] = f"/race/api/logos/file/{logo_id}/"
    return result


def upload_logo(file_obj: Any, team_color: str) -> dict[str, Any]:
    if file_obj is None:
        raise ValueError("No file uploaded")

    original_name = str(getattr(file_obj, "name", "logo")).strip() or "logo"
    lower_name = original_name.lower()
    if lower_name.endswith(".png"):
        ext = ".png"
    elif lower_name.endswith(".jpg") or lower_name.endswith(".jpeg"):
        ext = ".jpg"
    else:
        raise ValueError("Only PNG/JPG files are supported")

    logo_id = uuid.uuid4().hex
    filename = f"{logo_id}{ext}"

    _LOGO_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _LOGO_DIR / filename

    with output_path.open("wb") as handle:
        for chunk in file_obj.chunks():
            handle.write(chunk)

    with _STORE_LOCK:
        store = _load_store_locked()
        logos = store.setdefault("logos", {})
        team_assignments = store.setdefault("teamAssignments", {})

        logos[logo_id] = {
            "filename": filename,
            "originalName": original_name,
        }

        color = _normalize_color(team_color)
        if color:
            team_assignments[color] = logo_id

        _save_store_locked(store)

    return {
        "logoId": logo_id,
        "url": f"/race/api/logos/file/{logo_id}/",
    }


def assign_logo(team_color: str, logo_id: str) -> None:
    color = _normalize_color(team_color)
    if not color:
        raise ValueError("Invalid team color")

    with _STORE_LOCK:
        store = _load_store_locked()
        logos = store.setdefault("logos", {})
        assignments = store.setdefault("teamAssignments", {})

        if not logo_id:
            assignments.pop(color, None)
            _save_store_locked(store)
            return

        if logo_id not in logos:
            raise ValueError("Logo not found")

        assignments[color] = logo_id
        _save_store_locked(store)


def delete_logo(logo_id: str) -> None:
    with _STORE_LOCK:
        store = _load_store_locked()
        logos = store.setdefault("logos", {})
        assignments = store.setdefault("teamAssignments", {})

        if logo_id not in logos:
            raise ValueError("Logo not found")

        if logo_id in set(assignments.values()):
            raise ValueError("Logo is currently assigned to a team")

        filename = str(logos[logo_id].get("filename", "")).strip()
        logos.pop(logo_id, None)
        _save_store_locked(store)

    if filename:
        file_path = _LOGO_DIR / filename
        if file_path.exists():
            file_path.unlink()


def resolve_logo_path(logo_id: str) -> Optional[Path]:
    with _STORE_LOCK:
        store = _load_store_locked()
        logos = store.get("logos", {})
        info = logos.get(logo_id)
        if not isinstance(info, dict):
            return None
        filename = str(info.get("filename", "")).strip()

    if not filename:
        return None

    file_path = _LOGO_DIR / filename
    if not file_path.exists():
        return None
    return file_path


def _normalize_color(value: str) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        return ""
    if cleaned.startswith("#"):
        return cleaned.upper()
    if len(cleaned) in (6, 8):
        return f"#{cleaned.upper()}"
    return ""


def _load_store_locked() -> dict[str, Any]:
    if not _STORE_PATH.exists():
        return {"logos": {}, "teamAssignments": {}}

    try:
        parsed = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            parsed.setdefault("logos", {})
            parsed.setdefault("teamAssignments", {})
            return parsed
    except (OSError, json.JSONDecodeError):
        pass

    return {"logos": {}, "teamAssignments": {}}


def _save_store_locked(store: dict[str, Any]) -> None:
    _STORE_PATH.write_text(json.dumps(store), encoding="utf-8")
