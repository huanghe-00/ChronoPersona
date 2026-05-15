# ChronoPersona 项目执行排期表

**版本**: v1.0  
**基线日期**: 2026-05-15 (周五)  
**总工期**: 8 周（2026-05-11 ~ 2026-07-05）  
**当前状态**: Week 1 第 5 天（剩余 1 个工作日）

---

## 1. 排期总览（修订后）

| 周次 | 日期范围 | 阶段主题 | 核心交付物 | 状态 |
|------|---------|---------|-----------|------|
| **W1** | 05-11 ~ 05-17 | 契约与孤岛 | 接口冻结、Mock 全量、test_mock_pipeline 通过 | 🟡 收尾中 |
| **W2** | 05-18 ~ 05-24 | L0-L2 记忆核心 | LWW-CRDT、L1 滑动窗口、L2 Qdrant Mock、Session-MVCC | ⚪ 未开始 |
| **W3** | 05-25 ~ 05-31 | L3 + Intent Graph | PostgreSQL Schema、CTE 导航、MVO 种子、6 步检索 | ⚪ 未开始 |
| **W4** | 06-01 ~ 06-07 | Insight + 反思 | InsightGenerator、CAUSED Tier 2、A1/A2 召回测试 | ⚪ 未开始 |
| **W5** | 06-08 ~ 06-14 | Agent 核心循环 | LangGraph 状态机、LSTM 脚本、RL/VLA Placeholder | ⚪ 未开始 |
| **W6** | 06-15 ~ 06-21 | 评估框架 | A1-A11 对抗测试集、量化对比表、报告流水线 | ⚪ 未开始 |
| **W7** | 06-22 ~ 06-28 | 2D 世界 + 前端 | GridWorld、Action Bridge、极简 Canvas 前端 | ⚪ 未开始 |
| **W8** | 06-29 ~ 07-05 | 文档与面试 | README、技术博客、Slide Deck、Demo 脚本 | ⚪ 未开始 |

---

## 2. Week 1 收尾（今日 05-15 紧急）

**假设**: Week 1 从 05-11（周一）启动，已消耗 4 个工作日。

**今日必须完成（硬阻塞）**:
- [ ] `contracts/interfaces/` 下全部接口文件冻结，合并至 `main`（仅 W1 核心 5 个接口，`IPersonaInjector`/`ICostTracker` 等留 [FUTURE] 空壳）
- [ ] `mocks/` 全量实现与 `tests/test_mock_pipeline.py` 通过（28 个用例）
- [ ] LWW-CRDT 接口替换 Yjs（`IL0SyncLayer` / `ILWWMap`）
- [ ] PostgreSQL Schema + MVO 种子 SQL 文件合入（仅 6 张核心表，`insights`/`embodied_interactions` 标记为 [FUTURE]）

**28 个测试用例清单（W1 验收）**:

| 编号 | 用例类别 | 数量 | 验证目标 |
|------|---------|------|---------|
| T01-T05 | 端到端与基础 | 5 | Mock 对话、分支隔离、LWW merge、意图检索、人格注入 |
| T06-T10 | CRDT 核心 | 5 | merge、clock skew、conflict、sync broadcast、offline replay |
| T29-T31 | L0 CRDT 接口 | 3 | get/set、merge conflict、checkpoint |
| T11-T15 | Memory 层级 | 5 | L0/L1/L2/L3 读写、checkout、snapshot |
| T16-T20 | Agent 节点 | 5 | state machine、intent、memory node、LLM node、output node |
| T21-T25 | API 与序列化 | 5 | REST、WebSocket、error handling、schema validation、auth mock |
| T26-T28 | 集成回归 | 3 | full pipeline、persona switch、eval injection |
| T29-T31 | L0 CRDT | 3 | get/set、merge conflict、checkpoint |

**若今日未完成**: 占用 **W2 前 2 天（05-18/19）** 收尾，但不得超过 2 天，否则触发 **Checkpoint 1.1**（砍 Insight 模块，保 L0-L3 核心链路）。

---

## 3. 详细阶段计划

### Week 2: L0-L2 记忆核心（05-18 ~ 05-24）

| 日期 | 重点任务 | 产出物 | 检查标准 |
|------|---------|--------|---------|
| 05-18 (一) | L0 `LWWMap` 实现 + HLC 时钟 | `l0_crdt/lww_map.py` | 单测覆盖 merge、clock skew 检测 |
| 05-19 (二) | L1 Working Memory 滑动窗口 + 压缩 | `l1_working/sliding_window.py` | 超 token 阈值触发 LLM 摘要 |
| 05-20 (三) | L2 Episodic Mock 接入 + BGE Embedding | `l2_episodic/mock_store.py` | Qdrant Mock 支持 payload 过滤 |
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
