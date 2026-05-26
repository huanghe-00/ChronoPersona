# ChronoPersona 面试备忘（Cheat Sheet）

## 1. 项目一句话定位

> ChronoPersona 是一个面向生产级 AI Companion 的长期记忆系统，核心差异化是将 **CRDT 分布式一致性**与 **MVCC 版本化记忆**引入 Agent 架构，解决多端同步冲突、角色人格漂移、记忆幻觉三大痛点，同时通过 Token→Action Bridge 实现人格与身体的解耦。

---

## 2. 技术亮点与数据支撑

| 面试官问题 | 关键数据 | 可展开点 |
|-----------|---------|---------|
| "你们的测试覆盖率怎么样？" | **39 个测试文件，400+ passed，94% 语句覆盖率** | A1-A11 对抗评估全自动化，`make test` 唯一入口 |
| "多端同步怎么做？" | 自研 LWWMap + HLC（500ms skew 检测），1,000 节点 P99 < 2ms | add-wins 语义；clock-skew 时保留双版本 + `CONTRADICTS` 边 |
| "角色隔离怎么保证不串台？" | `branch_id` 显式传递，物理隔离；`IntentGraph` 按 branch 存储 | 类比 git checkout；L1 session 结束即丢弃 |
| "记忆幻觉怎么解决？" | Faiss `_deleted_indices` 过滤 + `SemanticEdge.status` 过滤 | 幽灵记忆消除；反学习 deprecated 边即时生效 |
| "情感状态怎么影响行为？" | CONCERNED 降速 50%、音量降 20%；NEUTRAL 基准不降速 | H1 时序修复：`_update_emotion` 前置于 ActionPlanner |
| "评估框架有什么？" | A1-A11 对抗测试集 + `evaluation/runner.py` 量化报告 | 向量基线 vs 意图图谱导航的对比；Recall@5 / MRR |

---

## 3. 已知缺陷与坦诚应答（加分项）

**Q: "你们的系统有什么生产级缺陷？"**

**标准答法**：
1. **条件感知蒸馏缺失**：Dreaming 阶段 LLM 摘要会丢失"如果/除非"等条件从句。MVA 阶段 Schema 已预留 `BehavioralRule.trigger`，但 NLP 条件句识别模块推迟到 W8+。
2. **MockBGEEmbedder 的局限性**：当前基于文本长度生成确定性向量，无法检测语义近重复（如"short" vs "short version"）。生产环境必须替换为 sentence-transformers。
3. **WebSocket 实时联调未完成**：`serve_mva.py` 已提供零依赖 HTTP API（`POST /chat` 返回结构化 JSON），但 WebSocket 双向实时推送与 Canvas 前端数据联动仍待 W8+。

**禁忌**：不要试图掩盖缺陷；面试官更欣赏对边界的清醒认知。

---

## 4. 架构决策深潜（可能被追问）

### 4.1 为什么不用 Yjs，要自研 CRDT？

> Yjs 是通用文本协同库，但我们的场景是 KV 存储 + add-wins 语义。自研 `LWWMap` 可以：
> 1. 精确控制 HLC 物理时间 + 逻辑计数器的比较逻辑；
> 2. 嵌入 clock-skew 检测（500ms 阈值），这是 Yjs 不具备的；
> 3. 避免引入整个 Yjs 依赖树（MVA 追求轻量）。

### 4.2 为什么情感引擎用 T0 规则 + LSTM，不用端到端 LLM？

> 1. **确定性**：T0 规则引擎对"难过/焦虑"等关键词的响应是 100% 可预期的，LLM 可能因 Prompt 变化产生漂移；
> 2. **资源效率**：Qwen3.5-9B 本地推理 ~100ms+，T0 规则 <1ms；
> 3. **可审计**：规则触发的 emotion state 可以精确追溯原因（`trigger_reason`），LLM 的黑盒 reasoning 难以调试。
> LSTM 回归器作为 Layer 2，用于捕捉"连续 5 轮负面输入"这类规则无法覆盖的时序模式。

### 4.3 为什么 Intent Graph 用 8 类边而不是更少的通用边？

> 8 类边来自对对话场景的语义分析：
> - `MENTIONS`：指代消解（"那个餐厅" → 具体实体）
> - `CAUSED`：因果回溯（"为什么焦虑" → 工作压力）
> - `TEMPORAL_NEXT`：时序推理（"方案后来怎样" → 实施记忆）
> - `CONTRADICTS`：多端冲突保留
> - `SIMILAR_TO`：平行比较（"川菜和粤菜哪个好"）
> 减少边类型会损失这些特定检索路径；增加更多类型会导致边稀疏、导航效率下降。8 类是在 A1-A11 评估中验证的甜点。

---

## 5. 演示脚本（3 分钟版本）

```bash
# 1. 全量测试（展示工程纪律）
make test  # 400+ passed

# 2. 评估报告（展示量化思维）
make eval  # A1-A6 量化 JSON

# 3. 2D 世界演示（展示具身智能）
python scripts/serve_mva.py  # 启动 MVA 服务器
# 浏览器打开 frontend/index.html，展示 20×20 网格 + Agent 位置
```

---

*版本: v1.0 | 日期: 2026-05-22 | 下次更新: W8 结束*
