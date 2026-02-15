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
        left.appendChild(document.createTextNode(player.name));

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

async function refresh() {
    try {
        const response = await fetch('/race/api/state/');
        const data = await response.json();
        renderPlayers(data.players || []);
        renderTeams(data.teamScores || {});
    } catch (error) {
        console.error('Failed to refresh state', error);
    }
}

refresh();
setInterval(refresh, 1000);
