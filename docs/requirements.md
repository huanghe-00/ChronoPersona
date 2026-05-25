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
