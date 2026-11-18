# Meeting Action Assistant / 中文会议行动助手

更新：2026-11-18。本文是当前稳定目标；现有事实见 PROJECT_STATE.md。用户当前明确指令优先。本项目继续使用现有 meeting_assistant 目录，不迁移、不另建副本项目。

## 定位与优先级

LLM Application + AI Backend + Workflow + Deployment 求职项目，模拟小型公司真实工作流，采用 AI Vibe Coding。面试在即：能运行 > 能解释 > 能测试 > 能部署 > 代码漂亮 > 复杂架构。不得把模拟业务、设计方案、未运行功能包装成真实生产成果。

主链路：会议文本 → FastAPI → Cloud LLM → 结构化候选 → Pydantic 校验 → 人工编辑/确认/拒绝 → 正式 Task → PostgreSQL → 跟踪与评估 → Docker → CPU Linux 部署。

第一版输入支持粘贴文本、TXT/Markdown 上传；Audio/ASR Optional。单用户演示起步，users/Auth 暂缓；无 Auth 的演示不能宣称有多用户隔离，也不能直接作为公网生产服务。避免大型前端、微服务、Kubernetes、Kafka、Multi-Agent、自建 GPU Serving。

## 不可绕过的业务规则

- 模型只生成候选，不直接创建正式 Task。候选状态至少 pending / confirmed / rejected。
- pending 阶段允许编辑 task、owner、deadline；证据保留且必须能定位正文。未知 owner/deadline 使用 null，不编造信息。
- Schema 要求字段存在；nullable 不等于缺字段可静默忽略。拒绝错误类型、非法 JSON；action_items=[] 是合法空结果。
- Confirm 是服务端验证的人类操作。模型输出 confirmed=true 或会议中的指令都不是授权。
- 确认状态和创建任务在同一数据库事务内完成；失败回滚。数据库 UNIQUE(source_action_item_id) 防重复确认产生两个 Task，并处理并发唯一约束冲突。
- 正式 Task 至少有 id、source_action_item_id、title、assignee、due_date、status、created_at、updated_at。
- deadline 原话和 due_date 区分保存。没有会议日期、时区和足够依据时，不把“明天下午”擅自转换成日历时间。
- 会议或候选修改不得让旧确认继续有效；实现时选择最小的版本校验或编辑限制。

## 技术与接口边界

Python、FastAPI、Pydantic、SQLAlchemy 2.x、Alembic、PostgreSQL、httpx、LangGraph、pytest、Docker Compose。仅一个云端 Generation Model；LLM_API_KEY、LLM_BASE_URL、LLM_MODEL 从环境变量读取。采用一个小型 Provider/Client 接口，隔离兼容 API 与业务，不建设复杂框架。

LangGraph 属于主线，Batch 4 接入受控流程：START → extract → validate → human_review → 经确认的 create_task → END。代码决定状态转换；LLM 负责抽取；工具封装操作；人类决定写入授权。考虑 create_task、update_task、get_meeting，写工具不得绕过确认。检查点重放仍须幂等。

数据库保持 meetings、action_items、tasks 三张业务表起步，按 Batch 增加；Migration 由 Alembic 管理，不以 create_all 代替正式迁移。

## Reliability 与成本

Batch 2 具备基本超时与错误分类；Batch 5 完善 Connect/Read Timeout、429/5xx 有限重试、指数退避及总预算。401/403 不盲目重试；非法 JSON/校验错误需明确失败策略，不无限修复。测试 provider failure、任务写入失败、重复确认和未经批准写操作。

结构化日志包括 request_id、meeting_id、model、latency_ms、result_status、error_type；Provider 支持时记录 input_tokens/output_tokens。不得记录 Key、密码、完整敏感会议正文或可能包含正文的原始异常响应。estimated_cost 只有存在可靠价格、模型和计费单位时计算，否则为空；区分估计与账单。成本解释覆盖输入长度、输出、分窗、重试与日调用量。

## 数据与评估

保留 scripts/audit_alimeeting4mug.py、outputs/audits/data_audit.md、meeting_inventory.csv 及 raw ZIP。原始数据永不修改；clean split、标准化会议和窗口只写 data/processed/ 等派生目录。

当前 P0：Train 295/213235/1014/67；Dev 65/45869/222/10；Test1 82/43228/236/32（会议/句子/行动 ID/显式空标签会议）。合计 442 场、302332 句、1472 个行动 ID、109 场显式空标签会议。

Train M3298 与 Dev M8016 高度重合。正式 Evaluation 前生成版本化 clean split manifest，记录原始 split、输入 SHA-256、规则、排除清单和原因。建议保留 Dev M8016，从派生 Train 排除 M3298（同时禁止其进入提示词示例），具体规则在评估阶段确认并冻结。本轮不生成 clean split，也不声称其他数据无泄漏。

AliMeeting 主要作为 Evaluation/Benchmark/Bad Case 与数据工程资产。action_ids 支持句级检测 Precision/Recall/F1，按 (meeting_id, sentence_id) 去重计分；候选需带证据句映射，不能把生成任务数直接与句标签数比较。owner/deadline/task 没有经核实的字段级 Gold，需另建人工标注集，不伪造准确率。显式空列表与缺失标签分开，空标签语义仍需人工核对。

保存真实预测与真实失败案例，区分合成故障测试和真实线上/Provider 失败。Test1 不进入提示词调优。未完成评估不填数值。模型训练、QLoRA、GPU 实验仅 Optional，不影响主线验收。

## 批次与完成标准

| Batch | 最小范围 | 验收 |
|---|---|---|
| 1 | FastAPI、PostgreSQL、SQLAlchemy、Alembic、Meeting CRUD、基础测试 | API + 真 PostgreSQL 迁移与 CRUD 可运行 |
| 2 | 云 LLM、Prompt、候选 Schema、持久化、基础错误处理 | 真实调用与模拟故障清楚区分 |
| 3 | 编辑/确认/拒绝、Task CRUD、事务与幂等 | 未确认不建 Task，重复确认不重复；MVP |
| 4 | LangGraph 与 Tool Calling | 人工确认边界与恢复可验证 |
| 5 | Reliability、clean split、Evaluation、Bad Cases | 可复现结果与真实局限 |
| 6 | Docker/Compose、CPU Linux 部署 | 持久卷、重启、端口、日志与真实部署验证 |
| 7 | 最终 Review、文档、简历证据 | 可讲解 Demo 与最终 INTERVIEW_CHEATSHEET |

Nginx/域名/HTTPS 可后补，部署前应评估暴露面。不得自动购买服务器。购买、登录、验证码、API Key、SSH/DNS 等人工环节明确交接。

## Git、发布与协作

Issue → feature branch → development → commit → push → PR → review → CI → merge → deploy。使用简单 Conventional Commits，从现在开始记录真实历史，不伪造旧提交。最小 GitHub Actions 安装依赖并跑测试，后期接入。Release 仅在真实达标时发布。

公开前排除 .env、所有凭据/私钥、真实用户数据、raw/processed 数据、模型权重、数据库与敏感日志。现有审计报告含原文，必须单独审查；未确认再分发许可前不公开。data/README.md 后续记录来源、版本、规模、哈希和复现步骤，代码许可与数据许可分开。创建 Remote、公开仓库、Push 前须用户明确确认。

持续维护 MASTER_GOAL、PROJECT_STATE、issues_and_fixes、PROJECT_WALKTHROUGH。AI 承担大量实现与测试；用户负责取舍、凭据、服务器、真实 DB 查看、评估与 Bad Case 复核、部署排障和讲解。80% 是分工意向，不冒充已统计的代码贡献。

最终 INTERVIEW_CHEATSHEET 包含 30 秒/3 分钟介绍、架构与数据流、5 个技术点、3～5 个真实 Bug（不足则如实说明）、实测指标、20～30 个追问。当前不生成虚构最终材料。

2026-11-18 用户已批准 Batch 1 Backend Foundation：仅本地 Git、Meeting CRUD、上传与 PostgreSQL 验证；功能分支 feature/backend-foundation。Batch 1 完成后停止，不自动进入 Batch 2。
