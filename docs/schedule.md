# ChronoPersona 项目执行排期表

**版本**: v1.5  
**基线日期**: 2026-05-15 (周五)  
**总工期**: 8 周（2026-05-11 ~ 2026-07-05）  
**当前状态**: Week 1 已完成，Week 2 启动中（258 passed / 94% coverage / W1 MVA 闭合）

---

## 1. 排期总览（修订后）

| 周次 | 日期范围 | 阶段主题 | 核心交付物 | 状态 |
|------|---------|---------|-----------|------|
| **W1** | 05-11 ~ 05-17 | 契约与孤岛 | 接口冻结(14个)、Mock全量(12个)、真实节点(5个)、测试258 passed 覆盖率94% | ✅ 已完成 |
| **W2** | 05-18 ~ 05-24 | 评估基线与骨架预热 | Dreaming骨架、L2指数衰减GC、Eval基线、PersonaInjector | 🟡 进行中 |
| **W3** | 05-25 ~ 05-31 | L3 + Intent Graph | PostgreSQL Schema、CTE 导航、MVO 种子、6 步检索 | ⚪ 未开始 |
| **W4** | 06-01 ~ 06-07 | Insight + 反思 | InsightGenerator、CAUSED Tier 2、A1/A2 召回测试 | ⚪ 未开始 |
| **W5** | 06-08 ~ 06-14 | Agent 核心循环 | LangGraph 状态机、LSTM 脚本、RL/VLA Placeholder | ⚪ 未开始 |
| **W6** | 06-15 ~ 06-21 | 评估框架 | A1-A11 对抗测试集、量化对比表、报告流水线 | ⚪ 未开始 |
| **W7** | 06-22 ~ 06-28 | 2D 世界 + 前端 | GridWorld、Action Bridge、极简 Canvas 前端 | ⚪ 未开始 |
| **W8** | 06-29 ~ 07-05 | 文档与面试 | README、技术博客、Slide Deck、Demo 脚本 | ⚪ 未开始 |

---

## 2. Week 1 完成总结（05-15 基线锚定）

**实际达成**：
- `contracts/interfaces/` 14 个抽象接口全部冻结并导出。
- `mocks/` 12 个 Mock 实现 100% 覆盖对应接口。
- `tests/` 新增 12 个专门测试文件，全量 **258 passed, 1 skipped, 0 failed**；语句覆盖率 **94%**。
- 真实实现交付：`L0SyncLayer`（HLC + add-wins + clock-skew）、`GridWorldAdapter`（FOV + 边界钳制）、`IntentGraph`/`IntentNavigator`（BFS + 意图模式匹配）、`StateMachineAgentCore`（端到端状态机）、`WorkingMemoryWindow`（滑动窗口 + 动态压缩）。
- 关键缺陷修复：`L0SyncLayer.get_delta()` 运行时 `NameError`（缺失 `self.`）。
- PLACEHOLDER 合规：`test_caused_tier2.py` 正确 skip，无违规实现复杂算法。
- Anthropic 借鉴点吸收：`MemoryEntry` 重要性评分 Schema 落地、L2 检索加权实现。

**W1 验收测试矩阵**：

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
| **合计** | **16 个测试文件** | **258** | **全部通过** |

---

## 3. 详细阶段计划

### Week 2: L0-L2 记忆核心（05-18 ~ 05-24）

| 日期 | 重点任务 | 产出物 | 检查标准 |
|------|---------|--------|---------|
| 05-18 (一) | L0 `LWWMap` 实现 + HLC 时钟 | `l0_crdt/lww_map.py` | 单测覆盖 merge、clock skew 检测 |
| 05-19 (二) | L1 Working Memory 滑动窗口 + 压缩 | `l1_working/sliding_window.py` | 超 token 阈值触发 LLM 摘要 |
| 05-20 (三) | L2 Episodic Mock 接入 + BGE Embedding | `l2_episodic/mock_store.py` | ✅ Qdrant Mock 支持 payload 过滤 |
| 05-21 (四) | L2 Session-MVCC Snapshot | `session_snapshots` 表写入 | 会话结束自动打 snapshot |
| 05-22 (五) | L0-L2 集成 + 多端冲突模拟 | `tests/test_l0_l2_integration.py` | CONTRADICTS 边正确生成 |
| 05-23~24 | 缓冲 / 文档 / CR 修复 | — | `make test` 全绿 |

### Week 3: L3 + Intent Graph（05-25 ~ 05-31）

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
- **A6 指标说明**: W3 的 0.6 为 CTE 可用标准；设计文档 8.2 要求的 A6 ≥ 0.8 为 **W6 优化目标**，依赖 CTE 性能调优与更多种子数据，**不阻塞 W3**。
- **若未通过**: Week 4 前 3 天全部用于修复 L3，Insight 模块顺延至 Week 5，保核心记忆链路。

### Week 4: Insight + 反思（06-01 ~ 06-07）

| 日期 | 重点任务 | 备注 |
|------|---------|------|
| 06-01 (一) | Checkpoint 3.1 复盘 / L3 修复 | Go/No-Go 决策日 |
| 06-02 (二) | `InsightGenerator` 框架 + 触发器 | 每 N 轮 / 每日凌晨 |
| 06-03 (三) | Insight 类型实现（pattern/trend/conflict） | `insights` 表写入 |
| 06-04 (四) | CAUSED Tier 2 统计共现 | 基于模板匹配的统计验证 |
| 06-05 (五) | A1/A2 评估 + Insight 辅助召回测试 | 自动化断言召回提升 |
| 06-06~07 | 缓冲 | — |

### Week 5: Agent 核心循环（06-08 ~ 06-14）

| 日期 | 重点任务 |
|------|---------|
| 06-08 (一) | LangGraph State Machine: Input → Intent → Memory → LLM → Output |
| 06-09 (二) | Intent Node（T0/T1 本地模型接入）+ Entity Extract（T2） |
| 06-10 (三) | Memory Node（分支 checkout + 混合检索） |
| 06-11 (四) | LLM Node + Persona Anchor 注入 + Emotion Filter |
| 06-12 (五) | Output Node + ActionPlanner + Emotion→Behavior 调制表 |
| 06-13 (六) | `trainable_emotion_model.py` LSTM 脚本 + `[RL-PLACEHOLDER]` 空接口 |
| 06-14 (日) | **评估前置**: A4-A5 自动化脚本 + `metrics.py` 骨架启动 | 利用周末降低 W6 密度，产出 `tests/test_a4_a5.py` 框架 |

### Week 6: 评估框架（06-15 ~ 06-21）

**⚠️ 假期影响**: 06-19（周五）端午节法定假，06-20~21 调休/周末，本周仅 **4 个工作日**。

**评估左移后目标**: A1-A3 框架已在 W3 Checkpoint 产出；本周聚焦 **A4-A11 补全 + 基线集成 + 最终量化表**。

| 日期 | 重点任务 |
|------|---------|
| 06-15 (一) | A4-A5 角色隔离/多端冲突补全（W5 周末已启动骨架） |
| 06-16 (二) | A6 意图图谱导航 + A7 情感一致性 |
| 06-17 (三) | A8 具身感知 + A9-A11 跨本体/可审计/漂移 |
| 06-18 (四) | `evaluation/baseline.py` 纯向量 RAG 基线 + `metrics.py` 最终集成 |
| 06-19 (五) | **端午节假期** — 提前完成或顺延至 06-22 |

**评估工作流**: W3 产 A1-A3 框架 → W5 周末产 A4-A5 骨架 → W6 补全 A6-A11 + 填满量化表。

### Week 7: 2D 世界 + 前端（06-22 ~ 06-28）

| 日期 | 重点任务 |
|------|---------|
| 06-22 (一) | GridWorld 20×20 世界模型 + FOV 感知 |
| 06-23 (二) | Token→Action Bridge: `EmbodiedAdapter` + 映射字典 |
| 06-24 (三) | ActionPlanner + 具身上下文注入 L1 |
| 06-25 (四) | 极简 HTML Canvas 前端 + WebSocket 连接 |
| 06-26 (五) | 前端联调：位置变化 → 对话内容差异验证 |
| 06-27~28 | Demo 视频录制缓冲 |

### Week 8: 文档与面试（06-29 ~ 07-05）

| 日期 | 重点任务 |
|------|---------|
| 06-29 (一) | README.md 重构（架构图、快速开始、评估结果） |
| 06-30 (二) | 技术博客初稿 |
| 07-01 (三) | Slide Deck（10 页面试提纲） |
| 07-02 (四) | 3 分钟介绍 + 5 分钟 Deep Dive 脚本定稿 |
| 07-03 (五) | 全量文档 Review + 量化对比表最终数据填入 |
| 07-04~05 | 最终缓冲 / 预演 |

---

## 4. 关键里程碑与 Go/No-Go Checkpoint

| 检查点 | 日期 | 通过标准 | 未通过兜底 |
|--------|------|---------|-----------|
| **M1** | 05-17 | `make test` 28 个用例通过，接口冻结 | W2 前 2 天收尾，Insight 模块降级 |
| **Checkpoint 3.1** | 05-30 | L3 10 轮稳定性 + CTE Recall@5 ≥ 0.6 | W4 修 L3，Insight 延至 W5 |
| **M2** | 06-07 | A1/A2 召回测试自动化通过 | 砍 CAUSED Tier 2，保 Tier 1 |
| **M3** | 06-14 | 端到端 Agent 对话可用，情感状态机可观测 | 砍 LSTM 训练，保 Rule-based 情感 |
| **M4** | 06-21 (前) | 评估框架输出完整量化对比表 | 砍 A9-A11，保 A1-A6 |
| **M5** | 07-05 | README + Blog + Slide 完成 | — |

---

## 5. 假期与风险缓冲

| 风险项 | 影响时间 | 应对策略 |
|--------|---------|---------|
| **端午节假期** | 06-19~21 | Week 6 压缩为 4 天；评估 metrics 函数提前至 Week 5 开发 |
| **Week 1 今日收尾压力** | 05-15 | 若接口今日未冻结，严格限制 W2 前两天收口，禁止蔓延 |
| **Qwen3.5 本地性能不足** | W2-W3 | 立即降级 DS-V4-flash，不阻塞排期 |
| **PostgreSQL CTE 性能超标** | W3 | 若 Execution Time > 200ms，启用 MATERIALIZED CTE + 反向索引 |
| **8 周做不完** | 全局 | Week 4 Checkpoint 为核心分水岭：保记忆+评估，砍 Insight/2D 前端 |

---

## 6. 本周行动项（Action Items）

**负责人**: 全体  
**截止日期**: 2026-05-15 20:00

1. `contracts/interfaces/` 全部接口通过 Code Review 并合并。
2. `tests/test_mock_pipeline.py` 在 CI 中跑通 28 个用例。
3. `mocks/` 下所有依赖（Qdrant/PostgreSQL/LLM）Mock 实现 100% 覆盖。
4. 冻结接口后，任何变更必须经过 **接口变更审批单**（防止 Week 2 后仍改接口导致连锁反应）。

---

*排期基线: 2026-05-15 | 下次基线审视: 2026-05-22 (Week 2 结束)*
