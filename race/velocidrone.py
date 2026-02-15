import json
import threading
import time
from typing import Any

from websocket import WebSocket, WebSocketConnectionClosedException, create_connection

from .state import ingest_velocidrone_event


class VelocidroneClient:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ws: WebSocket | None = None
        self._machine_ip = ""
        self._running = False
        self._thread: threading.Thread | None = None
        self._connected = False
        self._last_error = ""
        self._last_message_ts = 0.0

    def configure(self, machine_ip: str) -> None:
        ip = machine_ip.strip()
        with self._lock:
            self._machine_ip = ip

        self.start()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            ws = self._ws
            self._ws = None

        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    def send_command(self, payload: dict[str, Any]) -> bool:
        text = json.dumps(payload)
        with self._lock:
            ws = self._ws

        if ws is None:
            return False

        try:
            ws.send(text)
            return True
        except (WebSocketConnectionClosedException, OSError):
            self._set_connected(False)
            return False

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "machineIp": self._machine_ip,
                "connected": self._connected,
                "lastError": self._last_error,
                "lastMessageTs": self._last_message_ts,
            }

    def _set_connected(self, value: bool) -> None:
        with self._lock:
            self._connected = value
            if not value:
                self._ws = None

    def _set_error(self, value: str) -> None:
        with self._lock:
            self._last_error = value

    def _worker(self) -> None:
        ping_interval_seconds = 5.0
        reconnect_delay_seconds = 2.0
        last_ping_ts = 0.0

        while True:
            with self._lock:
                if not self._running:
                    return
                machine_ip = self._machine_ip
                ws = self._ws

            if not machine_ip:
                self._set_connected(False)
                time.sleep(1.0)
                continue

            if ws is None:
                try:
                    socket_url = f"ws://{machine_ip}:60003/velocidrone"
                    socket = create_connection(socket_url, timeout=2)
                    socket.settimeout(0.25)
                    with self._lock:
                        self._ws = socket
                        self._connected = True
                        self._last_error = ""
                    last_ping_ts = 0.0
                except Exception as error:
                    self._set_connected(False)
                    self._set_error(str(error))
                    time.sleep(reconnect_delay_seconds)
                    continue

            now = time.time()
            if now - last_ping_ts >= ping_interval_seconds:
                if not self.send_command({"command": "ping"}):
                    time.sleep(reconnect_delay_seconds)
                    continue
                last_ping_ts = now

            with self._lock:
                active_ws = self._ws

            if active_ws is None:
                time.sleep(0.2)
                continue

            try:
                raw_message = active_ws.recv()
                if not raw_message:
                    continue
                parsed = json.loads(raw_message)
                if isinstance(parsed, dict):
                    ingest_velocidrone_event(parsed)
                    with self._lock:
                        self._last_message_ts = time.time()
            except TimeoutError:
                continue
            except json.JSONDecodeError:
                continue
            except (WebSocketConnectionClosedException, OSError) as error:
                self._set_connected(False)
                self._set_error(str(error))
                time.sleep(reconnect_delay_seconds)


client = VelocidroneClient()
