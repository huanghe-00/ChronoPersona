# ChronoPersona 具身模块演示脚本

## 启动

```bash
python scripts/serve_mva.py
# 打开 http://localhost:8080
```

## 演示流程

1. **导航演示**：输入"去沙发旁边" → Agent 圆形从 (3,4) 移动到 (2,3)
2. **情感动作演示**：输入"你能慢慢靠近吗" → Agent 向当前朝向缓慢移动
3. **位置感知演示**：移动后输入"我饿了" → 回复内容随坐标变化
4. **FOV 高亮验证**：观察视野内物体红色描边
5. **动作可审计**：检查回复中的 `reasoning` 字段

## 附录：Habitat 3D 演示迁移（v1.1.0+）

### 环境准备

```bash
# 1. 安装 Habitat-sim
conda install habitat-sim -c conda-forge -c aihabitat

# 2. 下载场景文件（Replica 数据集，约 200MB）
mkdir -p data/scenes
wget https://github.com/facebookresearch/Replica-Dataset/releases/download/v1.0/apartment_0.glb \
  -O data/scenes/apartment_0.glb

# 3. 启动 3D 演示（装配自动切换）
export HABITAT_SCENE=data/scenes/apartment_0.glb
python scripts/serve_mva.py
```

### 3D 演示流程

1. **启动验证**：确认后端日志显示 `HabitatAdapter: simulator initialized with data/scenes/apartment_0.glb`
2. **3D 语义导航**：输入"去厨房" → `HabitatAdapter.navigate_to_object("厨房")` → A* 路径规划 → Agent 3D 坐标更新 → 前端显示新位置
3. **多模态感知**：输入"看看周围" → `get_visual_observation()` 返回 RGB/深度/语义掩码 → 前端面板显示语义标签列表（如 `sofa: 0.8m`, `table: 1.2m`）
4. **跨本体一致性验证**：同一套人格配置（`therapist`）在 3D 场景与 2D 网格中，`approach_gently` 的 `speed_mult` 调制参数一致（CONCERNED=0.5）

### 前端 3D 状态面板（最小适配）

替换 `canvas.js` 中的 2D 渲染为 3D 状态文本：

```javascript
} else if (msg.event === 'embodied.state') {
    const s = msg.data;
    log(`3D Position: (${s.x.toFixed(2)}, ${s.y.toFixed(2)}, ${s.z?.toFixed(2) || 0.0})`);
    log(`Rotation: ${s.theta?.toFixed(2) || 0.0} rad`);
    log(`Semantic FOV: ${s.fov_objects?.join(', ') || 'none'}`);
}
```

### 测试验证

```bash
# 3D 导航端到端测试
pytest tests/test_embodied_navigation_end_to_end.py -v -k "known_target"
# 预期：Habitat A* 导航成功，final_position 为真实 3D 场景坐标（非 2D 网格坐标）
```
