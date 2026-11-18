# 项目 Walkthrough（持续更新）

更新：2026-11-18。供后续项目教学和面试使用。当前已实现 P0 与 Batch 1 Backend Foundation。LLM、人工确认、Task 和 LangGraph 仍为后续设计。

## 1. Business Problem

会议中安排分散，用户需要带证据的候选事项，并控制是否进入正式任务。我们模拟单用户工作流，没有真实企业使用或上线收益数据。

## 2. Architecture（实际实现）

FastAPI factory → API 路由 → Pydantic 输入校验 → SQLAlchemy Session/Meeting → PostgreSQL。Alembic 单独管理 schema 版本。同步路由与同步数据库足够支撑本机 MVP，避免异步 Session 和多层 Repository 增加讲解成本。

app/main.py 的 create_app() 创建 Engine、sessionmaker 与路由；lifespan 在退出时释放 Engine。/health 只代表进程可用；数据库错误返回 503，日志仅包含类型与路由模板，防止 SQL 参数泄露。

## 3. End-to-End Data Flow（实际实现）

POST /meetings → MeetingCreate 校验标题/正文 → create_meeting() → save_meeting() → Session.add/commit/refresh → MeetingRead 序列化为 201 JSON。get_session() 为请求提供独立 Session，异常 rollback，结束 close。

GET 使用 select()/Session.get()；不存在返回 404。PATCH 使用 exclude_unset=True，只更新提供字段；拒绝 null/空 PATCH，避免无意覆盖。DELETE 提交后返回空 204。列表按 created_at 与 id 排序，limit/offset 简单分页。

上传为 multipart → 扩展名和 MIME 检查 → 最多读取 1 MiB + 1 字节 → UTF-8-sig 解码 → MeetingCreate 再校验 → 同一 save_meeting() 持久化。文件名仅用于推导标题，不作为磁盘路径。文件不永久保留；multipart 解析仍可能使用框架临时缓冲，当前没有公网入口流量限制。

P0 真实链路仍为只读 ZIP → 内层 ZIP → Tab CSV/JSON → 数据审计 → 本地报告/清单。

## 4. Code Map（全部为真实文件与符号）

| 文件 | class/function | 职责 |
|---|---|---|
| app/main.py | create_app / health / database_error | factory、存活检查、DB 错误映射 |
| app/core/config.py | Settings / postgres_only | .env 与环境变量、PostgreSQL URL 校验 |
| app/db/session.py | Base / build_engine / get_session | ORM 基类、连接池、Session 生命周期 |
| app/models/meeting.py | Meeting | typed Mapped 字段和数据库约束 |
| app/schemas/meeting.py | MeetingCreate / MeetingPatch / MeetingRead | 输入输出契约、部分更新 |
| app/api/meetings.py | create_meeting / list_meetings / get_meeting / patch_meeting / delete_meeting | CRUD 路由 |
| app/api/meetings.py | upload_meeting / find_meeting / save_meeting | 上传、404 查询和共享创建逻辑 |
| migrations/env.py | Alembic 执行入口 | 环境配置、metadata、在线/离线迁移 |
| migrations/versions/0001_create_meetings.py | upgrade / downgrade | 建表与显式回退 |
| tests/conftest.py | database_url / client | 临时真实 PG 库、迁移、savepoint 隔离、清理 |
| tests/test_meetings.py | test_crud / test_upload / test_bad_upload 等 | 请求行为与异常验证 |
| tests/test_meetings.py | test_postgres_schema_and_migration / test_real_commit_persists_between_sessions | 真实 PG schema、迁移差异、跨 Session 提交 |
| scripts/audit_alimeeting4mug.py | inspect_archive / audit_record / render_report / main | P0 只读原包审计及本地报告 |
| scripts/audit_alimeeting4mug.py | cross_split_overlaps / cross_split_long_sentence_pairs / example_markdown | 重复检测、Train 样例（不公开报告） |

## 5. Database Schema（实际实现）

仅 meetings 业务表：UUID id、VARCHAR(200) title、TEXT content、source_type（pasted_text/txt/markdown）、status（ready）、TIMESTAMPTZ created_at/updated_at。SQLAlchemy 声明字段和 ORM 行为；PostgreSQL 存储及执行约束；Alembic 负责版本化建表。updated_at 由 ORM onupdate 更新，不是直接 SQL 写入的自动触发器。

0001_create_meetings 已应用开发库与随机测试库；alembic check 验证模型与 schema 一致。没有 create_all，没有 action_items/tasks。

## 6. API Design（实际实现）

GET /health；POST/GET /meetings；GET/PATCH/DELETE /meetings/{meeting_id}；POST /meetings/upload。201 表示创建，204 表示删除且无 body；404 不存在，422 输入/编码错误，415 文件类型错误，413 超大文件，503 DB 失败。

pytest 31 项通过，全部 API 测试连接独立 PostgreSQL 测试库。普通测试用外层事务回滚，另有真实跨 Session 提交用例。测试库名由 uuid 生成，finally 仅清理该库，避免误删开发数据。独立 Uvicorn 的 HTTP 冒烟也通过，合成记录已清理。

参考实现语义：[SQLAlchemy Session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)、[FastAPI UploadFile](https://fastapi.tiangolo.com/tutorial/request-files/)、[Alembic Migration](https://alembic.sqlalchemy.org/en/latest/tutorial.html)。

## 7. LLM Provider

尚未选定或调用真实 Provider。计划通过 LLM_API_KEY/LLM_BASE_URL/LLM_MODEL 配置一个 OpenAI-compatible client，由小接口隔离业务与 HTTP 协议。支持程度需要真实联调，不承诺所有兼容服务完全一致。

## 8. Structured Output

计划必填 task、owner、deadline、evidence，其中 owner/deadline 可 null。Pydantic 拒绝缺字段与错误类型，结构有效后仍要检查证据支持。JSON 合法不等于任务事实正确。缺 JSON、无效 JSON 与合法空数组分开处理。

## 9. Human-in-the-loop

pending 允许编辑；用户确认或拒绝；未经确认不能生成 Task。模型与会议文本无权批准自己。未知日期保持原话；确认时可由用户补充，不能伪称数据原本提供。

## 10. LangGraph

Batch 4 实现确定性抽取、校验、等待、分支和创建。使用 Workflow 是因为流程边界明确且写入需要人类授权；自由 Agent 不适合自行决定是否建任务。持久化和恢复必须用真实测试验证，不因使用框架就宣称可靠。

## 11. Tool Calling

计划 create_task、update_task、get_meeting。工具调用是受控函数入口，不能把模型参数当权限凭证。人类确认后的写工具与 API 共享业务服务，避免绕过状态检查。

## 12. Reliability

Batch 1 已实现数据库连接超时、请求 Session 回收/异常回滚、503 错误分类和日志字段限制。LLM 的连接/读取超时、429/5xx 退避、401/403、非法 JSON 及 request_id/token 日志仍属于后续阶段。

## 13. Idempotency

尚未实现。核心是数据库 UNIQUE(source_action_item_id) + 确认与任务同事务，不仅在 Python 中先查再写。重复点击与并发请求、数据库失败回滚、Graph 重放均需测试；不宣称跨系统恰好一次。

## 14. Evaluation

现有证据是数据审计：442 场、302332 句、1472 个行动 ID、109 场显式空标签；不是模型效果。无 Precision/Recall/F1 实测。未来按句级证据 ID 评估检测，字段级需人工 Gold。先处理 M3298/M8016、冻结 clean split；不要在 Test1 调提示词。长会议需要覆盖策略，不得静默截断后报告全场 Recall。

## 15. Bad Cases

目前没有模型输出，也没有模型失败集。P0 已记录 Train M1989 的背景式正例、M0099 的含行动线索空标签，属于标注复核候选，不是已证实错标或模型 Bug。以后保存真实失败预测、配置、来源、原因和人工结论；公开版脱敏与许可审核。

## 16. Deployment

尚未部署。计划 CPU Linux + FastAPI + PostgreSQL + Docker Compose，练习 SSH、环境变量、持久卷、端口、日志、重启。本地 PostgreSQL Compose 已启动并验证，持久卷保留；应用尚未容器化。无服务器购买、登录或云部署记录。API Key 与账号操作由用户负责。

## 17. Issues & Fixes

见 issues_and_fixes.md：泄漏风险、旧文档过时、Docker 服务不可连接、报告原文发布风险。只记录真实现象；尚无应用 Bug 修复记录。

## 18. Git Workflow

本地 main 已有 d753085 安全基线，Batch 1 在 feature/backend-foundation 实现并提交。未建立 Remote/PR/CI，远程操作待确认。面试只能展示从实施日起真实记录。

## 19. AI 与人工分工

本轮用户明确目标与约束；AI 读取全部项目文本、运行 P0 全量复核、检查本地环境和 Git、编写四份新文档。Batch 1 由 AI 实现后端/迁移/测试并执行本地验证，生成被忽略的本机开发随机密码。用户负责需求边界和验收，下一步亲自检查 Swagger 与数据库。未来部署/凭据/Bad Case 复核仍需用户参与，不声称用户手写了 AI 生成代码。

## 20. 当前可诚实使用的面试表达

“项目完成了 442 场会议的数据审计，以及 FastAPI + PostgreSQL 后端，支持会议 CRUD 和文本上传，用 Alembic 管理表结构，31 项真实 PostgreSQL 测试通过。下一步接入云 LLM 结构化抽取；人工确认和部署尚未实现。”

完成 Batch 3、真实评估和部署后再更新介绍。最终 Cheatsheet 在 Batch 7 编制，不提前填入不存在的效果、Bug 或上线成果。

## 新主线增量：Authentication（已实现）

单公司多用户；app/models/user.py 的 User 保存 email、Argon2id password_hash、is_active/is_owner。app/core/security.py 的 current_user() 校验固定 HS256、issuer/audience/exp/iat/sub，并重新查询用户状态；create_token() 颁发限时 JWT。app/api/auth.py 的 register/login/me 暴露接口，客户端不能指定 Owner。app/services/access.py 的 meeting_query/require_meeting 将权限约束用于列表和对象访问，非本人返回 404 防枚举。

scripts/promote_owner.py 由本地管理员显式提升已注册用户；运行 `uv run python -m scripts.promote_owner --email ...`。不可在模型工具中调用。迁移 0002_auth 保留旧会议为空 creator，普通用户不可访问。tests/test_auth.py 覆盖重复注册、无效登录/JWT、禁止自提权、跨用户访问和禁用账户。

## 新主线增量：Extraction / Review / Tasks（已实现）

app/llm/client.py 的 LLMClient.generate() 只封装兼容 API，app/llm/extraction.py 的 extract()/text_windows() 分窗覆盖、严格 Pydantic 校验、证据必须为原文连续片段；超过 50000 字符明确返回 413，不静默截断。未知负责人只保留 assignee_name，与系统用户不同。

app/api/actions.py 的 extract_meeting() 网络调用前释放事务，保存时重新锁定会议检查正文和并发结果。ActionItem 状态 pending/confirmed/rejected；CandidateEdit/Review 使用 revision 防止旧页面确认。app/services/actions.py 的 confirm_candidate() 先权限校验和行锁，同事务写确认与 Task，UNIQUE(source_action_item_id) 防并发重复。失败由请求 Session rollback，不留下已确认但无 Task 的状态。已有候选的会议不能改正文或删除，避免证据失效。

Task 使用 assignee_user_id 可空 + assignee_name，/tasks/my 只返回绑定到当前 User 的任务。被指派用户可看自己任务并修改 status，不能改标题/负责人，也不因分配任务获得整个会议访问权。会议 Creator/Owner 可管理完整任务。

关键文件：app/models/action_item.py（ActionItem/Task）；app/schemas/actions.py（CandidateEdit/Review/TaskEdit）；migrations/versions/0003_actions_tasks.py；tests/test_actions.py（审核、权限、并发/事务）；tests/test_llm.py（成功/非法 JSON/错误字段/timeout/429/5xx/401/403）。实际云端调用未执行，所有模型结果明确来自 Mock。
