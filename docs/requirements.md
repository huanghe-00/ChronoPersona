# ChronoPersona 需求文档

> 本文档描述 ChronoPersona 记忆系统的核心需求与设计决策。

---

## 4.1 LWW-CRDT 多端同步

（此处省略原有内容，保留原有章节结构）

#### 冲突边数量上限（MVA 软限制）

发生冲突的 key 总量超过 **10 个** 时，系统触发 `logger.warning` 告警，提示运维人员介入归档，但不阻塞写入（避免数据丢失）。该上限防止多设备长期冲突导致内存膨胀。

---

## 4.4 L2 Episodic Memory

**检索打分公式（增强版）**：
```
score = cosine_similarity * importance * (1 + log1p(effective_access))
effective_access = access_count * exp(-days_since_last_access / 30.0)
```
- `access_count` 引入 **30 天半衰期衰减**，避免高频旧记忆永久压制低频新记忆。
- 若 `last_accessed` 解析失败，回退到原始 `access_count`。

**近重复检测与合并（Near-Dedup）**：
- L2 写入前，对目标 branch 现有记忆做向量预检；若最高相似度 > 0.95，视为近重复。
- 合并策略：保留较早 `created_at`，`access_count` 累加，`content` 保留较长版本。
- 返回原记忆 ID，避免 Top-K 槽位被重复内容占据。

**意图参数分层说明**：
- `SimpleEpisodicStore.retrieve(..., intent: Optional[str])` 中的 `intent` 参数当前为 **API 预留**，不参与底层向量 scoring（MVA 阶段底层存储仅负责语义相似度）。
- 意图过滤在 `MemoryNode` / `HybridRetriever` 层完成：拿到 `RetrievedContext` 后，根据 `IntentPattern` 的 `trigger_keywords` 与 `target_memory_types` 对召回结果做后过滤。
- **生产级方案**：在 `HybridRetriever` 层实现 intent-aware 融合，底层存储保留 `intent` 参数以支持未来分桶索引。

---

## 补充说明：检索路径 6 步流程实现状态（4.5.6 更新）

**MVA 阶段（当前已落地）**：
- **图导航**：纯 Python BFS（`IntentGraph.navigate` 使用 `collections.deque` 内存遍历），时间复杂度 O(V+E)，满足 20×20 网格 / 1000 节点内 < 10ms 响应。
- **向量检索**：`SimpleEpisodicStore` / `FaissEpisodicStore`（CPU 版，FAISS `IndexFlatIP`），无外部向量数据库依赖。
- **混合召回**：`HybridRetriever` 在 Python 层执行 0.6×图谱结果 + 0.4×向量结果的融合与去重。

**W8+ 生产级方案**：
- **图持久化**：`IntentGraph` 边表迁移至 PostgreSQL，`get_edges()` 改写为 `SELECT * FROM semantic_edges WHERE branch_id = ?`；`navigate()` 使用 Recursive CTE 执行 BFS：
  ```sql
  WITH RECURSIVE nav AS (
      SELECT target_id, 1 AS hops, weight FROM semantic_edges
      WHERE source_id = ? AND edge_type = ANY(?) AND branch_id = ?
      UNION ALL
      SELECT e.target_id, n.hops + 1, n.weight * e.weight * 0.9
      FROM semantic_edges e JOIN nav n ON e.source_id = n.target_id
      WHERE n.hops < ? AND e.edge_type = ANY(?) AND e.branch_id = ?
  ) SELECT * FROM nav;
  ```
- **向量数据库**：`Qdrant` 或 `Milvus` 替换本地 FAISS，支持 HNSW 近似索引、分布式部署、动态扩缩容。
- **执行计划优化**：PostgreSQL 对 `source_id + edge_type` 建立复合索引；CTE 使用 `MATERIALIZED` hint 避免递归层数过深导致的计划劣化。
- **混合召回**：数据库层返回图谱结果 ID 列表，Qdrant 返回向量结果 ID 列表，`IHybridRetriever` 按 MVA 已验证的 0.6/0.4 权重融合。

**依赖条件**：PostgreSQL 14+（支持 Recursive CTE），Qdrant 服务端，SQLAlchemy async 驱动。

---

## 4.5.3 语义边与反学习

**边的生命周期状态**：
- `SemanticEdge` 增加 `status: str` 字段（`"active"` / `"deprecated"` / `"archived"`）。
- `IntentGraph` 通过 `_deprecated_edges` 集合维护已弃用边 ID，`get_edges()` 与 `navigate()` 均过滤该集合中的边，反学习即时生效。
- `deprecate_edge()` / `reactivate_edge()` 方法同步更新 `SemanticEdge.status` 字段与 `_deprecated_edges` 集合，确保状态一致性。

---

## 4.13 差异化遗忘（L3 反学习）

- **L1**：session 结束即清空，无需遗忘。
- **L2**：指数衰减 `R = e^(-t/S)`，低于阈值后标记 `deprecated`。
- **L3**：`deprecated` 边在 `IntentGraph` 过滤机制中不参与 `navigate` 与 `get_edges`，但保留在存储中供审计追溯。`SemanticEdge.status` 字段与 `_deprecated_edges` 集合双重维护。
- **动态重要性重算**（W8+）：每月/每 100 轮触发一次全量 L3 `importance` 审计，剔除被后续 `CONTRADICTS` 覆盖的低分记忆。

---

## 4.9 Emotion Engine

**情感置信度传播（T0 规则引擎增强）**：
- `EmotionState` 增加 `confidence: float` 字段。
- T0 规则引擎：关键词匹配成功 → `confidence = 0.9`；无匹配 → `confidence = 0.5`。
- `_build_prompt` 仅当 `confidence >= 0.7` 且 `current_state != NEUTRAL` 时注入 `[Emotion State]` 文本段，避免模糊输入触发错误状态转移。

---

## 4.12 Dreaming

**条件感知蒸馏（Conditional Distiller）**：
- Dreaming 阶段增加 NLP 条件句识别（"如果..."、"除非..."、"当...时"）。
- 将条件从结论中剥离，提取为 `BehavioralRule.trigger` 字段，结论作为 `.action`，避免"条件上下文剥离"导致关键约束丢失。
- 否定词（"不"、"没有"）在蒸馏时保留，禁止消除。
