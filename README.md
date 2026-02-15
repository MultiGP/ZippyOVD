# ZippyOVD

ZippyOVD is a Python/Django project for consuming Velocidrone race telemetry and rendering browser overlays ("race bug") plus an admin control page.

## Current scaffold

- Django project + `race` app
- Velocidrone websocket bridge (client thread):
  - Connects to `ws://<machine-ip>:60003/velocidrone`
  - Sends keepalive ping every 5 seconds
  - Ingests events and builds race bug state from `racedata`
- Admin page (`/race/admin/`) with:
  - Machine IP setting
  - Buttons: Start Race, Abort Race, All Spectate
  - Camera actions: Spectate/FPV/Reset, Camera Select, Camera Player (UID)
- Race bug page (`/race/bug/`) showing:
  - Player name + color + lap + UID
  - Team scores (team = shared color)
- API endpoints:
  - `GET/POST /race/api/config/`
  - `POST /race/api/action/`
  - `POST /race/api/telemetry/` (manual fallback ingest)
  - `GET /race/api/state/` (normalized display state + websocket status)

## Quick start

```bash
cd ZippyOVD
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open:
- Admin: http://127.0.0.1:8000/race/admin/
- Race Bug: http://127.0.0.1:8000/race/bug/

## Test telemetry

```bash
curl -X POST http://127.0.0.1:8000/race/api/telemetry/ \
  -H 'content-type: application/json' \
  -d '{
    "players": [
      {"name": "Pilot A", "color": "#ff3b30", "lap": 2},
      {"name": "Pilot B", "color": "#34c759", "lap": 1},
      {"name": "Pilot C", "color": "#ff3b30", "lap": 3}
    ]
  }'
```

## Next steps

1. Add real Velocidrone websocket client service.
2. Map admin actions to websocket command protocol.
3. Add auth for admin page.
4. Move in-memory state to Redis/db for multi-process safety.
