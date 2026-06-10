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

const TARGETS = {
    sofa: { x: 2, y: 3, label: '沙发' },
    bed: { x: 8, y: 12, label: '床' },
    table: { x: 3, y: 2, label: '桌子' },
    kitchen: { x: 15, y: 5, label: '厨房' }
};

const WS_URL = 'ws://localhost:8765/ws';
let ws = null;
let agentState = { x: 3, y: 4, theta: 0 };

function connectWebSocket() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.event === 'chat.reply') {
            const reply = msg.data.reply_text || '(no text)';
            log(`Agent: ${reply}`);
            if (reply.includes('已到达')) {
                log('[导航完成] ' + reply);
            }
            if (msg.data.action_plan && msg.data.action_plan.reasoning) {
                log(`Reasoning: ${msg.data.action_plan.reasoning}`);
            }
        } else if (msg.event === 'embodied.state') {
            const s = msg.data;
            agentState = { x: s.x, y: s.y, theta: s.theta || 0 };
            // Redraw canvas with new state
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            drawGrid();
            Object.values(TARGETS).forEach(t => drawObject(t.x, t.y, t.label));
            if (s.fov_objects) {
                s.fov_objects.forEach((obj, idx) => {
                    // Optional: draw dynamic FOV objects
                });
            }
            drawAgent(agentState.x, agentState.y, agentState.theta);
            log(`State update: (${s.x}, ${s.y}) θ=${s.theta}`);
        }
    };

    ws.onclose = () => {
        log('WebSocket disconnected, retrying in 3s...');
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
        log('WebSocket error');
        console.error(err);
    };
}

function sendMsg() {
    const input = document.getElementById('msg');
    const text = input.value.trim();
    if (!text) return;
    log(`User: ${text}`);
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ message: text, branch_id: 'main' }));
    } else {
        log('WebSocket not connected, message queued');
    }
    input.value = '';
}

// Initial render
drawGrid();
Object.values(TARGETS).forEach(t => drawObject(t.x, t.y, t.label));
drawAgent(agentState.x, agentState.y, agentState.theta);
log('MVA: 2D world initialized. Grid 20x20, Agent at (3,4).');
connectWebSocket();
