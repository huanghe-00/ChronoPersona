# W8 交付物检查清单

**项目**: ChronoPersona  
**版本**: v1.0-mva  
**冻结日期**: 2026-05-29

---

## 1. 工程交付物

| 文件 | 状态 | 验证方式 |
|------|------|---------|
| `make test` | ✅ 425 passed | 本地执行 |
| `make eval` | ✅ A1-A5 recall@5=1.0, A3=0.0 (expected) | 本地执行 |
| `pytest tests/test_mock_pipeline.py` | ✅ W1 守卫 | CI 阻塞项 |

## 2. 架构文档

| 文件 | 用途 | 面试官场景 |
|------|------|-----------|
| `docs/requirements.md` | 需求与设计决策 | "你们是怎么设计的？" |
| `docs/beyond_mva.md` | 生产级优化路线图 | "有什么生产级缺陷？" |
| `docs/tech_blog_draft.md` | 技术博客初稿 | "写篇博客怎么介绍？" |
| `docs/interview_cheat_sheet.md` | 应答脚本 | 深挖问题快速索引 |
| `docs/slide_deck.md` | 10 页面试提纲 | 3 分钟 + 5 分钟 Deep Dive |

## 3. 已知限制（面试时必须坦诚）

1. `serve_mva.py` HTTP API 已可用（`GET /health` + `POST /chat`），WebSocket 实时双向推送待 W8+
2. `MockBGEEmbedder` 基于长度，非语义相似度
3. `GridWorldAdapter` 返回命令但未执行闭环（无 `execute()` 回写 L2）
4. `LWWMap.get_delta` 修复后需压测验证增量同步性能

## 4. Git Tag

```bash
git tag -a v1.0-mva -m "MVA freeze: 425 passed, 94% coverage, 7 docs, serve_mva.py HTTP API"
```
