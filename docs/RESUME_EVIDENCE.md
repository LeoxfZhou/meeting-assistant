> 2026-11-19 更新：真实云基础部署、迁移、CPU检索、容器及整机重启已验证；云端LLM因Provider网络连接超时尚未完成。下方原本地验收/待部署描述为历史快照，以文末云验收记录为准。

# 简历证据：Implemented / Measured / Planned

2026-11-18。本项目是单公司内部系统模拟，不是商业生产系统。AI 参与主要实现，用户负责取舍、真实外部服务与验收；不宣称全部代码手写。

## Implemented（可由代码与测试核对）

- FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL：用户、会议、候选、任务、企业文档、知识片段六表。
- JWT/Argon2id、Creator/Owner 权限；会议人物与系统用户分离。
- 结构化云 LLM 客户端、Pydantic 校验、证据定位、超时/有限退避/错误分类。错误路径Mock测试；当前Provider已有合成小样本真实验证。
- 人工编辑/确认/拒绝；revision、事务、行锁与 UNIQUE(source_action_item_id)；重复确认不新增任务。
- CPU multilingual E5 384维 + pgvector；12份原创合成公司文档、授权历史会议、可追溯引用。
- LangGraph 受控流程、四个 schema 工具；SQL 持久人工边界，不声称原生 interrupt 或自由 Agent。
- Docker Compose API/PG、轻量 UI、独立 PostgreSQL 测试库、评估与数据审计工具。

## Measured（实际证据）

| 内容 | 结果 | 本地证据与限制 |
|---|---|---|
| 数据规模 | 442会议 / 302332句 / 1472行动ID / 109空标签 | outputs/audits；原文报告不公开 |
| 派生划分 | Train294 / Dev65 / Test1 82 | data/processed/clean_split.json；raw hash保留 |
| 测试 | 最新73 passed / 22.98s | 当前完整 pytest；真实PG/CPU，外部LLM Mock |
| 抽取 | Dev65空预测基线 P/R/F1均0 | outputs/evaluations/extraction_empty_baseline/report.json；不是模型指标 |
| RAG检索 | Hit@5=1，Recall@5=1，MRR=0.893939 | outputs/evaluations/rag/report.json；22有答案题，自编小集 |
| RAG生成 | 6题首轮5/6；有答案引用4/4；无答案1/2 | 空拒答修复后单题复测通过，非完整集指标 |
| 容器 | API/PG healthy；重启后审核状态保留 | outputs/checks/compose_smoke.json；合成候选fixture |
| 页面 | 注册/会议/索引/检索显示通过 | outputs/checks/ui_smoke.json与截图 |
| Git / CI | Private origin已push；远程73 passed / 14.73s | Actions 44308229328，b7cd07e；真实文档PR交接见GITHUB_WORKFLOW |

## Planned / 需人工完成

当前Provider小样本兼容性和真实失败已验证；仍待用户UI Demo、字段人工评估、完整模型指标与真实成本；GitHub已Private接入并通过首轮CI；CPU Linux 部署/SSH/备份恢复验收。HTTPS、ASR、QLoRA为后续可选，不写成现有能力。

## 可用简历表述

“开发中文会议行动助手，基于 FastAPI/PostgreSQL 实现人工审核到任务创建的事务链路，以唯一约束保证重复确认幂等；构建带访问权限过滤的 CPU multilingual embedding + pgvector 检索与 LangGraph 受控工作流，完成73项测试和本地 Docker Compose 重启验证。”

如写 RAG 数值，必须附“小型自编合成集22个有答案问题”；不得单写“准确率100%”。不得声称生产部署、企业用户收益、真实模型抽取F1或成本下降。API和实际class/function见 PROJECT_WALKTHROUGH，技术取舍见 INTERVIEW_CHEATSHEET。

## 本轮 Real API Verified

gpt-6-luna，18次尝试、16次HTTP200；5类合成抽取5/5通过，真实抽取→候选→API确认→Task与Docker出站通过。输入12363/输出1491 tokens；未计算价格。真实失败：旧token参数HTTP400，拒答空answer被Schema拒绝；修复及原始证据见 REAL_PROVIDER_VERIFICATION。确认由授权自动API测试执行，不能写成真人UI验收。未对AliMeeting云评测。

远程CI为实测，可如实写“GitHub Actions执行73项测试通过”；该结果不代表云服务器已经部署，也不是多人独立Code Review证明。

## 2026-11-19 真实Linux部署进展

服务器xyhleo-server：Ubuntu24.04.5 LTS、2vCPU、约1.7GiB可见RAM、40GiB盘；未执行发行版升级。新增2GiB /swapfile-meeting并写fstab，保留原fstab备份。安装Ubuntu仓库Docker29.1.3、Compose2.40.3；UFW仅放行SSH22，SSH密码认证原已禁用。

部署路径/opt/meeting-assistant，源为GitHub main c4aa706（CI success）。服务器Docker Hub连接超时，改为本机官方来源构建linux/amd64镜像，经SSH docker save/load传输；没有复制GitHub凭据或本机.env。服务器独立生成DB/JWT secret，.env权限600。CPU模型4文件SHA256全部一致。

Compose云覆盖：API900MiB、PG450MiB，PG shared_buffers64MB/max_connections30，日志10MiB×3。API/PG healthy，Alembic0004_knowledge(head)，真实注册/登录、会议、CPU向量检索通过；容器重启后同一合成会议仍可读。API检索后约635MiB，PG约41MiB。应用8000与数据库55432只绑定loopback，未开放公网5432。

整机重启验收已完成，详见下文；服务器无凭据连接OpenAI失败，LLM三变量暂空，尚未验证服务器真实云生成，不宣称完整云业务链路成功。

### 整机重启验收完成（2026-11-19）

boot ID从b5801c58-0b2b-472b-aba6-7505d6193958变为a434b186-f13c-41f6-942a-7143b5e3f826；Docker enabled，API/PG自动healthy，2GiB Swap恢复。同一合成会议022a2ba1-d0f3-4401-a24a-ff62cb3d8bfe重启后读取和CPU向量检索通过。未重建或清空命名数据库卷。

部署主机仅SSH公开，应用/DB绑定127.0.0.1。访问方式：`ssh -N -L 18081:127.0.0.1:8000 xyhleo-server`，浏览器打开http://127.0.0.1:18081。云资源已真实部署，但服务器LLM尚未完成：无凭据curl直连api.openai.com:443重复超时（8秒连接上限），不能判断为Key错误。用户需确定服务器可用的合规Provider连接方式，再在服务器/opt/meeting-assistant/.env设置三项LLM变量；不在聊天提交密钥。没有将本机Key复制到服务器或绕过服务访问限制。

当前源代码部署来自已验证Git main归档，不是服务器持有GitHub凭据直接clone。更新需重新传输受审提交/镜像；没有伪造远程clone。compose.cloud.yml记录实际低内存参数。合成验证账户/会议保留用于重启证据，凭据仅服务器/root/.meeting-probe.json（600），不进Git。
