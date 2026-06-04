# ChronoPersona 技术汇报 Slide Deck

> **主题**：人格与记忆的模块化融合——可迁移 Agent 架构探索  
> **时长**：3 分钟项目介绍 + 5 分钟 Deep Dive + 2 分钟 Q&A  
> **版本**：v1.0.0 MVA 冻结

---

## Slide 1：封面

**ChronoPersona**  
人格与记忆的模块化融合：探索可迁移 Agent 架构的前沿验证平台

- 技术探索项目 | Python | MIT License
- 432 tests passed | 94% coverage | 8 个迭代 MVA

---

## Slide 2：问题定义——AI Companion 的三大痛点

| 痛点 | 现状 | 后果 |
|------|------|------|
| **记忆幻觉** | 纯向量检索召回相似但错误的记忆 | 手机号 138→139 错误召回 |
| **多端冲突** | 手机/车机各自为政 | 偏好设置互相覆盖 |
| **角色串台** | Prompt 替换，记忆共享无隔离 | 心理医生知道 RPG 剧情 |

> **核心洞察**：记忆的可靠性不是锦上添花，而是 AI Companion 的根基。

---

## Slide 3：核心差异化——4 大架构创新

1. **LWW-CRDT 多端同步**：自研轻量 CRDT，HLC 混合逻辑时钟，冲突保留不覆盖
2. **MVCC 角色分支**：`git checkout` 式物理隔离，分支间记忆零穿透
3. **意图图谱导航**：8 类语义边 + 8 类意图策略，结构化检索替代纯向量
4. **Token→Action Bridge**：人格与身体解耦，零样本跨本体迁移

---

## Slide 4：系统架构总览

```
User Input → Intent Node → Memory Node → LLM Node → ActionPlanner → Output
                ↑              ↑            ↑
           L0 CRDT      L1/L2/L3      Persona Anchor
           (Sync)       (Retrieve)    + Emotion Modulation
```

- **分层记忆**：L0 同步 / L1 工作 / L2 情景 / L3 语义
- **双层情感**：T0 规则引擎（确定性）+ LSTM 骨架（可训练插槽）

---

## Slide 5：工程硬核——CRDT & MVCC

**LWW-CRDT 自研**
- 替换 Yjs，基于 HLC（物理时间 + 逻辑计数器）add-wins
- 500ms clock-skew 检测，超出阈值保留双版本 + `CONTRADICTS` 边
- 1,000 节点 P99 < 2ms

**MVCC Branch**
- `main` / `therapist` / `rpg-hero` 物理隔离
- L2 Session-MVCC：每 session 结束打 snapshot
- L3 Entity-MVCC：每条事实独立版本链

---

## Slide 6：意图图谱导航——比 RAG 更聪明的检索

**纯向量 RAG 的局限**
- "我上周的方案后来怎样" → 无法关联时序
- "川菜和粤菜我喜欢哪个" → 无法聚合对比

**ChronoPersona 方案**
- 8 类语义边：`IS_A` / `MENTIONS` / `TEMPORAL_NEXT` / `CAUSED` / `CONTRADICTS` / `BELONGS_TO` / `SIMILAR_TO` / `TRIGGERED_BY`
- 8 类意图策略：retrieve / temporal_trace / causal_explore / empathize / ...
- 混合召回：`0.6 × graph_score + 0.4 × vector_score`

---

## Slide 7：情感调制与跨本体迁移

**Emotion→Behavior 调制表**
| 状态 | 速度 | 音量 | 距离 |
|------|------|------|------|
| NEUTRAL | 1.0x | 1.0x | 1.5m |
| CONCERNED | 0.5x | 0.8x | 0.8m |

**Token→Action Bridge**
- LLM 输出 `approach_gently`
- `ActionPlanner` 应用情感调制
- `EmbodiedAdapter` 翻译为 grid_2d / ROS2 / MuJoCo 指令
- **同一套人格，零样本迁移到任意机器人本体**

---

## Slide 8：评估框架——A1-A11 对抗测试

| 场景 | 验证目标 |
|------|---------|
| A1-A2 | 记忆召回与跨 session 关联 |
| A3-A4 | 角色隔离与共享穿透 |
| A5 | 多端 CRDT 冲突合并 |
| A6 | 意图图谱导航精度 |
| A7-A11 | 情感一致性 / 具身感知 / 跨本体迁移 / 动作可审计 / 人格漂移 |

**工程纪律**：432 passed / 94% coverage / 测试语义红线（禁止"测试迁就实现"）

---

## Slide 9：MVA 穿插改进与生产路线图

**v0.7.0 已落地的 5 项增强**
- A-MAC 准入评分（TypePrior 加权 + 两级阈值）
- L1 Budget 显式分层（40/30/20/10 硬截断）
- Engram Schema 扩展（abstracted_fact / affective_valence）
- Spindle Gating（importance ≥ 0.7 硬门槛）
- Affective VAD（valence / arousal 接入行为调制）

**v1.1.0–v2.0.0 路线图**
- v1.1.0 生产基线硬化（认证 / 预算 / 隐私过滤）
- v1.2.0 记忆质量跃迁（条件蒸馏 / 动态重要性）
- v1.3.0 图谱生产化（PostgreSQL CTE / Qdrant）
- v1.4.0 认知深化（L4/L5 / Dream 全周期）
- v2.0.0 架构换代（LangGraph / 多模态）

---

## Slide 10：结语与 Q&A

> **"带镣铐的建筑"**  
> 在端侧内存 / Token 配额 / 开发周期的极限约束下，构建生产级可靠的 AI Agent 记忆大脑。

**快速验证**
```bash
git clone <repo>
pip install -r requirements.txt
make test        # 432 passed
make eval        # A1-A11 量化报告
python scripts/serve_mva.py  # 启动 API + WebSocket
```

**Q&A**

---
