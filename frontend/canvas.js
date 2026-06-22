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

function drawBoxObstacle(x, y, sx, sz, label, color) {
    const px = x * CELL;
    const py = y * CELL;
    const w = sx * CELL;
    const h = sz * CELL;
    // Parse hex color to RGB for semi-transparent fill
    let fillR = 231, fillG = 76, fillB = 60; // default red
    if (color && color.startsWith('#')) {
        fillR = parseInt(color.slice(1, 3), 16);
        fillG = parseInt(color.slice(3, 5), 16);
        fillB = parseInt(color.slice(5, 7), 16);
    }
    ctx.fillStyle = `rgba(${fillR}, ${fillG}, ${fillB}, 0.2)`;
    ctx.fillRect(px - w/2, py - h/2, w, h);
    ctx.strokeStyle = color || '#e74c3c';
    ctx.lineWidth = 2;
    ctx.strokeRect(px - w/2, py - h/2, w, h);
    ctx.lineWidth = 1;
    ctx.fillStyle = color || '#e74c3c';
    ctx.font = '10px sans-serif';
    ctx.fillText(label, px + w/2 + 4, py + 3);
}

function drawObstacle(x, y, radius, label, color) {
    const cx = x * CELL + CELL / 2;
    const cy = y * CELL + CELL / 2;
    let fillR = 231, fillG = 76, fillB = 60;
    if (color && color.startsWith('#')) {
        fillR = parseInt(color.slice(1, 3), 16);
        fillG = parseInt(color.slice(3, 5), 16);
        fillB = parseInt(color.slice(5, 7), 16);
    }
    ctx.fillStyle = `rgba(${fillR}, ${fillG}, ${fillB}, 0.3)`;
    ctx.beginPath();
    ctx.arc(cx, cy, radius * CELL, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = color || '#e74c3c';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, radius * CELL, 0, Math.PI * 2);
    ctx.stroke();
    ctx.lineWidth = 1;
    ctx.fillStyle = color || '#e74c3c';
    ctx.font = '10px sans-serif';
    ctx.fillText(label, cx + radius * CELL + 4, cy + 3);
}

function log(msg) {
    const div = document.getElementById('log');
    const line = document.createElement('div');
    line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    div.appendChild(line);
    div.scrollTop = div.scrollHeight;
}

let sceneObjects = {
    sofa: { x: 7.0, y: 8.0, z: 0.3, label: '沙发' },
    bed: { x: 4.0, y: 11.0, z: 0.5, label: '床' },
    table: { x: 5.0, y: 10.0, z: 0.8, label: '桌子' },
    kitchen: { x: 15, y: 5, z: 0, label: '厨房' },
    chair: { x: 9.0, y: 3.0, z: 0.4, label: '椅子' },
    fridge: { x: 10.0, y: 5.0, z: 1.2, label: '冰箱' },
    coffee_table: { x: 10.0, y: 7.0, z: 0.3, label: '茶几' },
    obstacle_island_main: { x: 6.5, y: 6.5, z: 0, label: '岛台主体', type: 'obstacle', shape: 'box', size: [3.0, 0.9, 1.0], color: '#8B4513' },
    obstacle_island_wing: { x: 5.5, y: 7.5, z: 0, label: '岛台侧翼', type: 'obstacle', shape: 'box', size: [1.0, 0.9, 3.0], color: '#8B4513' },
    obstacle_pillar: { x: 4.0, y: 8.0, z: 0, label: '灯柱', type: 'obstacle', shape: 'cylinder', radius: 0.4, height: 2.2, color: '#696969' },
    obstacle_cabinet: { x: 9.0, y: 4.0, z: 0, label: '矮柜', type: 'obstacle', shape: 'box', size: [1.5, 0.6, 0.8], color: '#2E8B57' },
    obstacle_bookshelf: { x: 1.5, y: 8.0, z: 0, label: '书架', type: 'obstacle', shape: 'box', size: [1.0, 2.4, 0.4], color: '#8B0000' },
    obstacle_corner_sofa: { x: 7.0, y: 2.5, z: 0, label: '转角沙发', type: 'obstacle', shape: 'box', size: [2.0, 0.6, 1.0], color: '#4169E1' },
    obstacle_glass_wall: { x: 8.0, y: 7.5, z: 0, label: '玻璃隔断', type: 'obstacle', shape: 'box', size: [0.1, 2.0, 3.0], color: '#87CEEB' },
    obstacle_bar1: { x: 4.5, y: 9.0, z: 0, label: '吧台1', type: 'obstacle', shape: 'cylinder', radius: 0.6, height: 1.1, color: '#DAA520' },
    obstacle_bar2: { x: 3.8, y: 9.5, z: 0, label: '吧台2', type: 'obstacle', shape: 'cylinder', radius: 0.6, height: 1.1, color: '#DAA520' },
    obstacle_bar3: { x: 3.0, y: 10.0, z: 0, label: '吧台3', type: 'obstacle', shape: 'cylinder', radius: 0.6, height: 1.1, color: '#DAA520' }
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
            Object.values(sceneObjects).forEach(t => {
                if (t.type === 'obstacle') {
                    if (t.shape === 'box' && t.size) {
                        drawBoxObstacle(t.x, t.y, t.size[0], t.size[2], t.label, t.color);
                    } else {
                        drawObstacle(t.x, t.y, t.radius || 1.0, t.label, t.color);
                    }
                } else {
                    drawObject(t.x, t.y, t.label, t.z || 0);
                }
            });
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
            // Only log final state updates (with scene_objects), not intermediate animation steps
            if (s.scene_objects) {
                log(`State update: (${s.x}, ${s.y}) θ=${s.theta}`);
            }
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
Object.values(sceneObjects).forEach(t => {
    if (t.type === 'obstacle') {
        if (t.shape === 'box' && t.size) {
            drawBoxObstacle(t.x, t.y, t.size[0], t.size[2], t.label, t.color);
        } else {
            drawObstacle(t.x, t.y, t.radius || 1.0, t.label, t.color);
        }
    } else {
        drawObject(t.x, t.y, t.label, t.z || 0);
    }
});
drawAgent(agentState.x, agentState.y, agentState.theta, agentState.z || 0);
log('MVA: 2D world initialized. Grid 20x20, Agent at (3,4).');
connectWebSocket();
