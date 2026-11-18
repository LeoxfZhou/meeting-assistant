# 项目当前状态

核验日期：2026-11-18。以当前持续目标及 MASTER_GOAL 为准，连续推进完整本地主线；旧 Batch 1 停止规则不再适用。主线为 LLM Application / AI Backend / RAG / Workflow / Deployment，训练和 ASR Optional。

## Git

本轮开发分支 `feature/real-provider-verification`，验收后本地合并到 `main` 交接。基础版 d753085 → e8ed364 → 537953e 已保留并合入 main；Auth f431b78、候选/任务 317248d 已测试后本地合入 main。RAG/工作流/本地部署已由5955295合入main，本轮修复真实Provider兼容性并更新验证证据，最终 hash 以 git log 为准。未配置 Remote、未 Push、未创建 PR。CI 配置已准备，未在 GitHub 执行。

## 已实现与边界

- 独立 Python 3.13.9 .venv，pyproject.toml + uv.lock。
- 注册/登录、Argon2id、JWT、Creator/Owner 授权；Owner 通过本地管理命令显式设置。
- Meeting CRUD、UTF-8 TXT/MD 上传；1MiB 文件、4MiB 请求体限制。
- HTTPS 兼容云 LLM Client、严格 JSON/Pydantic、证据定位、分窗、有限重试、错误分类。gpt-6-luna 已真实小样本验证；错误路径继续由 Mock 回归覆盖。
- pending/confirmed/rejected 人工审核、revision 冲突检查；同事务确认与建 Task，来源唯一约束；My Tasks 与状态更新。会议人物可不绑定系统账号。
- 12 份原创虚构公司文档、授权历史会议索引；本地 CPU multilingual E5 ONNX、pgvector 精确 cosine；SQL 授权先于 Top-K；引用回查与原文校验。
- LangGraph 确定流程，条件检索，SQL pending 状态跨请求/重启持久化；确认使用独立 graph。未使用原生 interrupt/checkpointer；工具不是自由模型 Agent。
- request_id、结构化日志、脱敏；真实 PostgreSQL 回归；轻量浏览器页面。

## 当前 API

- `/auth/register`、`/auth/login`、`/auth/me`、`/users`。
- `/meetings` CRUD、`/meetings/upload`。
- `/meetings/{id}/extract`、`/workflow`、`/candidates`；`/candidates/{id}` PATCH/confirm/reject。
- `/tasks`、`/tasks/my`、`/tasks/{id}` GET/PATCH。
- `/knowledge/company/ingest`、`/meetings/{id}/index`、`/knowledge/search`、`/knowledge/ask`、chunk/document 引用回查。
- `/workflow/tools` 只提供 schema；`/` 演示页面；`/health` liveness。

准确 HTTP 方法与完整路径见 README；业务接口要求 Bearer JWT。

## 数据库与迁移

PostgreSQL 16.16 + pgvector 0.8.7。业务表 users、meetings、action_items、tasks、company_documents、knowledge_chunks，加 alembic_version。0001_create_meetings → 0002_auth → 0003_actions_tasks → 0004_knowledge；当前实际 head 为 0004_knowledge。使用 Alembic 管理，不用 create_all。旧会议 creator 可空只为保留历史，仅 Owner 可访问。

## 实际验证

- 最新完整 pytest：**73 passed in 22.98s**；无跳过。DB 测试在本机随机独立 PostgreSQL 数据库迁移、运行、清理。包含并发确认、真实 commit、注入插入失败 rollback、权限、重启审核、真实 CPU 向量。
- `alembic check` 已通过；最新 `alembic current` 确认 0004_knowledge (head)。
- Compose API/PG 均 healthy，端口仅 127.0.0.1:8000 / 55432，PG 命名持久卷。
- `outputs/checks/compose_smoke.json`：真实注册、CRUD、TXT/MD、向量检索、容器重启持久化、重复确认同 Task、My Tasks。候选明确为合成 fixture，不冒充 LLM 输出。
- `outputs/checks/ui_smoke.json` 和截图：独立 Chrome profile 验证登录、创建会议、索引、检索显示；临时用户/会议已清理。

## Evaluation

- P0 原始 442 场 / 302332 句 / 1472 行动 IDs / 109 显式空标签保留；原包 SHA 666899476df91a0791b3b5e83994463c2a40e83d6d02e2b50cf2d32a556fec70。
- clean_split.py 派生 manifest 排除 Train M3298、保留 Dev M8016；294/65/82，raw 不变。其他近重复未穷尽。
- Dev65 全空基线 TP0/FP0/FN222，P/R/F1=0。仅验证评分链路；无真实云抽取效果。字段级 Gold 不足，不编造 assignee/deadline Accuracy。
- RAG 25 题、22 有答案、3 无答案、12 企业文档 + 3 合成会议：Hit@5=1、Recall@5=1、MRR=0.893939。4 个非首位命中排序弱项已保存，Top5 均覆盖。
- 完整25题生成指标仍未测。6题真实子集首轮5/6通过，有答案4/4引用有效，无答案1/2通过；空拒答修复后单题复测通过，未重跑全子集。自编小集不代表企业独立效果。

## 人工阻塞与下一步

1. LLM配置与本轮有限调用已完成；用户可在UI真实审核，并抽查本轮Bad Cases。后续更大规模评测需另定预算。
2. GitHub 登录与仓库选择/可见性确认；之后建立真实 Remote/PR/CI。默认建议 Private，未自动创建。
3. 用户自行准备 CPU Linux Server 和 SSH；之后实际部署、日志、重启、持久化验证。当前没有云部署证据。DNS/HTTPS Optional。

所有 Secret、原始/派生数据、outputs、models、.venv 均忽略。P0 含原文报告保留本地，不能默认公开；公开前仍需数据许可、个人信息与代码许可证确认。

已知限制：无生产级入口限流/刷新令牌/密码找回；长窗按证据去重可能合并同证据不同任务；引用存在不等于语义蕴含；当前Provider小样本兼容性已验证；完整生成指标和真实成本仍未验证。没有线上业务收益或性能规模主张。

交接入口：PROJECT_WALKTHROUGH、INTERVIEW_CHEATSHEET、RESUME_EVIDENCE、GOAL_CHECKLIST、DEPLOYMENT。历史问题在 issues_and_fixes，历史批次快照可从 Git 查询。

## 最终本地交接复核

迁移检查无差异；Compose冒烟再次通过且临时记录清理；8项原始ZIP/P0脚本/报告/清单/旧规划SHA与接手前一致。index/history扫描140个不同blob未发现禁止路径、大文件、已知本地Secret或凭据模式。该段扫描为上一轮本地交接记录；本轮真实云验证结果如下。

## 本轮真实云验证

18次生成尝试，16次HTTP200、1次HTTP400、1次连接超时；输入12363/输出1491/总计13854 tokens，cost=null。Smoke+5类抽取通过；真实候选→自动化API确认→Task/幂等通过；Docker真实出站通过且临时记录清理。不是用户本人UI点击。真实失败包括旧参数不兼容和空拒答Schema错误，已修复并保留原记录。没有AliMeeting云调用。详细界限见 REAL_PROVIDER_VERIFICATION.md。
