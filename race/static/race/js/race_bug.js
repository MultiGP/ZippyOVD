let teamMode = 'sum';

function renderPlayers(players) {
    const container = document.getElementById('players');
    container.innerHTML = '';

    if (!players.length) {
        container.textContent = 'No player data yet.';
        return;
    }

    players.forEach((player) => {
        const row = document.createElement('div');
        row.className = 'player-row';

        const left = document.createElement('div');
        const chip = document.createElement('span');
        chip.className = 'color-chip';
        chip.style.backgroundColor = player.color;
        left.appendChild(chip);
        const label = player.uid ? `${player.name} (UID ${player.uid})` : player.name;
        left.appendChild(document.createTextNode(label));

        const right = document.createElement('div');
        right.textContent = `Lap ${player.lap}`;

        row.appendChild(left);
        row.appendChild(right);
        container.appendChild(row);
    });
}

function renderTeams(teamScores) {
    const container = document.getElementById('teams');
    container.innerHTML = '';

    const colors = Object.keys(teamScores || {});
    if (!colors.length) {
        container.textContent = 'No team scores yet.';
        return;
    }

    colors.forEach((color) => {
        const row = document.createElement('div');
        row.className = 'team-row';

        const left = document.createElement('div');
        const chip = document.createElement('span');
        chip.className = 'color-chip';
        chip.style.backgroundColor = color;
        left.appendChild(chip);
        left.appendChild(document.createTextNode(`Team ${color}`));

        const right = document.createElement('div');
        right.textContent = String(teamScores[color]);

        row.appendChild(left);
        row.appendChild(right);
        container.appendChild(row);
    });
}

function syncModeFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const mode = params.get('teamMode');
    if (mode === 'completed' || mode === 'sum') {
        teamMode = mode;
    }

    const select = document.getElementById('teamMode');
    if (select) {
        select.value = teamMode;
    }
}

function setMode(mode) {
    teamMode = mode === 'completed' ? 'completed' : 'sum';
    const params = new URLSearchParams(window.location.search);
    params.set('teamMode', teamMode);
    const nextUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, '', nextUrl);
}

async function refresh() {
    try {
        const response = await fetch(`/race/api/state/?teamMode=${encodeURIComponent(teamMode)}`);
        const data = await response.json();
        renderPlayers(data.players || []);
        renderTeams(data.teamScores || {});

        const ws = data.ws || {};
        const connected = ws.connected ? 'connected' : 'disconnected';
        const error = ws.lastError ? ` | error: ${ws.lastError}` : '';
        document.getElementById('wsState').textContent = `WebSocket: ${connected}${error}`;
    } catch (error) {
        console.error('Failed to refresh state', error);
    }
}

function bindEvents() {
    const select = document.getElementById('teamMode');
    if (!select) {
        return;
    }

    select.addEventListener('change', () => {
        setMode(select.value);
        refresh();
    });
}

syncModeFromUrl();
bindEvents();
refresh();
setInterval(refresh, 1000);
