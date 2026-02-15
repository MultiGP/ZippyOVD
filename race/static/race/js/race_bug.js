let teamMode = 'sum';
let stream = null;

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
        if (player.color) {
            const chip = document.createElement('span');
            chip.className = 'color-chip';
            chip.style.backgroundColor = player.color;
            left.appendChild(chip);
        }
        const flag = player.finished ? ' 🏁' : '';
        const baseLabel = player.uid ? `${player.name} (UID ${player.uid})` : player.name;
        const label = `${baseLabel}${flag}`;
        left.appendChild(document.createTextNode(label));

        const right = document.createElement('div');
        const lap = Number(player.lap || 0);
        const gate = Number(player.gate || 0);
        right.textContent = `Lap: ${lap} Gate: ${gate}`;

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

function applyState(data) {
    renderPlayers(data.players || []);
    renderTeams(data.teamScores || {});

    const ws = data.ws || {};
    const connected = ws.connected ? 'connected' : 'disconnected';
    const error = ws.lastError ? ` | error: ${ws.lastError}` : '';
    document.getElementById('wsState').textContent = `WebSocket: ${connected}${error}`;
}

function connectStream() {
    if (stream) {
        stream.close();
    }

    stream = new EventSource(`/race/api/stream/?teamMode=${encodeURIComponent(teamMode)}`);
    stream.addEventListener('state', (event) => {
        const data = JSON.parse(event.data);
        applyState(data);
    });
    stream.onerror = () => {
        document.getElementById('wsState').textContent = 'State stream disconnected; retrying...';
    };
}

function bindEvents() {
    const select = document.getElementById('teamMode');
    if (!select) {
        return;
    }

    select.addEventListener('change', () => {
        setMode(select.value);
        connectStream();
    });
}

syncModeFromUrl();
bindEvents();
connectStream();
