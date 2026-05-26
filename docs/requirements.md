# ChronoPersona 系统设计文档

**版本**: MVA v1.5 (Minimal Viable Architecture)  
**日期**: 2026-05-18  
**定位**: 面向面试的 AI Agent 长期记忆系统项目  
**核心差异化**: CRDT 多端同步 + MVCC 角色分支 + 意图图谱导航 + Token→Action Bridge 具身人格移植 + 酒馆式混合格式人格工程 + **认知仿生记忆架构借鉴**

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
10. [Cursor 多 Agent 架构深度调研：对 ChronoPersona 的借鉴分析](#10-cursor-多-agent-架构深度调研对-chronopersona-的借鉴分析)
11. [风险与兜底策略](#11-风险与兜底策略)

---

## 术语表

| 术语 | 定义 |
|------|------|
| **意图图谱导航** | 基于意图分类结果，在语义图谱中按预定义边类型进行递归遍历的检索策略 |
| **Session-MVCC** | L2 层级以 Session 为粒度的粗粒度版本控制（每 session 结束打 snapshot） |
| **Entity-MVCC** | L3 层级以 Entity 为粒度的细粒度版本控制（每条事实/画像独立版本链） |
| **Token→Action Bridge** | 将 LLM 输出的自然语言动作意图翻译为结构化 action_token，再通过 EmbodiedAdapter 映射为低层执行指令的完整链路 |
| **Distillation** | L2 情景记忆向 L3 语义记忆的转化过程，信息密度从"高冗余、高噪声"向"高结构化、低冗余"跃迁 |
| **Dreaming** | 空闲时段运行的 Memory Consolidation Agent，从情景记忆中提取行为模式并固化为语义规则 |
| **Importance Score** | 多因子加权模型（信息熵增益、任务关联度、访问频率、用户显式标记），决定记忆固化资格 |
| **Ebbinghaus Decay** | 差异化遗忘曲线：工作记忆会话结束即清空、情景记忆指数衰减、语义记忆极慢衰减 |

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

- **LWW-CRDT 多端同步**：自研轻量 CRDT，基于 HLC 混合逻辑时钟，冲突记忆保留而非覆盖
- **MVCC 角色分支**：每条记忆支持版本链，角色切换 = `git checkout`
- **意图图谱导航**：将用户查询意图翻译为结构化检索路径，而非单纯向量相似度
- **人格工程**：借鉴酒馆社区验证的混合格式定义（W++ + Ali:Chat + 自然语言），系统化有机约束与风格指纹漂移检测
- **分层模型路由**：高频分类任务走本地 Qwen3.5-9B，质量敏感任务走 DeepSeek-V4-pro
- **认知仿生记忆架构**：工作/情景/语义三层 + 差异化遗忘 + Dreaming 主动反思 + 重要性评分驱动固化

### 1.3 对标分析

| 方案 | 记忆持久化 | 多端同步 | 角色隔离 | 意图导航 | 具身感知 | 主动进化 |
|------|-----------|---------|---------|---------|---------|---------|
| Mem0 | ✅ 向量库 | ❌ 无 | ❌ 无 | ❌ 纯向量 | ❌ 无 | ❌ 无 |
| Zep | ✅ 向量+图 | ❌ 无 | ❌ 无 | ❌ 纯向量 | ❌ 无 | ❌ 无 |
| Letta (MemGPT) | ✅ 分层 | ❌ 无 | ❌ 无 | ❌ 纯向量 | ❌ 无 | ❌ 无 |
| 认知仿生标杆（行业实践） | ✅ 分层+蒸馏 | ❌ 无 | ❌ 无 | ❌ 纯向量 | ❌ 无 | ✅ Dreaming |
| **ChronoPersona** | ✅ 分层+版本+蒸馏 | ✅ CRDT | ✅ MVCC | ✅ 意图图谱 | ✅ 极简 VLA | ✅ Dreaming |

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
| PostgreSQL | 🟡 混合：PostgresSemanticStore 接口就绪，IntentGraph 为内存实现 | ✅ Docker 真实接入 |
| 主动反思 | 🟡 MVA 已实现 SimpleInsightEngine（关键词共现），LLM 驱动洞察为 W4+ | ✅ 完整实现 |
| 可训练情感模型 | 🟡 LSTM 训练脚本 + Placeholder | ✅ 可选接入 |
| VLA 微调通道 | 🟡 接口预留 | ✅ 默认 LLM 实现 |
| **统一日志系统** | ✅ loguru 已落地，L0 CRDT / L1 压缩 / Agent 核心路径已接入 | ✅ 全链路 trace + 统计 |
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
CRDT Sync ──► LWW-CRDT operation 广播至其他设备
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
skill_permissions:
  allowed_skills:
    - "memory_recall"
    - "relaxation_guide"
    - "crisis_hotline_lookup"
    - "session_summary"
  forbidden_skills:
    - "rpg_dice_roll"

skill_preferences:
  preferred_skills: []
  fallback_strategy: "ask_user"

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



#### Privacy Filter 设计

**保护范围（PII 定义）**：

| 级别 | 数据类型 | 检测方式 | MVA 策略 |
|------|---------|---------|---------|
| L0 | 手机号、身份证号、邮箱、银行卡号 | 正则表达式 | 强制替换为 `<REDACTED>` |
| L1 | 人名、地址、机构名 | NER 模型（本地 Qwen3.5-9B） | 若置信度 > 0.9 则替换 |
| L2 | 医疗记录、情感隐私 | 关键词 + LLM 分类 | MVA 阶段不做，标记为 `[FUTURE]` |

**过滤行为**：
- 跨人格迁移时，源记忆经过 `IPrivacyFilter.apply(content, level=L1)` 处理
- 匹配到的敏感片段替换为 `<REDACTED:类型:哈希>`（如 `<REDACTED:phone:7a3f...>`），保留结构但不泄露内容
- 若单条记忆的敏感内容占比 > 30%，整条记忆标记为 `MIGRATION_BLOCKED`，不入目标分支

**准确率目标**：
- MVA 阶段：L0 正则召回率 ≥ 95%，精确率 ≥ 90%；L1 NER 召回率 ≥ 80%
- 后续迭代：L1 召回率 ≥ 95%，新增 L2 语义隐私检测

**接口契约**：
```python
IPrivacyFilter (ABC)
├── apply(content: str, filter_level: FilterLevel, branch_id: str) -> FilteredContent
├── detect_pii(content: str) -> List[PiiSpan]          # 返回匹配区间和类型
└── get_stats(branch_id: str) -> PrivacyFilterStats    # 过滤次数、准确率监控
```

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

**时钟与冲突策略**：

| 项目 | 决策内容 |
|------|---------|
| 时间源 | 物理时间戳（time.time_ns()）+ Hybrid Logical Clock (HLC) 偏移 |
| 时钟同步 | 设备启动时强制 NTP 同步，运行期每 10 分钟校准一次 |
| 偏差容忍 | 最大可接受偏差 `MAX_CLOCK_SKEW = 500ms` |
| 偏差检测 | 收到远程操作时，若 `|remote_ts - local_ts| > MAX_CLOCK_SKEW` → 标记为 `SUSPECTED_SKEW` |
| 偏差处理 | `SUSPECTED_SKEW` 操作不自动覆盖本地值，而是创建 CONTRADICTS 边，通知用户决策 |

**HLC 实现**：
```python
class HybridTimestamp:
    def __init__(self, physical: int, logical: int = 0):
        self.physical = physical  # 物理时间（ns）
        self.logical = logical    # 逻辑计数器（解决同一毫秒内多操作）
    
    def __lt__(self, other):
        if self.physical != other.physical:
            return self.physical < other.physical
        return self.logical < other.logical
```

**关键语义修正**：
- LWW 的"Last"不是"物理时间上最后发生"，而是"HLC 排序上最后提交"
- 当物理时间戳差异在 `MAX_CLOCK_SKEW` 内时，信任 LWW 语义
- 当差异超出容忍度时，降级为"保留冲突，人工决策"

**时钟同步与偏差容忍**：
- 设备启动时强制 NTP 同步，运行期每 10 分钟校准一次
- 最大可接受偏差 `MAX_CLOCK_SKEW = 500ms`
- 收到远程操作时，若 `|remote_ts - local_ts| > MAX_CLOCK_SKEW` → 标记为 `SUSPECTED_SKEW`
- `SUSPECTED_SKEW` 操作不自动覆盖本地值，而是创建 CONTRADICTS 边，通知用户决策

**核心特性**：
- **冲突处理**：`LWWMap` 以 `(timestamp, device_id)` 为全序比较器，天然 add-wins。上层 MVCC 保留冲突版本，标记为 `CONTRADICTS` 边，不自动消解。
- **实时同步**：设备间通过 WebSocket 广播 LWW-CRDT 操作（`op_type, key, value, timestamp, device_id`）。
- **定期刷盘**：每 5 分钟或 session 结束，将 `dirty_keys` 刷入 L3 `entity_versions`。
- **初始化**：从 L3 加载当前 branch 的 profile 事实初始化 L0。


**L0→L3 刷盘契约**：

```python
class SyncManager:
    def checkpoint(self, branch_id: str) -> None:
        """
        触发条件：每 5 分钟 / session 结束 / dirty_keys 超 100 条。
        执行流：
          1. 冻结 lww_map.dirty_keys 快照
          2. 调用 version_manager.commit(branch_id, snapshot)
          3. 按 entity_id 分组写入 entity_versions
          4. 冲突解决：比较 HLC
             • HLC 可比较 → LWW，旧版标记 superseded
             • HLC 不可比较（超出 MAX_CLOCK_SKEW）→ 保留双版本，创建 CONTRADICTS 边
          5. 清空 dirty_keys，广播 checkpoint_ack
        """
```

**W1 实现状态**：`LWWMap`、`HybridTimestamp`、`L0SyncLayer`、`SyncManager` 已全部真实实现并单元测试覆盖。支持 multi-device add-wins、HLC 逻辑时钟、500ms clock-skew 检测与冲突标记。`MockL0SyncLayer` 保留用于快速测试。
```

#### 4.1.1 故障恢复与同步保障

**三种故障模式**：

| 故障模式 | 检测方式 | 恢复策略 |
|---------|---------|---------|
| 网络分区 | WebSocket 心跳超时（30s 无响应） | 本地操作日志持续写入 SQLite，恢复后重放 |
| 消息丢失 | ACK 机制：接收方需回复 `sync_ack` | 发送方 5s 内未收到 ACK 则加入重试队列 |
| 设备离线重连 | 连接断开后重连事件 | 请求 `SyncManager.get_delta(since=last_vector_clock)` 增量同步 |

**重试策略**：
- 指数退避：1s → 2s → 4s → 8s，最多 4 次
- 超过 4 次仍失败 → 标记该设备为 `STALE`，写入 `sync_conflicts` 表待人工介入

**冲突通知机制**：
- LWW-CRDT 合并后若检测到同一 key 存在多个有效版本（vector_clock 不可比较）→ 不自动消解
- 生成 `ConflictNotification` 事件，由 Agent Core 在下一轮对话中向用户报告："检测到手机和车机的偏好设置不一致，请确认保留哪个"

**脏数据清理**：
- `dirty_keys` 存活超过 1 小时未刷盘 → 强制触发 checkpoint
- checkpoint 失败超过 3 次 → 告警并保留操作日志供排查

#### 4.1.2 无冲突域写入契约（借鉴 Cursor 物理隔离优先原则）

**核心原则**：在高度结构化数据领域（记忆/知识图谱），**物理隔离优于自动合并**。自动合并仅适用于无冲突域或原子级操作，语义级冲突必须引入仲裁。

**分层写入域锁定**：

| 层级 | 写入域单位 | 并发规则 | 隔离机制 |
|------|-----------|---------|---------|
| **L0** | key-value 键 | 同 key 跨设备写入 → LWW-CRDT add-wins | HLC 全序比较，冲突保留双版本 |
| **L1** | session 上下文 | 仅当前会话写入，session 结束即丢弃 | 会话级物理隔离，无需跨端合并 |
| **L2** | session_id 分区 | 不同 session 间无交集 | 分区即隔离，session_id 作为物理分片键 |
| **L3** | concept_id / edge_id | **禁止对同一 entity_id 并发写入不同属性** | 写入前检查 entity 锁（W2 实现） |

**架构契约（W2 落地）**：
```python
class WriteDomainLock:
    """显式化无冲突域划分，确保同 entity 不被并发修改。"""
    
    def acquire(self, layer: str, entity_id: str, branch_id: str) -> bool:
        """
        返回 True 表示获得写入权；False 表示该 entity 正被其他设备/Agent 修改。
        L0: key 级锁
        L1: session 级锁（单会话天然串行）
        L2: session_id 级锁（不同 session 并行）
        L3: concept_id / edge_id 级锁
        """
        ...
```

**价值**：规避 Cursor 所警告的"文本级 CRDT 合并结构化数据导致语法崩溃"问题。ChronoPersona 的分层设计已隐含此思想，显式化为契约后可在多端场景下避免隐式冲突。

### 4.2 MVCC Version & Branch Manager

**混合粒度设计**：

| 层级 | 粒度 | 实现方式 | MVCC 机制 |
|------|------|---------|----------|
| **L2 Episodic** | Session-MVCC（Session 级粗粒度） | 每 session 结束对 L0 lww_map 状态及 L2 索引打 snapshot | `SnapshotVersionManager`：序列化 LWWMap JSON + L2 metadata |
| **L3 Semantic** | Entity-MVCC（Entity 级细粒度） | 每条事实/画像独立版本链 | `EntityVersionManager`：逐 entity 维护 `version_chain` |
| **L0 CRDT** | Key-MVCC（Key 级细粒度） | 每个 key 独立版本链，与 LWW 冲突保留协同 | `KeyVersionManager`：逐 key 维护 `version_chain`，与 LWWMap 共享 HLC |

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
| **压缩追溯** | 每个压缩摘要包含 `summary_id` 和 `source_turn_ids: List[int]`，关联原始对话轮次；摘要不参与向量检索（仅作为 L1 上下文），原始轮次仍保留在 L2 供精确召回 |
| **具身上下文注入** | 2D 环境状态（Agent 位置、视野内物体、最近动作）转换为文本描述，注入 system prompt |

**L1 压缩摘要存储契约**：

| 属性 | 说明 |
|------|------|
| 存储位置 | L1 Working Memory 内部 `compressed_summaries: List[CompressedSummary]`（内存对象，**不进入向量库**） |
| 生命周期 | 与当前 session 绑定，session 结束随 L1 丢弃；需长期保留的摘要由 Reflection Agent 异步提炼后写入 L3 |
| 数据结构 | `CompressedSummary(summary_id, source_turn_ids: List[int], content, created_at, token_count)` |
| 引用方式 | L1 上下文组装时按 `created_at` 逆序拼接；原始轮次保留在 L2，通过 `source_turn_ids` 可追溯 |

**具身上下文示例**：
```
[Embodied Context]
Agent位于客厅(3,4)，面向北方。
视野内：沙发(2,3)、茶几(3,2)、用户(4,4)。
最近动作：从厨房移动到客厅。
```

### 4.4 L2: Episodic Memory

| 特性 | MVA 实现 | 后续迭代 |
|------|---------|---------|
| **存储引擎** | **FAISS** (`faiss-cpu`) 内存索引，按 `branch_id` 隔离 | Qdrant Docker 部署 |
| **索引算法** | `IndexFlatIP`（精确内积，L2 归一化后等价 Cosine） | HNSW（`m=16`, `ef_construct=100`） |
| **Embedding** | `MockBGEEmbedder`（128d 确定性向量） | BAAI/bge-large-zh-v1.5（1024d） |
| **量化** | 未启用（数据量 < 10K） | Scalar 1-bit/2-bit 量化 |
| **Payload 过滤** | 内存内按 `branch_id` 字典隔离 | Qdrant payload 过滤 |
| **时间索引** | 未实现 | 按 `created_at` 范围过滤 |
| **MVCC** | Session snapshot 接口预留 | Session 级 snapshot 自动刷盘 |
| **重要性加权** | `importance` 字段参与检索排序（`score = sim * importance * freq_boost`） | 同左，Qdrant 内通过 payload 过滤实现 |

**选型理由**：FAISS 在万级以下数据提供 O(1) 精确检索，零 Docker 依赖，与自研 `MockBGEEmbedder` 无缝集成。当数据量突破 10K 或需要持久化时，可无缝迁移至 Qdrant HNSW。

**性能边界（MVA 实测）**：
- 1,000 节点：P99 检索延迟 < 2ms
- 10,000 节点：P99 检索延迟 < 5ms
- 100,000 节点：建议切换至 `IndexIVFFlat` 或 Qdrant HNSW

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

### 4.5 L3: Semantic Memory + Intent Graph

#### 4.5.1 数据模型（纯 PostgreSQL）

#### 4.5.2 语义边构建策略（带置信度 + 分流处理）

**核心原则**：每类边有独立的构建方法、置信度阈值、失败兜底。

| 边类型 | 构建方法 | 置信度来源 | MVA 阈值 | 失败兜底 |
|--------|---------|-----------|---------|---------|
| **MENTIONS** | 规则：NER 实体在对话中出现 | 实体链接置信度 | 0.85 | 不写入 |
| **TEMPORAL_NEXT** | 规则：同 session 相邻 turn；跨 session 按时间戳 | 时间邻近度 | 0.90 | 不写入 |
| **IS_A** | LLM 泛化 | LLM logprob | 0.75 | 挂起待审核 |
| **CAUSED** | **Tier 1 模板匹配** + LLM 二次验证 | 模板匹配度 × LLM 确认 | 0.80 | **降级为 CORRELATED** |
| **CORRELATED** | CAUSED 降级产物 + 统计共现 | 共现频率 | 0.60 | 不写入 |
| **CONTRADICTS** | 规则：同一 key 新旧值语义相反 | 语义对立检测 | 0.90 | 人工确认 |
| **SIMILAR_TO** | 向量相似度 > 0.85 | 向量相似度 | 0.85 | 不写入 |
| **BELONGS_TO** | 系统元数据 | 1.0 | 1.0 | 无 |
| **TRIGGERED_BY** | MVA：关键词模板 | 共现频率 | 0.70 | 不写入 |

#### 4.5.3 CAUSED 边三阶策略

**W1 实现状态**：Tier 1（模板匹配）已在 `SimpleInsightEngine` / `memory_system/insight/` 中 MVA 实现，准确率目标 > 95%，召回率 ~40%。不匹配模板时降级为 `CORRELATED` 边。

Tier 2（统计共现评估）和 Tier 3（LLM 深度因果推理）标记为 `[FUTURE]`，W1 测试文件 `test_caused_tier2.py` 已按规范 `pytest.skip`。

**注意**：当前代码示例仅实现 Tier 1 模板匹配；Tier 2/3 为 `[FUTURE]` 占位，不在 MVA 范围内。

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
9. `CORRELATED`：弱相关关系（CAUSED 降级产物，不进入因果推理链）

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
| `correlate` | "和...有关吗" | `CORRELATED` | 2 |

#### 4.5.4 最小可行本体（MVO）种子注入

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

**4.5.5 关键词快速通道（借鉴酒馆 World Info）**

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

**补充说明：检索路径 6 步流程实现状态（4.5.6 更新）**

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

**4.5.6 异步构建流水线**

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

**Insight 触发量化契约（MVA）**：
- `trigger_rounds`: 每 **10 轮**对话（可配置，范围 5–20）
- `trigger_daily`: 每日 **03:00 UTC** 兜底扫描（无论轮数是否达标）
- `min_confidence`: 0.6（低于此值的 insight 不写入，避免噪声）

**4.5.7 检索路径精确执行流程（6 步）**

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

**4.5.8 性能边界与保障**

| 数据规模 | 延迟 | 评级 |
|---------|------|------|
| 1,000 节点 / 5,000 边 | 10-30ms | ✅ |
| **MVA 目标：10,000 节点 / 50,000 边** | **50-150ms** | ✅ |
| 100,000 节点 / 500,000 边 | 200-800ms | ⚠️ 需优化 |

**保障策略**：
1. 限制 `max_hops ≤ 3`
2. 分层查询（hop_limit 1→2→3，召回足够提前返回）
3. 对 `semantic_edges(source_id, edge_type, branch_id)` 建立复合索引

**性能验证计划（Week 3 执行）**：
- 使用 `EXPLAIN (ANALYZE, BUFFERS)` 在 10,000 节点 / 50,000 边数据集上执行标准 CTE 查询（见 4.5.7 模板），目标 Planning Time < 5ms、Execution Time < 150ms。
- 若 Execution Time > 200ms，触发优化：增加 `(target_id, edge_type)` 反向索引、或启用 `MATERIALIZED` CTE 缓存中间结果。
- 性能基线数据写入 `reports/perf_baseline.json`，作为后续回归测试基准。

**4.5.9 冷启动三阶段**

| 阶段 | 时间 | 内容 |
|------|------|------|
| **Phase 1** | Week 1-2 | 种子注入：200 概念 + 6 条硬编码策略 |
| **Phase 2** | Week 2-4 | 对话驱动：前 50 轮产 MENTIONS + TEMPORAL_NEXT；50-200 轮积累 IS_A |
| **Phase 3** | Week 4+ | Insight 驱动：周期性主动反思优化图谱 |

**MVO 种子扩展接口**：
- 配置文件：`configs/mvo_extensions/{domain_name}.yaml`，包含 `concepts` 列表和 `intent_patterns` 列表。
- 加载契约：`IMVOSeedLoader.load(domain: str, branch_id: str) -> SeedPayload`，幂等执行（重复加载不重复插入）。
- 示例：新增医疗域时，放置 `medical.yaml`（含概念"症状、药物、就诊"和意图策略"症状追溯"），重启后自动注入，无需改代码。
- 冲突处理：同名 `concept_id` 已存在时跳过，避免覆盖用户已有概念。

**4.5.10 混合召回融合权重**

MVA 初始权重：`final_score = 0.6 * graph_score + 0.4 * vector_score`

后续根据 A6 评估场景动态调参。
### 4.6 Retrieval Engine

检索执行遵循 4.5.7 的 6 步流程，混合召回阶段采用 `0.6 * graph_score + 0.4 * vector_score` 的融合权重。

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
| **T3b** | CORRELATED 边构建 | 本地规则引擎 | — | 本地 |
| **T4** | 记忆反思/摘要 | Kimi 2.6 | DS-V4-pro | 云端 |
| **T5** | 回复生成 | DS-V4-pro | Kimi 2.6 | 云端 |
| **T6** | 冲突消解语义 | Kimi 2.6 | DS-V4-pro | 云端 |
| **T7** | 评估/测试 | DS-V4-pro | Kimi 2.6 | 云端 |

**缓存策略**：SQLite 缓存，TTL 24h，缓存键为 `hash(task_type + prompt + branch_id + persona_id)`，避免跨分支/人格的缓存污染。  
**缓存键生成规则**：`cache_key = hash(task_type + prompt + branch_id + persona_id)`，确保不同分支、不同人格的请求不会共享缓存。  
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
  "token_scope": str,         # system / user / agent，区分系统开销与业务 token
  "latency_ms": float,        # 端到端耗时（含网络）
  "ttft_ms": float,           # Time To First Token（流式场景）
  "cost_usd": float,          # 按模型单价计算的预估费用
  "cache_hit": bool,          # 是否命中 prompt cache（若模型支持）
  "status": str               # success / error / timeout
}
```

#### 存储与聚合

- **原始记录**：写入独立的 `metrics_store`（SQLite / 轻量级时序库），**不直接污染记忆层级**。原始 prompt 在持久化前经 `IPrivacyFilter.apply(content, level=L0)` 脱敏处理；日志中存储 prompt 哈希值用于去重，不存储原始文本。
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

**排期**: W1 冻结接口签名（Mock 实现为空 pass）；W5 与 Model Router 同步实现，作为 Agent 核心循环的可观测性基础。

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

**情感置信度传播（T0 规则引擎增强）**：
- `EmotionState` 增加 `confidence: float` 字段。
- T0 规则引擎：关键词匹配成功 → `confidence = 0.9`；无匹配 → `confidence = 0.5`。
- `_build_prompt` 仅当 `confidence >= 0.7` 且 `current_state != NEUTRAL` 时注入 `[Emotion State]` 文本段，避免模糊输入触发错误状态转移。

**训练数据规范（Week 5 补充）**：
- **数据来源**：从 L2 Episodic Memory 中按 session 采样对话轮次，优先选取情感极性明显的片段（用户明确表达喜怒哀乐）。
- **标注 schema**：每条样本包含 `(context_text, emotion_label, intensity)`。
  - `emotion_label`: NEUTRAL / CURIOUS / EMPATHETIC / CONCERNED / REFLECTIVE
  - `intensity`: 0.0 ~ 1.0 连续值，由标注者根据情感强烈程度打分
- **标注指南**：
  - 强度 ≥ 0.7 为强烈情感（如"我好难过" → CONCERNED 0.85）
  - 强度 ≤ 0.3 为轻微情感（如"有点担心" → CONCERNED 0.25）
  - 中性闲聊标记为 NEUTRAL 0.0
- **评估指标**：MAE < 0.2（预测强度与标注强度的平均绝对误差）；5-fold 交叉验证。
- **数据划分**：训练 70% / 验证 15% / 测试 15%，按 session 划分避免数据泄漏。

### 4.10 2D Virtual Environment（Token→Action Bridge 架构）

**W1 实现状态**：`GridWorldAdapter` 已真实实现（非 Mock），支持 20×20 网格坐标、FOV 锥形视野计算、边界钳制、`action_token` → `LowLevelCommand` 映射。MVA 阶段纯文本描述感知输出，无 Canvas 渲染。Week 7 补极简 HTML 前端。

**核心定位**：不为机器人训练"身体"（VLA），而是构建可跨本体移植的"人格灵魂"。

**设计边界**：极简网格世界验证人格-身体解耦，不追求真实物理仿真。

| 组件 | 设计 |
|------|------|
| **世界模型** | 离散网格（20×20），每个格子可有物体/障碍物 |
| **Agent 状态** | `(x, y, θ)` 坐标 + 朝向，FOV 锥形视野（5格距离，90°视角） |
| **物体** | 静态（家具、墙）/ 动态（用户位置、可拾取物品） |
| **高层动作 Token** | `approach_gently`, `retreat_slowly`, `turn_to_user`, `interact`, `look_around` |
| **感知输出** | 视野内物体列表 + 相对位置 + 属性描述 → 文本化注入 L1 |
| **感知更新频率** | 每 100ms 更新一次；被遮挡物体不输出；动态物体进入 FOV 时触发即时更新 |

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

#### 4.11.1 权限校验流程

**双重校验机制**：

```
LLM 生成 skill_call 意图
    │
    ▼
[第一层: 预过滤] ──► ISkillRegistry.get_available_skills(branch_id, persona_id)
    │                    • 读取 PersonaAnchor.skill_permissions
    │                    • 过滤掉 forbidden_skills
    │                    • 仅返回 allowed_skills（若 allowed_skills 非空）
    │                    • 返回列表注入 LLM system prompt（模型只能看到可用技能）
    ▼
[第二层: 执行校验] ──► ISkillRegistry.execute(skill_id, ...)
    │                    • 再次检查 skill_id 是否在可用列表
    │                    • 不在列表中 → 抛出 SkillPermissionDenied
    │                    • 在列表中 → 正常执行
    ▼
   执行 Skill
```

**关键规则**：
- `allowed_skills` 非空时 → 白名单模式，仅列表内技能可用
- `allowed_skills` 为空且 `forbidden_skills` 非空时 → 黑名单模式，仅排除禁用技能
- 两者冲突时（某 skill 同时在 allowed 和 forbidden 中）→ `forbidden_skills` 优先，拒绝执行

**错误契约**：
```python
class SkillPermissionDenied(Exception):
    skill_id: str
    persona_id: str
    reason: str   # "not_in_allowed_list" / "explicitly_forbidden"
    
    # Agent Core 捕获后行为：
    # 1. 记录 ERROR 日志
    # 2. 向用户返回："当前人格不支持该操作"
    # 3. 不暴露具体权限配置（防止信息泄露）
```

**与 4.0.1 的联动**：
- `therapist` 人格配置 `forbidden_skills: ["rpg_dice_roll"]`
- 若用户通过提示词注入（prompt injection）诱导 LLM 调用 `rpg_dice_roll` → 第二层校验拦截，返回礼貌拒绝

### 4.12 记忆蒸馏与 Dreaming 机制（借鉴认知仿生主动反思架构）

**核心哲学**：L2 Episodic 向 L3 Semantic 的转化不是简单复制，而是**蒸馏（Distillation）**——信息密度从"高冗余、高噪声"向"高结构化、低冗余"跃迁。

**Dreaming（Memory Consolidation Agent）**：

触发条件：每 24 小时、每完成 5 个会话周期、或系统空闲时自动启动。

执行流程：
1. **读取阶段**：从 L2 拉取近期高重要性会话（按 `importance` 预过滤，仅处理 top-K）。
2. **模式提取（Pattern Extraction）**：识别重复交互模式。
   - 示例："用户每次提到'优化性能'时，后续都会要求查看火焰图"
   - 示例："当代码包含 `unsafe` 块时，Agent 应主动提示安全检查清单"
3. **噪声清理（Noise Reduction）**：去除临时性、上下文依赖过强的内容，保留可泛化的行为规则。
4. **知识固化（Crystallization）**：将自然语言经验转化为结构化规则，存储格式为 **三元组 + 向量嵌入** 的混合形式：
   ```python
   BehavioralRule(
       trigger="用户提及性能优化",
       action="主动建议查看火焰图",
       confidence=0.92,
       source_memory_ids=["mem-001", "mem-003"],
       branch_id="main",
   )
   ```
5. **写入语义记忆**：更新 L3 `insights` 表，建立反向索引，确保主 Agent 通过 RAG 快速召回。

**与 RAG 的本质区别**：RAG 是"外部知识注入"（读文档），Dreaming 是"经验学习"（从自身操作历史中提炼启发式规则）。模型权重不变，但系统行为持续进化。

**W1 实现状态**：`SimpleInsightEngine` 已实现 Tier 1 关键词共现（Phase A 骨架）。Phase B 模式提取标记为 `[FUTURE]`，W2 启动轻量级骨架。

### 4.13 差异化遗忘与重要性评分（借鉴行业实践 "Pull on demand, never fill up"）

**三层记忆的差异化衰减策略**：

| 层级 | 衰减函数 | 生命周期 | 清空/保留策略 |
|------|---------|---------|--------------|
| **L1 Working** | 无衰减，会话结束即清空 | 单会话 | 仅保留最后 N 轮作为摘要，原始轮次在 L2 |
| **L2 Episodic** | 指数衰减 `R = e^(-t/S)`，S = importance × ttl_base | 中期（数小时至数天） | `importance < 0.2` 且过期 → 软删除；`gc()` 定期清理，MVCC 历史保留审计 |
| **L3 Semantic** | 极慢衰减，近似永久 | 长期（跨会话） | 通过"反学习"（Unlearning）处理过时知识：新旧冲突时旧知识标记 `deprecated`，不物理删除 |

**多因子重要性评分模型**：

```
importance = σ(
    w1 × entropy_gain      # 信息熵增益：LLM 困惑度越高越重要
  + w2 × task_success      # 任务成功关联：RLHF 反馈
  + w3 × log1p(access_count)  # 访问频率：LFU 信号
  + w4 × user_explicit     # 用户显式标记："记住这个"
)

effective_score = vector_similarity × importance × exp(-elapsed_hours / (ttl_base × importance))
```

**Schema 落地**：`MemoryEntry` 已包含 `importance` / `access_count` / `ttl_hours` / `entropy_gain` / `last_accessed` 字段。`SimpleEpisodicStore.retrieve()` 已按 `importance × freq_boost` 加权排序。

**W1 实现状态**：Schema 与检索加权已落地；指数衰减 `gc()` 与 `entropy_gain` 计算标记为 `[FUTURE]`，W2 实现。

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

-- [FUTURE: W4] 周期性主动反思产出（Insight 模块启用时解冻）
-- CREATE TABLE insights (...);

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

-- [FUTURE: M4/W7] 空间-情感-动作关联记忆（具身模块启用时解冻）
-- CREATE TABLE embodied_interactions (...);

-- 同步操作日志（W1 冻结：CRDT 操作落盘与故障恢复）
CREATE TABLE sync_operation_logs (
    id UUID PRIMARY KEY,
    device_id TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    operation_type TEXT NOT NULL CHECK (operation_type IN ('set', 'delete', 'merge')),
    key TEXT NOT NULL,
    value_hash TEXT,         -- 值哈希，避免存储大对象
    hlc_timestamp JSONB NOT NULL,
    vector_clock JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sync_logs_device ON sync_operation_logs(device_id, branch_id, created_at);

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

**W1 冻结范围（硬阻塞）**: `AbstractMemoryStore`、`AbstractAgentCore`、`AbstractVersionManager`、`EmbodiedAdapter`、`ModelRouter`  
**[FUTURE] 预留接口（W4+ 启用）**: `IPersonaInjector`、`IMemoryMigrationService`、`ICostTracker`、`ISkillRegistry`、`ISkill` —— W1 仅冻结空接口签名，Mock 实现返回 `NotImplementedError` 或空值，确保编译与 `test_mock_pipeline.py` 通过。

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
├── importance: float           -- 多因子评分
├── access_count: int           -- LFU 信号
├── ttl_hours: Optional[float]  -- 指数衰减参数
├── entropy_gain: Optional[float]  -- 信息熵增益
├── last_accessed: Optional[str]   -- 最近访问时间
└── metadata: Dict

RetrievedContext
├── working_memories: List[MemoryEntry]     -- L1
├── episodic_memories: List[MemoryEntry]    -- L2
├── semantic_facts: List[Fact]              -- L3
├── insights: List[Insight]                   -- 主动反思
├── navigation_path: List[NavigationStep]    -- 意图图谱路径
└── total_tokens: int

Action
├── action_token: str
├── params: Dict

ActionPlan
├── action_token: str
├── action_params: Dict
└── reasoning: str

AgentOutput
├── reply_text: str
├── action_plan: Optional[ActionPlan]
├── emotion_modulation: Optional[Dict]  -- e.g., {speed_mult: 0.5, volume_mult: 0.8}
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

CostRecord
├── internal_tokens: int
├── internal_latency_ms: float
└── metadata: Dict

CostReport
├── total_calls: int
├── total_input_tokens: int
├── total_output_tokens: int
├── total_cost_usd: float
├── avg_latency_ms: float
├── breakdown_by_model: Dict[str, ModelSummary]
└── breakdown_by_branch: Dict[str, BranchSummary]

MemoryAnchor
├── persona_id: str
├── layer_level: str       -- "L0" / "L1" / "L2" / "L3"
└── time_range: Tuple[datetime, datetime]

MigrationResult
├── migrated_count: int
├── conflict_list: List[ConflictItem]
├── auto_resolution_rate: float
└── target_snapshot_id: str
```


### 6.2.1 认证与权限模型

**MVA 阶段采用轻量方案**：API Key + Branch 级 RBAC。

**认证机制**：
- HTTP Header: `Authorization: Bearer <api_key>`
- API Key 由部署时环境变量注入，MVA 阶段单租户单 Key
- WebSocket 连接时通过 `?token=<api_key>` 查询参数认证

**权限模型**：

| 角色 | 可读分支 | 可写分支 | 可执行操作 |
|------|---------|---------|-----------|
| `reader` | 授权分支列表 | 无 | GET /api/v1/memory/*, GET /api/v1/emotion |
| `writer` | 授权分支列表 | 授权分支列表 | POST /api/v1/chat, POST /api/v1/sync/force |
| `admin` | 全部 | 全部 | POST /api/v1/branches/*/checkout, DELETE 操作 |

**Persona Anchor 访问控制**：
- Persona Anchor 配置（含 `core_narrative`、`style_examples`、`skill_permissions`）属于敏感身份资产。
- 读取：仅限 `admin` 和该 Anchor 所属分支的 `writer`（需同时满足 `branch_id` 匹配）。
- 写入/更新：仅限 `admin`。
- **禁止**通过 `/api/v1/chat` 等用户对话接口返回完整 Anchor 内容（防止提示词注入反噬）；LLM 仅接收注入后的上下文，不接收原始 YAML。

**分支级隔离**：
- 每个 API Key 关联 `allowed_branches: List[str]`
- 请求中显式传递 `branch_id`，服务端校验该 Key 是否有权访问
- **禁止**使用默认全局分支或从 session 推断分支

**未授权处理**：
- 认证缺失 → `401 Unauthorized`
- 分支无权限 → `403 Forbidden` + `{"error": "branch_access_denied", "branch_id": "xxx"}`

**排期**: MVA 阶段采用单租户单 Key，权限系统为 `[FUTURE]`；W1 冻结 REST 路径规范，认证中间件留空接口 `IAuthMiddleware`。

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

WebSocket 传输采用 JSON 序列化，心跳间隔 30s，超时 60s 自动断线重连。

**传输安全**：
- 生产环境强制使用 `wss://`（TLS 加密），MVA 本地开发环境允许 `ws://`。
- 敏感字段（`user_profile`、`emotion_state`）在 CRDT 同步消息中端到端加密标记为 `[FUTURE]`；MVA 阶段依赖传输层 TLS。
- WebSocket 连接建立时通过 `?token=<api_key>` 进行认证，服务端在握手阶段即拒绝无效 token，避免建立未加密会话后才发现鉴权失败。

### 6.3.1 Request/Response Schema 示例

**POST /api/v1/chat 请求体**：
```json
{
  "message": "我最近总是睡不着",
  "branch_id": "therapist",
  "persona_id": "therapist",
  "embodied_state": {
    "x": 3,
    "y": 4,
    "theta": 0,
    "fov_objects": ["sofa", "table"]
  }
}
```

**POST /api/v1/chat 响应体**：
```json
{
  "reply_text": "失眠确实让人疲惫。在你躺下的时候，脑海中通常会浮现什么？",
  "action_plan": {
    "action_token": "approach_gently",
    "action_params": {"speed": 0.5, "proximity": 1.0},
    "reasoning": "用户焦虑，应缓慢接近"
  },
  "emotion_state": {
    "current_state": "EMPATHETIC",
    "intensity": 0.7
  },
  "used_memories": ["mem-001", "mem-003"],
  "branch_id": "therapist"
}
```

**WebSocket `chat.message` 事件**：
```json
{
  "event": "chat.message",
  "data": {
    "message": "我最近总是睡不着",
    "branch_id": "therapist",
    "persona_id": "therapist",
    "embodied_state": {
      "x": 3,
      "y": 4,
      "theta": 0,
      "fov_objects": ["sofa", "table"]
    }
  }
}
```

---

## 7. 模型路由策略

### 7.1 任务分级与路由表

| 任务层级 | 任务类型 | 首选模型 | 降级链 | 本地/云端 | 缓存 |
|---------|---------|---------|--------|----------|------|
| **T0** | 情感分类（3类） | Qwen3.5-9B | DS-V4-flash | 本地 | ✅ 24h |
| **T1** | 意图识别（8类） | Qwen3.5-9B | DS-V4-flash | 本地 | ✅ 24h |
| **T2** | 实体提取（NER） | DS-V4-flash | Kimi 2.6 | 云端 | ✅ 24h |
| **T3** | 边构建/关系推理 | DS-V4-flash | Kimi 2.6 | 云端 | ✅ 24h |
| **T3b** | CORRELATED 边构建 | 本地规则引擎 | — | 本地 | ❌ |
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

### 8.1.1 测试设计审查方案（Test Design Review Protocol）

**目的**：防止"测试迁就实现"（test accommodating bug），确保测试验证的是需求语义而非实现巧合。

**审查触发时机**：
1. 每个评估批次（A1-A11）完成后，必须执行一次审查。
2. 任何测试失败修复后，若涉及"修改测试预期值"，必须触发审查。
3. Week 5 收尾、Week 6 启动时，执行全量测试语义审计。

**审查角色**：
- **架构师（必需）**：审查测试断言与架构文档/需求文档的一致性。
- **测试作者**：解释测试意图与数据选取依据。
- **实现工程师**：说明实现逻辑，但不参与"是否该改测试"的决策。

**审查清单（Checklist）**：

| 检查项 | 通过标准 | 失败处理 |
|--------|---------|---------|
| **断言语义对齐** | `assert` 验证的是 `requirements.md` 或接口 docstring 中声明的行为，而非代码内部算法细节 | 回退测试修改，改为修复实现或更新需求文档 |
| **数据边界覆盖** | 数值型测试覆盖最小值、中间值、最大值（如 intensity ∈ [0.0, 0.5, 1.0]） | 补充缺失边界值用例 |
| **Mock 解耦** | Mock 的返回值与真实实现的内部状态机、算法路径无关 | 重构 Mock，消除隐式耦合 |
| **失败根因记录** | 每次测试失败修复必须在 `reports/test_failures/` 留下记录，说明：根因、修复方案、为何选择该方案 | 补录记录，否则禁止合入 |
| **PLACEBO 测试识别** | 不存在"仅因当前实现返回该值而通过，换种合法实现即失败"的测试 | 删除或重写为语义驱动 |

**审查产出物**：
- `reports/test_design_review.md`：包含审查日期、参与人、检查项结果、发现的问题列表、修复计划。
- 若审查发现"测试迁就实现"：必须在 24 小时内回退相关提交，修复实现后重新跑通全量测试。

**与排期的关系**：
- Week 5 收尾（06-14）：完成全量测试设计审查，产出首份报告。
- Week 6 每日站会：同步审查发现的问题，阻塞新评估任务直至测试债务清零。

### 8.2 轨道A：自建对抗测试集（8 场景）

| 场景ID | 场景名称 | 测试目标 | 构造方法 |
|--------|---------|---------|---------|
| A1 | 记忆召回 | 跨 session 事实检索 | 构造 5 轮 session，每轮植入 3-5 个事实，最后提问 |
| A2 | 跨 session 关联 | 时间线推理 | "上次你说的那个问题，后来解决了吗" |
| A3 | 角色隔离 | Branch 隔离有效性 | 在 Therapist branch 问 RPG 剧情，应回答"不知道" |
| A4 | 角色共享 | Main branch 穿透 | 在 RPG branch 问用户姓名（存在 Main），应正确回答 |
| A5 | 多端冲突 | CRDT 合并正确性 | 模拟手机/车机同时写入矛盾偏好，检查合并结果 |
| A6 | 意图图谱导航 | 结构化检索优于纯向量 | 同一问题分别用"纯向量"和"意图图谱"检索，对比召回 |
| A6b | CORRELATED 边召回 | 弱相关关系辅助检索 | 查询"和...有关吗"时，CORRELATED 边是否贡献额外召回 |

**W1 已完成的基础测试**：
- `test_intent_graph.py` / `test_intent_navigator.py`：验证 Intent Graph BFS 导航、max_hops 限制、分支隔离、意图模式匹配。为 A6 意图导航精度提供单元级基线。
- `test_grid_world.py`：验证 FOV 检测、边界钳制、动作 Token 翻译，为 A8/A9 具身感知提供基线。
- `test_l0_crdt.py`：验证 HLC add-wins、clock-skew 冲突解决、分支隔离，为 A5 多端冲突提供单元级基线。

#### A6 详细测试用例

| 测试 ID | 查询 | 纯向量 RAG 难点 | Intent Graph 优势 |
|--------|------|---------------|----------------|
| A6-1 | "我上周的方案后来怎样" | "方案"语义泛化 | TEMPORAL_NEXT 链 |
| A6-2 | "川菜和粤菜我喜欢哪个" | 无法聚合对比 | SIMILAR_TO + CONTRADICTS |
| A6-3 | "为什么我最近焦虑" | "焦虑"与"工作压力"向量距离远 | CAUSED 回溯 |
| A6-4 | "上次你说的那个餐厅" | "那个"无法向量匹配 | MENTIONS + 指代消解 |
| A6b-1 | "川菜和粤菜有关吗" | 纯向量无法表达弱相关 | CORRELATED 边提供弱关联线索 |

**A6 预期召回与通过标准**：
- A6-1：预期召回包含"上周方案"相关记忆节点（`memory_nodes.id` 对应 session_2 的方案讨论）；判定标准：Recall@5 ≥ 0.8 且目标记忆排名 ≤ 3。
- A6-2：预期召回同时包含"川菜"和"粤菜"的偏好记忆，并识别 CONTRADICTS 边；判定标准：Recall@5 ≥ 0.8 且矛盾边被检索到。
- A6-3：预期召回"工作压力"相关记忆，并通过 CAUSED 边回溯到"焦虑"概念；判定标准：Recall@5 ≥ 0.8 且因果链完整。
- A6-4：预期通过 MENTIONS 边和指代消解定位到"上次提到的餐厅"具体记忆；判定标准：Recall@5 ≥ 0.8 且目标记忆排名 ≤ 2。
| A7 | 情感一致性 | 状态机不漂移 | 连续输入负面内容，检查状态转移路径是否符合设计 |
| A8 | 具身感知 | 空间记忆影响对话 | Agent 在"厨房"vs"客厅"时，对"我饿了"的回复差异 |
| A9 | 跨本体迁移 | 人格一致性 | 同一人格驱动 grid_2d / ros2_mobile，行为参数一致 |
| A10 | 动作可审计 | 决策链追溯 | 检查每个动作是否有 reasoning 字段，且与情感状态一致 |
| A11 | 人格漂移检测 | 风格一致性 | 连续 10 轮对话后，检测输出与 style_examples 的 embedding 相似度是否 < 0.75 |

### 8.2.1 验收场景（用户故事）

将需求审查中的用户故事转化为可执行 pytest 验收条件：

| 场景ID | 用户故事 | 验收条件 | 对应测试文件 |
|--------|---------|---------|-------------|
| US-1 | 多端冲突自动通知 | 模拟手机/车机同时修改偏好 → 系统在 5 秒内生成 `ConflictNotification`，前端/日志收到冲突解决提示 | `tests/test_crdt_conflict.py` |
| US-2 | 隐私保护记忆迁移 | 将 therapist 分支记忆迁移到 companion，目标分支中通过正则扫描无手机号/身份证等 PII | `tests/test_privacy_filter.py` |
| US-3 | API 未授权访问拦截 | `curl` 无 token 请求 `POST /api/v1/chat` → 返回 401；token 正确但分支无权限 → 返回 403 | `tests/test_api_auth.py` |
| US-4 | 时钟偏差容忍 | 设备 A HLC 比 B 快 5 秒，B 写入同一 key → 合并后 B 的版本保留，且生成 CONTRADICTS 边 | `tests/test_hlc_skew.py` |
| US-5 | 意图图谱导航精度 | `pytest tests/test_a6_intent_graph.py` 全量通过，Recall@5 ≥ 0.8 | `tests/test_a6_intent_graph.py` |

### 8.3 指标定义

| 维度 | 指标 | 计算方式 |
|------|------|---------|
| **记忆准确性** | Recall@5 | 正确答案是否在 Top-5 召回中 |
| | MRR | 正确答案的倒数排名 |
| | Answer F1 | 生成答案与标准答案的 token-level F1 |
| **角色一致性** | Persona Drift Score | 单轮回复与 `PersonaAnchor.style_examples` 的 embedding 均值的余弦相似度（基准为所有 `style_examples` 的 embedding 均值）；< 0.75 触发告警 |
| | Role Confusion Rate | 在 branch A 问 branch B 的问题，错误回答的比例 |
| **CRDT 正确性** | Conflict Resolution Accuracy | 冲突记忆合并后是否保留全部信息 |
| | Sync Convergence Time | 模拟网络分区后恢复，测量最终一致性达成时间 |
| **检索质量** | Intent Navigation Precision | 意图图谱召回 vs 纯向量召回的准确率对比 |
| **系统效率** | P99 Retrieval Latency | 混合检索链路端到端延迟 |
| | Token Cost per Turn | 每轮对话平均 token 消耗，按 `token_scope`（system / user / agent）分层统计（参见 4.8.1 `ModelCallRecord.token_scope`）；系统开销（Persona Anchor 注入等）与业务 token 分别计算，确保成本归因清晰 |
| **量化精度** | Quantization Recall Degradation | 对比 FP32 全精度与 1-bit/2-bit Scalar 量化后的 Recall@5 下降幅度；目标下降 < 5%，若超过则回退至 FP16 或禁用量化 |

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

**CRDT 并发测试模板**：使用 `pytest-asyncio` 模拟双端并发写入，校验 vector_clock 和 CONTRADICTS 边。

```python
import asyncio
import pytest

@pytest.mark.asyncio
async def test_concurrent_write_creates_conflict_edge():
    # 模拟设备 A 和设备 B 同时写入同一 key
    # 断言：合并后存在 CONTRADICTS 边，且两个版本均保留
    ...
```

---

## 9. 8周执行路线图

### 9.1 Week 1: 契约与孤岛

**目标**：所有抽象接口、API 规范、Mock 实现、单测框架完成，`make test` 跑通全 Mock Agent 流程。

| 交付物 | 说明 |
|--------|------|
| `contracts/interfaces/` | **14 个抽象接口文件全部冻结**（含 W4+ 预留空壳） |
| `contracts/schemas/` | 18 个数据实体定义（含 `MemoryEntry` 重要性评分字段） |
| `mocks/` | **12 个 Mock 实现，全部通过专门单元测试** |
| `tests/` | **16 个测试文件，258 passed，94% 语句覆盖率** |
| 真实实现 | `L0SyncLayer`、`GridWorldAdapter`、`IntentGraph`、`IntentNavigator`、`StateMachineAgentCore`、`WorkingMemoryWindow`、`LLMNode`、`MemoryNode`、`OutputNode` |
| `Makefile` | `make test` 一键执行 |
| LWW-CRDT 自研 | 替换 Yjs，`LWWMap` + `HybridTimestamp` + `SyncManager` |
| MVO 种子 | 200 概念 + 6 条硬编码意图策略 |

**里程碑**：`make test` 通过 28 个测试用例，包含一个完整的"用户输入 → Agent 回复" Mock 流程。

**核心测试用例清单（部分）**：

| 用例名称 | 预期结果 |
|---------|---------|
| `test_mock_pipeline_full_turn` | 用户输入 → Agent 回复，返回非空文本 |
| `test_branch_isolation` | therapist 分支无法读取 rpg-hero 分支记忆 |
| `test_crdt_merge_add_wins` | 两个设备写入同一 key，add-wins 语义保留最新值 |
| `test_intent_graph_navigation` | 意图图谱检索返回预期记忆节点 |
| `test_persona_anchor_injection` | 切换人格后 system prompt 包含对应 Anchor |

### 9.2 Week 2-3: 记忆系统核心

**目标**：CRDT-MVCC 混合记忆层（L0-L3），命令行可演示角色切换和记忆召回。

| 周次 | 聚焦 | 交付物 |
|------|------|--------|
| Week 2 | L0 CRDT + L1 Working Memory + L2 Episodic Memory | **L0 LWW-CRDT 实现、滑动窗口、Qdrant Mock 接入** |
| Week 3 | L3 Semantic Memory + Intent Graph (PostgreSQL CTE) | 概念层级、语义边、意图导航策略、Recursive CTE（含 6 步检索、MVO 种子、PostgreSQL CTE） |

**持续回归要求**：Week 2 交付附带 ≥3 个集成测试（覆盖 `LWWMap.merge()`、滑动窗口压缩、Qdrant Mock 全链路）；Week 3 交付附带 ≥3 个集成测试（覆盖 CTE 导航、MVO 种子加载、边构建器正确性）。

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

**持续回归要求**：本周交付附带 ≥3 个集成测试，覆盖 Insight 生成触发条件、insight 有效期过期清理、以及 A1/A2 召回提升的自动化断言。

**里程碑**：运行 3 轮 session 后，系统自动产出洞察如"用户近3次谈话焦虑程度上升"。

**Checkpoint 3.1（Week 3 末尾强制关卡）**：
- L3 Semantic Memory 必须通过 **10 轮对话稳定性测试**：每轮对话后 MENTIONS / TEMPORAL_NEXT 边正确写入 PostgreSQL，Intent Graph CTE 查询 Recall@5 ≥ 0.6。
- **未通过**：推迟 Insight 模块到 Week 5，Week 4 优先修复 L3 检索链路。

### 9.4 Week 5: Agent 循环与算法插槽

**目标**：LangGraph 循环 + 可训练情感模型 + VLA 预留接口。

| 交付物 | 说明 |
|--------|------|
| LangGraph State Machine | Input → Intent → Memory → LLM → Output 完整链路 |
| `trainable_emotion_model.py` | LSTM 情感强度回归头 + 训练脚本 |
| `[RL-PLACEHOLDER]` | 标注未来 PPO/GRPO 优化位置 |
| VLA 可插拔接口 | `predict_action()` 默认 LLM 实现 |

**持续回归要求**：本周交付附带 ≥3 个集成测试，覆盖端到端对话流转、情感状态机转移路径验证、以及 ActionPlan 的可审计性（`reasoning` 字段非空校验）。

**里程碑**：端到端对话可用，情感状态机可观测，LSTM 模型可训练。

### 9.5 Week 6: 评估框架

**目标**：8 场景对抗测试集 + 量化对比表。

| 交付物 | 说明 |
|--------|------|
| `evaluation/scenarios.py` | A1-A8 测试场景定义 |
| `evaluation/metrics.py` | 指标计算（Recall@K, MRR, F1, Drift Score） |
| `evaluation/baseline.py` | 纯向量 RAG 基线实现 |
| `reports/` | 自动生成对比报告（Markdown + JSON） |

**持续回归要求**：本周交付附带 ≥3 个集成测试，覆盖评估流水线端到端执行、基线对比自动化、以及报告生成的正确性。

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

## 10. Cursor 多 Agent 架构深度调研：对 ChronoPersona 的借鉴分析

### 10.1 调研总结：Cursor 的真实架构 vs 技术误解

| 维度 | 社区误解 | Cursor 实际实现 |
|------|---------|----------------|
| **核心机制** | CRDT 自动合并多 Agent 结果 | **Git Worktree 物理隔离 + Best-of-N 选择** |
| **冲突处理** | 文本级 CRDT 解决冲突 | **不解决冲突，直接丢弃非最优结果** |
| **Agent 协作** | 运行时共享状态、协同编辑 | **零协作，完全隔离，互不感知** |
| **合并策略** | N 个部分结果合并为 1 个整体 | **明确禁止合并，人工/启发式选其一** |
| **适用边界** | 通用代码生成 | **仅限无重叠写入域的模块化任务** |

**Cursor 的核心洞察**：代码是高度结构化的 AST，而非纯文本。文本级 CRDT 会导致**语法崩溃、类型冲突、引用断裂**。因此工程上选择**物理隔离（Worktree）**规避合并难题，**人工/启发式选择（Best-of-N）**保证质量。

### 10.2 借鉴价值矩阵（按优先级）

#### P0：高度值得借鉴（与 ChronoPersona 当前架构强共鸣）

**1. 物理隔离优先 → 强化 MVCC Branch 的"临时探索"语义**

| Cursor 实践 | ChronoPersona 现状 | 借鉴落地 |
|------------|-------------------|---------|
| Git Worktree 完全隔离文件系统 | `main`/`therapist`/`rpg-hero` 持久分支 | 引入 **scratch branch**（临时探索分支）机制 |
| N 个 Agent 独立运行后选最优 | 单一路径的 `run_turn()` | `explore_branch(task, n=3)` 创建 N 个临时分支并行推理，父 Agent 评估后 cherry-pick 最优结果 |

**价值**：在 ActionPlanner（动作规划）或 Persona Switch（人格切换）场景中，可同时生成 N 个候选 plan，通过启发式评分（安全性/情感一致性/记忆引用完整度）选择最优，而非单一路径。**这与 Cursor 的 Best-of-N 机制异曲同工。**

**2. 无冲突域划分 → 细化 L0/L1/L2/L3 写入边界**

| Cursor 实践 | ChronoPersona 映射 | 借鉴落地 |
|------------|-------------------|---------|
| DB 层/业务层/展示层分离 | L0/L1/L2/L3 已分层 | 明确**同层同级不并发写入同一实体**的硬规则 |

具体写入域锁定：
- **L0**：仅 key-value 状态（偏好、配置、情感状态）。`LWWMap` 天然适合，因为 key 级 add-wins 无歧义。
- **L1**：仅当前会话上下文。会话结束即丢弃，**物理上无需跨端合并**。
- **L2**：仅按 `session_id` 分区的 episodic 记忆。session 间无交集，**分区即隔离**。
- **L3**：仅图节点/边操作。**禁止对同一 concept_id 并发写入不同属性**。

**价值**：Cursor 指出"无冲突域划分是规避合并难题的根本"。ChronoPersona 的分层已隐含此思想，但需显式强化为**架构契约**。

**3. 结构化操作而非文本级操作 → L3 IntentGraph 已是正确方向**

| Cursor 实践 | ChronoPersona 映射 | 验证 |
|------------|-------------------|------|
| AST-level 操作原语（InsertNode/DeleteNode/MoveNode） | L3 图操作原语（AddConcept/LinkEntities/DeprecateConcept） | ✅ 一致 |

Cursor 的核心教训是：**结构化数据必须用结构化操作原语，禁止文本级 diff/merge**。ChronoPersona 的 L3 已经采用节点+边+属性的图模型，而非原始文本拼接，这避免了 Cursor 所警告的"语法崩溃"问题。

**强化建议**：为 L3 语义操作引入**全局唯一 Stable ID**（类似 Cursor 的 AST 节点 UUID），替代依赖 `name` 或 `content_summary` 的弱标识。这使得跨设备的图合并可在节点级别确定性执行。

#### P1：中等借鉴价值（需适配到记忆领域）

**4. 依赖图感知合并顺序 → L3 语义边拓扑排序刷盘**

| Cursor 实践 | ChronoPersona 映射 |
|------------|-------------------|
| 先 Contract（接口）→ 再 Implementation（实现）→ 最后 Test（测试） | 先 IS_A（概念定义）→ 再 MENTIONS（实例关联）→ 最后 CAUSED/TRIGGERED_BY（因果边） |

**落地**：在 `SyncManager.checkpoint()` 中对 L3 dirty keys 按语义依赖拓扑排序：
```python
# 批次 1：概念层级（IS_A）
checkpoint_batch_1 = filter(is_concept_node, dirty_keys)
# 批次 2：实例关联（MENTIONS）
checkpoint_batch_2 = filter(is_memory_node, dirty_keys)
# 批次 3：因果/触发边（CAUSED, TRIGGERED_BY）
checkpoint_batch_3 = filter(is_causal_edge, dirty_keys)
```

**价值**：确保多端同步时，概念定义先达成一致，再同步基于这些概念的关联，避免"先同步边、后同步节点"导致的悬空引用。

**5. 语义三路合并（3-Way Semantic Merge）→ CONTRADICTS 边 + LLM 仲裁升级**

| Cursor 实践 | ChronoPersona 当前 | 升级方案 |
|------------|-------------------|---------|
| Base/Left/Right AST 三路合并，冲突时父 Agent 仲裁 | `CONTRADICTS` 边标记冲突，自动 add-wins | **高价值冲突触发 LLM Semantic Merge Agent** |

**触发条件**：
- `importance > 0.8` 或 `entity_type in ['preference', 'belief', 'identity']`
- HLC 不可比较（超出 500ms skew）
- 双方修改非简单覆盖（如一方改 `value`，另一方改 `metadata.confidence`）

**仲裁流程**：
```
CONTRADICTS 检测
    │
    ▼
[Semantic Merge Agent] ──► 输入 Base（旧值）+ Left（本地值）+ Right（远程值）
    │                         调用 DS-V4-flash（轻量模型）
    ▼
输出：融合后的值 + confidence + reasoning
    │
    ▼
写入 L3 为新版本，旧版本标记 deprecated（非删除）
```

**价值**：对于用户核心偏好（如"喜欢川菜" vs "讨厌川菜"），简单 add-wins 会丢失语义。LLM 仲裁可以产出"用户对川菜的偏好存在矛盾，可能取决于具体场景"这样的**元洞察**。

**6. Best-of-N 选择机制 → Reflection Agent 的候选 Insight 生成**

| Cursor 实践 | ChronoPersona 映射 |
|------------|-------------------|
| N 个 Agent 生成完整方案，启发式/人工选最优 | `SimpleInsightEngine` 单一路径关键词共现 |

**落地**：`MemoryConsolidationAgent`（Dreaming）在 Phase B（模式提取）时，可以生成 N 个候选 `BehavioralRule`，通过以下启发式选择：
- 规则覆盖的 `source_memory_ids` 数量（覆盖越多越可信）
- 规则与现有 L3 知识的一致性（避免与 `CONTRADICTS` 边冲突）
- 规则的 `confidence` 评分

### 10.3 需要规避的陷阱（Cursor 的教训）

| 陷阱 | Cursor 的遭遇 | ChronoPersona 的应对 |
|------|-------------|---------------------|
| **文本级 CRDT 合并结构化数据** | 代码语法崩溃、类型冲突 | L3 禁止文本级 diff，强制节点级操作 |
| **试图合并 N 个完整实现** | 官方明确警告不可行 | L0 冲突保留双版本（CONTRADICTS），不强行合并为单一值 |
| **忽略引用完整性** | 变量重命名 vs 新引用断裂 | L3 边操作使用 Stable ID，而非文本匹配 |
| **无域划分的并行写入** | 同一文件多 Agent 修改必冲突 | 同层同 entity_id 禁止并发写入（架构契约） |

### 10.4 与当前 W2 排期的对齐建议

基于 `docs/schedule.md` 的 Week 2-4 规划，建议将 Cursor 借鉴点嵌入以下任务：

| 排期任务 | Cursor 借鉴点 | 具体动作 |
|---------|--------------|---------|
| **W2: Dreaming 骨架** | Best-of-N Insight 选择 | `MemoryConsolidationAgent` 生成 3 个候选 BehavioralRule，选最优写入 |
| **W2: L2 指数衰减 GC** | 无冲突域划分 | 明确 `session_id` 作为 L2 物理分区键，session 间永不冲突 |
| **W3: L3 CTE 导航** | 依赖感知刷盘顺序 | `SyncManager.checkpoint()` 按 IS_A → MENTIONS → CAUSED 拓扑排序 |
| **W4: Insight 完整实现** | Semantic Merge Agent | `CONTRADICTS` 边触发 LLM 三路仲裁，产出融合洞察 |
| **W5: Agent 核心循环** | Branch 级 Best-of-N | `StateMachineAgentCore` 支持 `explore_branch(n=3)` 临时分支探索 |

### 10.5 结论

Cursor 的架构选择揭示了一个**跨领域通用原则**：

> **在高度结构化领域（代码/记忆/知识图谱），物理隔离 + 启发式选择，远比盲目追求全自动 CRDT 合并更务实。自动合并只适用于无冲突域或原子级操作（key-value、节点级），语义级冲突必须引入仲裁者（人工或 LLM）。**

ChronoPersona 的当前设计已无意中遵循了此原则：
- ✅ L0 用 key-value LWW-CRDT（原子级，适合自动合并）
- ✅ L1/L2 用会话/分区隔离（物理无冲突）
- ✅ L3 用图节点操作（结构化，非文本级）

**下一步关键动作**：
1. **显式化无冲突域契约**（写入前检查同 entity_id 是否被其他设备锁定）
2. **引入 scratch branch + Best-of-N**（临时分支探索机制）
3. **升级 L3 为 Stable ID + 依赖感知合并**（替代弱文本标识）
4. **高价值冲突启用 LLM Semantic Merge**（替代简单 add-wins）

这将在不引入 AST-CRDT 过重复杂度的前提下，获得 Cursor 架构的精髓。

---

## 11. 风险与兜底策略

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
