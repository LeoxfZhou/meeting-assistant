# 最新进展（2026-11-18）

当前 feature/auth：基础版 31 测试复验通过后已合并 main；新增注册、登录、Argon2id、JWT、Current User、Creator/Owner 会议权限。迁移 0002_auth 已应用；36 tests passed（8.06s），alembic check 无差异。旧会议 creator_user_id 可空以保留已有数据，仅 Owner 能访问；新会议必须来自已认证用户。Owner 通过本地管理命令显式指定，不自动赋予首个注册者。

最新范围以 MASTER_GOAL.md 为准，旧 Batch 停止规则失效。下一步自动继续 LLM/Candidate/Task，再 RAG/LangGraph/Evaluation/Docker。无 Remote，不伪造 PR；没有配置云 LLM Key 时继续不依赖 Key 的工作。

以下为基础版历史验收快照（其中“下一 Batch 待批准”等旧规则已失效）：

# 项目状态

最后核验：2026-11-18（北京时间）。**新 MASTER GOAL 已生效，正连续推进完整本地主线。** 主线仍为 LLM Application / AI Backend / Workflow / Deployment；QLoRA Optional。

## 已完成

- main 安全基线 d753085；当前 feature/backend-foundation；未创建 Remote、Push、PR 或 CI。
- 独立 .venv，Python 3.13.9；pyproject.toml + uv.lock，uv sync --frozen 可安装。
- FastAPI factory、Pydantic Settings/Schema、SQLAlchemy 2.x Session、PostgreSQL、Alembic。
- Meeting CRUD、TXT/Markdown 上传、输入/文件错误处理、503 数据库错误与受限日志。
- PostgreSQL 集成测试与独立 Uvicorn HTTP 冒烟验证。
- README、data/README、Walkthrough 和真实问题更新。

## API

| 方法 | 路径 | 成功 |
|---|---|---|
| GET | /health | 200，仅 liveness |
| POST | /meetings | 201 |
| GET | /meetings | 200，limit/offset |
| GET | /meetings/{meeting_id} | 200 |
| PATCH | /meetings/{meeting_id} | 200 |
| DELETE | /meetings/{meeting_id} | 204 |
| POST | /meetings/upload | 201，TXT/MD、UTF-8、≤1 MiB |

非法输入 422、不存在 404、不支持文件 415、超限 413、数据库失败 503。

## 数据库与迁移

真实数据库 PostgreSQL 16.16 (Debian 16.16-1.pgdg12+1)。仅业务表 meetings，加 Alembic 版本表 alembic_version；没有 action_items/tasks。

meetings：id UUID 主键、title VARCHAR(200)、content TEXT、source_type VARCHAR(20)、status VARCHAR(20)、created_at/updated_at TIMESTAMPTZ。状态只允许 ready；来源约束 pasted_text/txt/markdown；标题/正文非空。updated_at 由 ORM 更新，不是数据库 trigger。

Migration：migrations/versions/0001_create_meetings.py，revision 0001_create_meetings，开发库 upgrade head 成功；测试库从空库迁移成功，alembic check 无差异。应用未使用 create_all。

Compose 仅 postgres:16-bookworm；容器 meeting-assistant-postgres-1 healthy，绑定 127.0.0.1:55432，持久卷 meeting-assistant_postgres_data。本轮留数据库运行供人工检查；冒烟 Uvicorn 已停止，正式启动命令见 README。镜像使用 16 系列 tag，并非 digest 锁定。

## 测试证据

- pytest -q：31 passed，3.14s；1 条 Starlette TestClient 对 httpx 的弃用警告，未隐藏。
- 覆盖 health、CRUD、404、PATCH 部分更新/无效更新、UUID/分页、输入校验、TXT/MD/路径式文件名/BOM 上传、不支持格式、空文件、无效 UTF-8、超限、数据库错误脱敏、真实 schema/migration、跨连接持久化。
- 数据库错误映射测试使用注入 OperationalError；不将其宣称为真实数据库宕机演练。
- 所有 API 测试使用随机独立 PostgreSQL 测试库；测试结束已清理，核验残留测试库为 0。
- 独立启动 Uvicorn 在本机 18080，真实 HTTP health 200、CRUD、TXT/MD 上传全部通过；本轮合成记录已删除，开发库 meetings 行数 0。
- compileall 与 git diff --check 通过；现有原始 ZIP、P0 报告、清单、审计脚本及旧规划保留不变。

## Git / Public Strategy

main 基线提交：d753085 chore: initialize project repository。
本批提交分为后端实现、集成测试与文档两个有意义的单元；实际 hash 以 git log 为准。开发均在 feature/backend-foundation，最终工作区应无未提交变更；.env/.venv/raw/outputs 等保留本地并忽略。

.gitignore 排除 raw/processed/annotations、全部 outputs（含审计原文报告）、.env 与密钥、虚拟环境、数据库文件、缓存。保留纯占位 .env.example。当前随机开发密码只存在被忽略的本机 .env；未加入 Git，日志不打印密码。

GitHub 发布前仍需用户确认 Remote/仓库公开性，复核暂存区、数据来源/许可、Git 作者信息和代码许可证。没有公开授权，不推送；审计报告不能自动放行。

## 保留的数据资产与已知限制

P0：Train 295 场/213235 句/1014 行动 ID/67 空标签会议；Dev 65/45869/222/10；Test1 82/43228/236/32。合计 442/302332/1472/109。raw SHA-256：666899476df91a0791b3b5e83994463c2a40e83d6d02e2b50cf2d32a556fec70。

M3298/M8016 泄漏风险尚未处理。数据来源/许可仍待确认；不阻塞合成数据后端。旧 project-plan/ 文档原地保留为历史，不作为当前进度。

文件大小在 multipart 解析后检查，未实现生产入口请求体限流；无 Auth，仅本机开发。此批没有压测、生产部署或宕机演练。默认 Python 3.9.10 未使用；实际独立环境为已有 3.13.9（较早检查只查询了 3.11/3.12，不能据此断言无较新 Python）。

## 尚未实现 / 下一 Batch

LLM、Prompt、Action Items、Task、Human Review、LangGraph、Tool Calling、RAG、训练、前端、云部署均未实现。下一 Batch 2：云 LLM Client + Pydantic 结构化抽取 + 候选持久化 + 基础超时/错误处理，须用户另行批准。

用户现在可启动 README 中的 Uvicorn，在 /docs 创建、查询、修改、上传、删除合成会议，并用 psql 查看 meetings 表。
