# ChronoPersona — AI Coding 规范

> 本文件约束所有 AI 助手（Aider、Cursor、Claude Code 等）的通用行为，与工具无关。

---

## 1. 架构约束（不可违反）

| 约束 | 说明 | 违反后果 |
|------|------|---------|
| **接口优先** | 任何新模块必须先写 `contracts/interfaces/` 抽象类，再写实现 | 架构腐烂，模块耦合 |
| **Mock 就绪** | 所有外部依赖（DB、向量库、LLM）必须保留 Mock 实现 | `make test` 依赖 Docker，MVA 阶段不可用 |
| **MVA 裁剪** | Neo4j / 2D Canvas / LoCoMo 在 MVA 阶段不实现 | 范围蔓延，8 周 deadline 失控 |
| **类型硬化** | 所有公共函数必须有类型注解，复杂数据用 Pydantic Model | 代码不可维护 |
| **W1 基线** | 258 个测试用例全部通过，覆盖率 94% | 后续修改不得破坏此基线 |

---

## 2. 代码风格

### 命名规范
- **抽象接口**：`AbstractXxx`（例：`AbstractMemoryStore`）
- **实现类**：`XxxImpl` 或具体名称（例：`QdrantEpisodicStore`）
- **CRDT/MVCC**：`YjsXxx`、`VersionXxx`、`BranchXxx`
- **常量**：全大写，模块级（例：`MAX_HOPS = 3`）

### 异步边界
- I/O 操作（DB、网络、LLM API）必须 `async`
- 纯计算可 `sync`
- 禁止在 `async def` 内使用同步阻塞调用（如 `requests.get`）

---

## 3. 模块依赖方向

```
frontend → agent_core → memory_system → model_router
                     ↘ embodied → persona_engine
```

**铁律**：
- 禁止底层模块引用上层模块
- `contracts/` 可被任何层引用
- `mocks/` 只被 `tests/` 引用

---

## 4. 测试规范

| 测试类型 | 文件对应 | 要求 |
|---------|---------|------|
| 单元测试 | `tests/test_xxx.py` ↔ `chronopersona/xxx.py` | 覆盖率 > 80% |
| Mock 端到端 | `tests/test_mock_pipeline.py` | Week 1 必须跑通 28 例 |
| 评估测试 | `evaluation/scenarios.py` | Week 6 后纳入 `make eval` |

---

## 5. 扩展点标记

代码中保留 `[PLACEHOLDER]` 的地方：
- 添加 TODO 注释说明预留原因
- 技术评审时明确说明"这是预留扩展点"
- 关键设计决策（CRDT+MVCC 混合、意图图谱 8 类边）必须在注释中引用设计文档章节号

---

## 6. 提交规范

```
[<模块>] <动词>: <描述>

模块：memory / agent / embodied / persona / eval / docs
动词：feat / fix / refactor / test / chore
```

**例**：
- `[memory] feat: add MVCC snapshot manager`
- `[eval] test: add A3 role isolation scenario`
- `[agent] fix: correct emotion state transition logic`

---

## 7. 禁止清单

- ❌ 在 `core_narrative` 外单独写 `taboos` 列表（必须用有机约束）
- ❌ 直接调用 OpenAI 客户端（必须通过 `ModelRouter.route()`）
- ❌ `branch_id` 使用默认值穿透（必须显式传递）
- ❌ 意图图谱 `max_hops > 3`（防止 CTE 性能爆炸）
- ❌ Action Token 使用驼峰命名（必须 `snake_case`）
- ❌ 映射字典硬编码业务逻辑（只做纯翻译）
