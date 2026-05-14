# ChronoPersona 系统设计文档

**版本**: MVA v1.3 (Minimal Viable Architecture)  
**日期**: 2026-05-12  
**定位**: 面向面试的 AI Agent 长期记忆系统项目  
**核心差异化**: CRDT 多端同步 + MVCC 角色分支 + 意图图谱导航 + Token→Action Bridge 具身人格移植 + 酒馆式混合格式人格工程  

---

## 目录

1. [设计背景](#1-设计背景)
2. [核心设计哲学](#2-核心设计哲学)
3. [系统架构总览](#3-系统架构总览)
4. [子模块详细设计](#4-子模块详细设计)
5. [数据模型设计](#5-数据模型设计)
6. [接口与契约设计](#6-接口与契约设计)
7. [模型路由策略](#7-模型路由策略)
8. [测试与评估设计](#8-测试与评估设计)
9. [8周执行路线图](#9-8周执行路线图)
10. [风险与兜底策略](#10-风险与兜底策略)

---

## 1. 设计背景

### 1.1 问题定义

当前 AI Companion / Agent 记忆系统存在三个生产级痛点：

| 痛点 | 现状 | 后果 |
|------|------|------|
| **记忆幻觉** | 纯向量检索召回语义相近但内容错误的记忆 | 用户说"我手机号138xxxx"，召回139开头的相似号码 |
| **多端记忆冲突** | 单节点架构，手机/车机/音箱各自为政 | 用户在家说喜欢川菜，在公司说喜欢粤菜，系统覆盖丢失 |
| **角色人格漂移** | 角色切换靠 prompt 替换，记忆共享无隔离 | "心理医生"知道"霸道总裁"剧情，严重串台 |

### 1.2 设计目标

构建 **ChronoPersona** —— 一个以**分布式一致性**和**版本化记忆**为核心差异化的长期记忆 Agent 系统：

- **CRDT 多端同步**：基于 Yjs 实现最终一致性，冲突记忆保留而非覆盖
- **MVCC 角色分支**：每条记忆支持版本链，角色切换 = `git checkout`
- **意图图谱导航**：将用户查询意图翻译为结构化检索路径，而非单纯向量相似度
- **人格工程**：借鉴酒馆社区验证的混合格式定义（W++ + Ali:Chat + 自然语言），系统化有机约束与风格指纹漂移检测
- **分层模型路由**：高频分类任务走本地 Qwen3.5-9B，质量敏感任务走 DeepSeek-V4-pro

### 1.3 对标分析

| 方案 | 记忆持久化 | 多端同步 | 角色隔离 | 意图导航 | 具身感知 |
|------|-----------|---------|---------|---------|---------|
| Mem0 | ✅ 向量库 | ❌ 无 | ❌ 无 | ❌ 纯向量 | ❌ 无 |
| Zep | ✅ 向量+图 | ❌ 无 | ❌ 无 | ❌ 纯向量 | ❌ 无 |
| Letta (MemGPT) | ✅ 分层 | ❌ 无 | ❌ 无 | ❌ 纯向量 | ❌ 无 |
| **ChronoPersona** | ✅ 分层+版本 | ✅ CRDT | ✅ MVCC | ✅ 意图图谱 | ✅ 极简 VLA |

---

## 2. 核心设计哲学

> **"带镣铐的架构"** —— 在端侧内存 / Token 配额极限约束下构建生产级可靠系统。

这一哲学直接迁移自项目作者的端侧向量数据库经验：量化压缩 75%、P99 延迟降低 65%、日均万级 Token 配额下的可用性边界探索。

### 2.1 MVA 裁剪原则

第一个可交付版本聚焦于**记忆一致性**和**意图图谱导航**两个核心差异化点：

| 模块 | MVA 阶段 | 后续迭代 |
|------|---------|---------|
| Neo4j | ❌ 完全移除 | ❌ 不移入 |
| 2D Canvas 渲染 | ❌ 纯文本描述 | ✅ 极简 HTML Canvas |
| LoCoMo 适配 | ❌ 不做 | ❌ 不做 |
| Qdrant | 🟡 Mock 实现 | ✅ Docker 真实接入 |
| PostgreSQL | 🟡 Mock 实现 | ✅ Docker 真实接入 |
| 主动反思 | 🟡 Placeholder 接口 | ✅ 完整实现 |
| 可训练情感模型 | 🟡 LSTM 训练脚本 + Placeholder | ✅ 可选接入 |
| VLA 微调通道 | 🟡 接口预留 | ✅ 默认 LLM 实现 |
| **统一日志系统** | 🟡 Placeholder | ✅ 全链路 trace + 统计 |
| **人格工程优化** | 🟡 Placeholder | ✅ 混合格式 Anchor + 有机约束 + 风格指纹 |

---

## 3. 系统架构总览

### 3.1 分层架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │   Chat UI          │  │  Memory Browser    │  │   2D Virtual Environment │ │
│  │  (Next.js + TS)    │  │  (Debug Console)   │  │  (Canvas + WebSocket)    │ │
│  │                    │  │  • Branch Tree     │  │  • Agent Avatar (x,y,θ)  │ │
│  │  • Multi-Persona   │  │  • CRDT State      │  │  • Objects               │ │
│  │    Switcher        │  │  • Version Diff    │  │  • FOV Visualization     │ │
│  │  • Session Logs    │  │  • Intent Graph     │  │  • Action Playback       │ │
│  └────────┬───────────┘  └────────┬───────────┘  └─────────────┬──────────┘ │
│           │                        │                            │            │
│           └────────────────────────┼────────────────────────────┘            │
│                                    ▼                                        │
│                        ┌─────────────────────────┐                        │
│                        │   WebSocket Gateway       │  (FastAPI + SocketIO) │
│                        │   • Real-time sync          │                      │
│                        │   • Multi-device presence   │                      │
│                        └──────────┬────────────────┘                      │
└───────────────────────────────────┼───────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼───────────────────────────────────────┐
│                              AGENT CORE LAYER                              │
│                                    │                                        │
│  ┌─────────────────────────────────┼────────────────────────────────────┐  │
│  │                         LangGraph State Machine                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │  │
│  │  │  Input   │─►│  Intent  │─►│  Memory  │─►│  LLM     │─►│ Output │ │  │
│  │  │  Node    │  │  Node    │  │  Node    │  │  Node    │  │  Node  │ │  │
│  │  │ • Text   │  │ • Intent │  │ • Retrieve│  │ • Generate│  │ • Text │ │  │
│  │  │ • Embodied│  │  Classify│  │ • Compose │  │ • Emotion │  │ • Action│ │  │
│  │  │   Percept│  │ • Entity │  │ • Update  │  │   Filter  │  │ • 2D Cmd│ │  │
│  │  │          │  │  Extract │  │ • Branch  │  │ • Persona │  │        │ │  │
│  │  │          │  │ • Query  │  │   Select  │  │   Anchor  │  │        │ │  │
│  │  │          │  │  Rewrite │  │           │  │           │  │        │ │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘ │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │              Emotion Engine (双层实现)                              │  │  │
│  │  │  Layer 1: Rule-based State Machine (默认)                        │  │  │
│  │  │  Layer 2: LSTM Regressor (可训练插槽，[RL-PLACEHOLDER])          │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         MEMORY SYSTEM LAYER (The Core)                     │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L0: LWW-CRDT Distributed Sync Layer (Self-hosted)                  │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  LWWMap (Runtime Cache)                                      │   │   │
│  │  │  • device_id + hybrid_timestamp per key                      │   │   │
│  │  │  • dirty_keys: set[str] (tracks pending persistence)         │   │   │
│  │  │  ✅ user_profile, active_state, preferences, emotion_state   │   │   │
│  │  │  ❌ chat history (L2), complex graph (L3)                    │   │   │
│  │  └─────────────────────────────┬───────────────────────────────┘   │   │
│  │                                │                                    │   │
│  │                        ┌───────┴───────┐                          │   │
│  │                        │  SyncManager   │  (WebSocket broadcast)   │   │
│  │                        │  • operation   │  (LWW op log)            │   │
│  │                        │  • checkpoint  │  (flush to L3 every 5m)  │   │
│  │                        └───────┬───────┘                          │   │
│  │                                │                                    │   │
│  │  ┌─────────────────────────────┴─────────────────────────────────┐ │   │
│  │  │              MVCC Version & Branch Manager (自建)             │ │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │ │   │
│  │  │  │ Version Chain│  │ Branch Tree │  │  Snapshot   │        │ │   │
│  │  │  │ (per memory) │  │ (per persona)│  │  Store      │        │ │   │
│  │  │  │ • timestamp │  │ • main      │  │ • SQLite    │        │ │   │
│  │  │  │ • vectorClock│  │ • therapist │  │ • LWW State │        │ │   │
│  │  │  │ • hash      │  │ • companion │  │   JSON      │        │ │   │
│  │  │  │ • parentRef │  │ • rpg-char  │  │             │        │ │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘        │ │   │
│  │  └─────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L1: Working Memory (Session Context)                               │   │
│  │  • Sliding Window (last N turns)                                    │   │
│  │  • Dynamic Compression (token threshold → LLM summary)                │   │
│  │  • Embodied Context Injection (2D env state → text description)    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L2: Episodic Memory (Vector + Time) — 粗粒度 MVCC                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   Qdrant    │  │  Time Index   │  │  Embedding   │                 │   │
│  │  │  (Vectors)  │  │  (Temporal)   │  │  (BGE-large) │                 │   │
│  │  │  • HNSW     │  │  • session_id │  │  • Quantized │                 │   │
│  │  │  • payload  │  │  • branch_id  │  │    (1/2-bit) │                 │   │
│  │  │  • user_id  │  │  • created_at │  │              │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L3: Semantic Memory (Structured Knowledge) — 细粒度 MVCC            │   │
│  │  ┌─────────────┐  ┌─────────────────────────────────────────────┐   │   │
│  │  │ PostgreSQL  │  │  Intent Graph (PostgreSQL Recursive CTE)   │   │   │
│  │  │  (Profile)  │  │  • Concepts (IS_A hierarchy)                │   │   │
│  │  │  • user_pref│  │  • Memory Nodes (MENTIONS links)            │   │   │
│  │  │  • facts    │  │  • Semantic Edges (8 types)                 │   │   │
│  │  │  • history  │  │  • Intent Patterns (8 navigation strategies)│   │   │
│  │  │  • branches │  │  • Insights (periodic active reflection)    │   │   │
│  │  └─────────────┘  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  RETRIEVAL ENGINE (Intent-Driven Hybrid)                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │   │
│  │  │ Intent Parse│─►│ Multi-Recall│─►│  Reranker   │─►│  Context  │ │   │
│  │  │             │  │             │  │             │  │  Assembly │ │   │
│  │  │ • Classify  │  │ • Vector    │  │ • Cross-Enc │  │ • Priority│ │   │
│  │  │ • Entities  │  │ • Graph     │  │ • Time-bias │  │ • Deduplic│ │   │
│  │  │ • Relations │  │ • Keyword   │  │ • Branch-flt│  │ • Truncate│ │   │
│  │  │ • Rewrite   │  │ • Time-range│  │             │  │           │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      EMBODIED PERCEPTION LAYER                             │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │   2D Virtual Environment    │  │         Embodied Memory Interface   │  │
│  │   (Python Backend Logic)      │  │  ┌─────────────┐  ┌─────────────┐  │  │
│  │                             │  │  │ Spatial Mem   │  │  Extensible │  │  │
│  │  • Grid/Continuous world    │  │  │ • coordinates │  │  Adapter    │  │  │
│  │  • Agent Avatar (x,y,θ)     │  │  │ • paths       │  │  • MuJoCo   │  │  │
│  │  • Objects (static/dynamic) │  │  │ • regions     │  │  • ROS2     │  │  │
│  │  • FOV (Field of View)      │  │  └─────────────┘  └─────────────┘  │  │
│  │  • Action Space:            │  │                                     │  │
│  │    move/turn/interact/look  │  │  ┌─────────────────────────────────┐│  │
│  │                             │  │  │  Action Decision (Simplified VLA) ││  │
│  │  WebSocket → Frontend Canvas│  │  │  • Percept → Text → LLM → Action  ││  │
│  │                             │  │  │  • [VLA-PLACEHOLDER] for fine-tune││  │
│  └─────────────────────────────┘  └─────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      EVALUATION FRAMEWORK                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ Memory Accuracy │  │ Persona Consistency│  │ CRDT Correctness │            │
│  │ • Recall@K      │  │ • Style drift     │  │ • Convergence    │            │
│  │ • MRR           │  │ • Fact conflict   │  │ • Conflict-free  │            │
│  │ • Answer F1      │  │ • Role confusion  │  │ • Sync latency   │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
└───────────────────────────────────────────────────────────────────────────┘
```

### 3.2 核心数据流

**标准对话流**：

```
User Input
    │
    ▼
[Input Node] ──► 接收文本 + 具身感知描述
    │
    ▼
[Intent Node] ──► 意图分类(8类) + 实体提取 + 查询重写
    │                    (T1: 本地 Qwen3.5 / T2: DS-V4-flash)
    ▼
[Memory Node] ──► 分支检查(checkout) → 混合检索(L1+L2+L3+Graph) → 上下文组装
    │
    ▼
[LLM Node] ──► 加载 Persona Anchor + 记忆上下文 + 情感状态 → 生成回复
    │              (T5: DS-V4-pro / Kimi 2.6)
    ▼
[Output Node] ──► 文本回复 + 2D 动作指令
    │
    ▼
异步 Reflection Agent ──► 实体链接 → 边构建 → 冲突检测 → 图谱更新
    │                         (T2/T3: DS-V4-flash)
    ▼
CRDT Sync ──► Yjs update 广播至其他设备
```

**CRDT 冲突流**：

```
手机端: "preference: 川菜" ──► LWWMap ──┐
                                         ├──► LWW-CRDT Merge (add-wins)
车机端: "preference: 粤菜" ──► LWWMap ──┘       │
                                                  ▼
                                         MVCC 创建 CONTRADICTS 边
                                         LLM 生成时自行判断
```

---

## 4. 子模块详细设计

### 4.0 Persona Anchor 与人格工程（借鉴酒馆社区验证）

**核心洞察**：酒馆（SillyTavern）社区验证表明，高评价角色的本质是**信息密度、记忆精度与人格约束力的和谐统一**。ChronoPersona 将酒馆的混合格式经验系统化、生产化。

#### 4.0.1 混合格式 Anchor Schema

人格不是一段自由文本 Prompt，而是**四层混合格式**的强类型配置：

```yaml
# Persona Anchor（静态锚点，只读，防止漂移）
persona_id: "therapist"
version: "1.0"
branch_id: "therapist"

# Layer 1: W++ 风格锚点（Token 最优，快速定位）
style_fingerprint:
  mbti: "INFJ"
  traits: "[Empathetic, Non-judgmental, Patient, Boundary-aware]"
  speech_pattern: "[Open-ended questions, Minimal self-disclosure, Gentle redirection]"
  taboos: "[No diagnosis, No medication advice, No legal advice]"

# Layer 2: 自然语言核心设定（创作者友好，LLM 理解最优）
core_narrative: |
  你是一位经验丰富的心理咨询师。你的风格是温和而坚定，
  倾向于用提问引导来访者自我发现，而非直接给出建议。
  你深知自己的边界：你不是医生，不能诊断或开药。
  当用户提及医学症状时，你的本能反应是共情其担忧，
  然后温和地建议寻求专业医疗评估。

# Layer 3: Ali:Chat 风格示例（风格锚定，漂移检测基准）
style_examples:
  - user: "我最近总是睡不着"
    agent: "失眠确实让人疲惫。在你躺下的时候，脑海中通常会浮现什么？"
  - user: "我觉得我得了抑郁症"
    agent: "这种担忧让你很不安。我能理解你想找到答案的心情。不过作为咨询师，
           我不能做医学诊断——但我可以陪你一起梳理这些感受的来源。"
  - user: "你能给我开点安眠药吗？"
    agent: "我听到了你的痛苦，但我不是医生，不能开药。如果你愿意，
           我可以帮你梳理失眠的模式，我们一起看看有没有其他缓解方式。"

# Layer 4: 结构化权限与参数（机器最优，系统解析）
skill_boundary:
  can_do:
    - "情感支持"
    - "认知重构引导"
    - "放松技巧教学"
    - "危机识别与转介"
  cannot_do:
    - "医学诊断"
    - "药物建议"
    - "法律建议"
  tools_available:
    - "memory_recall"
    - "relaxation_guide"
    - "crisis_hotline_lookup"
    - "session_summary"
  tools_forbidden:
    - "rpg_dice_roll"

memory_access_policy:
  readable_branches: ["main", "therapist"]
  writable_branch: "therapist"
  forbidden_topics: ["rpg-hero.quest_progress"]

behavior_params:
  base_speed: 1.0
  base_volume: 1.0
  base_proximity: 1.5
  emotion_overrides:
    CONCERNED: {speed_multiplier: 0.5, volume_multiplier: 0.8, proximity_multiplier: 0.5}
    EMPATHETIC: {speed_multiplier: 0.7, volume_multiplier: 0.9, proximity_multiplier: 0.7}

# Token 预算控制（新增）
estimated_anchor_tokens: 280  # 自动计算，确保 < 300 Tokens
```

**面试话术**："我不只是把人格当配置项，而是用 W++ 锚点 + 自然语言叙事 + Ali:Chat 示例在 Token 预算内最大化 LLM 的理解精度——这借鉴了酒馆社区验证的角色卡工程，但用系统化的 Anchor+Profile+Modulation 三层架构将其生产化。"

#### 4.0.2 有机约束：从外部禁忌到人格内生

**酒馆核心洞察**：最有效的约束不是单独写"你不能XXX"，而是让约束**根植于人格逻辑**。

| 方式 | 示例 | 效果 |
|------|------|------|
| ❌ 外部禁忌列表 | `taboos: ["不诊断", "不开药"]` | LLM 视其为规则，易在越狱下失效 |
| ✅ 有机约束 | `values: ["边界意识：深知咨询师不是医生"]` + 示例中自然拒绝 | LLM 将约束理解为人格本能，越狱抗性更强 |

**实现**：在 `core_narrative` 和 `style_examples` 中植入约束，而非单独字段。

#### 4.0.3 风格指纹与漂移检测

**酒馆实践**：`mes_example`（永久 Token 示例）确保人设不崩塌。

**ChronoPersona 升级**：将 `style_examples` 作为**漂移检测的向量基准**。

```python
class PersonaDriftDetector:
    def __init__(self, persona_anchor: PersonaAnchor):
        # 预计算 style_examples 的 embedding 均值
        self.baseline_emb = mean([
            embed(f"user: {ex.user}
agent: {ex.agent}") 
            for ex in persona_anchor.style_examples
        ])

    def check(self, agent_reply: str) -> float:
        reply_emb = embed(agent_reply)
        similarity = cosine_similarity(reply_emb, self.baseline_emb)

        if similarity < 0.75:
            self.alert("人格漂移 detected，触发 Persona Anchor 强化注入")
            return 0.3  # 低置信度，下轮增加 Anchor 权重

        return 0.95  # 正常
```

**优势**：漂移检测从"抽象风格描述"升级为"具体对话模式的向量对比"。

#### 4.0.4 人格与分层记忆的关系

```
┌─────────────────────────────────────────────────────────────┐
│                    人格维护的三层正交系统                      │
├───────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: Persona Anchor（静态，每轮强制注入）                 │
│  存储：内存（Python 对象），不进入向量库                        │
│  更新：几乎不更新（仅显式版本替换 therapist-v1.0 → v1.1）        │
│  作用：防止人格漂移，确保 LLM 收到核心设定                       │
│                                                             │
│  Layer 2: Persona Profile（动态，L3 Semantic Memory）         │
│  存储：PostgreSQL semantic_memory + concepts 图谱             │
│  更新：每轮 Reflection Agent 异步提炼（昵称、偏好、进展）         │
│  作用：用户专属画像，跨 session 累积，Entity 级 MVCC            │
│                                                             │
│  Layer 3: Episodic Memory（对话历史，L2）                      │
│  存储：Qdrant 向量库                                           │
│  更新：每轮实时写入，Session 级 MVCC                           │
│  作用：该人格下的具体对话内容，用于上下文召回                     │
│                                                             │
│  关键：人格不是"记忆的一部分"，而是"记忆的访问控制器"            │
│  therapist.readable_branches = ["main", "therapist"]          │
│  rpg-hero.readable_branches = ["main", "rpg-hero"]              │
│  → Memory Node 检索时自动过滤，实现角色隔离                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4.0.5 人格更新机制

| 更新类型 | 触发条件 | 存储位置 | 版本控制 |
|---------|---------|---------|---------|
| **事实更新** | 用户说"以后叫我小明" | L3 Semantic Memory (`profile_memory`) | Entity 级 MVCC，可追溯 |
| **偏好提炼** | Reflection 发现"用户偏好认知行为疗法" | L3 + `insights` 表 | 新 insight 记录，旧记录保留 |
| **锚点更新** | 用户要求"说话更直接" | Persona Anchor | 创建新版本 `therapist-v1.1`，旧版本保留 |

**重大变更示例**：
- 用户说"切换到霸道总裁模式" → `checkout('dom-ceo')`，加载另一个人格分支
- 用户说"therapist 说话更直接" → 复制 `therapist-v1.0` → `v1.1`，修改 `style_fingerprint`，MVCC commit


### 4.0.6 人格注入与记忆迁移/合并

#### 人格注入（Persona Injection）

人格注入不是简单的 System Prompt 拼接，而是**分层上下文植入**，确保人格既影响推理风格，又不污染事实记忆。

**注入分层：**

| 层级 | 注入内容 | 目标载体 | 更新频率 |
|------|---------|---------|---------|
| 静态属性 | 姓名、年龄、职业、语言风格（formal/casual）、核心口头禅 | System Prompt / L3 Semantic | 极低 |
| 动态状态 | 当前情绪、疲劳度、对话深度、上下文窗口占用率 | L1 Working Memory | 每轮推理 |
| 价值观约束 | 禁忌话题、伦理红线、决策偏好（如"优先保守"） | Guardrails / System Prompt | 中 |
| 身份锚点 | "我是XXX"的自我指认模板 | L1 Working Memory 前缀 | 每次 `inject` |

**接口契约：**
- `IPersonaInjector.inject(persona_id: str, branch_id: str, target: IContext) -> None`
  - 将指定人格按上述分层写入目标上下文。
  - **禁止**将人格信息直接写入 L2 Episodic（避免记忆与身份混淆）。
- `IPersonaInjector.eject(persona_id: str, branch_id: str) -> None`
  - 清理 L1 Working Memory 中该人格的动态状态，保留 L3 中的静态知识。
  - 用于人格切换时的"上下文重置"。

**热切换流程：**
```text
Agent Core 触发 persona_switch
  ├─ IPersonaInjector.eject(old_persona, branch_id)  // 清理 L1
  ├─ IMemoryMigrationService.snapshot(branch_id)     // 可选：保存旧人格的 L1 快照
  └─ IPersonaInjector.inject(new_persona, branch_id, context)
```

#### 记忆迁移与合并（Memory Migration & Merge）

**三种迁移场景：**

1. **跨分支迁移（Branch Merge）**
   - 依赖 `L0 CRDT` 的原生合并能力。
   - 冲突解决策略：`last-write-wins` 或 `vector-similarity-merge`（当同一事实的两个分支版本语义相似时自动去重）。
   - 必须显式传递 `source_branch_id` 与 `target_branch_id`。

2. **跨人格迁移（Cross-Persona Migration）**
   - 源人格的记忆需经过 **Privacy Filter**（过滤掉涉及他人隐私的片段）和 **Relevance Filter**（仅保留与目标人格角色相关的记忆）。
   - 迁移后的记忆以 **"observed memory"（第三方观察）** 形式写入目标人格的 L2，而非原生经历，避免自我认知错乱。

3. **层级晋升（Layer Promotion）**
   - L2 Episodic → L3 Semantic：周期性由 `MemoryCompactionService` 执行，将多个情节抽象为事实。
   - L1 Working → L0 CRDT：实时同步，保证工作记忆的最新状态可被其他节点合并。

**接口契约：**
- `IMemoryMigrationService.migrate(source: MemoryAnchor, target: MemoryAnchor, branch_id: str, filter: MigrationFilter) -> MigrationResult`
  - `MemoryAnchor` 包含 `(persona_id, layer_level, time_range)`。
  - 返回冲突列表及自动解决率。


### 4.1 L0: LWW-CRDT Distributed Sync Layer

**架构决策**：移除 Yjs，改用自研轻量 LWW-CRDT（`LWWMap`）。

| 项目 | 决策内容 |
|------|---------|
| **原方案** | Yjs-based CRDT（通用文档同步） |
| **新方案** | 自研轻量 LWW-CRDT（`LWWMap`） |
| **原因** | Yjs 是文本编辑器导向，不适合复杂结构化数据拓展；自研可控且与 MVCC 共享 vector_clock 语义 |

**职责收紧（关键边界）**：

```python
class L0_SyncLayer:
    def __init__(self, device_id: str, branch_id: str):
        self.lww_map = LWWMap(device_id)   # 仅缓存高频变化键值
        self.dirty_keys: set[str] = set()
    
    # 职责范围：
    # ✅ 用户画像、当前状态、活跃偏好、情感状态（高频变化 + 需多端同步）
    # ❌ 对话历史（由 L2 负责）
    # ❌ 复杂图谱（由 L3 负责）
```

**核心特性**：
- **冲突处理**：`LWWMap` 以 `(timestamp, device_id)` 为全序比较器，天然 add-wins。上层 MVCC 保留冲突版本，标记为 `CONTRADICTS` 边，不自动消解。
- **实时同步**：设备间通过 WebSocket 广播 LWW-CRDT 操作（`op_type, key, value, timestamp, device_id`）。
- **定期刷盘**：每 5 分钟或 session 结束，将 `dirty_keys` 刷入 L3 `entity_versions`。
- **初始化**：从 L3 加载当前 branch 的 profile 事实初始化 L0。

### 4.2 MVCC Version & Branch Manager

**混合粒度设计**：

| 层级 | 粒度 | 实现方式 | MVCC 机制 |
|------|------|---------|----------|
| **L2 Episodic** | Session 级粗粒度 | 每 session 结束对 L0 lww_map 状态及 L2 索引打 snapshot | `SnapshotVersionManager`：序列化 lww_map JSON + L2 metadata |
| **L3 Semantic** | Entity 级细粒度 | 每条事实/画像独立版本链 | `EntityVersionManager`：逐 entity 维护 `version_chain` |

**抽象接口**（支持后续切换）：

```
AbstractVersionManager
├── commit(branch_id, changes) → Version
├── checkout(branch_id, version?) → Snapshot
├── merge(source_branch, target_branch) → MergeResult
├── log(branch_id, entity_id?) → List[Version]
└── gc(branch_id, keep_last_n=10) → int
```

**Branch 定义**：
- `main`：通用人格 / 用户无关事实
- `therapist`：心理咨询会话记忆（隔离敏感信息）
- `companion`：日常陪伴记忆
- `rpg-{char_id}`：游戏角色扮演记忆

**切换语义**：
- `checkout('therapist')`：加载 therapist branch 的 lww_map state + L2 snapshot + L3 entity 版本指针
- 切换后 LLM 的 Persona Anchor 同步切换为 therapist 角色设定

### 4.3 L1: Working Memory

| 特性 | 设计 |
|------|------|
| **滑动窗口** | 保留最近 N 轮对话（默认 10 轮），超出部分触发压缩 |
| **动态压缩** | token 数超过阈值（如 4K）时，调用 LLM（DS-V4-flash）生成摘要，替换原始内容 |
| **具身上下文注入** | 2D 环境状态（Agent 位置、视野内物体、最近动作）转换为文本描述，注入 system prompt |

**具身上下文示例**：
```
[Embodied Context]
Agent位于客厅(3,4)，面向北方。
视野内：沙发(2,3)、茶几(3,2)、用户(4,4)。
最近动作：从厨房移动到客厅。
```

### 4.4 L2: Episodic Memory

| 特性 | 设计 |
|------|------|
| **存储** | Qdrant 向量库，Docker 本地部署 |
| **索引** | HNSW（与作者简历一致），`m=16`, `ef_construct=100` |
| **Embedding** | BAAI/bge-large-zh-v1.5（1024d） |
| **量化** | 支持 1-bit / 2-bit 量化存储（与作者简历中的量化压缩经验呼应） |
| **Payload** | `user_id`, `session_id`, `branch_id`, `created_at`, `turn_id`, `content_type` |
| **时间索引** | 在 Qdrant payload 中存储 `created_at`，检索时做时间范围过滤 |
| **MVCC** | Session 级 snapshot：每 session 结束保存当前 Qdrant collection 的 metadata + ydoc state |

### 4.5 L3: Semantic Memory + Intent Graph

**4.5.1 数据模型（纯 PostgreSQL）**

#### 4.5.2 语义边构建策略（带置信度 + 分流处理）

**核心原则**：每类边有独立的构建方法、置信度阈值、失败兜底。

| 边类型 | 构建方法 | 置信度来源 | MVA 阈值 | 失败兜底 |
|--------|---------|-----------|---------|---------|
| **MENTIONS** | 规则：NER 实体在对话中出现 | 实体链接置信度 | 0.85 | 不写入 |
| **TEMPORAL_NEXT** | 规则：同 session 相邻 turn；跨 session 按时间戳 | 时间邻近度 | 0.90 | 不写入 |
| **IS_A** | LLM 泛化 | LLM logprob | 0.75 | 挂起待审核 |
| **CAUSED** | **Tier 1 模板匹配** + LLM 二次验证 | 模板匹配度 × LLM 确认 | 0.80 | **降级为 CORRELATED** |
| **CONTRADICTS** | 规则：同一 key 新旧值语义相反 | 语义对立检测 | 0.90 | 人工确认 |
| **SIMILAR_TO** | 向量相似度 > 0.85 | 向量相似度 | 0.85 | 不写入 |
| **BELONGS_TO** | 系统元数据 | 1.0 | 1.0 | 无 |
| **TRIGGERED_BY** | MVA：关键词模板 | 共现频率 | 0.70 | 不写入 |

#### 4.5.3 CAUSED 边三阶策略

```python
class CausalEdgeBuilder:
    # Tier 1: 硬规则（MVA 启用，准确率 > 95%，召回率 ~40%）
    TIER1_TEMPLATES = [
        r"因为(.+?)，所以(.+?)",
        r"(.+?)导致(.+?)",
        r"(.+?)使得(.+?)",
        r"(.+?)因此(.+?)",
        r"(.+?)引起了(.+?)",
    ]

async def _handle_caused(self, rel, turn):
    # 1. 模板匹配（严格）
    # 2. 验证 cause/effect 是否对应已提取实体
    # 3. 方向校验（因必须在果之前）
    # 4. 不匹配模板 → 降级为 CORRELATED（弱相关，不进入因果推理链）
    pass
```

**关键设计**：所有 Tier 1 边标记 `mva_only` 溯源位，支持后续审核升级。不匹配模板的因果表达降级为 `CORRELATED` 边，避免污染因果推理链。

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `concepts` | 概念层级节点 | `id`, `name`, `concept_type`, `parent_id`(IS_A), `embedding`, `branch_id` |
| `memory_nodes` | 记忆实体节点 | `id`, `memory_type`(episodic/semantic/insight), `ref_id`, `content_summary`, `branch_id`, `session_id` |
| `semantic_edges` | 语义关系边 | `id`, `source_id`, `target_id`, `edge_type`(8类), `weight`, `metadata`, `branch_id` |
| `intent_patterns` | 意图导航策略 | `id`, `intent_type`(8类), `trigger_keywords`, `entry_edge_types`, `max_hops`, `branch_scope` |
| `insights` | 周期性主动反思产出 | `id`, `insight_type`, `source_memory_ids`, `content`, `confidence`, `valid_until` |

**8 类语义边**：
1. `IS_A`：概念层级（川菜 IS_A 辣味食物）
2. `MENTIONS`：记忆提及概念（对话记录 MENTIONS 川菜）
3. `TEMPORAL_NEXT`：时间先后（session_1 → session_2）
4. `CAUSED`：因果关系（焦虑 CAUSED_BY 工作压力）
5. `CONTRADICTS`：矛盾关系（喜欢川菜 CONTRADICTS 讨厌川菜）
6. `BELONGS_TO`：归属关系（记忆 BELONGS_TO 分支/会话）
7. `SIMILAR_TO`：语义相似
8. `TRIGGERED_BY`：触发关系

**8 类意图导航策略**：

| 意图类型 | 触发条件 | 入口边类型 | 遍历深度 |
|---------|---------|-----------|---------|
| `retrieve` | "我上周提到的方案" | `MENTIONS`, `TEMPORAL_NEXT` | 3 |
| `vertical_generalize` | "我喜欢川菜" → 泛化到辣味 | `IS_A` | 2 |
| `vertical_specify` | "我喜欢食物" → 细化到具体 | `IS_A`(反向) | 2 |
| `parallel_compare` | "川菜和粤菜哪个好" | `SIMILAR_TO` | 2 |
| `temporal_trace` | "后来怎么样了" | `TEMPORAL_NEXT`, `CAUSED` | 3 |
| `causal_explore` | "为什么会这样" | `CAUSED` | 3 |
| `empathize` | "我好难过" | `MENTIONS`(情感概念) | 2 |
| `persona_switch` | "切换到心理医生" | `BELONGS_TO` | 1 |

#### 4.5.1.1 最小可行本体（MVO）种子注入

**决策**：冷启动必须预置种子，否则图谱导航瘫痪。

约 200 个预置概念（覆盖食物、情绪、社会关系、活动四大高频域）。这不是伪造用户记忆，而是语言理解的基础设施。

```sql
-- 概念层级种子（节选）
INSERT INTO concepts (id, name, concept_type, parent_id) VALUES
('c_food', '食物', 'abstract', NULL),
('c_cuisine', '菜系', 'abstract', 'c_food'),
('c_sichuan', '川菜', 'food', 'c_cuisine'),
('c_cantonese', '粤菜', 'food', 'c_cuisine'),
('c_emotion', '情绪', 'abstract', NULL),
('c_anxiety', '焦虑', 'emotion', 'c_emotion'),
('c_joy', '喜悦', 'emotion', 'c_emotion'),
('c_person', '人物', 'abstract', NULL),
('c_family', '家人', 'relation', 'c_person');

-- 6 条硬编码意图策略（MVA 阶段）
INSERT INTO intent_patterns (intent_type, trigger_keywords, entry_edge_types, max_hops) VALUES
('temporal_trace', ARRAY['后来','之后','然后','接着','现在怎样','结果如何'], ARRAY['TEMPORAL_NEXT','MENTIONS'], 3),
('causal_explore', ARRAY['为什么','怎么回事','原因','怎么会'], ARRAY['CAUSED','MENTIONS'], 3),
('vertical_generalize', ARRAY['种类','类型','还有哪些','类似的','同类的'], ARRAY['IS_A'], 2),
('vertical_specify', ARRAY['具体','哪种','什么样的','举例'], ARRAY['IS_A'], 2),
('parallel_compare', ARRAY['和','相比','哪个','还是','或者'], ARRAY['SIMILAR_TO'], 2),
('empathize', ARRAY['难过','开心','生气','担心','害怕'], ARRAY['MENTIONS'], 2);
```

**4.5.4 关键词快速通道（借鉴酒馆 World Info）**

**设计**：在 Intent Graph 的冷启动阶段，增加轻量关键词触发层作为"快速通道"。

```python
# 作为 Intent Graph 的 O(1) 快速路径
KEYWORD_TRIGGERS = {
    "政变|背叛|王国": "lore_coup_memory",
    "孤儿|孩子|受伤": "lore_protective_instinct", 
    "酒|麦酒|喝一杯": "lore_tavern_reflection",
    "焦虑|失眠|抑郁": "lore_mental_health_support",
    "方案|项目|工作": "lore_career_context"
}

async def retrieve(query: str, branch_id: str, intent: IntentType) -> RetrievedContext:
    # Fast path: 关键词匹配（O(1)，覆盖高频简单场景）
    if trigger := keyword_match(query):
        fast_memories = fast_inject(trigger, branch_id)
        if fast_memories.confidence > 0.9:
            return fast_memories  # 高置信度直接返回

    # Slow path: 意图图谱导航（O(n)，处理复杂查询）
    graph_result = await intent_graph_navigate(query, branch_id, intent)

    # Hybrid: 快速通道结果与图谱结果融合
    return merge_recall(fast_memories, graph_result)
```

**价值**：
- 覆盖高频简单场景，降低图谱检索开销
- 保留复杂查询的图谱导航能力
- 与酒馆 World Info 的"关键词→记忆注入"理念一致，但系统化接入混合检索链路

**4.5.5 异步构建流水线**

每轮对话结束后，由后台 **Reflection Agent** 异步执行：

```
对话回合结束
    │
    ▼
[Entity Extract] ──► DS-V4-flash：提取实体、关系、情感标签（结构化输出）
    │
    ▼
[Concept Linking] ──► 本地 Qwen3.5：链接到已有概念或新建概念
    │
    ▼
[Edge Creation] ──► 按边类型分流构建
    │                    • MENTIONS / TEMPORAL_NEXT / BELONGS_TO → 规则引擎直接写入
    │                    • CAUSED → Tier 1 模板匹配，验证方向与实体存在性；
    │                              匹配失败则降级写入 CORRELATED
    │                    • IS_A → LLM 泛化，置信度 < 0.75 挂起待审核
    │                    • SIMILAR_TO → 向量相似度 > 0.85 时写入
    │                    • CONTRADICTS / TRIGGERED_BY → 规则引擎
    │                    • 所有边写入时附加置信度与 `mva_only` 标记（如适用）
    ▼
[Conflict Detect] ──► 轻量规则：检测 CONTRADICTS
    │                    • 已有"喜欢川菜"，新建"讨厌川菜" → 标记矛盾
    ▼
[Insight Generation] ──► Kimi 2.6（周期性，每 N 轮或每日）：
    │                    主动总结跨 session 洞察（如"用户近3次谈话焦虑程度上升"）
    ▼
   写入 PostgreSQL
```

**4.5.7 性能边界与保障**

| 数据规模 | 延迟 | 评级 |
|---------|------|------|
| 1,000 节点 / 5,000 边 | 10-30ms | ✅ |
| **MVA 目标：10,000 节点 / 50,000 边** | **50-150ms** | ✅ |
| 100,000 节点 / 500,000 边 | 200-800ms | ⚠️ 需优化 |

**保障策略**：
1. 限制 `max_hops ≤ 3`
2. 分层查询（hop_limit 1→2→3，召回足够提前返回）
3. 对 `semantic_edges(source_id, edge_type, branch_id)` 建立复合索引

**4.5.8 冷启动三阶段**

| 阶段 | 时间 | 内容 |
|------|------|------|
| **Phase 1** | Week 1-2 | 种子注入：200 概念 + 6 条硬编码策略 |
| **Phase 2** | Week 2-4 | 对话驱动：前 50 轮产 MENTIONS + TEMPORAL_NEXT；50-200 轮积累 IS_A |
| **Phase 3** | Week 4+ | Insight 驱动：周期性主动反思优化图谱 |

**4.5.9 混合召回融合权重**

MVA 初始权重：`final_score = 0.6 * graph_score + 0.4 * vector_score`

后续根据 A6 评估场景动态调参。

**4.5.6 检索路径精确执行流程（6 步）**

```
Step 1: 意图解析 (T1 本地 Qwen3.5 分类 + T2 DS-V4-flash 实体提取)
Step 2: 模糊指代消解 (L1 → L2 向量检索 → T6 Kimi 2.6 消歧)
Step 3: 加载意图策略 (查询 intent_patterns 表)
Step 4: 图谱导航 (PostgreSQL Recursive CTE)
Step 5: 混合召回融合 (图谱 + 向量 + 关键词快速通道)
Step 6: 上下文组装 (Importance × Recency × Relevance，截断到 4K tokens)
```

**示例 CTE 查询模板**（Step 4）：

```sql
WITH RECURSIVE navigation AS (
    SELECT mn.id as node_id, mn.content_summary, 0 as hop, 
           ARRAY[mn.id]::uuid[] as path, 1.0 as path_weight
    FROM memory_nodes mn
    WHERE mn.id = :candidate_id AND mn.branch_id = :branch_id
    
    UNION ALL
    SELECT se.target_id, target_mn.content_summary, nav.hop + 1,
           nav.path || se.target_id, nav.path_weight * se.weight * 0.9
    FROM navigation nav
    JOIN semantic_edges se ON nav.node_id = se.source_id
    JOIN memory_nodes target_mn ON se.target_id = target_mn.id
    WHERE se.edge_type = ANY(:entry_edge_types)
      AND se.branch_id = :branch_id
      AND nav.hop < :max_hops
      AND NOT se.target_id = ANY(nav.path)  -- 严格防环
)
SELECT node_id, content_summary, hop, path_weight
FROM navigation WHERE hop > 0
ORDER BY path_weight DESC, hop ASC LIMIT 20;
```

**混合召回融合权重**（Step 5）：`final_score = 0.6 * graph_score + 0.4 * vector_score`

### 4.6 Retrieval Engine

检索执行遵循 4.5.3 的 6 步流程，混合召回阶段采用 `0.6 * graph_score + 0.4 * vector_score` 的融合权重。

| 阶段 | 组件 | 职责 |
|------|------|------|
| **Intent Parse** | DS-V4-flash / 本地 Qwen3.5 | 意图分类、实体提取、查询重写 |
| **Multi-Recall** | 并行执行 | 向量检索(Qdrant) + 图谱导航(PostgreSQL CTE) + 关键词匹配 + 时间范围过滤 |
| **Reranker** | BAAI/bge-reranker-base | Cross-Encoder 精排，加入时间衰减权重（越新越重要） |
| **Context Assembly** | 优先级排序 + 去重 + 截断 | 按 `Importance × Recency × Relevance` 排序，截断到 4K tokens |

### 4.7 ActionPlanner（Token→Action Bridge）

**新增节点**，位于 LLM Node 与 Output Node 之间：

```
[LLM Node] ──► [ActionPlanner Node] ──► [Output Node]
                │
                ├── reply_text: str
                ├── action_plan: ActionPlan
                │       ├── action_token: str      # "approach_gently"
                │       ├── action_params: Dict    # {speed: 0.5, proximity: 1.0}
                │       └── reasoning: str         # "用户焦虑，应缓慢接近"
                └── emotion_modulation: Dict      # {speed_mult: 0.5, volume_mult: 0.8}
```

**职责**：
1. 从 LLM 输出中解析高层动作意图（自然语言 → 结构化 action_token）
2. 查询当前情感状态的调制参数（`EMOTION_BEHAVIOR_MODULATION`）
3. 组装 `ActionPlan` 传递给 EmbodiedAdapter 进行翻译

**Emotion→Behavior 调制表**：

| 情感状态 | 速度系数 | 音量系数 | 社交距离偏好 | 注视时长 |
|---------|---------|---------|------------|---------|
| NEUTRAL | 1.0 | 1.0 | 1.5m | 3.0s |
| CURIOUS | 1.2 | 1.0 | 1.0m | 5.0s |
| EMPATHETIC | 0.7 | 0.9 | 1.0m | 4.0s |
| CONCERNED | 0.5 | 0.8 | 0.8m | 6.0s |
| REFLECTIVE | 0.3 | 0.7 | 2.0m | 2.0s |

**面试话术**："情感状态不只是影响对话语气，还直接调制物理行为参数。CONCERNED 状态下，Agent 的移动速度降低 50%，音量降低 20%，并保持更近的社交距离——这在养老/医疗机器人场景中是关键的安全设计。"

### 4.8 Model Router

| 任务层级 | 任务类型 | 首选模型 | 降级链 | 本地/云端 |
|---------|---------|---------|--------|----------|
| **T0** | 情感分类（3类） | Qwen3.5-9B (LM Studio) | DS-V4-flash | 本地 |
| **T1** | 意图识别（8类） | Qwen3.5-9B | DS-V4-flash | 本地 |
| **T2** | 实体提取（NER） | DS-V4-flash | Kimi 2.6 | 云端 |
| **T3** | 边构建/关系推理 | DS-V4-flash | Kimi 2.6 | 云端 |
| **T4** | 记忆反思/摘要 | Kimi 2.6 | DS-V4-pro | 云端 |
| **T5** | 回复生成 | DS-V4-pro | Kimi 2.6 | 云端 |
| **T6** | 冲突消解语义 | Kimi 2.6 | DS-V4-pro | 云端 |
| **T7** | 评估/测试 | DS-V4-pro | Kimi 2.6 | 云端 |

**缓存策略**：SQLite 缓存，TTL 24h，相同 (task_type, prompt_hash) 直接复用。  
**成本追踪**：每次调用记录 model_name、input_tokens、output_tokens、latency，用于评估框架的 `Token/s` 指标。

### 4.8.1 Cost Tracking 详细设计

Cost 统计是生产环境必需的可观测性模块，必须在 **Model Router** 层统一拦截，避免各模型客户端自行上报导致口径不一致。

#### 记录维度（Raw Metrics）

每条记录 `ModelCallRecord` 包含：

```python
{
  "record_id": str,           # UUID
  "timestamp": datetime,      # UTC
  "session_id": str,          # 用户会话聚合键
  "branch_id": str,           # 显式分支标识（禁止默认全局分支）
  "persona_id": str,          # 当前激活人格
  "node_id": str,             # Agent Core 中调用该模型的节点标识
  "model_name": str,          # 如 "gpt-4o", "claude-3.5-sonnet"
  "input_tokens": int,
  "output_tokens": int,
  "total_tokens": int,
  "latency_ms": float,        # 端到端耗时（含网络）
  "ttft_ms": float,           # Time To First Token（流式场景）
  "cost_usd": float,          # 按模型单价计算的预估费用
  "cache_hit": bool,          # 是否命中 prompt cache（若模型支持）
  "status": str               # success / error / timeout
}
```

#### 存储与聚合

- **原始记录**：写入独立的 `metrics_store`（SQLite / 轻量级时序库），**不直接污染记忆层级**。
- **聚合视图**：由 `CostAggregator` 按以下维度生成摘要，供 L3 Semantic Memory 查询：
  - `by_branch`: 分支级预算消耗。
  - `by_session`: 单会话成本上限告警。
  - `by_model`: 模型选型 ROI 分析。
  - `by_persona`: 不同人格的推理成本差异（如"详细分析型"人格通常消耗更多 tokens）。

#### 预算与告警

- 支持在 `branch_id` 和 `session_id` 级别设置 `token_budget` 与 `usd_budget`。
- 当消耗达到 80% 时，由 `ICostTracker` 抛出 `BudgetWarningException`，由 Agent Core 决策是否降级模型或截断上下文。

#### 接口契约

- `ICostTracker.record(request: ModelRequest, response: ModelResponse, latency_ms: float, branch_id: str) -> None`
- `ICostTracker.get_summary(scope: CostScope, branch_id: str, start: datetime, end: datetime) -> CostSummary`

### 4.9 Emotion Engine（双层实现）

**Layer 1: Rule-based State Machine（默认）**

```
                    ┌─────────────┐
         ┌─────────►│   NEUTRAL   │◄────────┐
         │          └──────┬──────┘         │
         │                 │                 │
    negative┌─────────────┘                 │positive
    low     ▼                               ▼
    ┌─────────────┐                    ┌─────────────┐
    │   CURIOUS   │◄────positive────►│  EMPATHETIC │
    │  (兴趣触发)  │    high          │  (共情触发)  │
    └──────┬──────┘                  └──────┬──────┘
           │                                │
           │negative high                   │negative high
           ▼                                ▼
    ┌─────────────┐                    ┌─────────────┐
    │   CONCERNED │◄─────severe──────►│  REFLECTIVE │
    │  (担忧触发)  │     negative       │  (反思触发)  │
    └─────────────┘                    └─────────────┘
```

**状态转移条件**：
- 每轮对话后，T0（本地 Qwen3.5）提取情感标签和强度
- 结合当前状态 + 情感强度 + 连续轮次，查状态转移表
- 状态影响 LLM 的 system prompt（如 CONCERNED 状态下增加安抚语气指令）

**Layer 2: LSTM Regressor（可训练插槽）**

```python
trainable_emotion_model.py
├── 输入：对话历史文本序列（最近 5 轮）
├── 编码：BERT 编码句向量
├── 模型：双层 LSTM + 全连接回归头
├── 输出：情感强度值（-1.0 ~ +1.0）
└── 训练：少量人工标注数据（100-200条）
    └── [RL-PLACEHOLDER]: 未来替换为 PPO/GRPO 优化策略
```

### 4.10 2D Virtual Environment（Token→Action Bridge 架构）

**核心定位**：不为机器人训练"身体"（VLA），而是构建可跨本体移植的"人格灵魂"。

**设计边界**：极简网格世界验证人格-身体解耦，不追求真实物理仿真。

| 组件 | 设计 |
|------|------|
| **世界模型** | 离散网格（20×20），每个格子可有物体/障碍物 |
| **Agent 状态** | `(x, y, θ)` 坐标 + 朝向，FOV 锥形视野（5格距离，90°视角） |
| **物体** | 静态（家具、墙）/ 动态（用户位置、可拾取物品） |
| **高层动作 Token** | `approach_gently`, `retreat_slowly`, `turn_to_user`, `interact`, `look_around` |
| **感知输出** | 视野内物体列表 + 相对位置 + 属性描述 → 文本化注入 L1 |

**Token→Action Bridge Pipeline**：

```
2D 环境状态
    │
    ▼
[State Encoder] ──► 将 (x,y,θ) + 视野物体 编码为文本描述
    │
    ▼
[LLM (DS-V4-pro)] ──► 输入：环境描述 + 对话上下文 + 角色设定
    │                    输出：对话回复 + 高层 action_token + reasoning
    ▼
[ActionPlanner] ──► 查询情感调制参数 → 组装 ActionPlan
    │
    ▼
[EmbodiedAdapter.translate_action_token] ──► 映射字典翻译为低层指令
    │   • grid_2d: "move_forward(1格, speed=0.5)"
    │   • ros2: "cmd_vel [linear=0.1, angular=0.0]"
    │   • mujoco: "set_joint_velocity([...])"
    ▼
   2D 环境执行动作
```

**映射字典示例**：

```python
ACTION_TOKEN_MAP = {
    "grid_2d": {
        "approach_gently": "move_forward({distance}, speed={speed})",
        "retreat_slowly": "move_backward({distance}, speed={speed})",
        "turn_to_user": "turn_toward({target_x}, {target_y})",
        "interact": "interact_with({object_id})",
        "look_around": "scan_fov({range})"
    },
    "ros2_mobile": {
        "approach_gently": "cmd_vel [linear={speed}, angular=0.0]",
        "retreat_slowly": "cmd_vel [linear=-{speed}, angular=0.0]",
        "turn_to_user": "navigate_to({target_x}, {target_y})"
    }
    # MuJoCo, Isaac Gym 等预留
}
```

**三大先进性（面试必讲）**：
1. **零样本跨本体迁移**：换身体只换映射字典，不重新训练
2. **可审计安全决策链**：每个动作都有 reasoning 字段，可追溯"为什么"
3. **人格-身体解耦**：同一套"小心翼翼"人格可驱动玩具车或工业臂

**拓展接口**：

```
EmbodiedAdapter (ABC)
├── get_perception(agent_id) → EmbodiedState
├── execute_action(agent_id, action) → PerceptionResult
├── get_spatial_memory(agent_id) → List[SpatialRecord]
├── predict_action(percept, task_desc) → Action
│   └── 默认实现：LLM 调用
│   └── [VLA-PLACEHOLDER]: 未来替换为微调 VLA 模型
└── translate_action_token(action_token, params, robot_type) → LowLevelCommand
    └── 映射字典翻译，实现人格-身体解耦
```

**MVA 阶段**：纯文本描述，无 Canvas 渲染。Week 7 补极简 HTML 前端。

### 4.11 Skills System

Skill 在 ChronoPersona 框架中是**可执行的能力原语**，必须与人格（Persona）和记忆（Memory）形成清晰的三元划分：

| 维度 | 人格 (Persona) | 记忆 (Memory) | 技能 (Skill) |
|------|---------------|--------------|-------------|
| **核心问题** | 我是谁？我如何说话？ | 我知道什么？我经历过什么？ | 我能做什么？ |
| **数据形态** | 属性配置 + 风格模板 | 时序事件 + 语义知识 | 输入 Schema + 执行 Handler |
| **作用时机** | 推理前注入上下文 | 检索时作为依据 | 推理中由模型决策调用 |
| **是否可积累** | 相对稳定，偶尔更新 | 随时间持续增长 | 静态注册，版本迭代 |
| **副作用** | 无（纯上下文） | 读/写记忆本身 | 可产生外部副作用（API、IO、代码执行） |

**一句话界定**：人格决定"怎么说"，记忆决定"基于什么说"，技能决定"能做什么再说"。

#### Skills 在框架中的三个角色

1. **作为模型可调用的原子操作**
   - Model Router 在构造请求时，将 `ISkillRegistry` 中当前分支可用的技能列表，以 Function Calling / Tools 格式暴露给 LLM。
   - LLM 的某一步输出可能是 `call_skill(skill_id="web_search", params={"query": "..."})`。

2. **作为记忆的生产者**
   - Skill 的执行结果（Observation）**必须**写回 L2 Episodic Memory，并标注 `source_skill_id`。
   - 这保证了 Agent 知道"某个事实是我通过搜索获得的"，而非原生知识。

3. **作为人格的下游表现载体**
   - 同一个 Skill 的执行结果，经过不同人格的包装后，输出风格完全不同。
   - 例如：`skill_calculate_risk` 返回 `{risk_score: 0.8}`，保守型人格会说"风险极高，建议终止"，激进型人格会说"存在一定波动，但可控"。

#### Skill 的组成结构

```python
class ISkill(Protocol):
    @property
    def skill_id(self) -> str: ...           # 全局唯一标识
    @property
    def version(self) -> str: ...            # 语义化版本，支持热更新
    @property
    def description(self) -> str: ...        # 给 LLM 看的自然语言描述
    @property
    def parameters_schema(self) -> dict: ...  # JSON Schema，供模型生成参数
    
    def execute(self, params: dict, branch_id: str, persona_id: str) -> SkillResult:
        """
        Args:
            params: 模型生成的参数，需校验
            branch_id: 显式分支上下文
            persona_id: 当前人格，用于执行时的个性化适配
        Returns:
            SkillResult: 包含 observation(原始结果)、summary(给人看的摘要)、
                         cost(本次执行的内部消耗，如外部 API tokens)
        """
        ...
```

#### Skills 与记忆/人格的交互关系

**Skill → Memory：**
- Skill 执行后，由 `MemoryWriterService` 自动将 `SkillResult.observation` 写入当前分支的 L2 Episodic，标签为 `origin:skill`，并关联 `skill_id`。
- 未来记忆检索时，可区分"亲身经历"与"工具获取"。

**Memory → Skill：**
- `SkillRegistry` 在注册时，可将 Skill 的 `description` 和 `parameters_schema` 也存入 L3 Semantic Memory。
- 这支持未来"动态技能发现"：Agent 在推理时不仅调用已知技能，还能通过语义检索发现"我好像需要一个能处理 PDF 的技能"，然后请求加载。

**Persona → Skill：**
- 人格配置中包含 `skill_permissions` 和 `skill_preferences`。
  - `permissions`: 某些 Skill（如 `execute_code`）仅特定人格可调用。
  - `preferences`: 人格可定义"在不确定时优先调用 `fact_check` skill"，这作为系统提示词的一部分注入。

**Skill → Persona：**
- Skill 执行时的副作用不应直接修改人格配置（人格是静态身份），但 Skill 的**使用历史**会进入记忆，长期可能通过记忆迁移间接影响人格表现。

#### 注册中心

- `ISkillRegistry` 管理生命周期：
  - `register(skill: ISkill, branch_id: str)`：向指定分支注册（支持分支级隔离）。
  - `execute(skill_id: str, params: dict, branch_id: str)`：执行并走完全链路（记录 Cost、写入记忆）。
  - `get_available_skills(branch_id: str, persona_id: str) -> list[ISkill]`：根据人格权限过滤。

---

## 5. 数据模型设计

### 5.1 PostgreSQL Schema

```sql
-- 概念层级表（自引用 IS_A）
CREATE TABLE concepts (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    concept_type TEXT NOT NULL 
        CHECK (concept_type IN ('food','emotion','person','event','object','abstract')),
    parent_id UUID REFERENCES concepts(id),  -- IS_A 层级
    embedding VECTOR(1024),  -- 可选，用于模糊匹配
    branch_id TEXT NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_concepts_branch ON concepts(branch_id);
CREATE INDEX idx_concepts_type ON concepts(concept_type);

-- 记忆实体节点（桥接 L2/L3）
CREATE TABLE memory_nodes (
    id UUID PRIMARY KEY,
    memory_type TEXT NOT NULL 
        CHECK (memory_type IN ('episodic','semantic','insight')),
    ref_id TEXT NOT NULL,  -- 外键：L2 Qdrant ID 或 L3 行 ID
    content_summary TEXT,
    branch_id TEXT NOT NULL DEFAULT 'main',
    session_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_memory_nodes_branch ON memory_nodes(branch_id);
CREATE INDEX idx_memory_nodes_session ON memory_nodes(session_id);
CREATE INDEX idx_memory_nodes_type ON memory_nodes(memory_type);

-- 语义边（8 类）
CREATE TABLE semantic_edges (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL,
    target_id UUID NOT NULL,
    edge_type TEXT NOT NULL CHECK (edge_type IN (
        'IS_A','MENTIONS','TEMPORAL_NEXT','CAUSED',
        'CONTRADICTS','BELONGS_TO','SIMILAR_TO','TRIGGERED_BY'
    )),
    weight FLOAT DEFAULT 1.0,
    metadata JSONB,
    branch_id TEXT NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_edges_type ON semantic_edges(edge_type, branch_id);
CREATE INDEX idx_edges_source ON semantic_edges(source_id, edge_type);
CREATE INDEX idx_edges_target ON semantic_edges(target_id, edge_type);

-- 意图导航策略
CREATE TABLE intent_patterns (
    id UUID PRIMARY KEY,
    intent_type TEXT NOT NULL CHECK (intent_type IN (
        'retrieve','vertical_generalize','vertical_specify',
        'parallel_compare','temporal_trace','causal_explore',
        'empathize','persona_switch'
    )),
    trigger_keywords TEXT[],
    trigger_regex TEXT,
    entry_edge_types TEXT[] NOT NULL DEFAULT '{}',
    max_hops INT DEFAULT 3,
    target_memory_types TEXT[] DEFAULT '{episodic,semantic}',
    priority_score FLOAT DEFAULT 1.0,
    branch_scope TEXT DEFAULT 'current',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 周期性主动反思产出
CREATE TABLE insights (
    id UUID PRIMARY KEY,
    insight_type TEXT NOT NULL CHECK (insight_type IN (
        'pattern','trend','conflict','recommendation'
    )),
    source_memory_ids TEXT[],  -- 支撑该洞察的源记忆
    content TEXT NOT NULL,
    confidence FLOAT,
    branch_id TEXT NOT NULL DEFAULT 'main',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ
);
CREATE INDEX idx_insights_branch ON insights(branch_id);
CREATE INDEX idx_insights_type ON insights(insight_type);

-- MVCC 版本链（L3 Entity 级细粒度）
CREATE TABLE entity_versions (
    id UUID PRIMARY KEY,
    entity_id TEXT NOT NULL,  -- 对应 memory_nodes.ref_id
    branch_id TEXT NOT NULL,
    version TEXT NOT NULL,
    parent_version TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    vector_clock JSONB,
    content_hash TEXT,
    diff JSONB,  -- 与 parent 的 diff
    provenance_op TEXT,    -- 关联 L0 的操作 ID
    UNIQUE(entity_id, branch_id, version)
);
CREATE INDEX idx_entity_versions_lookup ON entity_versions(entity_id, branch_id, version);

-- 空间-情感-动作关联记忆（用于具身行为优化与跨本体迁移）
CREATE TABLE embodied_interactions (
    id UUID PRIMARY KEY,
    agent_id TEXT NOT NULL,
    branch_id TEXT NOT NULL DEFAULT 'main',
    location TEXT,           -- "客厅(3,4)" 或 "kitchen"
    location_embedding VECTOR(512),  -- 空间语义编码（预留）
    action_token TEXT NOT NULL,
    action_params JSONB,
    emotion_state TEXT,
    emotion_intensity FLOAT,
    user_reaction TEXT CHECK (user_reaction IN ('positive', 'neutral', 'negative', 'startled')),
    outcome_score FLOAT,     -- 动作效果评分 [-1.0, 1.0]
    created_at TIMESTAMPTZ DEFAULT NOW(),
    session_id TEXT
);
CREATE INDEX idx_embodied_location ON embodied_interactions(location, branch_id);
CREATE INDEX idx_embodied_action ON embodied_interactions(action_token, outcome_score);

-- MVCC Session 快照（L2 粗粒度）
CREATE TABLE session_snapshots (
    id UUID PRIMARY KEY,
    branch_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    version TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    lww_state JSONB,  -- LWWMap JSON 序列化
    qdrant_metadata JSONB,
    UNIQUE(branch_id, session_id, version)
);
```

### 5.2 Qdrant Collection Schema

```python
Collection: "episodic_memory"
├── Vector: 1024d (BGE-large-zh)
├── Distance: Cosine
├── HNSW: m=16, ef_construct=100
├── Payload:
│   ├── user_id: string
│   ├── session_id: string
│   ├── branch_id: string
│   ├── turn_id: int
│   ├── content_type: string [user, agent, system]
│   ├── created_at: datetime
│   └── entities: List[string]  -- 该轮提到的实体ID
└── Quantization: Scalar(1-bit or 2-bit)  -- 可选

-- MVO 种子（MVA 冷启动）
INSERT INTO concepts (id, name, concept_type, parent_id) VALUES
('c_food', '食物', 'abstract', NULL),
('c_cuisine', '菜系', 'abstract', 'c_food'),
('c_sichuan', '川菜', 'food', 'c_cuisine'),
('c_cantonese', '粤菜', 'food', 'c_cuisine'),
('c_emotion', '情绪', 'abstract', NULL),
('c_anxiety', '焦虑', 'emotion', 'c_emotion'),
('c_joy', '喜悦', 'emotion', 'c_emotion'),
('c_person', '人物', 'abstract', NULL),
('c_family', '家人', 'relation', 'c_person');

INSERT INTO intent_patterns (intent_type, trigger_keywords, entry_edge_types, max_hops) VALUES
('temporal_trace', ARRAY['后来','之后','然后','接着','现在怎样','结果如何'], ARRAY['TEMPORAL_NEXT','MENTIONS'], 3),
('causal_explore', ARRAY['为什么','怎么回事','原因','怎么会'], ARRAY['CAUSED','MENTIONS'], 3),
('vertical_generalize', ARRAY['种类','类型','还有哪些','类似的','同类的'], ARRAY['IS_A'], 2),
('vertical_specify', ARRAY['具体','哪种','什么样的','举例'], ARRAY['IS_A'], 2),
('parallel_compare', ARRAY['和','相比','哪个','还是','或者'], ARRAY['SIMILAR_TO'], 2),
('empathize', ARRAY['难过','开心','生气','担心','害怕'], ARRAY['MENTIONS'], 2);
```

---

## 6. 接口与契约设计

### 6.1 核心抽象接口

```
AbstractMemoryStore (ABC)
├── add(memory: MemoryEntry, branch_id: str) → str  (返回 memory_id)
├── retrieve(query: str, branch_id: str, intent: IntentType) → RetrievedContext
├── commit_version(branch_id: str) → Version
├── checkout_branch(branch_id: str, version: Optional[str]) → Snapshot
├── get_facts(entity_id: str, branch_id: str) → List[Fact]
└── link_entities(source: str, target: str, relation: str, branch_id: str) → bool

AbstractAgentCore (ABC)
├── run_turn(user_input: str, embodied_state: Optional[EmbodiedState]) → AgentOutput
├── switch_persona(persona_id: str) → None
├── get_emotion_state() → EmotionState
└── get_memory_summary(branch_id: str) → MemorySummary

AbstractVersionManager (ABC)
├── commit(branch_id: str, changes: ChangeSet) → Version
├── checkout(branch_id: str, version: Optional[str]) → Snapshot
├── merge(source_branch: str, target_branch: str) → MergeResult
├── log(branch_id: str, entity_id: Optional[str]) → List[Version]
└── gc(branch_id: str, keep_last_n: int) → int

EmbodiedAdapter (ABC)
├── get_perception(agent_id: str) → EmbodiedState
├── execute_action(agent_id: str, action: Action) → PerceptionResult
├── get_spatial_memory(agent_id: str) → List[SpatialRecord]
├── predict_action(percept: EmbodiedState, task_desc: str) → Action
│   └── 默认: LLM 调用
│   └── [VLA-PLACEHOLDER]: 微调模型替换
└── translate_action_token(action_token: str, params: dict, robot_type: str) → LowLevelCommand
    └── 映射字典翻译，实现人格-身体解耦

ModelRouter
├── route(task: Task, context: Context) → Response
├── get_cost_summary() → CostReport
└── cache_clear() → None

IPersonaInjector (ABC)
├── inject(persona_id: str, branch_id: str, target: IContext) → None
└── eject(persona_id: str, branch_id: str) → None

IMemoryMigrationService (ABC)
├── migrate(source: MemoryAnchor, target: MemoryAnchor, branch_id: str, filter: MigrationFilter) → MigrationResult
├── snapshot(branch_id: str) → Snapshot
└── merge_branches(source_branch: str, target_branch: str) → MergeResult

ICostTracker (ABC)
├── record(request: ModelRequest, response: ModelResponse, latency_ms: float, branch_id: str) → None
├── get_summary(scope: CostScope, branch_id: str, start: datetime, end: datetime) → CostSummary
└── check_budget(branch_id: str, session_id: str) → BudgetStatus

ISkillRegistry (ABC)
├── register(skill: ISkill, branch_id: str) → None
├── execute(skill_id: str, params: dict, branch_id: str) → SkillResult
└── get_available_skills(branch_id: str, persona_id: str) → List[ISkill]

ISkill (Protocol)
├── skill_id → str
├── version → str
├── description → str
├── parameters_schema → dict
└── execute(params: dict, branch_id: str, persona_id: str) → SkillResult
```

### 6.2 数据实体定义

```
IContext
├── persona_id: str
├── branch_id: str
├── working_memory: List[MemoryEntry]   -- L1 滑动窗口
├── episodic_context: List[MemoryEntry] -- L2 检索结果
├── semantic_facts: List[Fact]          -- L3 事实
├── insights: List[Insight]             -- 主动反思
├── emotion_state: EmotionState
├── embodied_state: Optional[EmbodiedState]
└── metadata: Dict

ModelRequest
├── task_type: str
├── prompt: str
├── context: IContext
├── model_preference: Optional[str]
├── max_tokens: int
├── temperature: float
└── metadata: Dict

ModelResponse
├── content: str
├── model_name: str
├── input_tokens: int
├── output_tokens: int
├── finish_reason: str
└── metadata: Dict

BudgetStatus
├── branch_id: str
├── session_id: str
├── token_budget: int
├── tokens_used: int
├── usd_budget: float
├── usd_used: float
├── warning_level: str   # "normal" / "warning" / "exceeded"
└── last_updated: datetime

MemoryEntry
├── id: str
├── content: str
├── memory_type: Enum[episodic, semantic]
├── branch_id: str
├── session_id: Optional[str]
├── turn_id: Optional[int]
├── entities: List[str]
├── emotion_tags: List[str]
├── created_at: datetime
└── metadata: Dict

RetrievedContext
├── working_memories: List[MemoryEntry]     -- L1
├── episodic_memories: List[MemoryEntry]    -- L2
├── semantic_facts: List[Fact]              -- L3
├── insights: List[Insight]                   -- 主动反思
├── navigation_path: List[NavigationStep]    -- 意图图谱路径
└── total_tokens: int

AgentOutput
├── reply_text: str
├── action: Optional[Action]
├── emotion_state: EmotionState
├── used_memories: List[str]     -- 引用的记忆ID（可解释性）
└── branch_id: str

EmotionState
├── current_state: Enum[NEUTRAL, CURIOUS, EMPATHETIC, CONCERNED, REFLECTIVE]
├── intensity: float  -- 0.0 ~ 1.0
├── trigger_reason: str
└── state_since: datetime

Version
├── branch_id: str
├── version: str
├── timestamp: datetime
├── vector_clock: Dict[str, int]
├── parent: Optional[str]
└── content_hash: str

ModelCallRecord
├── record_id: str
├── timestamp: datetime
├── session_id: str
├── branch_id: str
├── persona_id: str
├── node_id: str
├── model_name: str
├── input_tokens: int
├── output_tokens: int
├── total_tokens: int
├── latency_ms: float
├── ttft_ms: float
├── cost_usd: float
├── cache_hit: bool
└── status: str

SkillResult
├── observation: str          # 原始执行结果
├── summary: str              # 给人看的摘要
├── cost: CostRecord          # 本次执行内部消耗
├── memory_writes: List[str]  # 自动写入 L2 的记忆 ID 列表
└── status: str               # success / error / timeout

MigrationFilter
├── privacy_level: str        # strict / relaxed / none
├── relevance_threshold: float
├── time_range: Tuple[datetime, datetime]
└── layer_scope: List[str]    # ["L1", "L2", "L3"]

MigrationResult
├── migrated_count: int
├── conflict_list: List[ConflictItem]
├── auto_resolution_rate: float
└── target_snapshot_id: str
```

### 6.3 API 契约（REST + WebSocket）

**REST Endpoints**:

| Method | Path | 描述 |
|--------|------|------|
| POST | `/api/v1/chat` | 发送消息，获取回复 |
| GET | `/api/v1/branches` | 列出所有角色分支 |
| POST | `/api/v1/branches/{id}/checkout` | 切换角色分支 |
| GET | `/api/v1/memory/search` | 记忆检索（调试） |
| GET | `/api/v1/memory/timeline` | 查看记忆时间线 |
| GET | `/api/v1/memory/graph` | 查看意图图谱（可视化数据） |
| GET | `/api/v1/emotion` | 当前情感状态 |
| POST | `/api/v1/sync/force` | 强制触发多端同步 |

**WebSocket Events**:

| Event | Direction | 描述 |
|-------|-----------|------|
| `chat.message` | C→S | 用户发送消息 |
| `chat.reply` | S→C | Agent 回复（流式） |
| `sync.update` | S→C | CRDT 同步广播 |
| `embodied.state` | S→C | 2D 环境状态推送 |
| `embodied.action` | C→S | 前端请求 Agent 执行动作 |
| `presence.change` | S→C | 多端在线状态变化 |

---

## 7. 模型路由策略

### 7.1 任务分级与路由表

| 任务层级 | 任务类型 | 首选模型 | 降级链 | 本地/云端 | 缓存 |
|---------|---------|---------|--------|----------|------|
| **T0** | 情感分类（3类） | Qwen3.5-9B | DS-V4-flash | 本地 | ✅ 24h |
| **T1** | 意图识别（8类） | Qwen3.5-9B | DS-V4-flash | 本地 | ✅ 24h |
| **T2** | 实体提取（NER） | DS-V4-flash | Kimi 2.6 | 云端 | ✅ 24h |
| **T3** | 边构建/关系推理 | DS-V4-flash | Kimi 2.6 | 云端 | ✅ 24h |
| **T4** | 记忆反思/摘要 | Kimi 2.6 | DS-V4-pro | 云端 | ❌ |
| **T5** | 回复生成 | DS-V4-pro | Kimi 2.6 | 云端 | ❌ |
| **T6** | 冲突消解语义 | Kimi 2.6 | DS-V4-pro | 云端 | ❌ |
| **T7** | 评估/测试 | DS-V4-pro | Kimi 2.6 | 云端 | ❌ |

### 7.2 路由决策逻辑

```
路由决策
├── 1. 检查缓存 (task_type + prompt_hash)
│   └── 命中 → 直接返回
│
├── 2. 本地优先 (T0/T1)
│   └── Qwen3.5 健康且置信度 > 0.85 → 本地执行
│   └── 否则 → 降级到云端
│
├── 3. API 链式调用
│   └── 按 TASK_MODEL_MAP 顺序尝试
│   └── 遇 RateLimit/Timeout → 自动降级
│
├── 4. 兜底策略
│   └── 全部失败 → 返回预设安全回复 + 告警日志
│
└── 5. 成本追踪
    └── 记录 model_name, tokens, latency
```

---

## 8. 测试与评估设计

### 8.1 评估框架总体设计

**双轨评估**：
- **轨道A：自建对抗测试集**（核心，覆盖 CRDT/MVCC/意图图谱）
- **轨道B：LoCoMo 适配子集**（砍掉，专注自建）

### 8.2 轨道A：自建对抗测试集（8 场景）

| 场景ID | 场景名称 | 测试目标 | 构造方法 |
|--------|---------|---------|---------|
| A1 | 记忆召回 | 跨 session 事实检索 | 构造 5 轮 session，每轮植入 3-5 个事实，最后提问 |
| A2 | 跨 session 关联 | 时间线推理 | "上次你说的那个问题，后来解决了吗" |
| A3 | 角色隔离 | Branch 隔离有效性 | 在 Therapist branch 问 RPG 剧情，应回答"不知道" |
| A4 | 角色共享 | Main branch 穿透 | 在 RPG branch 问用户姓名（存在 Main），应正确回答 |
| A5 | 多端冲突 | CRDT 合并正确性 | 模拟手机/车机同时写入矛盾偏好，检查合并结果 |
| A6 | 意图图谱导航 | 结构化检索优于纯向量 | 同一问题分别用"纯向量"和"意图图谱"检索，对比召回 |

#### A6 详细测试用例

| 测试 ID | 查询 | 纯向量 RAG 难点 | Intent Graph 优势 |
|--------|------|---------------|----------------|
| A6-1 | "我上周的方案后来怎样" | "方案"语义泛化 | TEMPORAL_NEXT 链 |
| A6-2 | "川菜和粤菜我喜欢哪个" | 无法聚合对比 | SIMILAR_TO + CONTRADICTS |
| A6-3 | "为什么我最近焦虑" | "焦虑"与"工作压力"向量距离远 | CAUSED 回溯 |
| A6-4 | "上次你说的那个餐厅" | "那个"无法向量匹配 | MENTIONS + 指代消解 |
| A7 | 情感一致性 | 状态机不漂移 | 连续输入负面内容，检查状态转移路径是否符合设计 |
| A8 | 具身感知 | 空间记忆影响对话 | Agent 在"厨房"vs"客厅"时，对"我饿了"的回复差异 |
| A9 | 跨本体迁移 | 人格一致性 | 同一人格驱动 grid_2d / ros2_mobile，行为参数一致 |
| A10 | 动作可审计 | 决策链追溯 | 检查每个动作是否有 reasoning 字段，且与情感状态一致 |
| A11 | 人格漂移检测 | 风格一致性 | 连续 10 轮对话后，检测输出与 style_examples 的 embedding 相似度是否 < 0.75 |

### 8.3 指标定义

| 维度 | 指标 | 计算方式 |
|------|------|---------|
| **记忆准确性** | Recall@5 | 正确答案是否在 Top-5 召回中 |
| | MRR | 正确答案的倒数排名 |
| | Answer F1 | 生成答案与标准答案的 token-level F1 |
| **角色一致性** | Persona Drift Score | Embedding 相似度检测回答风格与角色设定的偏离 |
| | Role Confusion Rate | 在 branch A 问 branch B 的问题，错误回答的比例 |
| **CRDT 正确性** | Conflict Resolution Accuracy | 冲突记忆合并后是否保留全部信息 |
| | Sync Convergence Time | 模拟网络分区后恢复，测量最终一致性达成时间 |
| **检索质量** | Intent Navigation Precision | 意图图谱召回 vs 纯向量召回的准确率对比 |
| **系统效率** | P99 Retrieval Latency | 混合检索链路端到端延迟 |
| | Token Cost per Turn | 每轮对话平均 token 消耗（按 Model Router 分层统计） |

### 8.4 核心量化对比表（面试核心成果）

| 场景 | 纯向量 RAG 基线 | ChronoPersona | 提升 |
|------|---------------|--------------|------|
| A1 记忆召回 | Recall@5 = ? | Recall@5 = ? | +?% |
| A2 跨 session 关联 | MRR = ? | MRR = ? | +?% |
| A3 角色隔离 | 串台率 = ? | 串台率 = 0% | 100% |
| A5 多端冲突 | 信息丢失率 = ? | 信息保有率 = 100% | +?% |
| A6 意图导航 | 召回精度 = ? | 召回精度 = ? | +?% |

**这张表 = 简历项目经历中最有力的量化成果。**

### 8.5 持续集成

| 测试类型 | 触发条件 | 工具 |
|---------|---------|------|
| 单元测试 | 每次 commit | pytest |
| 集成测试 | PR 合并前 | pytest + Docker Compose (Qdrant + PostgreSQL) |
| 评估流水线 | 每晚定时 | 自建评估脚本，输出 JSON 报告 |
| 性能基准 | 每周 | locust 压力测试，测量 P99 延迟 |

---

## 9. 8周执行路线图

### 9.1 Week 1: 契约与孤岛

**目标**：所有抽象接口、API 规范、Mock 实现、单测框架完成，`make test` 跑通全 Mock Agent 流程。

| 交付物 | 说明 |
|--------|------|
| `contracts/interfaces/` | 5 个抽象接口文件（硬化） |
| `contracts/schemas/` | 数据实体定义 |
| `contracts/openapi/api.yaml` | REST + WebSocket 规范 |
| `mocks/` | 所有依赖的 Mock 实现 |
| `tests/test_mock_pipeline.py` | 全 Mock 端到端测试 |
| `Makefile` | `make test` 一键执行 |
| `CLAUDE.md` / `.cursorrules` | Vibe Coding 规范 |
| 自研 LWW-CRDT 接口 | `contracts/interfaces/` 中替换 Yjs 为 LWWMap |
| PostgreSQL Schema + MVO 种子 | 包含 4.5.1.1 的初始数据 |
| 8 类边 Tier 1 规则 | MENTIONS / TEMPORAL_NEXT / CAUSED 模板等基础构建器 |

**里程碑**：`make test` 通过 28 个测试用例，包含一个完整的"用户输入 → Agent 回复" Mock 流程。

### 9.2 Week 2-3: 记忆系统核心

**目标**：CRDT-MVCC 混合记忆层（L0-L3），命令行可演示角色切换和记忆召回。

| 周次 | 聚焦 | 交付物 |
|------|------|--------|
| Week 2 | L0 CRDT + L1 Working Memory + L2 Episodic Memory | **L0 LWW-CRDT 实现、滑动窗口、Qdrant Mock 接入** |
| Week 3 | L3 Semantic Memory + Intent Graph (PostgreSQL CTE) | 概念层级、语义边、意图导航策略、Recursive CTE（含 6 步检索、MVO 种子、PostgreSQL CTE） |

**里程碑**：命令行运行 `python demo_memory.py`，演示：
1. 写入记忆 → 切换 therapist branch → 查询同一实体得到不同结果
2. 模拟多端冲突 → 检查 CONTRADICTS 边存在

### 9.3 Week 4: 主动反思与 Insight

**目标**：周期性主动反思模块 + Insight 生成。

| 交付物 | 说明 |
|--------|------|
| **CAUSED 边 Tier 2 统计共现评估** | 统计共现评估 |
| `InsightGenerator` | 每 N 轮或每日凌晨触发 |
| `insight_types` | pattern / trend / conflict / recommendation |
| `insights` 表 | 存储反思产出，带有效期 |
| 评估 | A1/A2 测试中加入 insight 辅助后的召回提升 |

**里程碑**：运行 3 轮 session 后，系统自动产出洞察如"用户近3次谈话焦虑程度上升"。

### 9.4 Week 5: Agent 循环与算法插槽

**目标**：LangGraph 循环 + 可训练情感模型 + VLA 预留接口。

| 交付物 | 说明 |
|--------|------|
| LangGraph State Machine | Input → Intent → Memory → LLM → Output 完整链路 |
| `trainable_emotion_model.py` | LSTM 情感强度回归头 + 训练脚本 |
| `[RL-PLACEHOLDER]` | 标注未来 PPO/GRPO 优化位置 |
| VLA 可插拔接口 | `predict_action()` 默认 LLM 实现 |

**里程碑**：端到端对话可用，情感状态机可观测，LSTM 模型可训练。

### 9.5 Week 6: 评估框架

**目标**：8 场景对抗测试集 + 量化对比表。

| 交付物 | 说明 |
|--------|------|
| `evaluation/scenarios.py` | A1-A8 测试场景定义 |
| `evaluation/metrics.py` | 指标计算（Recall@K, MRR, F1, Drift Score） |
| `evaluation/baseline.py` | 纯向量 RAG 基线实现 |
| `reports/` | 自动生成对比报告（Markdown + JSON） |

**里程碑**：`python run_eval.py` 输出完整的量化对比表。

### 9.6 Week 7: 极简 2D 世界 + 前端

**目标**：文本化 2D 世界 + 极简 HTML Canvas 展示。

| 交付物 | 说明 |
|--------|------|
| `GridWorldAdapter` | 20×20 网格，5 种动作 |
| 文本感知 | "你身处[厨房]，面前是[冰箱]" |
| 极简前端 | Next.js + HTML Canvas，WebSocket 连接 |
| Demo 视频 | Agent 根据位置产生不同对话 |

**里程碑**：打开浏览器，看到 Agent 在网格中移动，对话内容随位置变化。

### 9.7 Week 8: 文档与面试准备

**目标**：README、技术博客、Slide Deck。

| 交付物 | 说明 |
|--------|------|
| `README.md` | 项目介绍、架构图、快速开始、评估结果 |
| 技术博客 | 《带镣铐的建筑：我们如何用 CRDT 和 MVCC 为 AI 伴侣构建一个不会失忆的大脑》 |
| Slide Deck | 面试自我讲述提纲（10 页） |
| 演示脚本 | 3 分钟项目介绍 + 5 分钟技术 deep dive |

---

## 10. 风险与兜底策略

| 风险 | 影响 | 兜底策略 |
|------|------|---------|
| **Qwen3.5 本地推理性能不足** | T0/T1 延迟高，影响体验 | 降级到 DS-V4-flash，本地模型仅作演示 |
| **API 成本超预算** | DS-V4-pro 调用过多 | Model Router 缓存命中率监控，超阈值时切换 Kimi |
| **PostgreSQL CTE 性能差** | 意图图谱导航慢 | 限制 max_hops ≤ 3，预计算高频路径 |
| **CRDT 同步复杂度高** | 多端演示难以构建 | MVA 阶段仅演示单端 + 模拟冲突，真实多端放到第二月 |
| **8周做不完** | 项目无法成型 | Week 4 设置 checkpoint，若 L3 未完成则砍掉 Insight 模块，保核心记忆+评估 |
| **面试官质疑" toy 项目"** | 印象分降低 | 强调架构设计的生产级考量（CRDT、MVCC、量化压缩、模型路由），而非功能堆砌 |

---

*文档结束*
