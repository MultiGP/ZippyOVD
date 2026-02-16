let suppressIpRefreshUntil = 0;
let stream = null;
let latestState = null;
let logoData = { teams: [], logos: [], teamAssignments: {} };

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

function applyState(data) {
    latestState = data;

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

async function fetchLogos() {
    const response = await fetch('/race/api/logos/');
    logoData = await response.json();
    renderTeamLogoManager();
    renderStoredLogos();
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

async function assignLogo(teamColor, logoId) {
    const response = await fetch('/race/api/logos/assign/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ teamColor, logoId }),
    });

    const data = await response.json();
    if (!response.ok) {
        document.getElementById('actionStatus').textContent = data.error || 'Failed to assign logo';
        return;
    }

    document.getElementById('actionStatus').textContent = `Updated logo assignment for ${teamColor}.`;
    await fetchLogos();
}

async function uploadLogo(teamColor, fileInput) {
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
        document.getElementById('actionStatus').textContent = 'Select a PNG/JPG file first, then click Upload.';
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('teamColor', teamColor);

    const response = await fetch('/race/api/logos/upload/', {
        method: 'POST',
        body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
        document.getElementById('actionStatus').textContent = data.error || 'Failed to upload logo';
        return;
    }

    fileInput.value = '';
    document.getElementById('actionStatus').textContent = `Uploaded logo and assigned to ${teamColor}.`;
    await fetchLogos();
}

async function deleteLogo(logoId) {
    const response = await fetch(`/race/api/logos/${encodeURIComponent(logoId)}/`, {
        method: 'DELETE',
    });
    const data = await response.json();

    if (!response.ok) {
        document.getElementById('actionStatus').textContent = data.error || 'Failed to delete logo';
        return;
    }

    document.getElementById('actionStatus').textContent = 'Deleted unused logo.';
    await fetchLogos();
}

function renderTeamLogoManager() {
    const container = document.getElementById('teamLogoManager');
    if (!container) {
        return;
    }

    const discovered = new Set();
    ((latestState && latestState.players) || []).forEach((player) => {
        if (player.color) {
            discovered.add(player.color);
        }
    });
    Object.keys(((latestState && latestState.teamScores) || {})).forEach((color) => {
        if (color) {
            discovered.add(color);
        }
    });

    const teamColors = Array.from(discovered).sort();
    container.innerHTML = '';

    if (!teamColors.length) {
        const empty = document.createElement('span');
        empty.className = 'muted';
        empty.textContent = 'No teams discovered yet.';
        container.appendChild(empty);
        return;
    }

    teamColors.forEach((teamColor) => {
        const row = document.createElement('div');
        row.className = 'team-logo-row';

        const colorBlock = document.createElement('div');
        colorBlock.className = 'row';

        const chip = document.createElement('span');
        chip.className = 'color-chip';
        chip.style.backgroundColor = teamColor;

        const label = document.createElement('span');
        label.textContent = `Team ${teamColor}`;

        colorBlock.appendChild(chip);
        colorBlock.appendChild(label);

        const assignedLogoId = (logoData.teamAssignments || {})[teamColor] || '';
        const logoUrl = assignedLogoId ? `/race/api/logos/file/${assignedLogoId}/` : '';
        const preview = document.createElement('img');
        preview.className = 'team-logo-preview';
        preview.alt = 'Team logo';
        if (logoUrl) {
            preview.src = logoUrl;
        } else {
            preview.style.visibility = 'hidden';
        }

        const select = document.createElement('select');
        const noneOption = document.createElement('option');
        noneOption.value = '';
        noneOption.textContent = '(No logo)';
        select.appendChild(noneOption);
        (logoData.logos || []).forEach((logo) => {
            const option = document.createElement('option');
            option.value = logo.id;
            option.textContent = logo.name;
            select.appendChild(option);
        });
        select.value = assignedLogoId;

        const assignButton = document.createElement('button');
        assignButton.type = 'button';
        assignButton.textContent = 'Assign';
        assignButton.addEventListener('click', () => {
            assignLogo(teamColor, select.value);
        });

        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.png,.jpg,.jpeg,image/png,image/jpeg';

        const uploadButton = document.createElement('button');
        uploadButton.type = 'button';
        uploadButton.textContent = 'Upload';
        uploadButton.addEventListener('click', () => {
            uploadLogo(teamColor, fileInput);
        });

        row.appendChild(colorBlock);
        row.appendChild(preview);
        row.appendChild(select);
        row.appendChild(assignButton);
        row.appendChild(fileInput);
        row.appendChild(uploadButton);

        container.appendChild(row);
    });
}

function renderStoredLogos() {
    const container = document.getElementById('storedLogoManager');
    if (!container) {
        return;
    }

    container.innerHTML = '';
    const logos = logoData.logos || [];

    if (!logos.length) {
        const empty = document.createElement('span');
        empty.className = 'muted';
        empty.textContent = 'No stored logos yet.';
        container.appendChild(empty);
        return;
    }

    logos.forEach((logo) => {
        const row = document.createElement('div');
        row.className = 'stored-logo-row';

        const preview = document.createElement('img');
        preview.className = 'team-logo-preview';
        preview.src = logo.url;
        preview.alt = logo.name;

        const name = document.createElement('span');
        name.textContent = logo.name;

        const deleteButton = document.createElement('button');
        deleteButton.type = 'button';
        deleteButton.textContent = logo.inUse ? 'In use' : 'Delete';
        deleteButton.disabled = Boolean(logo.inUse);
        deleteButton.addEventListener('click', () => {
            deleteLogo(logo.id);
        });

        row.appendChild(preview);
        row.appendChild(name);
        row.appendChild(deleteButton);

        container.appendChild(row);
    });
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
fetchLogos();
setInterval(fetchLogos, 15000);
