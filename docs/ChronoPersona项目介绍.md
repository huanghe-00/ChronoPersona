# ChronoPersona 长期记忆 Agent 系统

**项目定位**：面向生产级 AI Companion 的分布式长期记忆与多角色人格架构验证项目  
**当前阶段**：MVA v1.5（Minimal Viable Architecture）  
**核心周期**：2026.05 – 2026.07（8 周 MVA 冲刺）  
**代码基线**：39 个测试文件 / 400+ 自动化断言 / 94% 语句覆盖率  

---

## 1. 项目概述

ChronoPersona 尝试解决当前 AI Companion 领域的三个结构性痛点：

1. **多端记忆冲突**：用户在手机与车机分别表达矛盾偏好时，传统"后写覆盖"导致信息永久丢失；
2. **角色人格串台**：同一用户在不同人格（心理咨询师 / 日常伴侣 / RPG 角色）下的记忆共享同一向量空间，造成隐私泄露与人格违和；
3. **记忆幻觉与检索失效**：纯向量 RAG 对时序推理（"后来怎样"）、因果回溯（"为什么焦虑"）和指代消解（"那个方案"）召回精度不足。

核心差异化不是依赖更大的 LLM，而是通过**分布式系统与数据库领域的成熟抽象**重构记忆层：自研轻量 LWW-CRDT 保证多端最终一致性，MVCC `branch_id` 物理隔离实现角色硬隔离，意图图谱将检索从"相似度匹配"升级为"结构化认知推理"。

---

## 2. 整体设计思路

### 2.1 认知仿生记忆分层

参考人类记忆的多_store 模型，设计 L0–L3 四级架构，每层有独立的存储语义、遗忘策略与并发边界：

| 层级 | 类比 | 存储内容 | 生命周期 | 隔离粒度 |
|------|------|---------|---------|---------|
| **L0** | 工作记忆缓存 | 用户画像、活跃偏好、情感状态 | 高频变化，定期刷盘 | Key 级 LWW-CRDT |
| **L1** | 当前对话上下文 | 最近 N 轮对话，动态压缩摘要 | Session 结束即物理丢弃 | Session 级隔离 |
| **L2** | 情景记忆 | 对话历史，向量索引，时间线 | 中期（指数衰减） | Session-MVCC 粗粒度 |
| **L3** | 语义记忆 | 概念层级、语义边、意图策略、Insight | 长期（反学习过滤） | Entity-MVCC 细粒度 |

### 2.2 两条核心架构原则

**原则一：物理隔离优于逻辑隔离**

- 所有数据操作显式传递 `branch_id`，禁止默认全局分支。切换人格等效于 `git checkout`：L1 即时清空，L2/L3 按分支物理隔离。
- 跨分支共享仅通过显式 `merge`，且需经过 `IPrivacyFilter` + `IRelevanceFilter` 双重过滤（接口已冻结，MVA 阶段以 Mock 占位）。

**原则二：结构化操作原语优于文本级合并**

- L3 语义记忆采用节点+边+属性的图模型，禁止文本级 diff/merge，规避结构化数据在自动合并时的"语法崩溃"问题。
- 多端冲突时，不在文本层消解，而是在图层标记 `CONTRADICTS` 边，保留双版本供上层仲裁。

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND / API                        │
│  • HTTP API (Python 脚本 serve_mva.py)                       │
│  • WebSocket Gateway (Stub，W7 骨架，W8+ 生产级)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      AGENT CORE 层                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │  Input  │→│  Intent │→│  Memory │→│  LLM    │       │
│  │  Node   │  │  Node   │  │  Node   │  │  Node   │       │
│  └─────────┘  └─────────┘  └─────────┘  └────┬────┘       │
│                                               │            │
│                              ┌────────────────┼────────┐  │
│                              ▼                ▼        │  │
│                        [ActionPlanner]    [Emotion     │  │
│                              │            Engine]       │  │
│                              ▼                │        │  │
│                        ┌──────────┐           │        │  │
│                        │  Output  │◄──────────┘        │  │
│                        │  Node    │                     │  │
│                        └──────────┘                     │  │
│                                                         │  │
│  StateMachineAgentCore（纯 Python 状态机，MVA 手写实现）    │  │
│  • 非 LangGraph 外部依赖，保障零依赖启动与可审计性          │  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      MEMORY SYSTEM 层                        │
│                                                              │
│  L0: LWW-CRDT Sync Layer                                     │
│  • HybridTimestamp (物理时间 + 逻辑计数器)                    │
│  • LWWMap: add-wins 语义，500ms clock-skew 检测              │
│  • SyncManager: 脏键追踪与 checkpoint 刷盘                   │
│                                                              │
│  L1: WorkingMemoryWindow                                     │
│  • 滑动窗口 (max_turns + token_limit 双阈值)                  │
│  • 动态压缩：超标时生成 CompressedSummary，保留 source_turn_ids│
│                                                              │
│  L2: Episodic Memory                                         │
│  • SimpleEpisodicStore（纯 Python，余弦相似度）               │
│  • FaissEpisodicStore（FAISS IndexFlatIP，分支隔离索引）      │
│  • MockBGEEmbedder（128d 确定性向量，MVA 占位）               │
│  • 近重复合并 (sim > 0.95) + access_count 30 天半衰期衰减      │
│                                                              │
│  L3: Semantic Memory (Intent Graph)                          │
│  • 内存 BFS 导航 (collections.deque)                         │
│  • 8 类语义边: MENTIONS / CAUSED / TEMPORAL_NEXT / ...        │
│  • SemanticEdge.status 反学习过滤 (active/deprecated/archived)│
│  • MVO 最小可行本体种子（200 概念 + 6 条硬编码意图策略）       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    EMBODIED PERCEPTION                       │
│  GridWorldAdapter（已真实实现）                               │
│  • 20×20 离散网格，(x, y, θ) 状态 + FOV 锥形视野               │
│  • 5 种高层 action_token → grid_2d 低层指令映射               │
│  • 文本化感知输出，注入 L1 Working Memory                     │
│  • ROS2 / MuJoCo 映射字典预留（接口就绪，适配器 W8+）          │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 核心模块已实现内容（MVA 真实落地）

### 4.1 L0 自研 CRDT：LWWMap + HybridTimestamp

**代码位置**：`chronopersona/memory_system/l0_crdt/`

- **LWWMap**：基于 `(physical_time, logical_counter, device_id)` 的全序比较，实现 add-wins 语义。非文本级 CRDT，专为 KV 结构化数据设计。
- **HybridTimestamp**：混合逻辑时钟，物理时间戳解决常规排序，逻辑计数器解决同一毫秒内多操作的并发。
- **Clock-skew 检测**：当两设备物理时间差 > 500ms，不自动覆盖，而是保留双版本，由上层 MVCC 创建 `CONTRADICTS` 边。
- **SyncManager**：管理脏键集合 (`dirty_keys`)，每 5 分钟或 Session 结束触发 checkpoint，将 L0 状态刷入持久化层接口。

**工程验证**：`tests/test_l0_crdt.py` 覆盖 HLC 比较、分支隔离、merge、checkpoint 与 delta 同步。

### 4.2 L1 工作记忆：滑动窗口与动态压缩

**代码位置**：`chronopersona/memory_system/l1_working/sliding_window.py`

- **双阈值触发**：同时监控轮次数 (`max_turns`) 与 Token 数 (`token_limit`)，任一超标即触发压缩。
- **压缩策略**：调用摘要节点（MVA 阶段以规则/模板模拟，接口预留 LLM 接入点）生成 `CompressedSummary`，替换原始轮次。摘要包含 `source_turn_ids` 追溯索引，原始内容仍可在 L2 反查。
- **Session 隔离**：所有数据绑定 `branch_id`，Session 结束即物理清空，绝不进入向量库。

### 4.3 L2 情景记忆：向量检索与差异化遗忘

**代码位置**：`chronopersona/memory_system/l2_episodic/`

- **双存储实现**：
  - `SimpleEpisodicStore`：纯 Python 实现，基于标准库 `math` 的余弦相似度，零外部依赖，适合 MVA 快速验证与 CI 环境。
  - `FaissEpisodicStore`：基于 `faiss-cpu` 的 `IndexFlatIP`（L2 归一化后等价 Cosine），按 `branch_id` 维护独立 FAISS 索引，严格物理隔离。
- **近重复合并**：写入前预检，若与已有记忆余弦相似度 > 0.95，触发合并（`access_count` 累加、保留较长内容、返回原 ID），避免 Top-K 被重复内容占据。
- **差异化遗忘**：检索排序引入 `importance × freq_boost` 权重，其中 `effective_access = access_count × exp(-days/30)`，防止高频旧记忆永久压制新信号。
- **幽灵记忆防御**：`FaissEpisodicStore` 维护 `_deleted_indices` 集合，被删除记忆的索引 ID 永久屏蔽，禁止通过旧 ID 召回。

### 4.4 L3 意图图谱：语义导航与反学习

**代码位置**：`chronopersona/memory_system/l3_semantic/intent_graph.py`

- **8 类语义边**：`IS_A`, `MENTIONS`, `TEMPORAL_NEXT`, `CAUSED`, `CONTRADICTS`, `BELONGS_TO`, `SIMILAR_TO`, `TRIGGERED_BY`。
- **意图导航**：将用户查询解析为 `temporal_trace` / `causal_explore` 等策略，按预定义的入口边类型与 `max_hops` 执行 BFS 遍历。
- **反学习 (Unlearning)**：`SemanticEdge` 包含 `status` 字段（`active` / `deprecated` / `archived`）。`deprecate_edge()` 即时将边加入 `_deprecated_edges` 集合，`navigate()` 与 `get_edges()` 均过滤该集合，无需物理删除即可实现知识过时处理。
- **MVA 边界**：当前为纯内存 Python BFS（`deque`）。PostgreSQL + Recursive CTE 持久化是 W8+ 生产级优化项，Schema 与 CTE 查询模板已设计完毕。

### 4.5 Agent Core：端到端状态机

**代码位置**：`chronopersona/agent_core/state_machine.py`

- **纯 Python 状态机**：Input → Intent → Memory → LLM → Output 五节点管线，MVA 阶段未引入 LangGraph 等外部依赖，确保零依赖启动与全链路可审计。
- **Persona Anchor 注入**：支持人格切换 (`switch_persona`)，Persona 配置包含 W++ 风格锚点、自然语言叙事、Ali:Chat 风格示例与结构化权限四层混合格式。
- **MVCC 分支隔离**：`run_turn` 与 `switch_persona` 均强制要求 `branch_id`，L1/L2/L3 按分支物理隔离。

### 4.6 情感引擎与 ActionPlanner

**代码位置**：`chronopersona/agent_core/action_planner.py`, `contracts/schemas/agent.py`

- **双层架构**：
  - **T0 规则层**：关键词匹配状态机（NEUTRAL → CURIOUS / EMPATHETIC → CONCERNED / REFLECTIVE），< 1ms 延迟，100% 可预期。
  - **LSTM 骨架**：监督学习回归器（`torch.nn.LSTM` + `MSELoss`），用于捕捉"连续多轮负面输入"等规则无法覆盖的时序模式。当前为接口与训练脚本骨架，训练闭环可在 CPU 完成。
- **置信度传播**：`EmotionState` 包含 `confidence` 字段。仅当 `confidence ≥ 0.7` 且 `current_state != NEUTRAL` 时，`_build_prompt` 才向 LLM Prompt 注入 `[Emotion State]` 文本段，避免模糊状态污染生成。
- **H1 时序修复**：`_update_emotion` 已前置于 `ActionPlanner.plan()` 调用之前，确保动作调制参数基于当前轮次最新情感状态。
- **Token→Action Bridge**：`ActionPlanner` 解析 LLM 输出为结构化 `ActionPlan`（`action_token` + `action_params` + `reasoning`），并查询 `EMOTION_BEHAVIOR_MODULATION` 表将情感状态翻译为物理行为参数（如 CONCERNED → `speed_multiplier=0.5`）。

### 4.7 具身智能：GridWorldAdapter

**代码位置**：`chronopersona/embodied/grid_world_adapter.py`

- **20×20 网格世界**：Agent 状态 `(x, y, θ)`，FOV 锥形视野计算（5 格距离，90°视角），边界钳制。
- **文本化感知**：视野内物体列表 + 相对位置 + 环境描述 → 文本化注入 L1 Working Memory。
- **跨本体映射字典**：`action_token`（如 `approach_gently`）通过 `translate_action_token` 映射为 `grid_2d` / `ros2_mobile` 低层指令。`grid_2d` 已真实实现；ROS2 / MuJoCo 映射字典已定义，适配器为 W8+ 预留。

### 4.8 评估框架

**代码位置**：`evaluation/`

- **A1–A11 对抗测试集**：覆盖记忆召回、跨 Session 关联、角色隔离、多端冲突、意图图谱导航、情感一致性、具身感知、跨本体一致性、动作可审计性、人格漂移检测等维度。
- **双轨输出**：
  - 轨道 A：pytest 语义断言（PASS/FAIL）。
  - 轨道 B：`evaluation/runner.py` 输出量化 JSON（Recall@5 / MRR / Persona Drift Score）。
- **PersonaDriftChecker**：基于 `MockBGEEmbedder` 计算 Agent 回复与 `style_examples` 的 embedding 均值相似度，< 0.75 触发漂移告警。

---

## 5. 未实现 / W8+ 规划内容

以下模块在 MVA 阶段已识别并文档化，但因排期或复杂度原因推迟：

| 模块 | MVA 状态 | W8+ 规划 | 备注 |
|------|---------|---------|------|
| **PostgreSQL CTE 持久化** | 纯内存 BFS | Recursive CTE + 复合索引 | Schema 与 CTE 模板已设计 |
| **LangGraph 迁移** | 手写纯 Python 状态机 | `StateGraph` 条件边路由 | P2 级优化，接口预留 |
| **真实模型路由** | MockModelRouter | Qwen3.5-9B 本地 + DS-V4-pro 云端 | 当前为 Mock，成本追踪接口已冻结 |
| **WebSocket 实时同步** | Stub | FastAPI + SocketIO 多端广播 | LWW-CRDT 操作日志格式已定义 |
| **Canvas 前端** | 无 | 极简 HTML Canvas 20×20 渲染 | W7 骨架，W8 联调 |
| **LSTM 训练闭环** | 骨架 + 训练脚本 | 100-200 条标注数据微调 | 监督学习，CPU 可跑；**RL 严格 PLACEHOLDER** |
| **Qdrant 分布式向量库** | FAISS 内存索引 | HNSW + 多副本 + 快照恢复 | P2 级优化 |
| **条件感知蒸馏器** | 无 | NLP 条件句识别 + `BehavioralRule.trigger` | P1 级，解决 Dreaming 条件剥离 |

---

## 6. 方案选型与关键取舍

### 6.1 为什么自研 CRDT，不用 Yjs？

Yjs 是通用文本协同库，面向富文本编辑器的字符级合并。ChronoPersona 的场景是**结构化 KV 存储**，需要：
1. 精确控制 HLC 比较逻辑（物理时间优先，逻辑计数器兜底）；
2. 嵌入 500ms clock-skew 检测与冲突标记；
3. 避免引入 Yjs 完整依赖树（MVA 追求轻量）。

自研 `LWWMap` 代码量 < 500 行，但完全掌控冲突语义。

### 6.2 为什么情感引擎用 T0 + LSTM，不用端到端 LLM？

1. **确定性**：T0 规则对"焦虑/难过"的响应 100% 可预期，LLM 会因 Prompt 变化漂移；
2. **资源效率**：T0 < 1ms，本地 Qwen3.5-9B ~100ms+；
3. **可审计**：规则触发可精确追溯 `trigger_reason`，LLM 黑盒难以调试；
4. **LSTM 定位**：仅作为 Layer 2 捕捉时序模式，**明确禁止在情感回归层引入 PPO/GRPO**（违反 AIDER.md PLACEHOLDER 红线，且任务类型错配）。

### 6.3 为什么 L3 先内存 BFS，不直接上 PostgreSQL CTE？

MVA 的核心目标是**验证意图图谱的检索语义正确性**（A6 场景 Recall@5 对比纯向量的提升）。在 1,000 节点 / 5,000 边规模下，Python `deque` BFS 延迟 < 10ms，足够支撑 MVA 评估。PostgreSQL CTE 持久化是生产级优化（W8+），当前已预留 `(source_id, edge_type)` 复合索引与 `MATERIALIZED` CTE hint 方案。

---

## 7. 工程纪律与质量保障

- **测试语义红线**：断言必须基于业务语义与架构文档，禁止基于实现内部细节或临时凑数。测试失败时默认假设为"实现缺陷"，未经审查禁止直接修改测试数据去迁就实现。
- **PLACEHOLDER 合规**：`[RL-PLACEHOLDER]`、`[VLA-PLACEHOLDER]` 等标记仅保留 TODO 注释与空接口，未实现任何复杂算法，确保代码库可编译、可测试、无失控依赖。
- **原子修改规则**：任何接口变更必须同步处理接口定义、具体实现、Mock、单元测试、`__init__.py` 导出。
- **核心守卫**：`tests/test_mock_pipeline.py`（31 项断言）是全项目回归基线，任何改动不得破坏其通过性。

---

## 8. 未来方向（Beyond MVA）

1. **记忆溯源链 (Provenance Chain)**：为 `MemoryEntry` / `Fact` 增加 `source_memory_ids` + `extraction_model` + `extraction_confidence`，支持逐条追溯"这条知识从哪来"。
2. **硬预算截断 (Hard Budget Throttle)**：实时 token 计数器，80% 预算时 T2/T3 降级为本地规则，100% 时关闭 Reflection Agent。
3. **跨分支记忆继承过滤器**：`main` 向子分支穿透时，通过 `IPrivacyFilter`（PII 正则 + NER）与 `IRelevanceFilter` 双重过滤，仅保留基础画像。
4. **检索结果可解释性**：为 `RetrievedContext.navigation_path` 填充详细路径（为什么召回这条），解决"Recall@5 高但用户感觉健忘"的截断感知问题。

---

## 9. 技术亮点总结

| 维度 | 关键数据 / 特性 |
|------|----------------|
| **分布式一致性** | 自研 LWW-CRDT，HLC 全序，500ms skew 检测，add-wins + 冲突保留 |
| **角色隔离** | `branch_id` 物理隔离，Session-MVCC + Entity-MVCC 混合粒度 |
| **检索语义** | 8 类语义边 + 8 类意图策略，纯向量 RAG 难以覆盖时序/因果/指代消解 |
| **具身解耦** | Token→Action Bridge，同一 `action_token` 零样本映射 grid_2d / ros2 / MuJoCo |
| **工程底座** | 400+ 自动化断言，94% 覆盖率，39 个测试文件，全链路 Mock 与真实实现并行 |
| **资源约束** | 万级 Token 配额下运行，FAISS 精确索引（MVA），SQLite 缓存，零 Docker 依赖启动 |

---

*文档版本: v1.0*  
*基线日期: 2026-05-22*  
*对应代码版本: MVA v1.5*
