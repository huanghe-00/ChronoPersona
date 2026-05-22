const canvas = document.getElementById('world');
const ctx = canvas.getContext('2d');
const CELL = 20; // 20x20 grid on 400px canvas

function drawGrid() {
    ctx.strokeStyle = '#e0e0e0';
    for (let i = 0; i <= 20; i++) {
        ctx.beginPath();
        ctx.moveTo(i * CELL, 0);
        ctx.lineTo(i * CELL, 400);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i * CELL);
        ctx.lineTo(400, i * CELL);
        ctx.stroke();
    }
}

function drawAgent(x, y, theta) {
    const cx = x * CELL + CELL / 2;
    const cy = y * CELL + CELL / 2;
    ctx.fillStyle = '#3498db';
    ctx.beginPath();
    ctx.arc(cx, cy, CELL / 3, 0, Math.PI * 2);
    ctx.fill();
    // Facing direction
    ctx.strokeStyle = '#e74c3c';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(theta) * CELL * 0.8, cy + Math.sin(theta) * CELL * 0.8);
    ctx.stroke();
    ctx.lineWidth = 1;
}

function drawObject(x, y, label) {
    ctx.fillStyle = '#2ecc71';
    ctx.fillRect(x * CELL + 2, y * CELL + 2, CELL - 4, CELL - 4);
    ctx.fillStyle = '#000';
    ctx.font = '10px sans-serif';
    ctx.fillText(label, x * CELL + 4, y * CELL + 14);
}

function log(msg) {
    const div = document.getElementById('log');
    const line = document.createElement('div');
    line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    div.appendChild(line);
    div.scrollTop = div.scrollHeight;
}

function sendMsg() {
    const input = document.getElementById('msg');
    const text = input.value.trim();
    if (!text) return;
    log(`User: ${text}`);
    // MVA: simulate async response; W7+ integrates real WebSocket
    setTimeout(() => {
        log('Agent: (MVA stub — WebSocket integration pending)');
    }, 300);
    input.value = '';
}

// Initial render
drawGrid();
drawObject(2, 3, 'sofa');
drawObject(3, 2, 'table');
drawAgent(3, 4, 0);
log('MVA: 2D world initialized. Grid 20x20, Agent at (3,4).');
