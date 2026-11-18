# 中文会议行动助手：可交接教学 Walkthrough

核验日期：2026-11-18。面向没有参与开发的“C老师·项目实战指导”。以下区分已经运行的程序、Mock验证的错误行为、小样本真实Provider结果、仍待人工的UI验收与云部署。最新范围见 MASTER_GOAL；旧 project-plan 是历史资料。

## 1. Business Problem

我们模拟一家公司的内部会议行动管理：会议安排散落在文字中，负责人可能未注册，截止时间可能不明确，AI 不能替人批准任务。另一个问题是制度与历史会议难查，因此用 RAG 返回可追溯依据。没有真实企业用户、生产收益或自动通知系统。

业务不变量：模型只提出候选；人类编辑/确认/拒绝；正式任务来自确认，不能因为模型说“已确认”就写入。系统用户 User 与会议人物 assignee_name 独立，名字相同不自动绑定。

## 2. Final Architecture（本地已实现）

```text
Browser / Swagger → FastAPI → JWT + Authorization
  ├─ Meeting CRUD / TXT-MD → SQLAlchemy → PostgreSQL
  ├─ LangGraph extraction → httpx Cloud LLM Client → strict Schema
  │                       → optional search_knowledge → pending candidates
  │   Human confirm → confirmation graph → create_task tool → transaction + UNIQUE
  └─ Company Docs / authorized Meetings → chunk → CPU E5 ONNX → pgvector
      Question → query embedding → authorized SQL Top-K → context → LLM answer + citations
```

CPU Generation 不在本地运行；本地 ONNX 模型只做 Embedding。FastAPI/pgvector 在 Compose，模型目录只读挂载。没有 Redis、Celery、独立向量服务、Multi-Agent 或训练栈。

## 3. End-to-End Data Flow

1. 用户注册、登录取得 JWT；服务端每次验证签名/时效并查用户状态。
2. 创建会议时 creator_user_id 来自当前认证用户，不接受客户端指定归属。
3. 提取请求进入 Graph，读取授权会议，释放数据库事务后调用 LLM，避免长期持锁。
4. 分窗覆盖正文；每窗 strict JSON/Pydantic；证据必须是该窗连续原文。任一窗失败，整次返回错误，不保存“部分成功”。
5. 如文本包含制度/SOP/P1/P2/流程线索，受控检索只作为审核参考，不能从制度凭空创建新任务。
6. 保存前重新锁定会议并比较原文，防止模型调用期间会议变化；并发提取只允许一方保存候选。
7. Graph 结束于 awaiting_human_review。候选是 PostgreSQL 持久状态；没有占住 HTTP 请求等用户。
8. 用户编辑会增加 revision。确认时校验版本、权限、状态；同事务更新状态并写 Task。
9. 重复确认返回同一 Task；分配给系统用户后进入 My Tasks，未绑定用户仍显示文本姓名。
10. 会议索引是另一个显式操作；修改正文/标题会清除旧索引，下一次检索不会读到旧版本。

## 4. Real Code Map

| 文件 | class/function | 教学重点 |
|---|---|---|
| app/main.py | create_app、request_log、database_error、llm_error | factory、依赖、生命周期、错误与 request_id |
| app/core/config.py | Settings | env/SecretStr、超时与重试上限 |
| app/core/security.py | current_user、create_token、verify_password | JWT 固定算法、DB 用户状态、Argon2 |
| app/core/body_limit.py | RequestBodyLimitMiddleware | multipart 解析前的 4MiB 请求上限 |
| app/core/logging.py | log_event、request_context | JSON 字段、失败 ERROR、上下文隔离 |
| app/db/session.py | Base、build_engine、get_session | 连接池、每请求 Session、异常 rollback |
| app/models/user.py | User | 唯一邮箱、散列密码、active/owner |
| app/models/meeting.py | Meeting | 所有者、正文、来源、时间 |
| app/models/action_item.py | ActionItem、Task | 候选与正式任务分表、唯一来源约束 |
| app/models/knowledge.py | CompanyDocument、KnowledgeChunk | 双来源、Vector(384)、来源/字符范围 |
| app/schemas/auth.py | Register、Login、UserRead、Token | 不暴露 password_hash，不接受自提权 |
| app/schemas/meeting.py | MeetingCreate、MeetingPatch、MeetingRead | 部分更新、拒绝空值与未知字段 |
| app/schemas/actions.py | CandidateEdit、Review、TaskEdit、TaskRead | revision、可空绑定、时区校验 |
| app/api/auth.py | register、login、me | HTTP Auth 契约 |
| app/api/meetings.py | create/list/get/patch/delete_meeting、upload_meeting、save_meeting | CRUD 与上传复用 |
| app/api/actions.py | extract_meeting、extraction_workflow、edit_candidate、confirm、reject、my_tasks | 人工审核入口 |
| app/api/knowledge.py | ingest、index、search、ask、get_chunk、get_document | RAG HTTP 入口与引用回查 |
| app/services/access.py | meeting_query、require_meeting | 统一 Creator/Owner 过滤 |
| app/services/actions.py | require_candidate、check_pending、confirm_candidate、task_query、update_task | 锁、状态、幂等、分配权限 |
| app/llm/client.py | LLMClient.generate、LLMError | 单 Provider 抽象、错误分类、有限重试 |
| app/llm/extraction.py | ExtractedItem、Extraction、text_windows、extract | 分窗、严格结构与证据 |
| app/rag/embedding.py | Embedder.encode、get_embedder | ONNX、prefix、pooling、归一化 |
| app/rag/chunking.py | chunks | 段落/句界、重叠、字符偏移 |
| app/rag/service.py | ingest_company、index_meeting、retrieve、company_id | 入库幂等、权限 SQL、cosine |
| app/rag/answer.py | Answer、Citation、answer_question | context-only、拒答、引用校验 |
| app/workflow/graph.py | run_extraction、run_confirmation、ExtractionState | 有限有向流程与 SQL 审核边界 |
| app/workflow/tools.py | ToolContext、execute_tool、tool_schemas | Schema 参数与服务端写授权 |
| app/web/index.html | api、candidates、tasks、sources | 极简 UI、内存 token、textContent 防注入 |
| migrations/env.py / versions/ | upgrade、downgrade | 版本化 schema，不 create_all |
| scripts/audit_alimeeting4mug.py | inspect_archive、audit_record、render_report | P0 原包只读审计 |
| scripts/clean_split.py | main | 只生成派生 manifest |
| evaluation/extraction.py | score、evidence_ids | 句级身份、P/R/F1、跨句证据 |
| evaluation/database.py | isolated_database | 评估数据库隔离与清理 |
| scripts/evaluate_extraction.py | records、main | 真数据/Provider 或显式空基线 |
| scripts/evaluate_rag.py | main | 独立合成评估、检索与可选生成指标 |
| scripts/download_embedding.py | main | 固定 revision、下载重试、SHA manifest |
| scripts/promote_owner.py | main | 仅本地管理者显式设 Owner |
| scripts/smoke_compose.py | main | 真实容器/重启验证，合成候选不是模型成功 |
| scripts/audit_public_repo.py | main | index/history 路径、大文件和已知 Secret 检查 |

## 5. Database Schema

六张业务表 + alembic_version：

- users：UUID、唯一 email、display_name、password_hash、is_active/is_owner、created_at。
- meetings：UUID、creator_user_id FK、title/content、source_type、ready、created_at/updated_at。
- action_items：meeting_id FK、task、assignee_name、可空 assignee_user_id、due_date_text、evidence、pending/confirmed/rejected、revision。
- tasks：唯一 source_action_item_id FK、source_meeting_id FK、title、姓名/可空 User、due_date_text/可空带时区 due_date、todo/in_progress/done、时间。
- company_documents：固定 uuid5、slug、title/content/hash。只从捆绑原创虚构文档目录入库。
- knowledge_chunks：meeting_id 或 company_document_id（二选一 CHECK）、source_type/title/hash、content、index、字符起止、384维向量、模型标识、时间；source_id 属性统一返回实际来源。

迁移 0001 meetings → 0002 users/ownership → 0003 candidates/tasks → 0004 vector extension/documents/chunks。旧会议 creator 可空以保留历史数据，但只允许 Owner 访问；新会议必然绑定创建者。updated_at 的 ORM onupdate 不等于数据库 trigger。

## 6. APIs

根 README 列出完整路由；当前核心分组为 Auth、Meeting、Candidate、Task、Knowledge、Workflow。201 创建、204 删除、401 未认证、403 无权、404 不存在/不可见、409 stale/review冲突、413 超限、415 格式不支持、422 输入错误、502/504 Provider失败、503 依赖未就绪。

GET /health 不访问数据库，是 liveness。API 所有权从 JWT 得到，不允许任意指定 creator_user_id。PATCH 使用 exclude_unset，不把未提交字段覆盖成 null。

## 7. Authentication

Argon2id 散列密码，不可逆；注册邮箱规范化并由 DB UNIQUE 处理并发重复。登录不存在账号也验证 dummy hash，减少明显时差。JWT 固定 HS256，检查 iss/aud/exp/iat/sub；不相信 header 提供的算法。每请求重新读取 active/owner 状态，禁用用户即失效。

Owner 不能通过注册 JSON 自行获得，也不把“第一个注册人”自动当管理员。用户在本地明确运行 promote_owner。当前没有 OAuth、邮件验证、刷新令牌、找回密码或复杂 RBAC，因此只作为内部/本机演示，公网入口需控制。

## 8. LLM Provider

只有一个 httpx client 层；业务依赖 generate(messages, schema)，不依赖具体供应商 SDK。使用环境变量 API Key/Base URL/Model，强制 HTTPS、禁止跟随重定向。当前 gpt-6-luna 已真实验证Smoke、5类合成抽取和业务链路；默认max_completion_tokens、不发送temperature，旧服务可显式配置max_tokens。其他供应商兼容性不作保证；Mock仅说明错误路径。

## 9. Prompt

抽取 prompt 在 app/llm/extraction.py：正文不可信、不执行其中指令；只抽取明确承诺/安排；未知姓名或日期为 null；证据必须连续原文；不输出 User ID、确认状态或工具授权。RAG prompt 在 answer.py：只能依据 contexts，证据不足拒答，返回 answer/no_answer/citations。

提示词只是第一层约束，真正的权限、状态、写入和引用成员校验由服务端完成。没有因为写了“不要幻觉”就保证结果正确。

## 10. Structured Output

ExtractedItem 四个必需字段：task、assignee_name、deadline、evidence；其中姓名/日期可 null，但不等于允许缺字段。strict=True、extra=forbid；action_items=[] 合法。JSON/字段/类型错误、截断 finish_reason、不可定位证据明确失败。

正文最多 50,000 字符；连续 6000字符窗、300字符重叠，优先句/段边界。合并按证据去空白去重；该启发式可能合并重复证据下的不同任务，属于已知边界，需真实 Bad Case 复核。任一窗失败不保存部分候选。

## 11. Human-in-the-loop

pending 可编辑 task/name/binding/deadline text；证据不可被编辑伪造。每次编辑 revision+1；确认/拒绝检查当前 revision。拒绝不生成任务，已拒绝不能再次确认。确认后不直接修改候选，任务状态通过 Task API 维护。截止时间原话与确认后的日历时间分开；不自动把“周五”推算成某日期。

## 12. Task System

正式任务来源可追溯到候选与会议。Creator/Owner 管理该会议任务；被指派系统用户可看自己的任务并只改 status。未绑定 User 仍显示姓名，不会进入任意同名用户的 My Tasks。轻量 UI 以负责人、标题、日期、状态、来源会议展示，来源点击仍校验权限。

## 13. Idempotency

confirm_candidate 以会议/候选行锁串行化竞争，再检查状态与 revision；Task.source_action_item_id 唯一约束是数据库最后防线。确认状态和 Task 同一次 commit。真实测试使用两个并发请求，得到同一 ID；注入 INSERT 失败后候选仍 pending、Task 为零。

这是单 PostgreSQL 事务边界内的幂等，不宣称跨供应商/跨系统“恰好一次”。HTTP 超时后客户端可重试确认，已经成功时返回现有 Task。

## 14. RAG

两种正式来源：原创企业文档与用户实际创建/授权的会议。12份虚构资料涉及 HR、差旅、远程办公、发布、Review、Incident、部署、会议跟进、升级、Alpha/Beta、安全边界。每份有 Synthetic 标记、版本和生效日期。

公司文档由 Owner 触发 ingestion，固定 slug→uuid5，重复入库替换同源 chunks；会议索引先计算向量，保存前锁定复查版本。会议更新时同事务删除旧 chunks，删除会议由 FK cascade 清理。AliMeeting 的原包、processed 和评测预测没有 ingestion 路径。

## 15. Embedding

基模型 intfloat/multilingual-e5-small；固定 Xenova ONNX int8 导出 revision 761b726dd34fb83930e26aab4e9ac3899aa1fa78，文件 118,308,185 bytes，模型 SHA f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193。384维，query:/passage: 前缀；attention mask mean pooling，再 L2。CPU 两线程、8条一批，不静默截断超过512 token文本。

模型使用方法依据 [原模型卡](https://huggingface.co/intfloat/multilingual-e5-small)；下载的是 [ONNX 导出](https://huggingface.co/Xenova/multilingual-e5-small)。中文/英文可用不代表每个领域都优质，需要评估。

## 16. pgvector

PostgreSQL 16.16 + pgvector 0.8.7，Vector(384)，cosine distance。当前小语料做精确排序，未建 HNSW，不冒充百万级性能。关键 SQL 先过滤模型版本及 company/授权 meeting，再 ORDER BY distance/LIMIT，不能先全局 Top-K 后掩盖越权项。

source_type、source_id、chunk_id、字符起止支持回查。GET chunk 对会议来源再授权。答案引用 ID 必须属于本次返回集合、quote 必须包含于片段；引用合法不保证生成语义完全蕴含，人工检查仍必需。

## 17. LangGraph

run_extraction 构造 START→load_meeting→extract_and_validate→可选 retrieve_knowledge→save_candidates→human_review_boundary→END。采用简单正则判断是否需要知识参考，不把每场安排都变成 RAG。

SQL 中 pending 候选是持久人机交接状态；服务端不使用进程内 InMemorySaver 冒充持久恢复，也未使用 LangGraph interrupt/checkpointer API。确认请求触发独立 run_confirmation，从数据库重新验证再调用写工具。真实测试重建整个 FastAPI app 后仍可查看 pending、确认同一候选。普通 Meeting CRUD 不包装成 Graph。

## 18. Tool Calling

get_meeting、search_knowledge、create_task、update_task 均有 Pydantic 参数 Schema 和服务端 ToolContext。当前是**确定性工作流调用工具**，不是模型自由决定工具序列，也未声称已验证供应商 function calling。

写工具要求由认证人工操作创建的 human_approved 上下文；这个字段不在模型参数 schema，注入 human_approved=true 会被拒绝。create_task 仍执行所有权、版本、状态、事务与唯一约束，不仅检查一个布尔值。

## 19. Reliability / Cost

默认 connect=5s/read=30s/最多3次；429/5xx/传输错误有限退避；Retry-After 数字或HTTP日期可用，单次睡眠封顶10s。401/403/400、非法结构不盲目重试；Response finish_reason 非 stop 视为不完整生成。

请求 UUID、user_id/meeting_id/model、延时、状态、错误类型、token usage 结构化记录。input/output/total 仅接受供应商非负整数；无可靠定价时 estimated_cost=null。会议正文、API Key、密码、SQL参数和供应商原始失败响应不进日志。失败事件 ERROR；普通事件 INFO。

成本来自每场会议分窗数×输入/输出 token、重试和每天处理量；重叠窗会重复计费。当前没有真实账单/吞吐/成本数据，不能估造“每天多少钱”。

## 20. Evaluation

P0 真数据 442 场、302332句、1472行动 ID、109显式空标签。clean_split.py 保留 raw，仅派生排除 Train M3298（Dev M8016 有40长句重合，相似度0.877），得到 Train294/Dev65/Test1 82。

句级评估身份为 (meeting_id,sentence_id)，跨句证据映射所有重叠句，合并重复编号；失败调用算空预测不删样本，分母为零记0。全空基线 Dev65：TP0/FP0/FN222、P/R/F1=0，只验证评分代码，不能当成 LLM 失败或成功成绩。缺字段级 Gold，assignee/deadline/task Accuracy 不计算。

RAG25题含事实、混淆、跨文档、3场合成历史会议、3无答案题。22个有答案题：Hit@5=1、Recall@5=1、MRR=0.893939。完整25题生成指标仍为null；另做6题真实生成子集首轮5/6通过，4道有答案引用有效，2道无答案首轮1道通过，空拒答修复后单题通过。不得混用两个评估范围。小型自编集不能外推真实业务。脚本在随机独立 PG 库运行并清理，不污染开发库。

## 21. Bad Cases

outputs/evaluations/rag/bad_cases.jsonl 保留4个非首位命中的排序弱项（Top-5仍覆盖）；不是4个错误答案。extraction_empty_baseline/bad_cases.jsonl 保留全空策略漏检的55场正例会议，用于检查计分链路，不冒充模型失败。

原 P0 的 M1989 背景式正例、M0099 含行动线索空标签是人工标注复核候选，尚未证明错标。真实云失败已保存：HTTP400旧max_tokens不支持、无答案answer为空造成Schema错误；后者修复prompt并复测通过。用户人工抽查仍待完成，不把开发失败称为生产事故。

## 22. Docker

Dockerfile 使用官方 Python3.13 + 固定 uv0.10.12、uv sync --frozen --no-dev，非root运行。Compose 含 API 和 PG+pgvector，模型只读挂载，PG 命名卷，healthcheck，两服务端口仅loopback。

真实 Compose 冒烟执行注册/CRUD/上传/CPU检索、重启、pending保留、确认幂等/MyTasks。任务候选来自明确的合成 fixture，不是假的 LLM 成功。临时用户/会议已删除，12份虚构制度保留。备份 pre_pgvector.dump 在忽略的 outputs/checks，不公开。

## 23. Server Deployment

尚未购买或登录服务器，未部署云端、域名、Nginx/HTTPS。docs/DEPLOYMENT.md 给出 SSH tunnel、随机环境变量、持久卷、备份和验证步骤。服务器、SSH、DNS与真实付费操作需要用户，不自动代购。

## 24. Git Workflow

基础版 d753085/e8ed364/537953e 真实保留；复验后 main 合并。feature/auth 的 f431b78、feature/extraction-review-tasks 的 317248d 经过测试后本地合并。RAG/Workflow/Evaluation/Deployment 后续提交以 git log 为准。此前未配置Remote，因此不补造旧PR。用户建立Private仓库后，b7cd07e首次push已通过真实Actions：73项测试、14.73秒；本轮文档以新分支/真实PR交接，见GITHUB_WORKFLOW。

## 25. Issues & Fixes

详见 issues_and_fixes.md。真实问题包括跨划分泄漏、旧路线过时、Docker socket权限、uv缓存/网络、HTTPS CA、日志级别回归、基础镜像下载/标签错误、浏览器预览连接与首屏执行上下文。能解释现象、证据、修复和边界，不编造“线上事故”。

## 26. AI vs Human Contribution / 教学顺序

AI：读取与验证旧资产、编写大部分实现、迁移/测试、构造原创合成集、运行真实 PG/CPU RAG/Compose、更新文档。用户：制定业务边界、提供 API/账号/服务器、做真实模型与 Bad Case 复核、最终讲解和演示。没有统计代码贡献比例，不把 AI 代码声称为本人逐行手写。

建议教学顺序：先在UI/Swagger跑用户→会议→候选→任务（本机已配置Key；新环境需自行配置）；再读 current_user/require_meeting；用两次确认解释事务与唯一约束；看 retrieve 的 SQL 权限；再解释 Graph 的持久人工边界；最后读评估报告的 null/局限与部署状态。面试只说已实现和已测事实，速查见 INTERVIEW_CHEATSHEET，证据分类见 RESUME_EVIDENCE。

## 27. 真实Provider联调教学补充

入口 scripts/verify_real_provider.py 的 BudgetTransport.handle_request 在发出请求前落盘计数，响应仅保留安全指标和合成内容；main 分阶段执行抽取、隔离PG业务链路、RAG子集。pytest不自动调用此脚本。18次尝试与用量、失败/复测口径见 REAL_PROVIDER_VERIFICATION.md。

实际发现的max_tokens错误推动LLMClient可配置token参数；RAG拒答为空推动prompt要求非空说明，Schema保持严格。候选确认是用户授权的API自动测试，不是用户UI确认。生产日志新增http_status，依然不记录完整正文或Secret。

## 28. GitHub CI 实际链路

.github/workflows/tests.yml 在push/PR触发，Ubuntu runner启动pgvector PostgreSQL服务，安装Python3.13与锁定依赖，下载固定revision的CPU embedding，再运行pytest。测试创建随机独立数据库后清理。CI只用临时数据库/JWT测试值，不上传.env、不配置LLM Key、不调用付费Provider。首次成功run为44308229328，源commit b7cd07e。Git网络需遵循本机已有系统代理；没有改变全局Git设置。
