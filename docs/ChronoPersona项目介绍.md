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

---

## 10. 高频技术问答与深度追问

以下问答基于项目真实代码实现整理，用于技术评审与深度交流场景。

### 10.1 分布式一致性与 CRDT

**Q: 为什么选择自研 LWW-CRDT，而非直接采用 Yjs 或 Automerge？**

**A:** Yjs 是面向富文本协同的字符级 CRDT，其合并语义针对文本编辑器的插入/删除操作优化。ChronoPersona 的 L0 层是结构化 KV 存储（用户画像、活跃偏好、情感状态），需要：
1. 精确控制 `(physical_time, logical_counter, device_id)` 的全序比较逻辑；
2. 嵌入 500ms clock-skew 检测与冲突标记（`CONTRADICTS` 边），这是文本 CRDT 不具备的语义；
3. 避免引入 Yjs 完整的依赖树（MVA 追求零外部依赖启动）。

自研 `LWWMap` 代码量 < 500 行，但完全掌控 add-wins 语义与 HLC 逻辑时钟。

**追问：500ms 的 clock-skew 容忍阈值如何确定？如果生产环境出现更大偏差怎么办？**

**A:** 500ms 是 MVA 阶段基于"同一用户短时间内在两设备操作"的场景假设设定的经验值。物理时间差在此范围内时，信任 HLC 全序比较执行 add-wins；超出时，系统不自动覆盖，而是保留双版本并标记 `SUSPECTED_SKEW`，由上层创建 `CONTRADICTS` 语义边供 LLM 仲裁或向用户确认。生产环境可通过配置文件调整该阈值，且 NTP 同步是设备启动强制项。

### 10.2 MVCC 与角色隔离

**Q: `branch_id` 物理隔离具体如何落地？切换人格时记忆如何不串台？**

**A:** 所有数据操作（`add`/`retrieve`/`navigate`/`set`）强制显式传递 `branch_id`，接口层面禁止默认全局分支。具体隔离机制：
- **L1 Working Memory**：绑定 `branch_id`，session 结束即物理丢弃，切换人格时 L1 即时清空；
- **L2 Episodic**：`FaissEpisodicStore` 按 `branch_id` 维护独立 FAISS 索引，`SimpleEpisodicStore` 按 `branch_id` 字典隔离；
- **L3 Semantic**：`IntentGraph` 所有边与节点均存储 `branch_id`，导航时严格过滤。

`StateMachineAgentCore.switch_persona()` 的内部逻辑等效于 `git checkout`：加载目标 branch 的 L0 状态 + L2 snapshot + L3 实体指针，当前会话上下文重置。

**追问：如果用户希望在"心理咨询师"人格下复用"日常伴侣"的基础画像（如昵称），如何实现？**

**A:** 跨分支共享仅通过显式 `merge` 操作，且必须经过 `IPrivacyFilter` + `IRelevanceFilter` 双重过滤（接口已冻结，MVA 阶段以 Mock 占位）。`main` 分支向 `therapist` 穿透时，仅保留基础画像（姓名、通用偏好），医疗记录 / 剧情设定等敏感信息被过滤器拦截。该流程在 `docs/requirements.md` 中已完整设计，MVA 阶段通过 `tests/test_a4_a5.py` 验证隔离有效性。

### 10.3 意图图谱与检索

**Q: MVA 阶段 Intent Graph 使用纯内存 Python BFS，能否支撑生产环境？**

**A:** MVA 的核心目标是**验证意图图谱的检索语义正确性**（A6 场景 Recall@5 对比纯向量的提升）。在 1,000 节点 / 5,000 边规模下，`collections.deque` BFS 延迟 < 10ms，足够支撑 MVA 评估与演示。生产级持久化方案（PostgreSQL + Recursive CTE）是 W8+ 优化项，Schema 与 CTE 查询模板已设计完毕，当前代码已预留 `(source_id, edge_type)` 复合索引与 `MATERIALIZED` CTE hint 方案。

**追问：反学习（Unlearning）的实现机制是什么？物理删除还是逻辑标记？**

**A:** 逻辑标记，禁止物理删除以保留审计链。`SemanticEdge` 包含 `status` 字段（`active` / `deprecated` / `archived`）。调用 `deprecate_edge()` 时，边被加入 `_deprecated_edges` 集合且 `status` 同步更新；`navigate()` 与 `get_edges()` 均过滤该集合，实现即时反学习。该机制已通过 `tests/test_l3_unlearning.py` 验证。

### 10.4 情感引擎与具身智能

**Q: T0 规则引擎如何保证确定性？为何不信任 LLM 直接做情感分类？**

**A:** T0 规则引擎基于关键词匹配状态机（NEUTRAL → CURIOUS / EMPATHETIC → CONCERNED / REFLECTIVE），延迟 < 1ms，对"焦虑/难过"等关键词的响应 100% 可预期。LLM 会因 Prompt 变化、上下文长度、温度参数产生漂移，且黑盒 reasoning 难以调试。`EmotionState` 增加 `confidence` 字段，仅当 `confidence ≥ 0.7` 且 `current_state != NEUTRAL` 时才向 LLM Prompt 注入 `[Emotion State]` 文本段，避免模糊状态污染生成。

**追问：CONCERNED 状态下的具身参数调制（降速 50%）是在哪个节点生效的？**

**A:** 在 `ActionPlanner.plan()` 中生效。`StateMachineAgentCore._build_prompt` 已执行 `_update_emotion()` 获取最新情感状态（H1 时序修复确保前置），`ActionPlanner` 查询 `EMOTION_BEHAVIOR_MODULATION` 参数表，将情感状态翻译为结构化 `ActionPlan`（如 `speed_multiplier=0.5`，`volume_multiplier=0.8`）。最终通过 `EmbodiedAdapter.translate_action_token()` 映射为 `grid_2d` 或 `ros2_mobile` 低层指令。

### 10.5 工程纪律与测试

**Q: 如何防止"测试迁就实现"（test accommodating bug）？**

**A:** 项目执行严格的**测试语义红线**：
1. 断言必须基于业务语义与架构文档，禁止基于实现内部细节或硬编码巧合数值；
2. 测试失败时默认假设为"实现缺陷"，未经架构师审查禁止直接修改测试预期值去迁就实现；
3. 任何涉及修改测试预期的提交必须在 commit message 中标注 `[TEST-REVIEW]`，并在 PR 中说明失败根因、为何修改测试而非实现、架构师是否已审查。

`tests/test_mock_pipeline.py`（31 项断言）是全项目回归基线，任何改动不得破坏其通过性。

---

## 11. 业界方案对比与借鉴

### 11.1 与 Mem0、Zep、Letta 的差异化

| 维度 | Mem0 | Zep | Letta (MemGPT) | **ChronoPersona** |
|------|------|-----|----------------|-------------------|
| **记忆持久化** | 向量库 | 向量+图 | 分层（上下文/外部存储） | **L0-L3 四级分层 + 版本链** |
| **多端同步** | ❌ 无 | ❌ 无 | ❌ 无 | **✅ 自研 LWW-CRDT + HLC** |
| **角色隔离** | ❌ 无 | ❌ 无 | ❌ 无 | **✅ MVCC `branch_id` 物理隔离** |
| **检索语义** | 纯向量相似度 | 纯向量相似度 | 纯向量相似度 | **✅ 意图图谱导航（8 类边 + 8 类策略）** |
| **具身感知** | ❌ 无 | ❌ 无 | ❌ 无 | **✅ Token→Action Bridge 跨本体映射** |
| **主动进化** | ❌ 无 | ❌ 无 | ✅ 有（类似记忆分页） | **✅ Dreaming 骨架（SimpleInsightEngine）** |
| **情感引擎** | ❌ 无 | ❌ 无 | ❌ 无 | **✅ T0 规则 + LSTM 回归双层** |

**核心差异总结**：Mem0/Zep/Letta 的记忆层本质上是"向量检索 + 长上下文窗口"的优化，未解决多端一致性与角色物理隔离问题。ChronoPersona 将**分布式系统（CRDT）**与**数据库（MVCC）**的成熟抽象引入记忆层，使记忆从"检索附件"升级为"带版本的一致性数据层"。

### 11.2 Cursor 多 Agent 架构的借鉴与规避

Cursor 的真实架构采用 **Git Worktree 物理隔离 + Best-of-N 选择**，而非社区误解的"CRDT 自动合并多 Agent 结果"。ChronoPersona 从中吸收了三项关键原则：

1. **物理隔离优先**：Cursor 指出"代码是高度结构化的 AST，文本级 CRDT 会导致语法崩溃"。ChronoPersona 的 L3 语义记忆强制使用节点+边+属性的图操作原语，禁止文本级 diff/merge，与 Cursor 的"结构化操作原语"理念一致。
2. **无冲突域划分**：Cursor 要求"同文件不并发写入"。ChronoPersona 显式化为分层写入域锁定——L0 key 级、L1 session 级、L2 session_id 分区、L3 entity_id 级，规避隐式冲突。
3. **启发式选择优于盲目合并**：Cursor 对 N 个 Agent 结果不做自动合并，而是人工/启发式选最优。ChronoPersona 的 L0 冲突保留双版本 + `CONTRADICTS` 边，同样拒绝"自动消解语义矛盾"，将仲裁权交还 LLM 或用户。

**规避的陷阱**：Cursor 明确警告"文本级 CRDT 合并结构化数据"不可行，ChronoPersona 因此完全放弃文本级 CRDT，自研 KV 级 `LWWMap`。

### 11.3 酒馆（SillyTavern）社区的人格工程验证

酒馆社区的高评价角色卡验证了一个核心洞察：**信息密度、记忆精度与人格约束力的和谐统一**。ChronoPersona 将酒馆经验系统化、生产化：

- **W++ 锚点**：用结构化字段（MBTI、traits、taboos）在最小 Token 内定位人格；
- **Ali:Chat 示例**：作为风格锚定与漂移检测的向量基准；
- **有机约束**：将禁忌根植于 `core_narrative` 和 `style_examples`，而非外部规则列表，提升越狱抗性；
- **四层混合格式**：W++ + 自然语言叙事 + Ali:Chat 示例 + 结构化权限，兼顾 LLM 理解精度与系统可解析性。

---

## 12. 核心设计深度展开

### 12.1 人格定义与跨本体迁移

#### 人格定义：四层混合格式 Anchor

在 ChronoPersona 中，人格不是一段自由文本 Prompt，而是**强类型的四层混合格式配置**（`PersonaAnchor`），存储于 `contracts/schemas/agent.py` 相关结构并由 `StateMachineAgentCore` 在 `_build_prompt` 时注入：

| 层级 | 格式 | 内容 | 作用 |
|------|------|------|------|
| **Layer 1** | W++ 风格 | `mbti`, `traits`, `speech_pattern`, `taboos` | Token 最优，快速定位人格内核 |
| **Layer 2** | 自然语言 | `core_narrative`（段落式核心设定） | 创作者友好，LLM 理解最优 |
| **Layer 3** | Ali:Chat 风格 | `style_examples`（用户- Agent 对话对） | 风格锚定，漂移检测基准 |
| **Layer 4** | 结构化参数 | `skill_permissions`, `memory_access_policy`, `behavior_params` | 机器最优，系统解析执行 |

`memory_access_policy` 是人格隔离的核心机制：
```yaml
readable_branches: ["main", "therapist"]  # 该人格可读取的分支
writable_branch: "therapist"              # 该人格只能写入指定分支
forbidden_topics: ["rpg-hero.quest_progress"]
```

#### 跨本体迁移：Token→Action Bridge

人格与执行本体解耦，通过 `ActionPlanner` + `EmbodiedAdapter` 实现"同一灵魂跨身体迁移"：

1. **高层语义统一**：LLM 输出自然语言动作意图（如"慢慢靠近"）；
2. **结构化解析**：`ActionPlanner.plan()` 解析为 `action_token`（如 `approach_gently`）+ `action_params` + `reasoning`；
3. **跨本体映射**：`EmbodiedAdapter.translate_action_token()` 通过映射字典翻译为不同本体指令：
   - `grid_2d`: `"move_forward({distance}, speed={speed})"`
   - `ros2_mobile`: `"cmd_vel [linear={speed}, angular=0.0]"`
   - `mujoco`: 预留接口，字典已定义

MVA 阶段 `grid_2d` 已真实实现；ROS2 / MuJoCo 映射字典已冻结，适配器为 W8+ 预留。情感调制（如 CONCERNED → `speed_multiplier=0.5`）在 `ActionPlanner` 层统一应用，与目标本体无关。

### 12.2 Dreaming 记忆蒸馏方案设计

Dreaming（Memory Consolidation）是 L2 情景记忆向 L3 语义记忆的**蒸馏（Distillation）**过程，信息密度从"高冗余、高噪声"跃迁为"高结构化、低冗余"。

#### 触发条件（MVA 已落地）

- `InsightScheduler` 管理触发器：
  - `trigger_rounds`: 每 **10 轮**对话（可配置范围 5–20）
  - `trigger_daily`: 每日 **03:00 UTC** 兜底扫描
  - `min_confidence`: 0.6（低于此值的 insight 不写入）

#### 执行流程（MVA Phase A 已落地，Phase B 为 `[FUTURE]`）

```
对话回合结束 / 定时触发
    │
    ▼
[SimpleInsightEngine Phase A: 实体链接]
    ├── 关键词共现统计（Tier 1）
    └── 产出：MENTIONS / TEMPORAL_NEXT / BELONGS_TO 边（规则引擎直接写入）
    │
    ▼
[Phase B: 模式提取] ←── [FUTURE] 占位
    ├── 识别重复交互模式（如"用户每次提到'优化性能'后要求查看火焰图"）
    └── 产出：BehavioralRule(trigger, action, confidence, source_memory_ids)
    │
    ▼
[写入 L3 Semantic Memory]
    ├── `insights` 表 / `semantic_edges` 边表
    └── 反向索引建立，支持 RAG 快速召回
```

#### BehavioralRule 结构（Schema 已冻结）

```python
BehavioralRule(
    trigger="用户提及性能优化",
    action="主动建议查看火焰图",
    confidence=0.92,
    source_memory_ids=["mem-001", "mem-003"],
    branch_id="main",
)
```

#### 条件感知蒸馏器（W8+ P1 级优化）

当前 MVA 的已知缺陷是 Dreaming 会丢失"如果/除非/当...时"等条件从句。生产级方案将引入 NLP 条件句识别模块，将条件提取为 `BehavioralRule.trigger`，结论作为 `.action`，否定词强制保留。

### 12.3 L0 持久化与 L1 不持久化的设计 rationale

#### L0 为什么持久化？

L0（`LWWMap` + `SyncManager`）存储的是**用户级全局状态**，具有跨 Session、跨设备、跨人格的基础属性：
- 用户画像（昵称、年龄、基础偏好）
- 活跃偏好（当前喜欢的菜系、音乐风格）
- 情感状态基线
- 多端同步的 CRDT 操作日志

这些状态需要在 Session 结束后继续存在，并在设备间同步。`SyncManager` 每 5 分钟或 Session 结束触发 `checkpoint()`，将 `dirty_keys` 刷入持久化层（MVA 阶段为 L3 语义层接口预留，W8+ 对接 PostgreSQL）。

#### L1 为什么不持久化？

L1（`WorkingMemoryWindow`）存储的是**当前 Session 的临时对话上下文**：
- 最近 N 轮原始对话
- 动态压缩生成的 `CompressedSummary`

设计为**物理上永不持久化**，原因如下：
1. **隐私与隔离**：Session 结束即清空，避免敏感对话残留；
2. **语义边界**：L1 是"工作记忆"，类比人类当前意识，不进入长期存储；
3. **成本控制**：若 L1 持久化，将与 L2 情景记忆功能重叠，导致冗余存储与向量库膨胀。

需要长期保留的对话内容，由 `Reflection Agent` 异步提炼后写入 L2/L3，而非直接持久化 L1。

### 12.4 下一阶段演进路线（Beyond MVA）

基于 `docs/schedule.md` 与 `docs/requirements.md` 第 12 章，W8+ 演进分为 P1/P2/P3 三级：

| 优先级 | 模块 | 目标 | 依赖条件 | 预估工时 |
|:------:|------|------|---------|---------|
| **P1** | **条件感知蒸馏器** | 解决 Dreaming 丢失"如果/除非"条件从句 | NLP 条件句识别（`spacy` 依存解析） | 3 天 |
| **P1** | **记忆溯源链** | 为 `MemoryEntry`/`Fact` 增加 `source_memory_ids` + `extraction_model`，支持逐条追溯 | Schema 扩展（非破坏性，新增可选字段） | 2 天 |
| **P1** | **LangGraph 状态机迁移** | 将手写 `StateMachineAgentCore` 重构为 `StateGraph`，支持条件边路由与循环回退 | `langgraph` 库 | 3 天 |
| **P2** | **硬预算截断** | 实时 token 计数器，80% 预算时 T2/T3 降级本地规则，100% 时关闭 Reflection Agent | `CostRecord` 实时累加逻辑 | 2 天 |
| **P2** | **跨分支记忆继承过滤器** | `main` 向子分支穿透时，通过 `IPrivacyFilter`（PII 正则 + NER）与 `IRelevanceFilter` 双重过滤 | PII 识别模块（`presidio` 或规则引擎） | 3 天 |
| **P2** | **IntentGraph PostgreSQL 持久化** | 内存 BFS 迁移至 Recursive CTE，支持进程重启不丢失图谱 | PostgreSQL 14+，复合索引 | 4 天 |
| **P2** | **Qdrant 分布式向量库** | 替换本地 FAISS `IndexFlatIP`，支持 HNSW + 多副本 + 快照恢复 | Qdrant HNSW 服务端 | 3 天 |
| **P3** | **检索结果可解释性** | 为 `RetrievedContext.navigation_path` 填充详细路径（为什么召回这条），解决"Recall@5 高但用户感觉健忘" | `navigation_path` 结构扩展 | 2 天 |
| **P3** | **边类型纠错机制** | `CORRELATED` 边满足条件时自动升级为 `CAUSED` | `EdgeBuilder` 置信度追踪增强 | 2 天 |

### 12.5 组件化与模块化架构

ChronoPersona 的设计目标是**"接口驱动、可插拔、可验证"**，所有核心能力均通过抽象接口定义，支持快速替换与 A/B 验证。

#### 12.5.1 接口冻结层（`contracts/interfaces/`）

MVA 阶段已冻结 **14 个抽象接口**，任何新模块必须先定义接口：

| 接口 | 职责 | 当前实现 | 可替换方案 |
|------|------|---------|-----------|
| `AbstractL0SyncLayer` | CRDT 同步 | `L0SyncLayer`（真实） / `MockL0SyncLayer` | Yjs 适配器（不推荐） |
| `AbstractMemoryStore` | 记忆存储 | `SimpleEpisodicStore` / `FaissEpisodicStore` | Qdrant / Milvus 适配器 |
| `AbstractAgentCore` | Agent 核心 | `StateMachineAgentCore` | LangGraph 重构（W8+） |
| `AbstractEmbedder` | 文本嵌入 | `MockBGEEmbedder` | `sentence-transformers` / BGE |
| `AbstractEmbodiedAdapter` | 具身适配 | `GridWorldAdapter`（真实） / `MockEmbodiedAdapter` | ROS2 / MuJoCo 适配器 |
| `AbstractActionPlanner` | 动作规划 | `ActionPlanner`（真实） / `MockActionPlanner` | RL 策略网络（远期） |
| `IPersonaInjector` | 人格注入 | Mock（接口冻结） | 完整 YAML 解析器 |
| `ISkillRegistry` / `ISkill` | 技能注册与执行 | Mock（接口冻结） | 函数调用插件系统 |

#### 12.5.2 Mock 优先验证机制

每个接口均配套 Mock 实现与专门测试，支持**零依赖快速验证新点子**：
- 新存储引擎：先实现 `AbstractMemoryStore` 的 Mock，跑通 `tests/test_mock_pipeline.py` 后再接入真实库；
- 新具身本体：先实现 `AbstractEmbodiedAdapter` 的 Mock，验证 `action_token` → 动作映射逻辑，再开发真实适配器；
- 新评估场景：在 `evaluation/scenarios.py` 中新增 `ScenarioBuilder` 静态方法，复用 `EvaluationRunner` 的指标计算流水线。

#### 12.5.3 分层无冲突域（快速装卸的基础）

L0–L3 的严格分层本身就是模块化基础：
- **L0 可独立替换**：`LWWMap` 可替换为 Redis / SQLite 后端，不影响 L1-L3；
- **L2 存储可插拔**：`SimpleEpisodicStore`（纯 Python，CI 友好）与 `FaissEpisodicStore`（FAISS，性能更优）通过同一接口切换；
- **L3 导航策略可扩展**：新增意图策略只需在 `intent_patterns` 表（或 MVO 种子配置文件）中注册，无需修改 BFS 引擎；
- **Agent Core 节点可重组**：Input/Intent/Memory/LLM/Output/ActionPlanner 六节点通过明确的数据契约（`AgentOutput`、`RetrievedContext`、`ActionPlan`）交互，支持单独替换或跳过。

#### 12.5.4 配置文件驱动的扩展点

- **MVO 种子扩展**：`configs/mvo_extensions/{domain}.yaml` 支持新增概念与意图策略，幂等加载，重启自动注入，无需改代码；
- **情感调制表扩展**：`EMOTION_BEHAVIOR_MODULATION` 是纯字典配置，新增情感状态只需添加行记录；
- **跨本体映射字典扩展**：`ACTION_TOKEN_MAP` 按 `robot_type` 分键，新增本体（如 `isaac_gym`）只需添加子字典。

### 12.6 风格指纹漂移检测详解

#### 概念背景
在长时间多轮对话中，LLM 存在"人格漂移"现象：即使 System Prompt 中固定了人格设定，Agent 的输出风格仍会逐渐受用户输入影响而偏离。例如，设定为"温和坚定的心理咨询师"的 Agent，在应对 20 轮用户愤怒输入后，可能不自觉地变得防御性或过于顺从；或者"霸道总裁"人格在长时间闲聊后失去了原有的语言锋芒。

传统方案依靠"定期刷新 System Prompt"或"硬编码语气规则"来抑制漂移，但缺乏**量化检测手段**——你不知道漂移何时发生，也无法衡量漂移程度。

#### 风格指纹的构建
ChronoPersona 将人格的"标准对话样本"（即 `PersonaAnchor.style_examples` 中的 Ali:Chat 对话对）通过 embedding 模型编码为高维向量，取均值作为该人格的**风格指纹（Style Fingerprint）**：

```
style_fingerprint = mean([
    embed(f"user: {ex.user}\nagent: {ex.agent}") 
    for ex in persona_anchor.style_examples
])
```

- **为什么用 style_examples 而非 core_narrative？**  
  `core_narrative` 是创作者友好的自然语言描述，但 embedding 后的语义中心较散；`style_examples` 是真实对话模式，向量均值更能代表"这种人格实际会怎么说话"的分布中心。

- **MVA 阶段的 embedding 模型**：使用 `MockBGEEmbedder`（128d 确定性向量，基于文本长度生成）。该模型不捕捉真实语义，但用于验证**检测流程**的正确性。生产环境需替换为 `sentence-transformers`（如 `paraphrase-multilingual-MiniLM-L12-v2`）或 BGE 系列，以获取真实语义相似度。

#### 漂移检测流程
每轮对话结束后，将 Agent 的实际回复进行同样的 embedding，与风格指纹计算**余弦相似度**：

```
similarity = cosine_similarity(embed(reply), style_fingerprint)
```

- **阈值判定**：`similarity < 0.75` 判定为漂移触发。
- **反馈机制**：下轮 `_build_prompt` 时自动提升 `PersonaAnchor` 的注入权重（如将 Anchor Token 预算从 300 提升到 500，或增加 `style_examples` 的示例对数量），强制"拉回"人格。
- **相对 gap 防御**：由于 MVA 使用 `MockBGEEmbedder`（长度敏感），绝对阈值可能失效。因此 A11 测试采用**相对 gap** 判定：`high_score（正常回复）> low_score（明显异常回复）`，而非硬编码 0.75。

#### 与业界方案的区别
传统方案多依赖人工抽查或用户反馈来发现漂移。ChronoPersona 将漂移检测**自动化、量化、前置化**——在评估流水线（A11 场景）中自动运行，产出 `drift_detection_rate`，作为人格工程的健康度指标。

---

### 12.7 三级风险兜底详解

#### 概念背景
ChronoPersona 的 Agent Core 依赖外部 LLM API（DeepSeek-V4-pro、Kimi 2.6 等）完成意图识别、记忆反思、回复生成等任务。在生产环境中，这些依赖存在三类风险：
1. **服务不稳定**：云端 API 超时、RateLimit、5xx 错误；
2. **网络故障**：设备断网、DNS 故障、TLS 握手失败；
3. **成本失控**：Token 配额耗尽、预算超支。

如果没有兜底策略，任何一层故障都会导致 Agent 完全失效（无响应、崩溃或返回异常）。**三级风险兜底是模型路由层的故障降级策略**，目标是在"理想智能"不可用时，以可预期的降级形态维持服务连续性。

#### 一级兜底：模型链式降级
**触发时机**：首选模型调用失败（超时 > 5s、HTTP 429/503、网络不可达）。

**执行逻辑**：按预设降级链自动切换下一级模型。以 T5（回复生成）为例：
```
DS-V4-pro (首选) → Kimi 2.6 (备选) → Qwen3.5-9B 本地 (兜底)
```

**关键设计**：
- 降级只切换**模型实例**，不切换任务类型（T5 仍然是 T5）。
- 每次降级记录 `ModelCallRecord.status = "degraded"`，用于后续成本审计。
- 降级后的回复质量可能下降，但对话连续性得以保持。

**MVA 状态**：降级链在 `docs/requirements.md` 4.8 节已完整定义；真实触发逻辑当前为 Mock（`MockModelRouter` 直接返回固定值，不模拟故障）。

#### 二级兜底：本地规则引擎
**触发时机**：**所有云端模型均不可用**（网络完全断开、API 密钥全局失效、所有模型同时 RateLimit）。

**执行逻辑**：Agent Core 放弃 LLM 调用，切换至**本地规则引擎**：
- **T0 情感分类**：关键词匹配规则机（已真实实现，<1ms）；
- **T1 意图识别**：模板匹配（8 类意图的关键词触发）；
- **T3b CORRELATED 边构建**：本地规则引擎直接写入弱相关边；
- **T5 回复生成**：fallback 为基于规则的安全回复模板（如"我理解你的感受，能详细说说吗？"）。

**关键设计**：
- 二级兜底的核心是**确定性**：规则引擎 100% 可预期，不受网络影响。
- 此时 Agent 失去"生成式智能"，但仍能保持基础交互能力（情感识别、意图分类、安全回复）。
- `ConsolidationAgent` 的 Tier 1 规则（关键词共现）已落地，可作为二级兜底的记忆构建基础。

**MVA 状态**：T0/T1 规则引擎已真实实现；T5 安全回复模板尚未固化。

#### 三级兜底：安全预设回复
**触发时机**：**连本地规则引擎也无法覆盖当前场景**（如遇到完全未知的意图类型、规则模板无匹配、或 Agent Core 内部异常）。

**执行逻辑**：
1. 返回预设的安全回复（如"我现在有点困惑，能换个说法吗？"或"这个问题我暂时无法回答，建议你稍后再试。"）；
2. 记录 ERROR 级别日志，包含当前 `branch_id`、`persona_id`、`user_input` 哈希（脱敏）；
3. 可选：向运维/开发者发送告警（Webhook / 邮件）。

**关键设计**：
- 三级兜底的目标是**防止胡说八道**：比"错误回答"更安全的是"承认不知道"。
- 回复必须简短（< 50 tokens），避免在异常状态下消耗额外资源。
- 禁止暴露内部错误堆栈或模型名称给用户（防止信息泄露）。

**MVA 状态**：安全预设回复逻辑当前为 Mock（直接返回空字符串或固定文本），未接入真实异常捕获。

#### 三级兜底的关系总结

| 层级 | 触发条件 | 核心目标 | 智能程度 | MVA 实现 |
|------|---------|---------|---------|---------|
| **一级** | 单模型故障 |  continuity（连续性） | 高（换模型） | 策略定义✅ 触发逻辑 Mock |
| **二级** | 全云端不可用 |  determinism（确定性） | 中（规则引擎） | T0/T1 规则✅ T5 模板❌ |
| **三级** | 规则也无法覆盖 |  safety（安全性） | 低（预设回复） | 策略定义✅ 执行 Mock |

#### 与"硬预算截断"的区别
三级兜底是**故障驱动**的被动降级；`docs/requirements.md` 12.2.2 提到的"硬预算截断"是**成本驱动**的主动降级（80% 预算时 T2/T3 降级为本地规则）。两者在二级兜底处交汇（都使用本地规则引擎），但触发原因不同。

#### 面试一句话表述
> "三级兜底是模型路由的故障降级策略：单模型故障时链式切换备选模型，全云端断网时退回到本地关键词规则，连规则都覆盖不了时返回安全预设回复。目标不是保持最高智能，而是保证任何情况下 Agent 都不崩溃、不胡说。"

---

*文档版本: v1.3*  
*新增章节: 第13-15章（含 12.6/12.7 详解）*  
*基线日期: 2026-05-22*  
*对应代码版本: MVA v1.5*

---

## 13. 简历关键技术点实现状态诚实评估

以下针对简历中三项核心表述，基于 MVA v1.5 代码基线做逐项对照。原则是：**已真实落地的如实描述，框架/接口就绪但无真实后端连接的明确标注，规划中的不夸大。**

---

### 13.1 四层 Persona Anchor 与 Embedding 风格指纹漂移检测

#### 13.1.1 四层混合格式 Anchor：框架冻结，完整解析器为 W8+

**简历表述**：四层 Persona Anchor（W++ 锚点 + 对话示例 + 叙事 + 权限）

**真实实现状态**：

| 层级 | 状态 | 代码证据 | 说明 |
|------|------|---------|------|
| **Schema 定义** | ✅ 已冻结 | `contracts/schemas/agent.py` 相关 dataclass / `docs/requirements.md` 4.0.1 | 四层结构（`style_fingerprint` / `core_narrative` / `style_examples` / `skill_permissions`）已作为强类型配置写入设计文档与数据契约。 |
| **Prompt 注入** | ✅ 已落地 | `StateMachineAgentCore._build_prompt()` | 人格切换时，`PersonaAnchor` 的 `core_narrative` 与 `style_fingerprint` 字段已注入 LLM Prompt。`switch_persona()` 方法强制要求 `branch_id`，切换后 L1 清空、L2/L3 按分支隔离。 |
| **W++ 解析器** | ⚠️ 框架级 | `IPersonaInjector` 接口已冻结 | W++ 字段（`mbti`, `traits`, `taboos`）当前作为 YAML 配置中的结构化文本直接拼接进 Prompt，**尚未实现 W++ 语法的专用解析器**（如 `{{char}}` 变量替换、属性继承）。 |
| **权限执行** | ⚠️ Mock 级 | `skill_permissions` / `memory_access_policy` 已定义 | `forbidden_skills` 与 `readable_branches` 在 Schema 中存在，但执行层校验当前为 Mock（`MockAgentCore` 直接放行）。生产级 `ISkillRegistry` 的权限拦截逻辑接口已冻结，W8+ 实现。 |
| **Ali:Chat 示例注入** | ✅ 已落地 | `PersonaAnchor.style_examples` | 对话对已作为 `list[dict]` 结构注入 Prompt，用于风格锚定。 |

**结论**：四层混合格式的**数据模型与 Prompt 注入链路**已在 MVA 跑通；但 W++ 专用语法解析器、权限执行的策略引擎属于**接口冻结 + Mock 占位**状态。面试时可表述为"四层 Schema 已冻结并验证注入效果，专用解析器与权限策略引擎是 W8+ 生产级收尾项"。

#### 13.1.2 Embedding 风格指纹漂移检测：已真实实现

**简历表述**：Embedding 风格指纹漂移检测

**真实实现状态**：

| 组件 | 状态 | 代码位置 | 说明 |
|------|------|---------|------|
| **PersonaDriftChecker** | ✅ 已真实实现 | `evaluation/drift_checker.py` | 基于 `MockBGEEmbedder` 预计算 `style_examples` 的 embedding 均值作为基线，单轮回复 embedding 与基线计算余弦相似度。 |
| **评估集成** | ✅ 已落地 | `evaluation/runner.py` `_evaluate_a11_persona_drift()` | A11 场景自动化运行漂移检测，输出 `high_score` / `low_score` 与 `drift_detection_rate`。 |
| **基线替换** | ⚠️ MVA 占位 | `MockBGEEmbedder` | 当前使用基于文本长度的确定性向量（128d），非真实语义 embedding。MVA 阶段验证**流程与接口**正确性；生产环境需替换为 `sentence-transformers`（`paraphrase-multilingual-MiniLM-L12-v2` 或 BGE 系列）以获取真实语义相似度。 |

**关键设计细节**：
- 基线计算：`mean([embed(f"user: {ex.user}\nagent: {ex.agent}") for ex in style_examples])`
- 阈值：`similarity < 0.75` 触发漂移告警，下轮增加 Anchor 权重。
- MVA 防御：由于 `MockBGEEmbedder` 是长度敏感型，A11 测试使用**相对 gap**（`high_score > low_score`）而非绝对阈值，避免与 Mock 内部实现耦合。

**结论**：风格指纹漂移检测的**完整链路（基线预计算 → 在线检测 → 告警反馈）已在 MVA 真实实现并纳入自动化评估**。唯一遗留是 embedding 模型从 Mock 迁移到生产级向量模型，属于"换模型不换架构"的低成本替换。

---

### 13.2 T0–T7 端云协同模型路由

#### 13.2.1 路由表与降级链：Schema 冻结，真实模型未接入

**简历表述**：构建 T0–T7 端云协同模型路由（端侧 Qwen3.5-9B / 云端 DS-V4-pro）

**真实实现状态**：

| 组件 | 状态 | 代码证据 | 说明 |
|------|------|---------|------|
| **路由表设计** | ✅ 已冻结 | `docs/requirements.md` 4.8 节 | T0–T7 八级任务分层、首选模型、降级链、本地/云端标注已全部文档化。 |
| **接口抽象** | ✅ 已冻结 | `contracts/interfaces/`（`AbstractModelRouter`） | `route()` / `get_cost_summary()` / `cache_clear()` 方法签名已冻结。 |
| **Mock 实现** | ✅ 已落地 | `mocks/mock_model_router.py` | MVA 阶段所有 LLM 调用均走 Mock，返回固定文本，保障 Agent Core 端到端流程可测试。 |
| **真实模型接入** | ❌ 未实现 | — | Qwen3.5-9B 本地部署（LM Studio / vLLM）与 DS-V4-pro / Kimi 2.6 云端 API 未接入。MVA 阶段无法产生真实模型延迟与成本数据。 |
| **端侧推理** | ❌ 未实现 | — | 本地 Qwen3.5-9B 的 ONNX / TorchScript 导出、量化压缩均未执行。 |
| **成本追踪** | ⚠️ 接口级 | `CostRecord` / `CostReport` Schema 已定义 | `ModelCallRecord` 的 16 个字段已设计（含 `ttft_ms`, `cache_hit`, `token_scope`），但 `ICostTracker.record()` 当前为 Mock 空实现。 |

**T0–T7 路由表（设计冻结状态）**：

| 任务层级 | 任务类型 | 首选模型 | 降级链 | MVA 实际运行 |
|---------|---------|---------|--------|-------------|
| T0 | 情感分类 | Qwen3.5-9B | DS-V4-flash | MockModelRouter 固定返回值 |
| T1 | 意图识别 | Qwen3.5-9B | DS-V4-flash | MockModelRouter 固定返回值 |
| T2 | 实体提取 | DS-V4-flash | Kimi 2.6 | MockModelRouter 固定返回值 |
| T3 | 边构建 | DS-V4-flash | Kimi 2.6 | MockModelRouter 固定返回值 |
| T4 | 记忆反思 | Kimi 2.6 | DS-V4-pro | MockModelRouter 固定返回值 |
| T5 | 回复生成 | DS-V4-pro | Kimi 2.6 | MockModelRouter 固定返回值 |
| T6 | 冲突消解 | Kimi 2.6 | DS-V4-pro | MockModelRouter 固定返回值 |
| T7 | 评估/测试 | DS-V4-pro | Kimi 2.6 | MockModelRouter 固定返回值 |

**结论**：T0–T7 的**分层策略、降级链、成本追踪 Schema** 已在 MVA 完成设计冻结；但**真实模型接入（本地 Qwen3.5 + 云端 DeepSeek/Kimi）尚未实现**。MVA 的核心目标是验证"Agent Core 在接到不同 task_type 时能否正确路由到对应模型槽位"，而非真实跑通多模型推理。面试时应明确表述为"路由策略与降级链已设计冻结，真实模型接入是生产级部署项"。

#### 13.2.2 是否有必要在 MVA 实现真实模型路由？

**必要性分析**：

| 维度 | 若 MVA 强行接入真实模型 | 当前 Mock 策略 |
|------|------------------------|---------------|
| **成本** | 8 周 MVA 日均万级 Token 配额，真实 DS-V4-pro 调用 3-5 天即可耗尽预算 | 零成本，无限测试 |
| **稳定性** | 云端 API RateLimit、网络抖动导致 CI 不稳定 | 100% 确定性，CI 可靠 |
| **核心目标** | MVA 需验证的是架构分层与接口契约，而非模型效果 | 精准验证接口契约 |
| **时间开销** | 本地 Qwen3.5-9B 部署需 1-2 天调通环境 | 零环境依赖 |

**结论**：MVA 阶段**不接入真实模型是正确取舍**。但 W8+ 生产化必须接入，否则"端云协同"仅停留在纸面设计。

---

### 13.3 SQLite 缓存与三级风险兜底

#### 13.3.1 SQLite 缓存：接口设计完成，真实缓存层未落地

**简历表述**：SQLite 缓存与三级风险兜底

**真实实现状态**：

| 组件 | 状态 | 代码证据 | 说明 |
|------|------|---------|------|
| **缓存策略设计** | ✅ 已冻结 | `docs/requirements.md` 4.8 节 | TTL 24h、缓存键 `hash(task_type + prompt + branch_id + persona_id)`、禁止跨分支污染，已文档化。 |
| **缓存键规则** | ✅ 已冻结 | `docs/requirements.md` 4.8 节 | 显式包含 `branch_id` 与 `persona_id`，确保不同分支/人格不共享缓存。 |
| **SQLite 表结构** | ⚠️ 未实现 | — | 无真实 SQLite 连接、无 `cache_entries` 表、无 `LRU eviction` 逻辑。 |
| **Mock 缓存** | ⚠️ 内存 Dict | `MockModelRouter` | MVA 阶段若存在缓存，仅为 Python 内存字典，进程退出即丢失。 |

#### 13.3.2 三级风险兜底：策略定义完成，执行层为 Mock

**三级兜底定义**（来自 `docs/requirements.md`）：

| 级别 | 触发条件 | 兜底动作 | MVA 状态 |
|------|---------|---------|---------|
| **一级** | 首选模型超时 / RateLimit | 降级到备选模型（T1→T2→T3 链） | 策略已定义，未真实触发 |
| **二级** | 云端全部不可用 | 切换本地规则引擎（T0/T1 规则 + T3b 模板） | `ConsolidationAgent` Tier 1 规则已落地，可作为二级兜底 |
| **三级** | 本地规则也无法覆盖 | 返回安全预设回复 + 记录告警日志 | `ActionPlanner` 预设安全回复尚未固化 |

**真实实现状态**：
- **一级降级**：`ModelRouter` 降级链在文档中完整定义，但 MVA 无真实模型调用，因此无超时/RateLimit 检测逻辑。
- **二级兜底**：T0 情感规则引擎、T1 意图模板匹配、T3b `CORRELATED` 边构建的本地规则已真实实现，可作为"云端不可用时"的降级基础。
- **三级兜底**：`ModelRouter` 在全部失败时返回预设安全回复的逻辑当前为 Mock（直接返回空字符串或固定文本），未接入真实异常捕获与日志告警。

#### 13.3.3 是否有必要在 MVA 实现？

| 组件 | MVA 必要性 | 理由 |
|------|-----------|------|
| SQLite 缓存 | 低 | MVA 调用量为 Mock，无真实延迟痛点；缓存主要是生产环境降低成本与提升稳定性的手段。 |
| 三级兜底 | 中 | 一级降级（模型切换）可推迟；但二级兜底（本地规则引擎）已部分实现（T0/T1 规则），这本身是 Agent Core 正确性的一部分。三级安全回复建议 W8 前补全，防止面试演示时异常路径暴露实现粗糙。 |

**结论**：SQLite 缓存属于**生产级成本优化项**，MVA 不做不影响架构验证；三级风险兜底的**策略层已定义，执行层为 Mock**，面试时可表述为"降级链与兜底策略已设计，生产环境需补齐异常捕获与安全回复固化"。

---

## 14. 面试话术修正建议

基于上述实现状态，以下是针对这三项技术的**诚实且专业**的面试表述：

### 14.1 Persona Anchor + 漂移检测

> "人格工程我们做了四层混合格式 Anchor：W++ 结构化锚点、自然语言叙事、Ali:Chat 风格示例、以及权限与行为参数。Schema 和 Prompt 注入链路已在 MVA 跑通，风格指纹漂移检测也已完成自动化评估（A11 场景）。当前 W++ 专用解析器和权限策略引擎是接口冻结状态，W8+ 补全为生产级解析器。"

### 14.2 T0–T7 模型路由

> "端云协同的路由策略已设计冻结：T0/T1 走本地 Qwen3.5-9B，T2-T7 按敏感度走云端 DeepSeek/Kimi，每级都有降级链。MVA 阶段用 Mock 验证路由接口与 Agent Core 的集成正确性，真实模型接入是生产部署项——这在 8 周 MVA 内是正确取舍，否则 API 成本 3-5 天就会耗尽预算。"

### 14.3 SQLite 缓存与三级兜底

> "缓存策略和三级兜底已经在架构文档中定义清楚：24h TTL、分支隔离的缓存键、以及模型→规则→安全回复的三级降级。MVA 阶段重点是验证核心记忆层与评估框架，缓存层和完整兜底执行是 W8+ 生产收尾。"

---

*文档版本: v1.2*  
*新增章节: 第13-14章*  
*基线日期: 2026-05-22*  
*对应代码版本: MVA v1.5*
