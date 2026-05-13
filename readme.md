# ChronoPersona

&gt; **带镣铐的架构：为 AI Companion 构建一个不会失忆、不串台、可跨本体移植的长期记忆大脑**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: MVA v1.2](https://img.shields.io/badge/status-MVA%20v1.2-green.svg)]()

**ChronoPersona** 是一个面向生产级 AI Agent 的长期记忆系统，核心差异化在于将**分布式一致性（CRDT）**与**版本化记忆（MVCC）**引入 Agent 记忆架构，解决多端同步冲突、角色人格漂移、记忆幻觉三大痛点。同时通过 **Token→Action Bridge** 实现人格与身体的解耦，使同一套"灵魂"可零样本迁移到任意机器人本体。

**定位**：面试展示项目 | **周期**：8 周（MVA） | **核心语言**：Python / TypeScript

---

## 🧠 核心架构亮点

| 维度 | 传统方案 | ChronoPersona |
|------|---------|---------------|
| **多端同步** | 单节点，各自为政 | **Yjs CRDT** 最终一致性，冲突保留不覆盖 |
| **角色隔离** | Prompt 替换，记忆共享 | **MVCC Branch**  checkout = `git checkout`，物理隔离 |
| **记忆检索** | 纯向量相似度 | **意图图谱导航**（8 类边 + 8 类意图策略） |
| **人格工程** | 自由文本 Prompt | **混合格式 Anchor**（W++ + Ali:Chat + 自然语言 + 结构化权限） |
| **具身智能** | 端到端 VLA 训练 | **Token→Action Bridge**，换身体只换映射字典 |

---

## 系统架构

```mermaid
graph TD
    A[User Input] --&gt; B[Intent Node&lt;br/&gt;8-class classify + Entity Extract]
    B --&gt; C[Memory Node&lt;br/&gt;Branch checkout → Hybrid Retrieve]
    C --&gt; D[LLM Node&lt;br/&gt;Persona Anchor + Context + Emotion]
    D --&gt; E[ActionPlanner&lt;br/&gt;Token → Action + Emotion Modulation]
    E --&gt; F[Output&lt;br/&gt;Text + 2D Command]
    F --&gt; G[Async Reflection&lt;br/&gt;Entity Link → Graph Update]
    G --&gt; H[(PostgreSQL&lt;br/&gt;Intent Graph)]
    C --&gt; I[(Qdrant&lt;br/&gt;Episodic Vector)]
    G --&gt; J[(Yjs CRDT&lt;br/&gt;Multi-device Sync)]
