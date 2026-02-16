let teamMode = 'sum';
let stream = null;
const isCompact = document.body.classList.contains('compact');

function renderPlayers(players, teamLogos) {
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
        left.className = 'player-left';
        if (player.color) {
            const chip = document.createElement('span');
            chip.className = 'color-chip';
            chip.style.backgroundColor = player.color;
            left.appendChild(chip);
        }
        const logoUrl = (teamLogos && player.color) ? teamLogos[player.color] : '';
        if (logoUrl) {
            const logo = document.createElement('img');
            logo.className = 'team-logo-inline';
            logo.src = logoUrl;
            logo.alt = 'Team logo';
            left.appendChild(logo);
        }

        const flag = player.finished ? ' 🏁' : '';
        let baseLabel = player.name;
        if (!isCompact && player.uid) {
            baseLabel = `${player.name} (UID ${player.uid})`;
        }
        const label = `${baseLabel}${flag}`;
        left.appendChild(document.createTextNode(label));

        const right = document.createElement('div');
        right.className = 'player-stats';
        const lap = Number(player.lap || 0);
        const gate = Number(player.gate || 0);
        right.textContent = `Lap: ${lap} Gate: ${gate}`;

        row.appendChild(left);
        row.appendChild(right);
        container.appendChild(row);
    });
}

function renderTeams(teamScores, teamLogos) {
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
        left.className = 'team-left';
        const chip = document.createElement('span');
        chip.className = 'color-chip';
        chip.style.backgroundColor = color;
        left.appendChild(chip);

        const logoUrl = teamLogos ? teamLogos[color] : '';
        if (logoUrl) {
            const logo = document.createElement('img');
            logo.className = 'team-logo-inline';
            logo.src = logoUrl;
            logo.alt = 'Team logo';
            left.appendChild(logo);
        }

        if (!isCompact) {
            left.appendChild(document.createTextNode(`Team ${color}`));
        }

        const right = document.createElement('div');
        right.className = 'team-score-wrap';

        const scoreLabel = document.createElement('div');
        scoreLabel.className = 'team-score-label';
        scoreLabel.textContent = 'Total Laps';

        const scoreValue = document.createElement('div');
        scoreValue.className = 'team-score-value';
        scoreValue.textContent = String(teamScores[color]);

        right.appendChild(scoreLabel);
        right.appendChild(scoreValue);

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
    const teamLogos = data.teamLogos || {};
    renderPlayers(data.players || [], teamLogos);
    renderTeams(data.teamScores || {}, teamLogos);

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
