# Beyond MVA：ChronoPersona 记忆系统生产级优化路线图

> 本文档记录 MVA（Minimum Viable Architecture）阶段已识别、但因排期/复杂度原因推迟至生产环境实施的优化项。  
> 面试价值：展示对"带镣铐的架构"之外的真实生产痛点的深度思考。

---

## 1. 已落地的 MVA 防御（当前状态）

| 缺陷类别 | MVA 已实施的防御 | 验证方式 |
|---------|----------------|---------|
| 错误分类（情感误标） | T0 规则引擎 + `confidence` 阈值（`>=0.7` 才注入 Prompt） | `test_state_machine.py` T18 |
| 错误分类（边类型滞后） | `SemanticEdge.status` 字段 + `deprecated` 过滤机制 | `test_intent_graph.py`（待补全） |
| 过拟合（LFU Trap） | `access_count` 30 天半衰期衰减 | `test_l2_episodic.py` T57 |
| 过拟合（重复膨胀） | L2 近重复检测与合并（`sim > 0.95`） | `test_l2_episodic.py` T58 |
| 归纳遗漏（幽灵记忆） | Faiss `_deleted_indices` 过滤 + 防御性跳过 | `test_faiss_store.py` T03 |
| 归纳遗漏（情感时序） | `_update_emotion` 前置于 `ActionPlanner.plan()` | `test_state_machine.py` T16 |
| 一致性（冲突堆积） | `MAX_CONTRADICT_KEYS` 软限制 + 告警 | `test_l0_crdt.py`（日志断言） |

---

## 2. 生产级优化路线图（按优先级）

### 2.1 P1：条件感知蒸馏器（Conditional Distiller）

**解决的问题**：归纳遗漏（条件上下文剥离）  
**根因**：Dreaming 阶段 LLM 摘要会丢弃"如果/除非/当...时"等条件从句，导致"如果明天不下雨就去爬山"蒸馏为"用户喜欢爬山"。

**设计思路**：
- 在 `ReflectionAgent` Phase B 中增加 NLP 条件句识别模块（基于依存句法分析或轻量规则）。
- 将条件提取为 `BehavioralRule.trigger` 字段，结论作为 `.action`。
- 否定词（"不"、"没有"）标记为不可消除，强制保留。

**依赖条件**：NLP 条件句识别模块（可用 `spacy` 或 `stanza` 的依存解析）。  
**预估工时**：3 天  
**MVA 状态**：Schema 已预留 `BehavioralRule` 结构，蒸馏逻辑为 `[FUTURE]` 占位。

---

### 2.2 P1：记忆溯源链（Provenance Chain）

**解决的问题**：幻觉注入、评估指标与真实体验脱节  
**根因**：LLM 生成的 L3 事实无法追溯原始来源，导致"用户有猫"幻觉无法根因定位。

**设计思路**：
- `MemoryEntry` / `Fact` 增加 `source_memory_ids: List[str]` + `extraction_model: str` + `extraction_confidence: float`。
- `RetrievedContext` 增加 `provenance: Dict[str, ProvenanceRecord]`，支持"这条知识从哪来"的逐条追溯。
- 面试价值：可解释 AI（XAI）的核心实践。

**依赖条件**：`MemoryEntry` / `Fact` Schema 扩展（非破坏性，新增可选字段）。  
**预估工时**：2 天  
**MVA 状态**：`RetrievedContext` 已存在，但未填充溯源信息。

---

### 2.3 P2：动态重要性重算（Dynamic Importance Recalc）

**解决的问题**：短期波动固化、遗忘曲线僵化  
**根因**：`MemoryEntry.importance` 写入后静态不变，临时情绪（"我讨厌社交"）被永久固化。

**设计思路**：
- 每月 / 每 100 轮触发一次"重要性审计"批量任务。
- 重新计算所有 L3 记忆的 `importance`：基于后续 `CONTRADICTS` 覆盖次数、访问频率衰减、时效性。
- 得分低于阈值的记忆标记 `deprecated`（非物理删除，保留审计链）。

**依赖条件**：定时任务基础设施（`APScheduler` 或 `celery beat`）。  
**预估工时**：4 天  
**MVA 状态**：`importance` 字段已存在，重算逻辑未实现。

---

### 2.4 P2：硬预算截断（Hard Budget Throttle）

**解决的问题**：成本失控  
**根因**：每轮多次 LLM 调用（T2 实体提取 + T3 边构建 + T4 反思），token 消耗指数增长。

**设计思路**：
- 实时 token 计数器（`session_id` 级累加）。
- 80% 预算时：T2/T3 降级为本地规则引擎（如 spaCy NER + 模板匹配）。
- 100% 预算时：关闭 `ReflectionAgent`，仅保留核心对话链路。
- 超支告警：单 session 超支时记录 `CostReport.budget_exceeded = True`。

**依赖条件**：`CostRecord` / `CostReport` Schema 已存在，需增加实时累加逻辑。  
**预估工时**：2 天  
**MVA 状态**：`MockModelRouter` 已记录成本，但无预算硬截断。

---

### 2.5 P2：跨分支记忆继承过滤器（Branch Inheritance Filter）

**解决的问题**：跨分支污染  
**根因**：`main` 分支向 `therapist` / `rpg-hero` 穿透时，可能携带医疗记录 / 剧情设定等敏感信息。

**设计思路**：
- 定义 `IPrivacyFilter` 接口：基于 `memory_type` + `content` NER 识别 PII（姓名、电话、地址、医疗术语）。
- 定义 `IRelevanceFilter` 接口：基于目标 branch 的 `IntentPattern` 判断记忆相关性。
- `main` → 子 branch 穿透时，双重过滤后仅保留"基础画像"（姓名、偏好）而非全量记忆。

**依赖条件**：PII 识别模块（可用 `presidio` 或规则引擎）。  
**预估工时**：3 天  
**MVA 状态**：`branch_id` 显式传递已物理隔离，过滤器为锦上添花。

---

### 2.6 P3：边类型纠错机制（Edge Type Correction）

**解决的问题**：错误分类（边类型误标）  
**根因**：Tier 1 模板匹配召回率 ~40%，大量真实因果被降级为 `CORRELATED`。

**设计思路**：
- `EdgeBuilder` 增加置信度追踪：记录 `tier1_confidence`、`tier2_statistical_score`、`tier3_llm_score`。
- 当后续发现 `CORRELATED` 边满足 Tier 2/3 升级条件（时间先后 + 共现频率 + 情感极性一致）时，自动升级为 `CAUSED`。
- 支持人工审核队列：高价值升级建议进入 `pending_review` 状态。

**依赖条件**：`EdgeBuilder` 置信度追踪增强。  
**预估工时**：2 天  
**MVA 状态**：`EdgeBuilder` 未在 MVA 中完整实现，为远期模块。

---

### 2.7 P3：动态 max_hops

**解决的问题**：多跳推理断裂  
**根因**：固定 `max_hops=3` 对 `CAUSED` 因果链过短，对 `IS_A` 泛化链过长。

**设计思路**：
- 按边类型配置动态 `max_hops`：
  - `CAUSED` / `TRIGGERED_BY`：允许 4-5 跳（因果链通常较长）
  - `IS_A` / `BELONGS_TO`：限制 2 跳（防止过度泛化）
  - `MENTIONS`：限制 1 跳（防止指代漂移）

**依赖条件**：`IntentPattern` 增加 `max_hops_by_edge_type: Dict[str, int]` 字段。  
**预估工时**：1 天  
**MVA 状态**：`IntentPattern` 已存在，配置扩展即可。

---

### 2.8 P3：动作执行后感知反馈闭环

**解决的问题**：动作-结果记忆对缺失  
**根因**：`GridWorldAdapter` 返回 `LowLevelCommand` 后，环境状态变化未回写 L2，无法形成"动作→结果"的条件反射。

**设计思路**：
- `GridWorldAdapter.execute()` 后，捕获环境 diff（Agent 坐标变化、FOV 变化、物体交互结果）。
- 将 diff 文本化为 `ActionResult` 记忆，写入 L2（`memory_type="action_result"`）。
- 后续 Dreaming 阶段提取"动作→结果"规则，强化行为策略。

**依赖条件**：`GridWorldAdapter` 执行接口与 diff 捕获。  
**预估工时**：2 天  
**MVA 状态**：`GridWorldAdapter` 返回命令但未执行，闭环待 W7+ 完善。

---

### 2.9 P3：检索结果可解释性（Retrieval Explanation）

**解决的问题**："Recall@5 高但用户感觉健忘"  
**根因**：检索返回了正确记忆，但排序靠后被截断在 4K token 外，用户无感知。

**设计思路**：
- `RetrievedContext` 的 `navigation_path` 字段填充详细路径（为什么召回这条）。
- 格式：`{"memory_id": "...", "path": ["IntentPattern.retrieve", "SemanticEdge.MENTIONS", "Concept.c_plan"], "score_breakdown": {"similarity": 0.9, "importance": 0.8, "recency": 0.7}}`
- 前端展示：鼠标悬停记忆片段时显示溯源路径。

**依赖条件**：`IntentGraph.navigate()` 返回路径详情。  
**预估工时**：2 天  
**MVA 状态**：`navigation_path` 字段已存在，当前为空列表。

---

## 3. 明确不采纳项（MVA 设计取舍）

以下项在 MVA 阶段经过评估后明确放弃，面试时可坦诚说明：

| 项 | 不采纳理由 |
|----|-----------|
| **Causal Tier 1.5 启发式规则** | 当前 Tier 1 召回率 ~40% 是已知设计取舍（`requirements.md` 4.5.2）。增加启发式规则会引入新的测试负担与误标风险，W6 排期无法收敛。生产环境建议直接上 Tier 2 统计验证或 Tier 3 LLM 验证。 |
| **近因偏见显式修正** | 与 `access_count` 时间衰减（P1 已落地）存在耦合，独立 `recency` 项需大量调参。MVA 阶段 `effective_access = access_count * exp(-days/30)` 已足够覆盖。 |
| **L1 分层保留原始轮次** | 已有 `CompressedSummary.source_turn_ids` 记录被压缩的原始索引。全量"归档区"需 `WorkingMemoryWindow` 存储结构重构（`_turns` + `_archive` 双区），MVA 收益不足以支持风险。 |

---

## 4. 面试应答脚本（关键问题）

**Q: "你们的记忆系统有什么生产级缺陷？"**  
A: "MVA 阶段我们主动识别了 15 项缺陷，其中 5 项已在代码中硬化防御（如 `access_count` 衰减、情感置信度、近重复合并），其余 9 项已文档化为 W8+ 路线图。最核心的是 **条件感知蒸馏** —— 当前 Dreaming 会丢失'如果/除非'等条件从句，生产环境必须补上 NLP 条件句识别模块。"

**Q: "评估指标高但用户仍感觉健忘，怎么解决？"**  
A: "这是检索结果可解释性问题。当前 Recall@5 高但排序靠后的记忆被 4K token 截断。我们的 roadmap 中有 **Retrieval Explanation**，为每条召回记忆填充 `navigation_path`，前端展示'为什么召回这条'，同时支持用户追问时反查 L2 原始轮次。"

---

*文档版本: v1.0 | 基线日期: 2026-05-22 | 下次审视: W8 结束（2026-07-05）*
