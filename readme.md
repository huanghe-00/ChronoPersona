# ChronoPersona

> **带镣铐的架构：为 AI Companion 构建一个不会失忆、不串台、可跨本体移植的长期记忆大脑**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: W1 MVA Complete](https://img.shields.io/badge/status-W1%20MVA%20Complete-brightgreen.svg)]()
[![Tests: 258 passed](https://img.shields.io/badge/tests-258%20passed-success.svg)]()
[![Coverage: 94%](https://img.shields.io/badge/coverage-94%25-success.svg)]()

**ChronoPersona** 是一个面向生产级 AI Agent 的长期记忆系统，核心差异化在于将**分布式一致性（CRDT）**与**版本化记忆（MVCC）**引入 Agent 记忆架构，解决多端同步冲突、角色人格漂移、记忆幻觉三大痛点。同时通过 **Token→Action Bridge** 实现人格与身体的解耦，使同一套"灵魂"可零样本迁移到任意机器人本体。

**定位**：面试展示项目 | **周期**：8 周（MVA） | **核心语言**：Python / TypeScript  
**当前状态**：W1 MVA 已完成 — **258 passed, 1 skipped, 94% coverage**

## 🚀 项目状态

**W1 MVA 已完成**：`make test` **258 passed, 1 skipped, 0 failed** | 语句覆盖率 **94%**

| 层级 | 状态 | 关键交付 |
|------|------|---------|
| **L0 CRDT** | ✅ 真实实现 | `LWWMap` + `HybridTimestamp` + `SyncManager`，支持多设备 add-wins 与 clock-skew 检测 |
| **L1 Working** | ✅ 真实实现 | 滑动窗口 + 动态压缩（Token 阈值触发） |
| **L2 Episodic** | ✅ 真实实现 | `SimpleEpisodicStore` / `FaissEpisodicStore` + `MockBGEEmbedder` 确定性向量；已落地重要性加权检索 |
| **L3 Semantic** | ✅ 真实实现 | `IntentGraph` + `IntentNavigator`，8 类语义边 + 8 类意图策略 |
| **Agent Core** | ✅ 真实实现 | `StateMachineAgentCore`（Input → Intent → Memory → LLM → Output） |
| **Embodied** | ✅ 真实实现 | `GridWorldAdapter`（20×20 网格、FOV、边界钳制、Token→Action Bridge） |

---

## 🧠 核心架构亮点

| 维度 | 传统方案 | ChronoPersona |
|------|---------|---------------|
| **多端同步** | 单节点，各自为政 | **自研 LWW-CRDT** 最终一致性，冲突保留不覆盖 |
| **角色隔离** | Prompt 替换，记忆共享 | **MVCC Branch**  checkout = `git checkout`，物理隔离 |
| **记忆检索** | 纯向量相似度 | **意图图谱导航**（8 类边 + 8 类意图策略） |
| **人格工程** | 自由文本 Prompt | **混合格式 Anchor**（W++ + Ali:Chat + 自然语言 + 结构化权限） |
| **具身智能** | 端到端 VLA 训练 | **Token→Action Bridge**，换身体只换映射字典 |

---

## 🧬 Anthropic 架构借鉴

本项目的记忆设计并非简单的"向量数据库+RAG"，而是吸收 Anthropic 认知仿生架构的工程化落地：

| 借鉴点 | Anthropic 原文 | ChronoPersona 实现 |
|--------|----------------|-------------------|
| **记忆蒸馏** | L2→L3 是密度跃迁（去噪+结构化） | `ReflectionAgent` 两阶段：Phase A 实体链接 + Phase B 模式提取（W2 骨架） |
| **Dreaming** | 空闲时段 Consolidation Agent 固化经验 | `MemoryConsolidationAgent` 每 5 session / 每日凌晨触发，提取 BehavioralRule |
| **重要性评分** | 信息熵 × 任务关联 × 访问频率 | `MemoryEntry.importance × entropy_gain × log1p(access_count)` 已落地 Schema |
| **差异化遗忘** | 工作/情景/语义三层不同衰减函数 | L1 会话结束清空、L2 指数衰减 `R=e^(-t/S)`、L3 `deprecated` 反学习 |
| **Pull on demand** | 按需拉取，绝不填满 | 意图图谱导航按需召回，低重要性记忆自动驱逐 |

## 📦 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行全量测试（258 passed）
make test

# 3. 运行特定模块
pytest tests/test_l0_crdt.py -v          # CRDT 核心
pytest tests/test_state_machine.py -v    # Agent 全链路
pytest tests/test_grid_world.py -v       # 具身感知
pytest tests/test_intent_graph.py -v     # 意图图谱
```

## 🗓️ 8 周路线图速览

- **W1** ✅ 契约冻结 + Mock 全量 + 真实节点（258 passed / 94% coverage）
- **W2** 🔄 Dreaming 骨架 + L2 指数衰减 GC + Eval 基线 + PersonaInjector
- **W3** L3 Unlearning + InsightScheduler + 性能基准
- **W4** Insight 完整实现 + CAUSED Tier 2
- **W5** Agent 核心循环 + 可训练情感模型
- **W6** 评估框架 A1-A11 + 量化对比表
- **W7** 2D Canvas 前端 + Demo 视频
- **W8** 技术博客 + Slide Deck + 面试准备

## 系统架构

```mermaid
graph TD
    A[User Input] --> B[Intent Node<br/>8-class classify + Entity Extract]
    B --> C[Memory Node<br/>Branch checkout → Hybrid Retrieve]
    C --> D[LLM Node<br/>Persona Anchor + Context + Emotion]
    D --> E[ActionPlanner<br/>Token → Action + Emotion Modulation]
    E --> F[Output<br/>Text + 2D Command]
    F --> G[Async Reflection<br/>Entity Link → Graph Update]
    G --> H[(PostgreSQL<br/>Intent Graph)]
    C --> I[(Qdrant<br/>Episodic Vector)]
    G --> J[(LWW-CRDT<br/>Multi-device Sync)]
