# PROJECT STATE

Status: Interview-ready / Feature frozen（工程演示；抽取质量有明显局限）

日期：2026-11-19。最终本地主线与评测完成；仅Bug/Security/Documentation Fix，不新增功能。封版分支docs/finalize-interview-demo；通过真实PR #3交付，最终main/CI/merge证据见GITHUB_WORKFLOW及PR记录。

## Completed / evidence

- Core implementation：Auth、Meeting/TXT/MD、LLM结构化候选、Review、幂等Task/MyTasks、CPU RAG、受控LangGraph、轻量页面。
- Local Real API Verified：历史5类合成抽取及真实API确认→Task；最终30场AliMeeting，30场未用于调试的Test1；micro P=0.0479、R=0.4366、F1=0.0864（TP=31 / FP=616 / FN=40）。
- Synthetic RAG：Synthetic RAG：25题，22有答案、3无答案；Hit@5=1.0、Recall@5=1.0、MRR=0.893939。全25题Generation未运行；历史6题生成首轮5/6，无答案1/2，修复后该失败题单题通过。
- Tests：82 passed；真实PostgreSQL，不使用SQLite代替；外部错误行为Mock。
- Migration：0001→0004_knowledge(head)；users/meetings/action_items/tasks/company_documents/knowledge_chunks。
- Cloud infrastructure deployment validation complete；cloud demo intentionally decommissioned；server retained for future personal projects。中国大陆阿里云ECS：Ubuntu24.04、2vCPU/2GiB、2GiB持久Swap，Docker/Compose、FastAPI/PG+pgvector healthy、迁移0004_knowledge、卷持久化及容器/整机重启恢复均已验证。云端Generation不在部署Scope；AI真实Provider在Mac验证。Demo已按授权永久下线，Docker/SSH/Swap及服务器保留。
- P0 raw与原报告不变；最终原包hash和inventory复现一致。

## Current API

Auth/register/login/me/users；Meeting CRUD/TXT/MD；meetings/{id}/extract与workflow；candidates编辑/confirm/reject；tasks/my与状态；knowledge/company/ingest、meeting index、knowledge/search/ask、引用回查。详见README。

## Known limits / public blockers

这是小规模、分层平衡的诊断评测，不是总体效果估计。AliMeeting缺负责人/日期/标准任务文字Gold，不报告这些字段准确率。严格句级标注与模型行动范围有差异，误报和漏报均保留，不以工程完整性冒充高抽取质量。 RAG自编小集；无全25题Generation指标。云端Generation明确排除，不再等待云端OpenAI。无生产级入口限流/刷新令牌/密码找回。服务器上已没有Meeting Assistant服务；本机可启动Demo。

Private仓库不自动转Public。Dataset redistribution license requires manual verification before repository is made public. 原文预测/坏例及原P0报告仅本地ignored；需人工确认数据来源/许可、个人元数据。安全扫描不保证检测所有未知Secret。

## Final artifacts

README；PROJECT_WALKTHROUGH；INTERVIEW_CHEATSHEET；RESUME_EVIDENCE；DEPLOYMENT；issues_and_fixes；evaluation/evidence；本地outputs/evaluations/action_item_*。

下一步仅用户讲解练习、坏例人工复核和可选公开审核。没有下一功能Batch。

## Public release audit

Original code now MIT (2026 LeoxfZhou); current/history checks and minimal fixes recorded in [PUBLIC_RELEASE_AUDIT.md](PUBLIC_RELEASE_AUDIT.md). DATASET_LICENSE_VERIFIED=NO; repository remains Private. Non-secret historical development paths do not justify automatic history rewriting.
