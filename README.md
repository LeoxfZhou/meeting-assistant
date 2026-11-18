# Meeting Action Assistant / 中文会议行动助手

一个面向单公司、多用户的 **LLM Application / AI Backend / RAG / Workflow** 求职演示项目：会议文本 → 结构化候选 → 人工确认 → 正式任务，并支持带权限的企业知识和历史会议检索。QLoRA/GPU 训练不在主线。

## 真实状态

已实现 Auth/JWT、Meeting CRUD/TXT/MD、云 LLM Client、Candidate Review、幂等 Task/My Tasks、CPU multilingual embedding + pgvector、LangGraph 受控流程、评估脚本、FastAPI/PostgreSQL Compose 和轻量演示页面。

- 73 项 pytest 通过，全部数据库集成使用真实 PostgreSQL；不是 SQLite 替代。
- 真实 CPU 检索：25 题合成集（22 有答案），Hit@5=1.0、Recall@5=1.0、MRR=0.893939。规模小且自编，不代表真实企业效果。
- **已完成 gpt-6-luna 小样本真实验证**：5类合成抽取通过，API确认到Task和Docker真实出站通过。RAG首轮5/6通过，1个空拒答失败修复后单题复测通过；不能当作全量准确率。详见 [真实验证](docs/REAL_PROVIDER_VERIFICATION.md)。
- Compose 已真实运行及重启验证；没有云服务器部署、GitHub Remote/PR 或远程 CI 成功记录。

## 快速启动

需要 Python 3.11–3.13、uv、Docker。已实测本机 Python 3.13.9；pyproject.toml 为依赖源，uv.lock 锁定版本。

```sh
uv sync --frozen
cp .env.example .env  # 已有 .env 时不要覆盖
```

在 `.env` 设置本机随机 `POSTGRES_PASSWORD`，同步 `DATABASE_URL` 密码部分，并生成至少 32 字符的 `JWT_SECRET`。不要提交或发到聊天。可用 Python `secrets.token_hex(32)` 在本机生成；`chmod 600 .env`。本次开发已经生成随机本地凭据，不需要重置现有文件。

```sh
uv run python -m scripts.download_embedding
docker compose up -d --build --wait
```

访问 [本地演示页面](http://127.0.0.1:8000) 或 [Swagger](http://127.0.0.1:8000/docs)。首次注册不会自动成为 Owner；本地管理员可对自己的已注册账号执行：

```sh
docker compose exec api python -m scripts.promote_owner --email your-email@example.com
```

Owner 可导入 12 份原创虚构企业资料。创建会议后点击“建立检索索引”，可检索自己的历史会议。LLM 未配置时“AI 提取”和“基于依据问答”会明确失败；不能把失败看成空结果。检索本身不需要云 Key。

## 本机 Python 开发方式

```sh
docker compose up -d --wait postgres
uv run alembic upgrade head
uv run alembic check
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 18080 --reload --no-access-log
```

此方式使用 `.env` 中 loopback 数据库 URL；Compose API 会将 URL 主机覆盖为服务名 postgres。所有命令在项目根执行。`/health` 是 liveness，实际数据库可用性要通过 CRUD 验证。

## 配置

| 变量 | 含义 |
|---|---|
| APP_ENV | development / test / production |
| DATABASE_URL | postgresql+psycopg 连接串（不要打印） |
| JWT_SECRET | 至少 32 字符随机签名密钥 |
| JWT_EXPIRE_MINUTES | 默认 60 分钟 |
| LOG_LEVEL | 默认 INFO；SQL 参数和网络调试日志不输出 |
| LLM_API_KEY / LLM_BASE_URL / LLM_MODEL | 云端 Generation；未配置时 503 |
| LLM_TOKEN_LIMIT_PARAMETER / LLM_MAX_COMPLETION_TOKENS | 默认 max_completion_tokens / 4096；旧兼容服务可显式选择 max_tokens |
| LLM_TEMPERATURE | 默认不发送；仅模型支持时设置 |
| LLM_CONNECT_TIMEOUT / LLM_READ_TIMEOUT / LLM_MAX_ATTEMPTS | 默认 5秒 / 30秒 / 3次 |
| POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB / POSTGRES_PORT | Compose 数据库配置；默认本机端口 55432 |

Provider 须支持 HTTPS 下的 OpenAI-compatible `/chat/completions` 与 JSON object 输出。不同兼容服务的支持程度需真实联调。模型名和定价未指定，不估造成本。

## 当前 API

除 `/`、`/health`、注册/登录、API 文档外，业务接口需要 Bearer JWT。

| 范围 | 接口 |
|---|---|
| 用户 | POST /auth/register、POST /auth/login、GET /auth/me、GET /users（绑定负责人目录） |
| 会议 | POST/GET /meetings、GET/PATCH/DELETE /meetings/{id}、POST /meetings/upload |
| 提取/流程 | POST /meetings/{id}/extract、POST /meetings/{id}/workflow、GET /workflow/tools |
| 候选 | GET /meetings/{id}/candidates、PATCH /candidates/{id}、POST /candidates/{id}/confirm 或 reject |
| 任务 | GET /tasks、GET /tasks/my、GET/PATCH /tasks/{id} |
| 知识 | POST /knowledge/company/ingest（Owner）、POST /meetings/{id}/index |
| 检索/问答 | POST /knowledge/search、POST /knowledge/ask |
| 引用 | GET /knowledge/chunks/{id}、GET /knowledge/documents/{id} |

Meeting 仅 Creator/Owner 可访问；历史向量检索在 SQL LIMIT 之前执行相同权限。被分配任务可查看该任务并改 status，但不会自动获得整场会议权限。`assignee_name` 与 User 独立，可不绑定系统账号。

候选编辑、确认、拒绝必须带当前 `revision`。编辑后旧版本确认返回 409；已确认候选重复确认返回同一 Task。候选/正式任务同事务，数据库 `UNIQUE(source_action_item_id)` 保证幂等。已有候选的会议不能改正文或删除；未提取会议修改后清除旧索引，需重新索引。

上传限 `.txt/.md`、UTF-8（含 BOM）、1 MiB，内容直接存正文，不保存原文件。请求体解析前限制 4 MiB；正文 1–1,000,000 字符，标题 1–200 字符；单次抽取最多 50,000 字符，超限明确拒绝，不静默截断。当前已有认证，但未实现生产级入口限流；不要直接暴露到公网。

错误：401 认证失败、403 权限不足、404 不可见/不存在、409 状态冲突、413 超限、415 文件不支持、422 校验失败、502/504 Provider 失败、503 未配置/DB/embedding 未就绪。

## Embedding / RAG

固定 `intfloat/multilingual-e5-small` 的 Xenova ONNX int8 导出，revision `761b726dd34fb83930e26aab4e9ac3899aa1fa78`，384 维；CPU、attention-mask mean pooling、L2 normalization；查询加 `query: `，文档加 `passage: `。文件 SHA-256 记录在忽略的 `models/.../manifest.json`。

Markdown 按段落/标题优先、380字符兜底；会议按句界、最多60字符重叠。当前小数据量使用 pgvector 精确 cosine 检索，无 BM25/reranker/Hybrid。返回 chunk/source ID 与字符范围。引用必须来自本次授权检索结果且 quote 为对应片段原文；这不等于已证明答案语义完全正确。

AliMeeting 仅用于抽取评估，**不会被企业资料 ingestion 或历史会议索引脚本自动导入**。

## Tests / Evaluation

```sh
uv run pytest -q
uv run python -m scripts.clean_split
uv run python -m scripts.evaluate_extraction --mode empty-baseline --split Dev --output outputs/evaluations/extraction_empty_baseline
uv run python -m scripts.evaluate_rag
```

pytest 和 RAG evaluation 在本机开发 PostgreSQL 中创建随机独立数据库，迁移后运行，结束清理；不清空开发库。需要 CREATEDB 权限，拒绝 production/远端连接。向量模型必须先下载；缺模型会真实失败，不跳过后宣称通过。

clean split 排除 Train M3298，保留 Dev M8016，记录原包 hash 和规则，只写 `data/processed/`。全空预测基线是评分工具基线，**不是 LLM 成绩**。真实 Provider 评估需 Key、模型与调用预算批准后再运行：

```sh
uv run python -m scripts.evaluate_extraction --mode provider --split Dev --limit 5 --output outputs/evaluations/extraction_provider_smoke
uv run python -m scripts.evaluate_rag --with-llm --output outputs/evaluations/rag_provider
```

结果写 outputs/evaluations，失败案例保留。任务字段无 AliMeeting Gold，不填 assignee/deadline Accuracy。检索评估有 3 道无答案题，未运行 LLM 时拒答准确率保持 null。

`python -m scripts.smoke_compose` 会对本机 Compose 创建临时合成用户/会议、索引、插入明确标记的候选 fixture、确认/重复确认并重启容器验证持久化，结束清理本次数据；不是模型效果评估，不应在生产执行。

## Git / 数据 / 部署

Local feature branch + tests + commit + merge；未创建远程仓库，不伪造 Issue/PR/CI。公开前运行 `uv run python -m scripts.audit_public_repo` 审查 index/history。此扫描不是完美的 Secret 保证，仍需人工许可与个人信息审查。

`.env`、raw/processed/annotations、所有 outputs（包括含 Train 原文的审计报告）、models、数据库文件、虚拟环境与私钥都不进入 Git。原始审计资产保留。数据来源/许可仍待确认，见 [data/README.md](data/README.md)。

Compose 默认只绑定本机，使用持久卷。`stop` 保留数据，勿用 `down -v` 清空。云服务器尚未购买/登录/部署；见 [部署交接](docs/DEPLOYMENT.md)。

当前证据：[PROJECT_STATE](docs/PROJECT_STATE.md) · [教学 Walkthrough](docs/PROJECT_WALKTHROUGH.md) · [面试速查](docs/INTERVIEW_CHEATSHEET.md) · [简历证据](docs/RESUME_EVIDENCE.md) · [真实问题](docs/issues_and_fixes.md)。历史 `docs/project-plan/` 已被当前 MASTER_GOAL 替代。
