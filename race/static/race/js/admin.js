function setPilotButtons(players) {
    const container = document.getElementById('pilotCameraButtons');
    container.innerHTML = '';

    const allPlayers = players || [];
    if (!allPlayers.length) {
        const empty = document.createElement('span');
        empty.className = 'muted';
        empty.textContent = 'No pilots available yet.';
        container.appendChild(empty);
        return;
    }

    allPlayers.forEach((player) => {
        const button = document.createElement('button');
        button.type = 'button';

        if (player.uid) {
            button.textContent = `${player.name} (UID ${player.uid})`;
            button.addEventListener('click', () => {
                sendAction('camera_player', { uid: String(player.uid) });
            });
        } else {
            button.textContent = `${player.name} (UID pending)`;
            button.disabled = true;
            button.title = 'UID not available yet from racedata';
        }

        container.appendChild(button);
    });
}

let suppressIpRefreshUntil = 0;
let stream = null;

function applyState(data) {
    const input = document.getElementById('machineIp');
    const now = Date.now();
    const isTypingIp = document.activeElement === input;
    if (!isTypingIp && now >= suppressIpRefreshUntil) {
        input.value = (data.ws && data.ws.machineIp) || '';
    }

    const ws = data.ws || {};
    const wsStatus = document.getElementById('wsStatus');
    const connected = ws.connected ? 'connected' : 'disconnected';
    const worker = ws.workerAlive ? 'worker:alive' : 'worker:dead';
    const messageAge = ws.lastMessageTs
        ? Math.floor(Date.now() / 1000 - Number(ws.lastMessageTs))
        : null;
    const ageText = messageAge === null ? ' | no messages yet' : ` | last message ${messageAge}s ago`;
    const errorText = ws.lastError ? ` | error: ${ws.lastError}` : '';
    wsStatus.textContent = `WebSocket: ${connected} | ${worker}${ageText}${errorText}`;

    setPilotButtons(data.players || []);
}

function connectStream() {
    if (stream) {
        stream.close();
    }

    stream = new EventSource('/race/api/stream/?teamMode=sum');
    stream.addEventListener('state', (event) => {
        const data = JSON.parse(event.data);
        applyState(data);
    });
    stream.onerror = () => {
        document.getElementById('wsStatus').textContent = 'WebSocket status stream disconnected; retrying...';
    };
}

async function saveIp() {
    const machineIp = document.getElementById('machineIp').value.trim();

    try {
        const response = await fetch('/race/api/config/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ machineIp }),
        });

        if (!response.ok) {
            document.getElementById('ipStatus').textContent = `Failed to save machine IP (HTTP ${response.status})`;
            return;
        }

        const data = await response.json();
        if (data.ok) {
            document.getElementById('ipStatus').textContent = `Saved machine IP: ${data.machineIp}`;
        } else {
            document.getElementById('ipStatus').textContent = 'Failed to save machine IP';
        }
    } catch (error) {
        document.getElementById('ipStatus').textContent = `Failed to save machine IP: ${error}`;
    }
}

async function sendAction(action, extraPayload = {}) {
    const requestPayload = { action, ...extraPayload };

    const response = await fetch('/race/api/action/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload),
    });
    const data = await response.json();

    if (data.ok) {
        const queuedState = data.queued ? 'sent' : 'not sent (socket offline)';
        document.getElementById('actionStatus').textContent = `Action ${data.action}: ${queuedState}`;
    } else {
        document.getElementById('actionStatus').textContent = data.error || 'Action failed';
    }
}

function bindEvents() {
    document.getElementById('saveIp').addEventListener('click', saveIp);

    const machineIpInput = document.getElementById('machineIp');
    machineIpInput.addEventListener('input', () => {
        suppressIpRefreshUntil = Date.now() + 10000;
    });

    document.querySelectorAll('button[data-action]').forEach((button) => {
        button.addEventListener('click', () => {
            const action = button.getAttribute('data-action');
            const cameraNumber = button.getAttribute('data-camera-number');
            if (cameraNumber) {
                sendAction(action, { number: Number(cameraNumber) });
                return;
            }
            sendAction(action);
        });
    });
}

bindEvents();
connectStream();
