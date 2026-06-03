# ChronoPersona 项目版本路线图

**版本**: v2.0  
**基线日期**: 2026-05-22 (周五)  
**总工期**: v0.1.0 ~ v2.0.0（MVA + 5 个生产迭代 + 架构换代）  
**当前状态**: v0.6.0 评估框架已完成，v0.7.0 2D 世界 + 前端进行中，v1.0.0 文档与发布准备启动

---

## 1. 排期总览（修订后）

| 版本 | 日期范围 | 阶段主题 | 核心交付物 | 状态 |
|------|---------|---------|-----------|------|
| **v0.1.0** | 05-11 ~ 05-17 | `foundation`：契约与孤岛 | 接口冻结(14个)、Mock全量(12个)、真实节点(5个)、**测试400+ passed** 覆盖率94% | ✅ 已完成 |
| **v0.2.0** | 05-18 ~ 05-24 | `memory-core`：评估基线与骨架预热 | 无冲突域契约、Dreaming骨架、L2GC、PersonaInjector、Eval基线、L3 Unlearning | ✅ 已完成 |
| **v0.3.0** | 05-25 ~ 05-31 | `insight`：L3 + Intent Graph 深化 | MVO Seed、EdgeBuilder、HybridRetriever、CTEs | ✅ 已完成 |
| **v0.4.0** | 06-01 ~ 06-07 | `agent-loop`：Insight + 反思 | InsightGenerator、CAUSED Tier 2、A1/A2 召回测试 | ✅ 已完成 |
| **v0.5.0** | 06-08 ~ 06-14 | `evaluation`：Agent 核心循环 | StateMachineAgentCore 端到端、ActionPlanner、LSTM 监督骨架、RL-PLACEHOLDER 合规、**H1 情感时序修复** | ✅ 已完成 |
| **v0.6.0** | 06-15 ~ 06-21 | `embodied`：评估框架 | A1-A11 对抗测试集（**39 文件/400+ 用例**）、量化对比表、**测试语义红线** | ✅ 已完成 |
| **v0.7.0** | 06-22 ~ 06-28 | `frontend`：2D 世界 + 前端 | GridWorldAdapter **5 动作真实跨本体映射**、WebSocket Gateway Stub、Canvas 骨架、`[Emotion State]` + `[Semantic Facts]` Prompt 注入 | 🟡 进行中 |
| **v1.0.0** | 06-29 ~ 07-05 | `mva`：文档与发布准备 | README、技术博客、Slide Deck、Demo 脚本、**记忆系统生产优化文档化** | ⚪ 未开始 |
| **v1.1.0** | 07-06 ~ 07-26 | `production-baseline`：生产基线硬化 | 认证权限、硬预算截断、跨分支隐私过滤、记忆溯源链、WebSocket 真实实现、全链路日志 trace | ⚪ 未开始 |
| **v1.2.0** | 07-27 ~ 08-16 | `memory-quality`：记忆质量跃迁 | 条件感知蒸馏器、动态重要性重算、检索结果可解释性、边类型纠错、动态 max_hops | ⚪ 未开始 |
| **v1.3.0** | 08-17 ~ 09-13 | `graph-production`：图谱与检索生产化 | IntentGraph PostgreSQL 持久化、Episodic Store Qdrant 分布式、Intent-Aware 融合、级联更新 | ⚪ 未开始 |
| **v1.4.0** | 09-14 ~ 10-18 | `cognitive-deepening`：认知仿生深化 | L4 程序记忆、Dream T2–T6 全周期、L5 元记忆、DynamicImportance、动作反馈闭环 | ⚪ 未开始 |
| **v1.5.0** | 10-19 ~ 11-08 | `agent-autonomy`：智能体自治增强 | 反事实回放、评估 CI 集成、VLA 真实实现、Persona Drift 自动修复、ContextualBias 检索 | ⚪ 未开始 |
| **v2.0.0** | 11-09 ~ 12-20 | `architecture-refresh`：架构换代 | LangGraph 状态机迁移、真实多端 CRDT 同步、多模态感知、Semantic Merge Agent | ⚪ 未开始 |

---

## 2. v0.1.0 发布总结（05-15 基线锚定）

**实际达成**：
- `contracts/interfaces/` 14 个抽象接口全部冻结并导出。
- `mocks/` 12 个 Mock 实现 100% 覆盖对应接口。
- `tests/` **39 个测试文件**，全量 **400+ passed, 1 skipped, 0 failed**；语句覆盖率 **94%**。
- 真实实现交付：`L0SyncLayer`（HLC + add-wins + clock-skew）、`GridWorldAdapter`（FOV + 边界钳制）、`IntentGraph`/`IntentNavigator`（BFS + 意图模式匹配）、`StateMachineAgentCore`（端到端状态机）、`WorkingMemoryWindow`（滑动窗口 + 动态压缩）。
- 关键缺陷修复：`L0SyncLayer.get_delta()` 运行时 `NameError`（缺失 `self.`）。
- PLACEHOLDER 合规：`test_caused_tier2.py` 正确 skip，无违规实现复杂算法。
- 借鉴点吸收：`MemoryEntry` 重要性评分 Schema 落地、L2 检索加权实现。

**v0.1.0 验收测试矩阵**：

| 编号 | 测试文件 | 用例数 | 验证目标 |
|------|---------|--------|---------|
| T01-T31 | `test_mock_pipeline.py` | 31 | 核心守卫：端到端、CRDT、Memory、Agent、API、集成回归 |
| T32-T39 | `test_l0_crdt.py` | 8 | 真实 L0SyncLayer + MockL0SyncLayer：get/set、分支隔离、merge、checkpoint、delta |
| T40-T45 | `test_working_memory.py` | 6 | L1 滑动窗口：压缩触发、逆序上下文、token 上限 |
| T46-T50 | `test_model_router.py` | 5 | MockModelRouter：route、cost、cache_clear 边界 |
| T51-T58 | `test_version_manager.py` | 8 | MockVersionManager：commit、checkout、merge、gc 边界 |
| T59-T65 | `test_agent_core.py` | 7 | MockAgentCore：run_turn、switch_persona、emotion、memory_summary |
| T66-T69 | `test_embodied_adapter.py` | 4 | MockEmbodiedAdapter：perception、translate_action_token |
| T70-T74 | `test_insight_generator.py` | 5 | MockInsightGenerator：generate、should_trigger 阈值 |
| T75-T77 | `test_sync_manager.py` | 3 | SyncManager + MockSyncManager：apply_remote、checkpoint |
| T78-T81 | `test_intent_graph.py` | 4 | IntentGraph：概念隔离、边类型校验、BFS 导航、max_hops |
| T82-T85 | `test_intent_navigator.py` | 4 | IntentNavigator：模式匹配、未知意图、空分支、无入口节点 |
| T86-T93 | `test_grid_world.py` | 9 | GridWorldAdapter：坐标运动、FOV、边界钳制、action_token 翻译 |
| T94-T101 | `test_state_machine.py` | 8 | StateMachineAgentCore：全链路、persona 切换、version commit、分支隔离 |
| T102-T103 | `test_llm_node.py` | 2 | LLMNode：delegation、空分支校验 |
| T104-T106 | `test_output_node.py` | 3 | OutputNode：assembly、emotion 默认、memory_id 过滤 |
| T107-T110 | `test_memory_node.py` | 4 | MemoryNode：retrieve、意图降级、intent graph boost |
| **合计** | **39 个测试文件** | **~170 显式编号 + 辅助/参数化用例 = 400+ 总断言** | **全部通过** |

---

## 3. 详细阶段计划

### v0.2.0: 评估基线与骨架预热（05-18 ~ 05-24）

| 日期 | 重点任务 | 产出物 | 检查标准 |
|------|---------|--------|---------|
| 05-18 (一) | **显式化无冲突域契约** + Dreaming 骨架 + L2 指数衰减 GC | `write_domain_lock.py` + `consolidation_agent.py` | L0-L3 写入边界单测 + decay 单测通过 |
| 05-19 (二) | Eval 基线搭建 + 端到端评估脚本 | `evaluation/baseline.py` + `tests/test_eval_end_to_end.py` | 纯向量 RAG 基线可运行 |
| 05-20 (三) | PersonaInjector 实现 + 注入/弹出契约 | `persona/injector.py` | 切换人格后 L1 上下文正确注入 |
| 05-21 (四) | L3 Unlearning 骨架 + 过时知识标记 | `l3_semantic/unlearning.py` | deprecated 标记写入，不物理删除 |
| 05-22 (五) | 集成回归 + 文档刷新 | `tests/test_mock_pipeline.py` 全量通过 | `make test` 全绿 |
| 05-23~24 | 缓冲 / CR 修复 / 排期审视 | — | v0.2.0 交付物冻结 |

### v0.3.0: L3 + Intent Graph（05-25 ~ 05-31）

| 日期 | 重点任务 | 产出物 | 检查标准 |
|------|---------|--------|---------|
| 05-25 (一) | PostgreSQL Schema 落地 + 索引 | `migrations/001_init.sql` | `EXPLAIN` 确认复合索引生效 |
| 05-26 (二) | MVO 种子注入 + `IMVOSeedLoader` | `configs/mvo_extensions/` | 幂等加载，重复启动不报错 |
| 05-27 (三) | 8 类边 Tier 1 构建器 | `semantic_edges` 写入逻辑 | MENTIONS/TEMPORAL_NEXT/CAUSED 覆盖 |
| 05-28 (四) | Recursive CTE 导航 + 6 步检索 | `retrieval/intent_graph.py` | CTE 查询模板固化 |
| 05-29 (五) | 混合召回融合 + 性能基线 | `reports/perf_baseline.json` | Execution Time < 150ms |
| 05-30 (六) | **Checkpoint 3.1** | — | 10 轮对话稳定性测试 |
| 05-31 (日) | 缓冲 / 修复 | — | Recall@5 ≥ 0.6 |

**Checkpoint 3.1（05-30 周六）**:
- 通过标准:
  1. L3 经过 10 轮对话稳定性测试，MENTIONS / TEMPORAL_NEXT 边正确写入。
  2. Intent Graph CTE Recall@5 ≥ **0.6**（W3 基础达标线，验证 CTE 可用）。
  3. A1-A3 评估基线自动化脚本产出首份 JSON（允许部分指标为 `null`，框架必须跑通）。
- **A6 指标说明**: v0.3.0 的 0.6 为 CTE 可用标准；设计文档 8.2 要求的 A6 ≥ 0.8 为 **v0.6.0 优化目标**，依赖 CTE 性能调优与更多种子数据，**不阻塞 v0.3.0**。
- **若未通过**: v0.4.0 前 3 天全部用于修复 L3，Insight 模块顺延至 v0.5.0，保核心记忆链路。

### v0.4.0: Insight + 反思（06-01 ~ 06-07）

| 日期 | 重点任务 | 备注 |
|------|---------|------|
| 06-01 (一) | Checkpoint 3.1 复盘 / L3 修复 | Go/No-Go 决策日 |
| 06-02 (二) | `InsightGenerator` 框架 + 触发器 | 每 N 轮 / 每日凌晨 |
| 06-03 (三) | Insight 类型实现（pattern/trend/conflict） | `insights` 表写入 |
| 06-04 (四) | CAUSED Tier 2 统计共现 | 基于模板匹配的统计验证 |
| 06-05 (五) | A1/A2 评估 + Insight 辅助召回测试 | 自动化断言召回提升 |
| 06-06~07 | 缓冲 | — |

### v0.5.0: Agent 核心循环（06-08 ~ 06-14）

| 日期 | 重点任务 |
|------|---------|
| 06-08 (一) | `StateMachineAgentCore` 纯 Python 状态机: Input → Intent → Memory → LLM → Output（MVA 手写状态机满足管线需求，未引入外部 LangGraph 库） |
| 06-09 (二) | Intent Node（T0/T1 本地模型接入）+ Entity Extract（T2） |
| 06-10 (三) | Memory Node（分支 checkout + 混合检索） |
| 06-11 (四) | LLM Node + Persona Anchor 注入 + Emotion Filter |
| 06-12 (五) | Output Node + ActionPlanner + Emotion→Behavior 调制表 |
| 06-13 (六) | `trainable_emotion_model.py` LSTM 脚本 + `[RL-PLACEHOLDER]` 空接口 |
| 06-14 (日) | **评估前置**: A4-A5 自动化脚本 + `metrics.py` 骨架启动 | 利用缓冲期降低 v0.6.0 密度，产出 `tests/test_a4_a5.py` 框架 |
| **v0.5.0 收尾** | 06-14 (日) | **测试设计审查** | 全量测试语义审计，识别并回退"测试迁就实现" | 🟡 本次新增 |

### v0.6.0: 评估框架（06-15 ~ 06-21）

**⚠️ 06-15 (周一) 上午：强制测试设计审查（Test Design Review）**

| 时间 | 任务 | 产出物 | 检查标准 |
|------|------|--------|---------|
| 09:00-12:00 | 全量测试语义审计 | `reports/test_design_review.md` | 逐条检查所有 `assert` 是否基于业务语义而非实现巧合；识别并回退"测试迁就实现"的用例 |

**审查清单（必做）**：
1. [ ] 所有涉及数值比较的测试（如 `speed_mult`、`intensity`、`recall`）是否使用了边界值而非巧合值？
2. [ ] 是否存在"修改测试数据后通过，但业务语义上原数据同样合法"的提交？
3. [ ] 测试失败时，是否有未审查直接改测试预期的记录？
4. [ ] Mock 的行为是否与真实实现解耦？

**未通过标准**：若发现 ≥1 处"测试迁就实现"且未修复，则 v0.6.0 阶段全部评估任务阻塞，优先修复测试债务。

**⚠️ 假期影响**: 06-19（周五）端午节法定假，06-20~21 调休/周末，本周仅 **4 个工作日**。

**评估左移后目标**: A1-A3 框架已在 v0.3.0 Checkpoint 产出；本周聚焦 **A4-A11 补全 + 基线集成 + 最终量化表**。

| 日期 | 重点任务 |
|------|---------|
| 06-15 (一) | A4-A5 角色隔离/多端冲突补全（W5 周末已启动骨架） |
| 06-16 (二) | A6 意图图谱导航 + A7 情感一致性 |
| 06-17 (三) | A8 具身感知 + A9-A11 跨本体/可审计/漂移 |
| 06-18 (四) | `evaluation/baseline.py` 纯向量 RAG 基线 + `metrics.py` 最终集成 |
| 06-19 (五) | **端午节假期** — 提前完成或顺延至 06-22 |

**评估工作流**: v0.3.0 产 A1-A3 框架 → v0.5.0 阶段末产 A4-A5 骨架 → v0.6.0 补全 A6-A11 + 填满量化表。

### v0.7.0: 2D 世界 + 前端（06-22 ~ 06-28）

| 日期 | 重点任务 |
|------|---------|
| 06-22 (一) | GridWorld 20×20 世界模型 + FOV 感知 |
| 06-23 (二) | Token→Action Bridge: `EmbodiedAdapter` + 映射字典 |
| 06-24 (三) | ActionPlanner + 具身上下文注入 L1 |
| 06-25 (四) | 极简 HTML Canvas 前端 + WebSocket 连接 |
| 06-26 (五) | 前端联调：位置变化 → 对话内容差异验证 |
| 06-27~28 | Demo 视频录制缓冲 |

### v1.0.0: 文档与发布准备（06-29 ~ 07-05）

| 日期 | 重点任务 |
|------|---------|
| 06-29 (一) | README.md 重构（架构图、快速开始、评估结果）；启动《生产级记忆系统的十五个陷阱与防御策略》技术博客 |
| 06-30 (二) | 技术博客初稿：CRDT+MVCC 工程化、Intent Graph CTE 导航、Token→Action Bridge 跨本体迁移 |
| 07-01 (三) | Slide Deck（10 页提纲）：3 分钟项目介绍 + 5 分钟 Deep Dive |
| 07-02 (四) | **记忆系统 Beyond MVA 路线图文档化**：条件感知蒸馏器、记忆溯源链、动态重要性重算、硬预算截断 |
| 07-03 (五) | 全量文档 Review + 量化对比表最终数据填入 |
| 07-04~05 | 最终缓冲 / 预演 |

**v1.0.0 新增交付物**：
- `docs/beyond_mva.md`：记忆系统生产级优化路线图（15 项缺陷的防御策略索引）。

---

### v1.1.0 `production-baseline`：生产基线硬化（3 周）

**目标**：让 MVA 从"能跑 demo"变成"可上线单租户"。

| 阶段 | 重点任务 | 产出物 | 检查标准 |
|------|---------|--------|---------|
| 第 1 周 | 认证与权限完整实现 | `IAuthMiddleware` 真实实现 + 多租户 API Key + Branch 级 RBAC | 渗透测试基线：未授权访问 401/403 100% 拦截 |
| 第 2 周 | 硬预算截断 + 跨分支记忆继承过滤器 | `ICostTracker` 实时累加 + 80% 降级/100% 熔断；`IPrivacyFilter` + `IRelevanceFilter` | 单 session 成本告警准确率 100%，熔断无漏触发 |
| 第 3 周 | 记忆溯源链 + WebSocket 真实实现 + 全链路日志 trace | `MemoryEntry` / `Fact` `source_memory_ids` 落地；`WebSocketGateway` 双向推送；`loguru` 结构化 trace | 检索结果 100% 可溯源；WebSocket 与 Canvas 联动可用 |

**准入标准**：`make test` 保持 400+ passed，覆盖率不下降；渗透测试与预算告警同时通过。

---

### v1.2.0 `memory-quality`：记忆质量跃迁（3 周）

**目标**：解决"条件丢失"、"幻觉注入"、"重要性僵化"。

| 阶段 | 重点任务 | 产出物 | 检查标准 |
|------|---------|--------|---------|
| 第 1 周 | 条件感知蒸馏器 + 动态重要性重算 | `ReflectionAgent` Phase B NLP 条件句识别（`spacy` 依存解析）；月度批量重要性审计任务 | Dreaming 条件句保留率 ≥ 90%（人工抽检 100 条） |
| 第 2 周 | Spindle Gating 完整版 + 检索结果可解释性 | `InsightScheduler` `importance_score` + `confidence` 双门槛；`RetrievedContext.navigation_path` 详细溯源 | 检索结果 100% 附带 `navigation_path` |
| 第 3 周 | 边类型纠错 + 动态 max_hops | `EdgeBuilder` 置信度追踪与自动升级；按边类型配置 `max_hops` | `CORRELATED` → `CAUSED` 升级准确率 ≥ 80% |

**准入标准**：重要性重算后，用户核心偏好零误删；A6 Recall@5 保持 ≥ 0.8。

---

### v1.3.0 `graph-production`：图谱与检索生产化（4 周）

**目标**：IntentGraph 从"内存 dict"走向生产级持久化与分布式。

| 阶段 | 重点任务 | 产出物 | 检查标准 |
|------|---------|--------|---------|
| 第 1-2 周 | IntentGraph 持久化 + Episodic Store 分布式化 | PostgreSQL Recursive CTE 替换内存 BFS；`FaissEpisodicStore` → `QdrantEpisodicStore` | 10 万节点/50 万边 CTE P99 < 200ms；Qdrant 单节点降级不丢数据 |
| 第 3 周 | HybridRetriever Intent-Aware 融合 + 级联更新 | `HybridRetriever` `intent` 精确匹配 + 相似度降级；图边传播局部向量 delta | Intent-Aware 融合后 A6 Recall@5 ≥ 0.85 |
| 第 4 周 | 语义边类型扩展评估 | 按需新增 `supports` / `generalizes` / `specializes` / `co_occurs` | 节点数 >50K 后评估必要性，不强制引入 |

**准入标准**：图谱持久化后 A1-A11 评估集无回归；Qdrant 集群故障时降级读取可用。

---

### v1.4.0 `cognitive-deepening`：认知仿生深化（5 周）

**目标**：补齐 L4/L5 层级，实现 Dream 完整周期与元记忆。

| 阶段 | 重点任务 | 产出物 | 检查标准 |
|------|---------|--------|---------|
| 第 1-2 周 | L4 Procedural Memory 层 + Dream T2–T4 | `ActionPlanner` + `ISkill` 显式程序记忆；`BehavioralRule` 自动晋升；T2 冲突消解、T3 模式分离、T4 系统巩固 | L4 规则自动晋升准确率 ≥ 80%（人工审核） |
| 第 3-4 周 | Dream T5–T6 + L5 Meta-Memory 层 | T5 程序结晶（L4 晋升）、T6 元记忆更新；`Memory Worth` + 自适应检索策略权重 + Meta-Dream | Meta-Memory 动态权重调整后 A6 召回波动 < 5% |
| 第 5 周 | DynamicImportance + 动作执行后感知反馈闭环 | `successful_uses` / `failed_uses` 追踪；`GridWorldAdapter.execute()` 环境 diff 回写 L2 | Dream 完整周期端到端可用 |

**准入标准**：Dream 完整周期端到端可用（触发 → 提取 → 仲裁 → 巩固 → 结晶 → 元更新）。

---

### v1.5.0 `agent-autonomy`：智能体自治增强（3 周）

**目标**：自学习、自审计、复杂推理。

| 阶段 | 重点任务 | 产出物 | 检查标准 |
|------|---------|--------|---------|
| 第 1 周 | 评估框架 CI 集成 + Stochastic Replay | nightly 自动化评估流水线 + `locust` 性能回归；LLM 生成反事实变体压力测试因果结构 | 反事实回放不破坏图谱一致性 |
| 第 2 周 | VLA 可插拔接口真实实现 + Persona Drift 自动修复 | `predict_action()` 接入微调 VLA 模型（替换 LLM default）；相似度 < 0.75 自动强化注入 Persona Anchor | VLA 模型 grid_2d 动作预测准确率 ≥ 85% |
| 第 3 周 | ContextualBias / Cluster 感知检索 | 基于话题聚类的上下文检索偏置 | 全量评估 nightly 运行，失败自动告警 |

**准入标准**：VLA 动作预测 ≥ 85%；全量评估 nightly 自动化通过。

---

### v2.0.0 `architecture-refresh`：架构换代（6 周）

**目标**：解决手写状态机维护瓶颈，引入多模态。

| 阶段 | 重点任务 | 产出物 | 检查标准 |
|------|---------|--------|---------|
| 第 1-2 周 | LangGraph 状态机迁移 | `StateMachineAgentCore` → `StateGraph`，节点化 + 条件边路由 + 循环回退 | LangGraph 状态机 100% 兼容 A1-A11 评估集 |
| 第 3-4 周 | 真实多设备 CRDT 同步 + 多模态感知 | 手机/车机/音箱三端真实 WebSocket 组网；FOV 视觉+文本（CLIP 编码图像特征注入 L1） | 三端 CRDT 冲突收敛时间 < 3 秒；多模态端到端延迟增加 < 200ms |
| 第 5-6 周 | Semantic Merge Agent + 架构固化 | `CONTRADICTS` 高价值冲突触发 LLM 三路仲裁（Base/Left/Right），产出融合洞察 | 仲裁产出融合洞察准确率 ≥ 80%（人工抽检） |

**准入标准**：A1-A11 评估集 100% 通过；三端真实组网同步可用。

---

## 4. 关键里程碑与 Go/No-Go Checkpoint

| 检查点 | 日期 | 通过标准 | 未通过兜底 |
|--------|------|---------|-----------|
| **M1** | 05-17 | `make test` 262 passed, 94% coverage, 接口冻结 ✅ 已完成 | v0.2.0 前 2 天收尾，Insight 模块降级 |
| **Checkpoint 3.1** | 05-30 | L3 10 轮稳定性 + CTE Recall@5 ≥ 0.6 | v0.4.0 修 L3，Insight 延至 v0.5.0 |
| **M2** | 06-07 | A1/A2 召回测试自动化通过 | 砍 CAUSED Tier 2，保 Tier 1 |
| **M3** | 06-14 | 端到端 Agent 对话可用，情感状态机可观测 | 砍 LSTM 训练，保 Rule-based 情感 |
| **M4** | 06-21 (前) | 评估框架输出完整量化对比表 | 砍 A9-A11，保 A1-A6 |
| **M5** | 07-05 | README + Blog + Slide 完成 | — |

---

## 5. 假期与风险缓冲

| 风险项 | 影响时间 | 应对策略 |
|--------|---------|---------|
| **端午节假期** | 06-19~21 | v0.6.0 阶段压缩为 4 天；评估 metrics 函数提前至 v0.5.0 阶段开发 |
| **v0.1.0 收尾压力** | 05-15 | 若接口今日未冻结，严格限制 v0.2.0 前两天收口，禁止蔓延 |
| **Qwen3.5 本地性能不足** | v0.2.0–v0.3.0 | 立即降级 DS-V4-flash，不阻塞排期 |
| **PostgreSQL CTE 性能超标** | v0.3.0 | 若 Execution Time > 200ms，启用 MATERIALIZED CTE + 反向索引 |
| **排期风险** | 全局 | v0.4.0 Checkpoint 为核心分水岭：保记忆+评估，砍 Insight/2D 前端 |

---

## 6. 本周行动项（Action Items）

**负责人**: 全体  
**截止日期**: 2026-05-29 (v0.7.0 末审视)

1. 全量回归 `make test` 保持 400+ passed，`make eval` 保持 6/6 PASS。
2. 确认 `IntentGraph` 的 `get_edges()` / `navigate()` deprecated 过滤与 `status` 字段同步已闭环（代码 + 测试 + 文档）。
3. 启动 v1.0.0 文档：`README.md` 架构图刷新（含 L3 Prompt 注入、情感时序、跨本体映射的新设计）。
4. 完成 Beyond MVA 优化项在 `docs/requirements.md` 第12节与 `docs/schedule.md` 第7节的交叉 Review，确保设计描述、依赖条件与工时排期一致；**删除**已归并的 `docs/beyond_mva.md` 独立文件，避免三份数据源。
5. 评估 `serve_mva.py` 是否需要引入真实 WebSocket 依赖（`websockets` / `fastapi`）或保持 MVA 占位。
6. **（新增）新想法评估结论的立刻执行任务（v0.7.0 阶段穿插执行）**：
   - **A-MAC 简化版**：整合现有 `importance`/`access_count`/`ttl_hours` 为 `AdmissionScore`，增加 `TypePrior` 权重（procedural=1.0, preference=0.9, fact=0.6, chitchat=0.1）与两级阈值（<0.40 丢弃，0.40–0.65 仅 L2，≥0.65 L2+L3）。修改 `MemoryEntry` 与 `SimpleEpisodicStore.add()` 入口。
   - **L1 Budget 显式分层**：按 MVA 实际 token 预算（4K–8K）设定 `session_history=40%` / `retrieved_memories=30%` / `persona_anchor=20%` / `scratchpad=10%`，在 `WorkingMemoryWindow` 实现硬截断。
   - **Engram Schema 简化扩展**：为 `MemoryEntry` 增加 `abstracted_fact`、`affective_valence`、`source_turn_index`；`relation_graph` 保留为 Reflection Agent 异步产物，不阻塞主链路。
   - **Spindle Gating**：在 `InsightScheduler` 中增加 `importance_score` 硬门槛（≥0.7），低价值记忆不进入 Insight 处理队列。
   - **Affective VAD 轻量扩展**：`EmotionState` 增加 `valence`/`arousal`，映射到 `ActionPlanner` 调制表；舍弃 Dominance 维度。

---

*排期基线: 2026-05-22 | 下次基线审视: 2026-06-29 (v1.0.0 启动)*

---

## 7. v1.1.0+ 生产级优化路线图

以下优化项按版本号分组，从生产基线硬化到架构换代，共 5 个生产迭代 + 1 次架构换代。

### v1.1.0 `production-baseline`：生产基线硬化（3 周）

| 优化项 | 解决的问题 | 依赖条件 | 预估工时 |
|--------|-----------|---------|---------|
| **认证与权限完整实现** | MVA 单 Key 无隔离 | 多租户 API Key + Branch 级 RBAC | 3d |
| **硬预算截断** | 成本失控 | 实时 token 计数器 + 80%/100% 阈值 | 2d |
| **跨分支记忆继承过滤器** | 跨分支污染 | `IPrivacyFilter` + `IRelevanceFilter` | 3d |
| **记忆溯源链** | 幻觉注入、评估脱节 | `MemoryEntry`/`Fact` Schema 扩展 | 2d |
| **WebSocket 真实实现** | 前端联动不可用 | `WebSocketGateway` 双向推送 + Canvas | 2d |
| **全链路日志 trace** | 可观测性不足 | `loguru` 结构化 + 请求链 ID | 1d |

### v1.2.0 `memory-quality`：记忆质量跃迁（3 周）

| 优化项 | 解决的问题 | 依赖条件 | 预估工时 |
|--------|-----------|---------|---------|
| **条件感知蒸馏器** | 归纳遗漏（条件剥离） | NLP 条件句识别模块 | 3d |
| **动态重要性重算** | 短期波动固化、遗忘曲线僵化 | 定时任务 + 全表扫描基础设施 | 4d |
| **Spindle Gating 完整版** | 低价值 Insight 堆积 | `importance_score` + `confidence` 双门槛 | 1d |
| **检索结果可解释性** | "Recall@5 高但用户感觉健忘" | `navigation_path` 详细填充 | 2d |
| **边类型纠错机制** | 错误分类（边类型误标） | EdgeBuilder 置信度追踪增强 | 2d |
| **动态 max_hops** | 多跳推理断裂 | 按边类型配置 max_hops | 1d |

### v1.3.0 `graph-production`：图谱与检索生产化（4 周）

| 优化项 | 解决的问题 | 依赖条件 | 预估工时 |
|--------|-----------|---------|---------|
| **IntentGraph 持久化** | MVA 纯内存，进程重启丢失 | PostgreSQL 14+ + Recursive CTE | 4d |
| **Episodic Store 分布式化** | FAISS 无法横向扩展 | Qdrant HNSW + 多副本 + 快照恢复 | 3d |
| **HybridRetriever Intent-Aware 融合** | `intent` 参数未消费 | `HybridRetriever` 精确匹配 + 降级 | 1d |
| **Engram Cascade Update** | 全局重嵌入成本高 | 数据量 >100K 或 Qdrant 迁移后 | 4d |
| **语义边类型扩展** | 关系表达不足 | L3 节点数 >50K 后评估 | 2d |

### v1.4.0 `cognitive-deepening`：认知仿生深化（5 周）

| 优化项 | 解决的问题 | 依赖条件 | 预估工时 |
|--------|-----------|---------|---------|
| **L4 Procedural Memory 层** | Skill/Rule 未显式固化 | L3 积累足够 `BehavioralRule` 数据 | 4d |
| **Dream Phase T2–T6** | Dream 仅 T1，缺少完整周期 | T1 去重稳定运行 | 12d（分批） |
| **L5 Meta-Memory 层** | 无自监控层 | 多轮检索 outcome 数据积累 | 5d |
| **DynamicImportance（基于 outcome）** | 重要性无反馈闭环 | L5 Meta-Memory 基础设施 | 3d |
| **动作执行后感知反馈闭环** | 动作-结果记忆对缺失 | 2D 环境状态变化回写 L2 | 2d |

### v1.5.0 `agent-autonomy`：智能体自治增强（3 周）

| 优化项 | 解决的问题 | 依赖条件 | 预估工时 |
|--------|-----------|---------|---------|
| **Stochastic Replay / Counterfactuals** | 因果结构压力测试不足 | 实验性分支 | 4d |
| **评估框架 CI 集成** | 评估无法自动化回归 | nightly 流水线 + `locust` 基准 | 2d |
| **VLA 可插拔接口真实实现** | `[VLA-PLACEHOLDER]` 未解禁 | 微调 VLA 模型（替换 LLM default） | 3d |
| **Persona Drift 自动修复** | 漂移需人工干预 | 检测相似度 < 0.75 自动强化 Anchor | 1d |
| **ContextualBias / Cluster 感知检索** | 检索缺乏话题感知 | 话题聚类模块 | 2d |

### v2.0.0 `architecture-refresh`：架构换代（6 周）

| 优化项 | 解决的问题 | 依赖条件 | 预估工时 |
|--------|-----------|---------|---------|
| **LangGraph 状态机迁移** | 手写状态机维护瓶颈 | `langgraph` 库 + `StateGraph` 重构 | 3d |
| **真实多设备 CRDT 同步** | MVA 仅单端模拟 | 手机/车机/音箱三端 WebSocket 组网 | 3d |
| **多模态感知** | FOV 仅文本描述 | CLIP 编码图像特征注入 L1 | 4d |
| **Semantic Merge Agent** | CONTRADICTS 无智能仲裁 | LLM 三路仲裁（Base/Left/Right） | 3d |

**明确不采纳项（MVA 设计取舍，v1.1.0+ 仍不采纳）**：

| 项 | 不采纳理由 |
|----|-----------|
| **Causal Tier 1.5 启发式规则** | 当前 Tier 1 召回率 ~40% 是已知设计取舍。增加启发式规则会引入新的测试负担与误标风险，生产环境建议直接上 Tier 2 统计验证或 Tier 3 LLM 验证。 |
| **近因偏见显式修正** | 与 `access_count` 时间衰减（已落地）存在耦合，独立 `recency` 项需大量调参。`effective_access = access_count * exp(-days/30)` 已足够覆盖。 |
| **L1 分层保留原始轮次** | 已有 `CompressedSummary.source_turn_ids` 记录被压缩的原始索引。全量归档区需存储结构重构，收益不足以支持风险。 |
