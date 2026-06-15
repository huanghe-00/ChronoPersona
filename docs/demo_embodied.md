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

### 3D 演示状态

- 代码状态：✅ `HabitatAdapter` 已真实实现，双轨切换就绪，**优雅降级已落地**
- 场景文件：🟡 需手动下载 Replica/Matterport3D 场景（受数据集分发协议限制，**不在 Git LFS 中**）
- 验证方法：设置 `HABITAT_SCENE=path/to/scene.glb` 启动，确认日志显示 `Using HabitatAdapter (3D)`
- 降级保障：若 `habitat_sim` 未安装或场景文件无效，服务自动回退到 `GridWorldAdapter (2D)`，**不阻塞启动**

### 环境准备

```bash
# 1. 安装 Habitat-sim（可选，未安装时自动降级到 2D）
conda install habitat-sim -c conda-forge -c aihabitat

# 2. 获取场景文件（三选一）
#    方案 A：检查 habitat-sim 自带测试场景（最快）
python -c "
import habitat_sim, os
sim_dir = os.path.dirname(habitat_sim.__file__)
for root, dirs, files in os.walk(sim_dir):
    for f in files:
        if f.endswith('.glb') or f.endswith('.ply'):
            print(os.path.join(root, f))
" | head -10
#    若有输出，直接复制路径作为 HABITAT_SCENE

#    方案 B：Replica 官方下载（需注册同意使用协议）
#    访问 https://github.com/facebookresearch/Replica-Dataset
#    按指引下载 apartment_0.glb（约 200MB）
mkdir -p data/scenes
#    将下载的 .glb 文件放入 data/scenes/

#    方案 C：占位符验证 3D 链路（闭环推荐，不阻塞演示）
mkdir -p data/scenes
touch data/scenes/apartment_0.glb
#    占位符仅验证代码走到 _ensure_sim，服务会优雅降级到 2D

# 3. 启动 3D 演示（装配自动切换 + 优雅降级）
export HABITAT_SCENE=data/scenes/apartment_0.glb
python scripts/serve_mva.py
#    若场景有效：日志显示 "Using HabitatAdapter (3D) with scene: ..."
#    若场景无效或 habitat_sim 未安装：日志显示 "Falling back to GridWorldAdapter (2D): ..."
```

### 3D 演示流程（场景文件就绪后）

1. **启动验证**：确认后端日志显示 `Using HabitatAdapter (3D) with scene: ...`（若显示降级信息则 2D 演示仍可用）
2. **3D 语义导航**：输入"去沙发"（或英文"sofa"）→ `HabitatAdapter.navigate_to_object` 匹配 `sofa` 类别 → A* 路径规划 → Agent 3D 坐标更新 → 前端显示新位置
   - 可用目标：沙发(sofa)、床(bed)、桌子(table)、椅子(chair)、冰箱(fridge)、茶几(coffee_table)
   - 输入"去厨房"将返回"无法找到"（Replica 场景类别需与映射表匹配）
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
# 3D 导航端到端测试（需真实场景文件）
pytest tests/test_embodied_navigation_end_to_end.py -v -k "known_target"
# 预期：Habitat A* 导航成功，final_position 为真实 3D 场景坐标（非 2D 网格坐标）

# 优雅降级验证（无需场景文件）
unset HABITAT_SCENE
python scripts/serve_mva.py
# 预期：日志显示 "Using GridWorldAdapter (2D)"，2D 演示正常可用

# HabitatAdapter 合约测试（无需场景文件）
pytest tests/test_habitat_adapter.py -v
# 预期：所有合约测试通过，3D 方法正确抛出 NotImplementedError
```
