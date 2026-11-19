> 当前范围：功能冻结与评测封版；云端基础设施已验证，云端 Generation 不属于部署验收范围。

# CPU Linux 部署与下线证据

已在中国大陆阿里云 ECS 完成基础部署；没有商业线上用户、域名或HTTPS。以下准备流程为历史可复现说明，真实证据在后文。

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

## 2026-11-19 真实Linux部署进展

服务器xyhleo-server：Ubuntu24.04.5 LTS、2vCPU、约1.7GiB可见RAM、40GiB盘；未执行发行版升级。新增2GiB /swapfile-meeting并写fstab，保留原fstab备份。安装Ubuntu仓库Docker29.1.3、Compose2.40.3；UFW仅放行SSH22，SSH密码认证原已禁用。

部署路径/opt/meeting-assistant，源为GitHub main c4aa706（CI success）。服务器Docker Hub连接超时，改为本机官方来源构建linux/amd64镜像，经SSH docker save/load传输；没有复制GitHub凭据或本机.env。服务器独立生成DB/JWT secret，.env权限600。CPU模型4文件SHA256全部一致。

Compose云覆盖：API900MiB、PG450MiB，PG shared_buffers64MB/max_connections30，日志10MiB×3。API/PG healthy，Alembic0004_knowledge(head)，真实注册/登录、会议、CPU向量检索通过；容器重启后同一合成会议仍可读。API检索后约635MiB，PG约41MiB。应用8000与数据库55432只绑定loopback，未开放公网5432。

整机重启验收已完成，详见下文；服务器无凭据连接OpenAI失败，LLM三变量暂空，尚未验证服务器真实云生成，不宣称完整云业务链路成功。

### 整机重启验收完成（2026-11-19）

boot ID从b5801c58-0b2b-472b-aba6-7505d6193958变为a434b186-f13c-41f6-942a-7143b5e3f826；Docker enabled，API/PG自动healthy，2GiB Swap恢复。同一合成会议022a2ba1-d0f3-4401-a24a-ff62cb3d8bfe重启后读取和CPU向量检索通过。未重建或清空命名数据库卷。

部署主机仅SSH公开，应用/DB绑定127.0.0.1。访问方式：`ssh -N -L 18081:127.0.0.1:8000 xyhleo-server`，浏览器打开http://127.0.0.1:18081。云端基础设施验收已完成。大陆ECS连接api.openai.com:443曾超时，但云端Generation现已明确排除在部署Scope之外，不再等待Provider配置；真实AI验证在开发环境完成。没有传输本机Key或绕过访问限制。

当前源代码部署来自已验证Git main归档，不是服务器持有GitHub凭据直接clone。更新需重新传输受审提交/镜像；没有伪造远程clone。compose.cloud.yml记录实际低内存参数。合成验证账户/会议保留用于重启证据，凭据仅服务器/root/.meeting-probe.json（600），不进Git。

## 下线前新增验收（2026-11-19）

再次核对API/PG healthy，40GiB盘已用7.7GiB，2GiB Swap存在。数据库只有1个合成探针用户、1场Synthetic server persistence probe会议、0候选/Task/企业文档，无唯一业务数据。服务器.env无需保留，用户已授权永久删除Demo。

实际执行compose down（不带-v）：API/PG容器和项目网络删除，但meeting-assistant_postgres_data仍存在。随后up --no-build --pull never --wait，两服务healthy；同一会议ID读取及CPU向量检索通过。原始终端记录位于忽略的outputs/checks/cloud_down_up.log。永久清理已在下面单独验收。

## 授权永久下线已完成（2026-11-19）

先将部署证据提交0d91cff并push到Private GitHub，然后再次断言数据库恰为1个合成用户、1场既有探针会议、0任务/候选。确认路径不是符号链接后执行指定Compose down -v；仅删除项目容器、network、meeting-assistant_postgres_data、/opt/meeting-assistant（含.env和模型副本）、/root/meeting_probe.py和/root/.meeting-probe.json。没有删除其他项目或执行全局prune。

下线后断言项目容器/网络/卷/目录/探针均不存在；全新SSH会话登录成功，Docker29.1.3仍可用且enabled，Compose2.40.3和2147479552-byte Swap保留，authorized_keys仍在。Ubuntu/SSH/Git/系统软件未卸载。磁盘快照已用8193327104→7979843584 bytes，释放约203.6MiB；保留缓存镜像，不声称清空整个Docker。内存已用约1009→469MiB，仅快照对比。

本项目Demo是有意下线，服务器保留为xyhleo personal server，不删除ECS、不重装系统。以后需要演示请在本机启动；原SSH Tunnel端口不再提供Meeting Assistant服务。公开证据：evaluation/evidence/cloud_validation.json。原始清理终端记录保留本地outputs/checks/cloud_cleanup.log。
