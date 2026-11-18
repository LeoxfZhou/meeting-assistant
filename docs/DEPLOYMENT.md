# CPU Linux 部署交接（尚未部署到云服务器）

本地 Compose 验证与真实云部署是两件事。当前不声称已有服务器、域名或线上用户。

## 人工准备

1. 用户自行选择并购买 CPU Linux 服务器，不需要 GPU。先按小流量演示准备，内存建议至少 4 GB；实际容量以运行测试为准。
2. 用户完成 SSH 登录和系统权限操作，不把私钥、系统密码贴入仓库或聊天。
3. 在服务器安装 Docker Engine 与 Compose plugin，核验 `docker info`。
4. 通过经确认的 GitHub Private 仓库或安全文件传输上传代码；不要上传 raw、数据库备份、私人会议和本机 .env。

## 环境与启动

- 在服务器项目目录单独创建 `.env`，设置随机 POSTGRES_PASSWORD、JWT_SECRET（≥32字符）、APP_ENV、LLM_API_KEY/BASE_URL/MODEL；`chmod 600 .env`。
- PostgreSQL 和 API 默认仅映射到 127.0.0.1，保留此设置。演示可使用 SSH tunnel：`ssh -L 8000:127.0.0.1:8000 <user>@<server>`，再从本机浏览器访问。
- 模型固定使用项目下载脚本的 revision，不把 `main` 浮动权重当作同一实验。可在服务器用独立 Python 环境运行 `python -m scripts.download_embedding`，或传输已校验的 models/ 文件和 manifest。
- 运行 `docker compose up -d --build --wait`。API 启动先执行 Alembic upgrade head，然后运行 Uvicorn。
- 用 `docker compose ps`、`docker compose logs --tail=100 api`、`curl http://127.0.0.1:8000/health` 核验；health 只表示进程存活，还要实际登录、创建/读取合成会议。
- 注册自己的用户后，管理员显式运行 `docker compose exec api python -m scripts.promote_owner --email <your-email>`。普通注册不能指定 Owner。
- Owner 导入企业资料，创建合成会议并建立索引；真实模型调用前确认 Provider、模型与预算。

## 数据与恢复

命名卷保存数据库；`docker compose stop`/`restart` 不删除卷。不要执行 `down -v` 清空数据。

迁移前用 `pg_dump -Fc` 保存到受限目录，并在单独数据库验证备份可读/可恢复。备份可能含用户和会议，不能提交 Git。应用镜像回退并不自动回退数据库 schema；破坏性迁移必须单独计划，当前主线不执行用户数据删除。

改 `.env` 中 POSTGRES_PASSWORD 不会自动改变已有数据库用户密码。JWT_SECRET 更换会使旧 token 失效，需重新登录。LLM Key 更新后重建 API 容器以读取新环境。

## 公网限制

当前是内部演示：开放注册、无邮箱验证、无刷新令牌/找回密码、无生产级限流。不要直接向公网开放 8000/55432。需要公网演示时先增加 HTTPS 和访问入口控制；Nginx/域名/DNS/证书需要用户明确配置，未在本地验证中冒充完成。

## 最终线上验收记录模板

待真实部署时记录：服务器系统/CPU/内存（不含 IP 或凭据亦可）、Git commit、镜像 digest、迁移版本、容器 health、CRUD/权限/检索/真实 LLM Demo、重启前后同一合成记录是否保留、日志和实际问题。没有这些证据，不填写“已上线”。
