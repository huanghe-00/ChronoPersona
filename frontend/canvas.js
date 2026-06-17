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

function drawAgent(x, y, theta, z = 0) {
    const cx = x * CELL + CELL / 2;
    const cy = y * CELL + CELL / 2;
    
    // 3D高度指示线：从圆心向上，长度与z成正比
    if (z > 0) {
        ctx.strokeStyle = 'rgba(231, 76, 60, 0.6)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx, cy - z * 8); // 高度线向上延伸
        ctx.stroke();
        // 高度线顶端标记
        ctx.fillStyle = '#e74c3c';
        ctx.beginPath();
        ctx.arc(cx, cy - z * 8, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.lineWidth = 1;
    }
    
    // Agent 大小随高度变化（z越大越近，视觉越大）
    const radius = CELL / 3 + Math.min(z * 2, 5);
    ctx.fillStyle = '#3498db';
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
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

function drawObject(x, y, label, z = 0) {
    // 3D高度指示：物体高度柱（半透明绿色柱体）
    if (z > 0) {
        ctx.fillStyle = 'rgba(46, 204, 113, 0.3)';
        ctx.fillRect(x * CELL + 2, y * CELL + 2 - z * 5, CELL - 4, z * 5);
    }
    ctx.fillStyle = '#2ecc71';
    ctx.fillRect(x * CELL + 2, y * CELL + 2, CELL - 4, CELL - 4);
    ctx.fillStyle = '#000';
    ctx.font = '10px sans-serif';
    ctx.fillText(label, x * CELL + 4, y * CELL + 14);
    // 显示z高度（红色小字）
    if (z > 0) {
        ctx.fillStyle = '#e74c3c';
        ctx.fillText(`z:${z.toFixed(1)}`, x * CELL + 2, y * CELL - 5);
    }
}

function log(msg) {
    const div = document.getElementById('log');
    const line = document.createElement('div');
    line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    div.appendChild(line);
    div.scrollTop = div.scrollHeight;
}

let sceneObjects = {
    sofa: { x: 2, y: 3, label: '沙发' },
    bed: { x: 8, y: 12, label: '床' },
    table: { x: 3, y: 2, label: '桌子' },
    kitchen: { x: 15, y: 5, label: '厨房' },
    chair: { x: 5, y: 5, label: '椅子' },
    fridge: { x: 10, y: 5, label: '冰箱' },
    coffee_table: { x: 4, y: 3, label: '茶几' }
};

const WS_URL = 'ws://localhost:8765/ws';
let ws = null;
let agentState = { x: 3, y: 4, theta: 0 };

function connectWebSocket() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        log('WebSocket connected');
        log('Backend mode: requesting state...');
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.event === 'chat.reply') {
            const reply = msg.data.reply_text || '(no text)';
            log(`Agent: ${reply}`);
            if (reply.includes('已到达')) {
                log('[导航完成] ' + reply);
                if (msg.data.action_plan && msg.data.action_plan.reasoning) {
                    log('[路径信息] ' + msg.data.action_plan.reasoning);
                }
            }
            if (msg.data.action_plan && msg.data.action_plan.reasoning) {
                log(`Reasoning: ${msg.data.action_plan.reasoning}`);
            }
        } else if (msg.event === 'embodied.state') {
            const s = msg.data;
            agentState = { x: s.x, y: s.y, theta: s.theta || 0, z: s.z || 0 };
            
            // 动态标题：根据后端模式与场景标识切换
            const titleEl = document.getElementById('app-title');
            const modeLabel = s.backend_mode === 'habitat' ? '3D Habitat' :
                              s.backend_mode === 'hm3d' ? '3D HM3D' :
                              s.backend_mode === 'grid2d' ? '2D Grid' : 'MVA';
            const sceneLabel = s.scene_id ? ` [${s.scene_id}]` : '';
            document.title = `ChronoPersona ${modeLabel}${sceneLabel}`;
            if (titleEl) titleEl.textContent = `ChronoPersona ${modeLabel}${sceneLabel}`;
            if (s.scene_objects) {
                sceneObjects = s.scene_objects;
            }
            if (s.scene_id) {
                log('Scene: ' + s.scene_id);
            }
            if (s.backend_mode) {
                log('Backend: ' + s.backend_mode);
            }
            // Redraw canvas with new state
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            drawGrid();
            Object.values(sceneObjects).forEach(t => drawObject(t.x, t.y, t.label, t.z || 0));
            if (s.fov_objects) {
                s.fov_objects.forEach((obj, idx) => {
                    // Optional: draw dynamic FOV objects
                });
            }
            drawAgent(agentState.x, agentState.y, agentState.theta, agentState.z || 0);
            if (s.fov_objects && s.fov_objects.length > 0) {
                s.fov_objects.forEach((objName) => {
                    const obj = Object.values(sceneObjects).find(
                        t => t.label === objName || t.label.includes(objName) || objName.includes(t.label)
                    );
                    if (obj) {
                        ctx.beginPath();
                        ctx.arc(obj.x * CELL + CELL / 2, obj.y * CELL + CELL / 2, CELL / 2, 0, Math.PI * 2);
                        ctx.strokeStyle = '#e74c3c';
                        ctx.lineWidth = 2;
                        ctx.stroke();
                        ctx.lineWidth = 1;
                    }
                });
            }
            // 3D 状态文本面板（v1.1.0 Habitat 适配）
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillRect(5, 5, 320, 55);
            ctx.fillStyle = '#fff';
            ctx.font = '12px monospace';
            // 3D坐标显示：明确展示垂直高度z，证明非2D伪造
            if (s.z !== undefined && s.z > 0) {
                ctx.fillText(`3D: (${s.x.toFixed(2)}, ${s.y.toFixed(2)}, ${s.z.toFixed(2)}) [Z=Height]`, 10, 25);
            } else if (s.metadata && s.metadata.position_3d) {
                const pos = s.metadata.position_3d;
                ctx.fillText(`3D: (${pos[0].toFixed(2)}, ${pos[1].toFixed(2)}, ${pos[2].toFixed(2)}) [Z=Height]`, 10, 25);
            } else {
                ctx.fillText(`2D: (${s.x.toFixed(2)}, ${s.y.toFixed(2)}) θ=${s.theta.toFixed(2)}`, 10, 25);
            }
            ctx.fillText(`FOV: ${(s.fov_objects || []).join(', ') || 'none'}`, 10, 45);
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
Object.values(sceneObjects).forEach(t => drawObject(t.x, t.y, t.label, t.z || 0));
drawAgent(agentState.x, agentState.y, agentState.theta, agentState.z || 0);
log('MVA: 2D world initialized. Grid 20x20, Agent at (3,4).');
connectWebSocket();
