function setPilotOptions(players) {
    const select = document.getElementById('pilotUid');
    const current = select.value;
    select.innerHTML = '';

    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Select pilot UID';
    select.appendChild(placeholder);

    (players || []).forEach((player) => {
        if (!player.uid) {
            return;
        }

        const option = document.createElement('option');
        option.value = String(player.uid);
        option.textContent = `${player.name} (UID ${player.uid})`;
        select.appendChild(option);
    });

    if (current) {
        select.value = current;
    }
}

async function fetchConfig() {
    const response = await fetch('/race/api/config/');
    const data = await response.json();
    const input = document.getElementById('machineIp');
    input.value = data.machineIp || '';

    const wsStatus = document.getElementById('wsStatus');
    const connected = data.wsConnected ? 'connected' : 'disconnected';
    const errorText = data.wsLastError ? ` | error: ${data.wsLastError}` : '';
    wsStatus.textContent = `WebSocket: ${connected}${errorText}`;

    const stateResponse = await fetch('/race/api/state/');
    const stateData = await stateResponse.json();
    setPilotOptions(stateData.players || []);
}

async function saveIp() {
    const machineIp = document.getElementById('machineIp').value.trim();
    const response = await fetch('/race/api/config/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ machineIp }),
    });
    const data = await response.json();

    if (data.ok) {
        document.getElementById('ipStatus').textContent = `Saved machine IP: ${data.machineIp}`;
    } else {
        document.getElementById('ipStatus').textContent = 'Failed to save machine IP';
    }

    await fetchConfig();
}

async function sendAction(action) {
    const uidValue = document.getElementById('pilotUid').value.trim();
    const numberValue = document.getElementById('cameraNumber').value.trim();

    const requestPayload = { action };
    if (uidValue !== '') {
        requestPayload.uid = Number(uidValue);
    }
    if (numberValue !== '') {
        requestPayload.number = Number(numberValue);
    }

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

    await fetchConfig();
}

function bindEvents() {
    document.getElementById('saveIp').addEventListener('click', saveIp);

    document.querySelectorAll('button[data-action]').forEach((button) => {
        button.addEventListener('click', () => {
            const action = button.getAttribute('data-action');
            sendAction(action);
        });
    });
}

fetchConfig();
bindEvents();
setInterval(fetchConfig, 5000);
