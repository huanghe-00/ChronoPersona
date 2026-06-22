# Habitat + HM3D 联合具身演示指南

## 1. 快速启动

```bash
# 方式 A：自动探测（推荐，按机器环境自动选择最优后端）
cd ~/projects/ChronoPersona
python scripts/serve_mva.py --backend auto

# 方式 A+：指定场景 ID（自动从 dataset root 查找）
python scripts/serve_mva.py --backend auto --scene-id 00337-CFVBbU9Rsyb

# 方式 B：强制 Habitat 真 3D（需 habitat-sim + GPU/EGL + 场景文件）
# ⚠ 仅在具备 GPU/EGL 的机器上可用（如 RTX 5080 开发机）
# 启动时自动探测 EGL，若不可用则降级为 HM3D 轻量模式
HABITAT_SCENE=/path/to/scene.glb python scripts/serve_mva.py --backend habitat
# 或使用 scene-id:
python scripts/serve_mva.py --backend habitat --scene-id 00337-CFVBbU9Rsyb

# 方式 C：强制 HM3D 轻量 3D（trimesh，无需 GPU，任意机器可用）
python scripts/serve_mva.py --backend hm3d --scene-id 00337-CFVBbU9Rsyb

# 方式 D：强制 2D 网格（无数据集依赖，任意机器可用）
python scripts/serve_mva.py --backend 2d
```

**机器分工建议**：

| 机器 | 推荐后端 | 原因 |
|------|---------|------|
| 机器A（WSL2/无显示器） | `--backend hm3d` 或 `--backend 2d` | 无 EGL 上下文，Habitat 渲染不可用 |
| 机器B（RTX 5080 + 原生 Linux） | `--backend habitat` | GPU/EGL 可用，支持真 3D A* 导航 |

启动后访问：
- 2D 前端：http://localhost:8080 （`frontend/canvas.html`）
- 3D 前端：http://localhost:8080/threejs_viewer.html （需新建，见下）

## 2. 三态后端切换

| 后端 | 触发条件 | 说明 | 目标机器 |
|------|---------|------|---------|
| **T1: Habitat 真 3D** | `--backend habitat` + `--scene-id` 或 `HABITAT_SCENE` | 需 `habitat-sim` + GPU/EGL；A* navmesh 路径规划 + RGB-D/Semantic 传感器 | 机器B（5080） |
| **T2: HM3D 轻量 3D** | `--backend hm3d` 或自动探测 | 纯 `trimesh` 加载 `.basis.glb`，10 步直线插值导航；自动探测 navmesh 文件 | 任意机器 |
| **T3: 2D Grid** | `--backend 2d` 或前两者均失败时降级 | 20×20 网格，A* 寻路，FOV 锥形检测 | 任意机器 |

**降级链**：T1 → T2 → T3。启动时 HabitatAdapter.probe() 检测 EGL/GPU，若不可用则自动降级并提示："该场景支持真3D导航，但当前环境无EGL/GPU，已降级为HM3D轻量模式"。

## 3. 导航算法（Phase 1 优化）

### 3.1 算法架构

HM3DAdapter 导航已从**贪心几何绕行**升级为**3D-aware A* + 路径平滑**：

| 阶段 | 算法 | 能力 |
|------|------|------|
| **Phase 1a** | 3D-aware 占据栅格 | 障碍物高度 < 0.15m 可跨越；底部高于 1.7m 可钻过；其余必须绕行 |
| **Phase 1b** | 8-连通 A* | 0.5m 栅格上全局最短路径，欧氏距离启发式，对角移动防角切 |
| **Phase 1c** | 迭代捷径化平滑 | 3 轮 shortcutting 消除硬拐角，生成更自然的运动轨迹 |

### 3.2 与旧算法对比

| 能力 | 旧算法（贪心绕行） | 新算法（A* + 平滑） |
|------|-------------------|-------------------|
| 全局最优 | ❌ 顺序敏感，无回溯 | ✅ A* 保证最短路径 |
| 3D 避障 | ❌ 仅 X-Z 平面 | ✅ 高度可跨越/可钻过判定 |
| 路径平滑 | ❌ 硬折线 C0 连续 | ✅ 捷径化后更少拐角 |
| 完备性 | ❌ 最多 4 绕行点 | ✅ A* 完备（可达则必找到） |
| 绕行方向 | ❌ 贪心局部偏移 | ✅ 全局最优绕行 |

### 3.3 支持的导航指令

发送以下中文指令到前端输入框（或 WebSocket）：

| 指令示例 | 目标 | 预期坐标 | A* 绕行障碍 |
|---------|------|---------|------------|
| `去沙发` / `导航到沙发` / `请到沙发旁边` | 沙发 | (8, 6) | 岛台主体（全局最短绕行） |
| `去冰箱` / `导航到冰箱` | 冰箱 | (10, 4) | 矮柜 |
| `去床` | 床 | (4, 11) | 玻璃隔断+吧台群 |
| `慢慢靠近椅子` | 椅子 | (9, 3) | 转角沙发 |
| `导航到茶几` | 茶几 | (9, 5) | 岛台主体 |
| `去桌子` | 桌子 | (5, 10) | 玻璃隔断+岛台侧翼 |

**回复示例**：`Agent: 已到达沙发，共移动 N 步`（步数由 A* 路径长度决定，约 0.5m/步）

**普通动作步进动画（P1 修复）**：`approach_gently` / `retreat_slowly` / `turn_to_user` / `look_around` 等普通动作现在也会生成 5 步中间坐标（`_nav_path`），前端可观测平滑位移，不再出现位置跳跃。导航指令使用 A* + 平滑路径，步数由路径长度动态决定。广播逻辑同时计算移动方向 theta，动画朝向自然过渡。

## 4. 坐标语义约定

- **前端 2D 俯视图**：`x` = 水平轴，`y` = 深度轴（对应 3D 的 `z`）
- **前端 3D 高度**：`z` = 垂直高度（对应 3D 的 `y`）
- **后端统一**：`HM3DAdapter` / `HabitatAdapter` 均按此约定输出

## 5. 验证清单

1. 启动后浏览器 `F12` → Network → WS，确认连接 `ws://localhost:8765/ws`
2. 前端 `log` 区域立即显示 `Scene: 00337-CFVBbU9Rsyb`（初始状态推送）
3. 输入 `去沙发` → Agent 蓝点沿 A* 最短路径平滑移动至目标（步数由路径长度决定）
4. 左上面板显示 `3D: (2.00, 3.00, 0.00) [Z=Height]`
5. `make test` 中 `tests/test_embodied_joint.py` 6 个用例全绿（含 A* 避障 + 路径平滑验证）
6. 路径不再穿越岛台主体等障碍物（A* 完备性保证）

## 6. 排期关联

- **v1.1.0 穿插**：`serve_mva.py` 三态切换、`--backend auto`、静态路由 `/assets/hm3d/`
- **P1 已交付**：智能启动、自动探测、WebSocket 步进动画
- **P2 进行中**：`frontend/threejs_viewer.html` Three.js 真 3D 渲染
