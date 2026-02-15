async function fetchConfig() {
    const response = await fetch('/race/api/config/');
    const data = await response.json();
    const input = document.getElementById('machineIp');
    input.value = data.machineIp || '';
}

async function saveIp() {
    const machineIp = document.getElementById('machineIp').value.trim();
    const response = await fetch('/race/api/config/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ machineIp }),
    });
    const data = await response.json();
    document.getElementById('ipStatus').textContent = data.ok
        ? `Saved machine IP: ${data.machineIp}`
        : 'Failed to save machine IP';
}

async function sendAction(action) {
    const pilot = document.getElementById('pilotName').value.trim();
    const response = await fetch('/race/api/action/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, pilot }),
    });
    const data = await response.json();
    document.getElementById('actionStatus').textContent = data.ok
        ? `Queued action: ${data.action}${data.pilot ? ` (${data.pilot})` : ''}`
        : 'Action failed';
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
