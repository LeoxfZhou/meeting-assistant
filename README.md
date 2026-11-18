# Meeting Action Assistant / 中文会议行动助手

面向中文会议的 AI Backend 求职项目：最终目标是云 LLM 提取候选、人工确认后建任务。本轮仅完成 Batch 1 Backend Foundation。主线为 LLM Application / AI Backend / Workflow / Deployment，QLoRA 仅 Optional。

## 当前范围

FastAPI、Pydantic、SQLAlchemy 2.x、真实 PostgreSQL、Alembic、Meeting CRUD、TXT/Markdown 上传和 PostgreSQL 集成测试。**尚未实现 LLM、Action Items、Task、Human Review、LangGraph、前端或云部署**。仅本机单用户开发，无 Auth，不作为公网生产服务。

## 本地准备

需要 Python 3.11–3.13、uv、Docker Desktop。当前实测 Python 3.13.9。`pyproject.toml` 是依赖源，`uv.lock` 锁定解析结果；没有第二套 requirements 清单。

```sh
uv sync --frozen
cp .env.example .env
```

已有 `.env` 时不要覆盖。把示例密码替换为随机本机开发密码，并同步 `POSTGRES_PASSWORD` 和 `DATABASE_URL` 的密码部分。凭据仅保存到忽略的 `.env`，不要发聊天或提交。建议 `chmod 600 .env`。此次开发已生成本机随机密码；不要为了运行再重置它。密码如含 URL 特殊字符须编码，使用随机十六进制字符串可避免歧义。

配置：APP_ENV、DATABASE_URL、LOG_LEVEL；Compose 使用 POSTGRES_USER、POSTGRES_PASSWORD、POSTGRES_DB、POSTGRES_PORT。Settings 从工作目录 `.env` 读取，因此以下命令均在项目根执行。

## 数据库与迁移

先打开 Docker Desktop：

```sh
docker compose up -d --wait postgres
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

Compose 只有 PostgreSQL 16，绑定 `127.0.0.1:55432`，使用命名持久卷及 healthcheck。现有卷初始化后修改 `.env` 密码不会自动修改数据库用户密码，不要盲目重建卷来修复。

查看实际数据库（无需把密码复制到命令）：

```sh
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"'
```

`docker compose stop` 保留数据。不要使用 `down -v`，除非明确要删除本地数据库。Migration 是正式 schema 来源，应用不调用 `metadata.create_all()`。

## 启动后端

```sh
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

访问 http://127.0.0.1:8000/docs 交互检查，或 http://127.0.0.1:8000/health。`/health` 仅进程存活检查，数据库可用性由实际 CRUD 验证。

## 当前 API

| 方法 | 路径 | 行为 |
|---|---|---|
| GET | /health | 200，status=ok |
| POST | /meetings | JSON title/content，201 |
| GET | /meetings | limit 1–100（默认 20）、offset ≥0 |
| GET | /meetings/{meeting_id} | UUID，200/404 |
| PATCH | /meetings/{meeting_id} | 部分修改 title/content，200 |
| DELETE | /meetings/{meeting_id} | 204，无响应体 |
| POST | /meetings/upload | multipart file，title 可选，201 |

标题去首尾空白，1–200 字符；正文去首尾空白，1–1,000,000 字符。PATCH 不接受空对象、显式 null、空白正文或未定义字段。NUL 字符不支持。上传限 .txt/.md、UTF-8（支持 BOM）、文件内容 ≤1 MiB，检查 Content Type；不持久保存上传文件，不用 filename 构造写入路径。没填 title 时使用去路径后的文件名主干。

错误：422 请求/编码/空内容无效，404 不存在，415 格式不支持，413 上传超限，503 数据库失败。数据库错误日志仅包含路由模板和异常类型，不输出连接串/SQL 参数/会议原文。LOG_LEVEL 不开启 SQL 调试输出。

当前文件上限在 multipart 解析后检查；尚无生产入口总请求流量限制，未来公网部署前需另行设置网关/请求体限制。

## Tests

```sh
uv run pytest -q
```

所有 API 测试连接真实 PostgreSQL，没有 SQLite 替代。测试从本机开发实例创建随机命名 `meeting_assistant_test_<uuid>` 数据库，先跑 Alembic；常规测试使用外层回滚事务，另有跨 Session 真提交测试。结束后仅删除本次创建的测试库，不清空开发库。要求本地开发用户具有 CREATEDB 权限；Compose 初始化用户仅供本机开发。APP_ENV=production 或非 loopback 数据库地址时测试拒绝运行。数据库不可用会失败，不跳过后假报通过。

实测 31 项通过；当前上游 Starlette 对 httpx TestClient 有一条弃用提示，暂不影响测试，后续升级测试适配时处理，未隐藏该提示。

## Git / Public Strategy

本地 `main` 保存安全基线，开发在 `feature/backend-foundation`。未创建 GitHub Remote、Push 或 PR。`.env`、虚拟环境、所有 outputs、raw/processed/annotations、数据库文件、私钥与缓存被忽略。

**原 `outputs/audits/data_audit.md` 含 Train 原文摘录，保留本地但不进入 Git。** 后续需要公开指标时逐文件审查后发布不含原文的摘要，不批量放行 outputs。数据来源、许可与版本仍需确认；见 [data/README.md](data/README.md)。公开前复查暂存区、凭据、个人信息和许可证。开发环境密码不能复用于生产。

当前目标：[MASTER_GOAL](docs/MASTER_GOAL.md)；状态：[PROJECT_STATE](docs/PROJECT_STATE.md)；代码解说：[PROJECT_WALKTHROUGH](docs/PROJECT_WALKTHROUGH.md)；真实问题：[issues_and_fixes](docs/issues_and_fixes.md)。`docs/project-plan/` 是历史方案，已被当前目标替代。
