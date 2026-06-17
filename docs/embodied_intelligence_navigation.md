# Habitat + HM3D 联合具身演示指南

## 1. 快速启动

```bash
# 方式 A：自动探测（推荐）
cd ~/projects/ChronoPersona
python scripts/serve_mva.py --backend auto

# 方式 B：强制指定 HM3D 轻量 3D
python scripts/serve_mva.py --backend hm3d

# 方式 C：强制 2D 网格（无数据集依赖）
python scripts/serve_mva.py --backend 2d
```

启动后访问：
- 2D 前端：http://localhost:8080 （`frontend/canvas.html`）
- 3D 前端：http://localhost:8080/threejs_viewer.html （需新建，见下）

## 2. 三态后端切换

| 后端 | 触发条件 | 说明 |
|------|---------|------|
| **Habitat 真 3D** | `HABITAT_SCENE=/path/to.glb python scripts/serve_mva.py` | 需 `habitat-sim` 安装，A* navmesh 路径规划 |
| **HM3D 轻量 3D** | 默认自动探测 `~/projects/.../example/00337-CFVBbU9Rsyb/` | 纯 `trimesh` 加载 `.basis.glb`，10 步直线插值导航 |
| **2D Grid** | 前两者均失败时降级 | 20×20 网格，A* 寻路，FOV 锥形检测 |

## 3. 支持的导航指令

发送以下中文指令到前端输入框（或 WebSocket）：

| 指令示例 | 目标 | 预期坐标 |
|---------|------|---------|
| `去沙发` / `导航到沙发` / `请到沙发旁边` | 沙发 | (2, 3) |
| `去冰箱` / `导航到冰箱` | 冰箱 | (10, 5) |
| `去床` | 床 | (8, 12) |
| `慢慢靠近椅子` | 椅子 | (5, 5) |
| `导航到茶几` | 茶几 | (4, 3) |

**回复示例**：`Agent: 已到达沙发，共移动 10 步`

## 4. 坐标语义约定

- **前端 2D 俯视图**：`x` = 水平轴，`y` = 深度轴（对应 3D 的 `z`）
- **前端 3D 高度**：`z` = 垂直高度（对应 3D 的 `y`）
- **后端统一**：`HM3DAdapter` / `HabitatAdapter` 均按此约定输出

## 5. 验证清单

1. 启动后浏览器 `F12` → Network → WS，确认连接 `ws://localhost:8765/ws`
2. 前端 `log` 区域立即显示 `Scene: 00337-CFVBbU9Rsyb`（初始状态推送）
3. 输入 `去沙发` → Agent 蓝点平滑移动 10 步至目标
4. 左上面板显示 `3D: (2.00, 3.00, 0.00) [Z=Height]`
5. `make test` 中 `tests/test_embodied_joint.py` 3 个用例全绿

## 6. 排期关联

- **v1.1.0 穿插**：`serve_mva.py` 三态切换、`--backend auto`、静态路由 `/assets/hm3d/`
- **P1 已交付**：智能启动、自动探测、WebSocket 步进动画
- **P2 进行中**：`frontend/threejs_viewer.html` Three.js 真 3D 渲染
