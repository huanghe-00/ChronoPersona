# Slide Deck: ChronoPersona 面试提纲

## Slide 1: 封面（30 秒）
**标题**: 带镣铐的建筑：CRDT + MVCC 构建 AI Agent 记忆大脑  
**副标题**: ChronoPersona —— 一个不会失忆、不串台、可跨本体移植的长期记忆系统  
**数据锚点**: 8 周 MVA | 39 测试文件 400+ passed | 94% 覆盖率

---

## Slide 2: 问题定义（45 秒）
**三大痛点**:
1. **多端同步冲突**: 手机"喜欢川菜" vs 车机"不能吃辣" → 传统方案后写覆盖或粗暴合并
2. **角色人格串台**: therapist 知道 companion 的日常，companion 知道 therapist 的医疗诊断
3. **记忆幻觉与遗忘**: LLM 摘要丢失条件从句，高频噪声淹没低频关键信号

**面试官钩子**: "这不是 RAG 能解决的问题，需要重新设计记忆的存储与检索架构。"

---

## Slide 3: 核心洞察（45 秒）
**记忆 = 带版本的多人协作**

| 借鉴领域 | 核心抽象 | ChronoPersona 落地 |
|---------|---------|-------------------|
| 分布式系统 | CRDT 最终一致性 | 自研 `LWWMap` + `HybridTimestamp` |
| 数据库 | MVCC 版本隔离 | `branch_id` 物理隔离 = `git checkout` |
| 认知科学 | 意图图谱导航 | 8 类语义边 + 8 类意图策略 |

---

## Slide 4: CRDT 多端同步（90 秒）
**架构图**: `LWWMap` + HLC + add-wins

**关键数据**:
- 设计目标: 1,000 节点 P99 < 2ms（MVA 阶段未压测，基于 HLC 比较逻辑的复杂度推导）
- 500ms clock-skew 检测，超阈值保留双版本 + `CONTRADICTS` 边
- `MAX_CONTRADICT_KEYS: 10` 软限制防止冲突堆积

**Demo 命令**: `pytest tests/test_l0_crdt.py -v`

---

## Slide 5: MVCC 人格隔离（60 秒）
**类比**: `git checkout` —— 切换 branch = 切换人格，物理隔离非逻辑隔离

**关键机制**:
- `branch_id` 显式传递，禁止默认全局分支
- L1 session 结束即丢弃，L2/L3 按 branch 隔离
- 跨 branch merge 需 `IPrivacyFilter` + `IRelevanceFilter`（W8+）

**Demo 命令**: `pytest tests/test_a4_a5.py -v`

---

## Slide 6: 意图图谱导航（90 秒）
**超越向量检索**: "手机没电了" vs "手机丢了" 向量相似但意图完全不同

**8 类边 + 8 类意图**:
- `MENTIONS` → 指代消解
- `CAUSED` → 因果回溯
- `TEMPORAL_NEXT` → 时序推理
- `CONTRADICTS` → 多端冲突保留

**混合召回**: 0.6 × 图谱 + 0.4 × 向量

---

## Slide 7: 情感引擎与具身智能（60 秒）
**情感时序修复（H1）**: `_update_emotion` 前置于 `ActionPlanner`，确保调制参数基于当前轮次

**Token→Action Bridge**:
- CONCERNED → 降速 50%、音量降 20%
- 同一"灵魂"驱动 grid_2d / ros2_mobile / MuJoCo
- 每个动作附带 `reasoning`，100% 可审计

---

## Slide 8: 评估框架（45 秒）
**A1-A11 对抗测试集**: 覆盖记忆召回、角色隔离、多端冲突、情感一致性等

**双轨评估**:
- pytest 断言驱动（PASS/FAIL）
- `evaluation/runner.py` 量化指标（Recall@5 / MRR）

**关键红线**: 识别并回退 1 处"测试迁就实现"（NEUTRAL 基准缺陷）

---

## Slide 9: 已知缺陷与 Beyond MVA（45 秒）
**坦诚加分项**:
1. 条件感知蒸馏缺失（Dreaming 丢失"如果/除非"）
2. MockBGEEmbedder 局限性（长度-based，非语义）
3. WebSocket 联调未完成

**路线图**: `docs/beyond_mva.md` —— 15 项缺陷的防御策略索引

---

## Slide 10: 结语（30 秒）
> "记忆的可靠性不是锦上添花，而是 AI Companion 的根基。"

**核心差异化**: 不是更大的模型，而是更可靠的架构 —— CRDT + MVCC + 意图图谱。

**联系方式**: [GitHub 占位] | [邮箱占位]

---

## 附录：面试官可能深挖的问题

**Q1**: "为什么不用 Yjs 要自研 CRDT？"  
**A**: 精确控制 HLC + clock-skew 检测 + 避免引入整个 Yjs 依赖树。

**Q2**: "Intent Graph 8 类边会不会太多？"  
**A**: 来自对话场景的语义分析，减少会损失检索路径，增加会导致边稀疏。8 类是 A1-A11 评估验证的甜点。

**Q3**: "评估指标高但用户仍感觉健忘怎么办？"  
**A**: 这是排序截断问题，roadmap 中有 Retrieval Explanation + `navigation_path` 逐条追溯。
