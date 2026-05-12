# Aider 开发规范 — ChronoPersona

> 本文件专供 Aider 读取（`--read AIDER.md`），约束 AI 在 Architect 模式下的行为边界。

---

## 1. 双模型协作协议

| 模型 | 职责 | 禁止行为 |
|------|------|---------|
| **主模型** (DeepSeek-V4-pro) | 架构决策、接口设计、跨模块协调、复杂逻辑规划 | 直接输出完整可运行代码，只输出伪代码/修改计划/接口签名 |
| **编辑模型** (Kimi 2.6) | 将伪代码转为可运行 Python、填充类型注解、处理边界条件、编写单测 | 修改接口定义或架构决策，只执行主模型规划 |

**协作流程**：
1. 用户提出需求 → 主模型分析 → 输出「修改计划」（改哪些文件、每处怎么改）
2. 编辑模型读取计划 → 逐文件生成代码 → 自动写入磁盘
3. 运行 `make test` → 通过则提交，失败则自动修复

---

## 2. 上下文加载优先级

Aider 启动时按此顺序读取上下文：

```
1. AIDER.md（本文件）
2. CLAUDE.md（通用架构规范）
3. contracts/interfaces/（抽象接口，最先硬化）
4. 目标实现文件
5. tests/（测试守卫）
```

**大文件策略**：设计文档超过 200 行时，按章节分段请求，禁止单次加载完整设计文档。

---

## 3. 多文件修改原子性

涉及多个模块的任务，必须在一个事务内处理以下全部：

1. **接口定义** (`contracts/interfaces/`)
2. **实现类** (具体模块目录)
3. **Mock 适配** (`mocks/`)
4. **测试用例** (`tests/`)
5. **`__init__.py`** 导出更新（若存在）

**禁止行为**：只改实现不改接口、只改接口不更新 Mock、跳过测试。

---

## 4. Git 工作流

- **自动提交**：每次任务完成后执行 `git add . && git commit`
- **提交格式**：`[<模块>] <动词>: <描述>`
  - 例：`[memory] feat: add MVCC snapshot manager`
  - 例：`[eval] test: add A3 role isolation scenario`
- **失败回滚**：`make test` 连续 3 次修复失败 → `git reset --soft HEAD~1` → 回退到上次稳定状态
- **上下文释放**：已通过测试的代码立即 commit，释放上下文窗口给后续任务

---

## 5. [PLACEHOLDER] 处理规则

遇到以下标记时严格执行：

| 标记 | 处理方式 |
|------|---------|
| `[RL-PLACEHOLDER]` | 保留标记，添加 TODO，实现一个空函数/Pass 行为 |
| `[VLA-PLACEHOLDER]` | 保留标记，添加 TODO，默认走 LLM 调用实现 |
| `[PLACEHOLDER]` | 保留标记，添加 TODO，确保测试不因此失败 |

**绝对禁止**：尝试实现 PPO/GRPO、VLA 微调等标记为 PLACEHOLDER 的复杂算法。

---

## 6. 测试驱动约束

- **新增接口**：必须同步生成 `tests/test_xxx.py`，至少 3 个测试用例
- **修改接口**：必须同步更新所有实现类 + Mock 类 + 关联测试
- **端到端守卫**：`test_mock_pipeline.py` 是 Week 1 核心守卫，任何改动不得破坏其通过性

---

## 7. 启动命令模板

```bash
aider \
  --model deepseek/deepseek-chat \
  --weak-model openrouter/moonshotai/kimi-k2 \
  --architect \
  --auto-test \
  --test-cmd "make test" \
  --read AIDER.md \
  --read CLAUDE.md
```

---

## 8. 紧急逃生舱

若 Aider 陷入循环（反复修改同一处无法通过测试）：
1. 输入 `/undo` 回退到上次稳定状态
2. 输入 `/drop` 清空当前文件上下文
3. 缩小任务范围：将大任务拆分为「只改一个接口 + 一个实现 + 一个测试」
4. 手动介入：退出 Aider，手动修复后重新启动
