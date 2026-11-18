# 持续目标逐项验收

2026-11-18。按 MASTER_GOAL 0–59 核对。状态“本地通过”不代表真实云模型、GitHub或云部署通过。证据是实际文件/测试/报告，不是本清单自身。外部未验证项不标完成；整体 Goal 仍有人工事项。

| 编号 | 要求 | 当前证据与结论 |
|---|---|---|
| 0 | 原项目、先阅读 | 原目录开发，四份文档/README/代码/数据/git已检查；未创建副本 |
| 1 | 应用主线 | README/MASTER_GOAL；无训练依赖 |
| 2 | AI/人工分工 | Walkthrough26；API/账号/服务器与人工评估待用户 |
| 3 | 自主推进且不伪造 | 本地实现/73测试；无删失败测试，外部未测显式标注 |
| 4 | 人工检查点 | Key已配置并获限量调用授权；GitHub人工建库后已复用现有登录；服务器仍需人工 |
| 5 | 独立环境 | .venv Python3.13.9、pyproject/uv.lock，真实imports/pytest |
| 6 | P0保留/泄漏 | raw/audits/scripts保留；clean_split manifest已生成 |
| 7 | 基础验证/合并 | 537953e基础31测试后合main；后续提交可追踪 |
| 8 | 单公司多用户 | Auth/meeting/candidate/task/knowledge APIs；真实合成云抽取已通过 |
| 9 | 人物≠用户 | ActionItem/Task可空assignee_user_id；test_assignee_my_tasks |
| 10 | Auth | test_auth.py：注册/登录/hash/JWT/Owner/inactive |
| 11 | 会议权限 | access.py；test_meeting_authorization与历史检索权限 |
| 12 | 输入 | test_meetings.py：CRUD/TXT/MD/BOM/非法格式编码大小 |
| 13 | LLM Provider | llm/client.py，HTTPS环境变量，Mock验证；当前Provider真实小样本已验证 |
| 14 | 结构化候选 | extraction.py/graph.py/actions.py；证据校验、保存pending |
| 15 | 输出校验 | test_llm.py：JSON/字段/类型/空结果/timeout4295xx |
| 16 | 人工审核 | test_actions.py：edit/confirm/reject/revision |
| 17 | Task字段 | models/action_item.py与0003，状态todo/in_progress/done |
| 18 | 幂等 | UNIQUE+事务+锁；真实并发和rollback测试 |
| 19 | Task展示/API | tasks/my/get/patch；web任务表，未实现通知 |
| 20 | 双来源RAG | rag/service.py；公司与授权会议真实CPU/PG测试 |
| 21 | 合成资料 | data/company_docs/共12份原创Synthetic文件 |
| 22 | 历史会议 | index_meeting、来源FK、权限/失效测试 |
| 23 | AliMeeting隔离 | 公司固定目录/会议业务ID索引；评估独立库，无raw ingestion |
| 24 | pgvector | 0004迁移、Vector384、PG16+vector0.8.7真实运行 |
| 25 | CPU Embedding | embedding.py/固定revision/manifest，真实encode测试 |
| 26 | chunking | chunking.py，标题段落/句界380字符+60重叠，覆盖测试 |
| 27 | metadata | KnowledgeChunk含source属性、标题、正文、index、embedding、时间、offset |
| 28 | 检索 | retrieve SQL授权先于LIMIT，精确cosine，无额外检索框架 |
| 29 | 答案与引用 | answer.py严格schema/引用原文/来源，Mock；6题真实子集已运行，首轮5/6，失败修复单题通过 |
| 30 | RAG评估集 | evaluation/rag_questions.jsonl25题含3无答案，expected sources/points |
| 31 | RAG指标 | report Hit@5/Recall@5=1、MRR0.893939；完整集citation/refusal未测，6题子集见真实报告 |
| 32 | LangGraph | graph.py实际StateGraph，test_workflow主路径/失败/重启 |
| 33 | 条件RAG | 受控关键词判断、test_optional_knowledge_branch |
| 34 | 四工具 | tools.py schema+ToolContext，写操作人工授权；无自由模型执行 |
| 35 | 可靠性 | client有限重试/退避/RetryAfter/timeout，401403不重试测试 |
| 36 | 日志 | request_id/user/meeting/model/latency/usage/status/error；脱敏测试 |
| 37 | token/cost | 只接受真实usage，未知cost为空；无实际账单 |
| 38 | AliMeeting评估 | clean_split/evaluate_extraction；Dev65空基线实际运行，AliMeeting云效果本轮未运行 |
| 39 | 字段指标 | report明确无Gold，禁止伪造；人工抽样仍待用户 |
| 40 | pytest | 73 passed，真实PG+CPU；外部LLM Mock |
| 41 | Compose | API+PG，持久卷/healthcheck，compose_smoke真实重启通过 |
| 42 | Git工作流 | 基础/Auth/Task分支测试后合并；本轮功能完成后本地提交合并 |
| 43 | GitHub | Private origin已推送；API确认private=true；index/history扫描155 blobs通过 |
| 44 | CI | 首次远程Actions44308229328成功，73测试14.73秒；当前PR状态见GITHUB_WORKFLOW |
| 45 | 云部署 | DEPLOYMENT步骤已写；服务器/SSH待用户，未部署 |
| 46 | HTTPS | Optional，未执行，DNS/域名需人工 |
| 47 | 轻量UI | app/web/index.html，真实Chrome注册/会议/索引/检索验证 |
| 48 | 不做项 | 无通知/TTS/MultiAgent/Kafka/K8s/微服务/完整RBAC |
| 49 | ASR | Optional未做，无大型ASR模型 |
| 50 | outputs规范 | evaluations/checks分目录，全部忽略，未平铺 |
| 51 | 状态/问题/教学文档 | 三文件已更新，当前状态替代历史快照 |
| 52 | Walkthrough26项 | 文档26节与真实Code Map；生成/部署未验证明确标注 |
| 53 | 面试速查 | INTERVIEW_CHEATSHEET含30秒/3分钟/5重点/5真问题/指标/28问答 |
| 54 | 简历证据 | RESUME_EVIDENCE区分Implemented/Measured/Planned |
| 55 | 优先级 | 主线完成本地实现后才轻量UI，Optional未扩展 |
| 56 | 连续执行 | 从基础复验→Auth→候选Task→RAG→workflow→reliability→eval→Docker→docs |
| 57 | 本地成功门槛 | 代码/PG/CPU/Compose已验证；真实生成小样本已验，完整指标未验；不称整体Goal完成 |
| 58 | 停止边界 | 本地检查完成后转人工配置，无普通批次停止 |
| 59 | 报告 | PROJECT_STATE/RESUME_EVIDENCE涵盖21项；最终人工交接明确未完成部分 |

## 需要外部证据才能关闭的事项

真实Provider小样本抽取/问答与失败已验证；完整指标和人工字段复核仍待；GitHub已接入且CI通过，当前PR见GITHUB_WORKFLOW；Linux服务器部署与持久化验证。不能用Mock或本机Compose替代这些证据。
