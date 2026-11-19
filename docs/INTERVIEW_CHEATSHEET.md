# 面试速查：中文会议行动助手

2026-11-19 / Feature frozen。项目是工程演示，不是高准确率生产系统；低分、失败、评测边界都要能解释。

## 30秒介绍

我做了中文会议行动助手，用FastAPI和PostgreSQL接收会议，通过云模型生成结构化候选，人工确认后才创建任务，并用事务和唯一约束防重复。还集成带权限的CPU E5+pgvector检索和LangGraph受控流程。完成82项测试、30场真实AliMeeting评测，以及阿里云Docker部署、持久化和重启验证；抽取仍有误报，评测结果如实保留。

## 3分钟介绍

业务模拟一家公司的会议跟进：会议人物可能没注册，截止时间可能模糊，AI不能替人批准。我把Meeting、Candidate、Task分开，名字和系统用户分开，日期原话和人工确定日期分开。

请求先经过FastAPI、JWT和权限检查，会议由SQLAlchemy写入PG，Alembic管理结构。长文本使用6000字符窗，模型输出经Pydantic严格校验。真实评测发现模型复述证据时会改写口语和换行，因此修复为编号行选择、服务器重建原文；越界仍拒绝，不用模糊匹配蒙混通过。

候选以pending持久化；用户编辑增加revision。确认时校验权限/版本/状态，在同一事务中创建Task，行锁和唯一约束防重复。LangGraph表达受控步骤与人工交接，工具写权限由服务端决定，不是自由Agent。

RAG来自12份原创虚构资料及授权历史会议，CPU E5产生384维向量，pgvector先权限过滤再TopK，答案引用回查片段。检索和生成分别评测：小型Synthetic集22个有答案题Hit@5为1、MRR约0.894，不能说企业RAG准确率100%。

AliMeeting审计442场，处理已知Train/Dev泄漏，开发诊断样本不进入最终30场。30场未用于调试的Test1；micro P=0.0479、R=0.4366、F1=0.0864（TP=31 / FP=616 / FN=40）。这说明工程链路完整并不代表模型质量已高；保留误报、漏报和失败，未伪造字段准确率。

基础设施在阿里云2核2GiBECS验证Docker、PG、卷和重启。真实Provider在Mac，大陆ECS不要求Generation；证据入GitHub后主动删除Demo及专属卷，保留服务器。82项测试，真实PR/CI；后续功能冻结，主要做讲解与坏例复核。

## Architecture / Main Data Flow

Meeting → FastAPI权限 → PG → 受控Graph → LLM/Pydantic/原文证据 → Candidate → Human Review → 事务+UNIQUE → Task。

Question → CPU query embedding → 授权pgvector TopK → Context → LLM → Citation/No-answer。

## 五个技术选择

1. 云API而非训练主线：优先交付和验证应用。
2. Pydantic+行号原文重建：结构与来源均有服务端约束。
3. 人工审核+事务/锁/UNIQUE：模型建议不能直接成为写授权。
4. LangGraph受控步骤+SQL人工状态：可解释、可重启，不自由操作DB。
5. pgvector同库权限过滤：小规模简单部署，先用真实评测解释边界。

## Real Metrics

30场未用于调试的Test1；micro P=0.0479、R=0.4366、F1=0.0864（TP=31 / FP=616 / FN=40）。这是小规模、分层平衡的诊断评测，不是总体效果估计。AliMeeting缺负责人/日期/标准任务文字Gold，不报告这些字段准确率。严格句级标注与模型行动范围有差异，误报和漏报均保留，不以工程完整性冒充高抽取质量。

Synthetic RAG：25题，22有答案、3无答案；Hit@5=1.0、Recall@5=1.0、MRR=0.893939。全25题Generation未运行；历史6题生成首轮5/6，无答案1/2，修复后该失败题单题通过。

82 pytest通过；最终评测75次HTTP尝试，2场失败；用量/重试详见evaluation/evidence，estimated_cost=null。

## 真实Bad Cases速查

下表保留ID，完整原文只在本地ignored报告；可能原因需人工复核。

| Meeting | Sentence | Type | Gold count | Predicted count |
|---|---:|---|---|---|
|M4285|304|false_positive|9|102|
|M4056|413|false_positive|4|64|
|M3291|3|false_positive|4|52|
|M3149|3|false_negative|13|41|
|M3181|93|false_negative|6|0|

不能断言所有FP都是幻觉：可能是证据范围过宽或标注口径差异；FN可能是隐含行动、跨窗上下文或整场失败。核心指标不通过人工模糊判定修改。

## 五个真实工程问题

- OpenAI旧max_tokens参数HTTP400：改默认max_completion_tokens，真实回归验证。
- RAG no_answer=true但answer为空：严格Schema拒绝，补充非空拒答提示，保留首轮失败。
- 口语证据改写：空白恢复不足，修复为行号定位和原文重建；开发/最终集隔离。
- ECS Docker Hub超时：本机官方来源构建amd64镜像，经SSH save/load，不用不明镜像站。
- 大陆ECS至Provider连接超时：不能误判Key/额度；按明确Scope在Mac验证AI，ECS验证基础设施。

## Deployment / Git

中国大陆阿里云ECS：Ubuntu24.04、2vCPU/2GiB、2GiB持久Swap，Docker/Compose、FastAPI/PG+pgvector healthy、迁移0004_knowledge、卷持久化及容器/整机重启恢复均已验证。云端Generation不在部署Scope；AI真实Provider在Mac验证。Demo已按授权永久下线，Docker/SSH/Swap及服务器保留。

真实GitHub分支/PR/CI/merge见GITHUB_WORKFLOW。云端删除前核对仅Demo，先保存证据；down保留卷、up恢复同一数据、down -v最终删卷；SSH/Docker/Swap仍保留。

## 30个高频追问

1. **为什么用API而不是自己训练？** 目标是应用交付与可解释的工作流；单一云Generation减少训练/算力负担，AliMeeting用于评测，QLoRA不在本轮。

2. **为什么需要Pydantic？** JSON能解析不代表业务可用；strict类型、必需字段、extra=forbid和范围校验形成服务端契约。

3. **Human-in-the-loop为什么存在？** 模型可能误读承诺或负责人；pending是建议，认证用户明确审核后才形成正式Task。

4. **怎么防重复Task？** 同一事务更新候选并写任务，行锁串行化竞争，UNIQUE(source_action_item_id)作最后防线，重复确认返回同一Task。

5. **创建Task失败会怎样？** 事务回滚，不留下confirmed但无Task；注入数据库失败测试覆盖该路径。

6. **旧页面确认如何处理？** revision过期返回409，用户刷新重新审核；已确认的幂等重试返回原任务。

7. **会议人物没有账号怎么办？** 保留assignee_name，assignee_user_id可空；人工绑定，不按同名自动推断系统用户。

8. **明天下午如何转换日期？** 保留due_date_text，具体日历due_date由人工设定，模型不猜参考日期。

9. **LangGraph为什么需要？** 明确读取、LLM、校验、可选检索、保存和人工边界的顺序，避免自由Agent自行写数据库。

10. **用了原生interrupt吗？** 没有，pending保存在SQL；抽取Graph结束，人工确认请求运行独立Graph，进程重启后可恢复业务状态。

11. **Tool Calling是模型选工具吗？** 不是。当前确定性流程调用Schema工具；写授权来自认证人工上下文，不接受模型提供human_approved。

12. **RAG数据从哪来？** 12份原创虚构公司资料和用户授权历史会议；评测有3场Synthetic历史会议。AliMeeting不进入RAG索引。

13. **为什么选pgvector？** 主库已有PostgreSQL，向量和权限可以同库联接，减少基础设施；当前小集精确cosine，不声称百万级性能。

14. **Embedding怎么运行？** 固定revision的multilingual E5 ONNX int8，CPU、384维、query/passage前缀、mean pooling与L2归一化。

15. **如何切块？** RAG文档按段落/标题、380字符兜底，会议按句界并有限重叠；抽取另用6000字符窗口/300重叠。

16. **如何避免越权检索？** Creator/Owner过滤在SQL ORDER/LIMIT之前；引用回查再次鉴权，Task分配不自动授予整场会议权限。

17. **Retrieval与Generation怎么区分故障？** 先查Gold来源是否进入TopK，再查答案/拒答/引用；检索成功不等于生成正确，分别报告指标。

18. **Hit@K、Recall@K和MRR是什么？** Hit看至少一个相关来源命中，Recall看Gold来源覆盖比例，MRR看首个相关片段倒数排名；无答案题不进入这三个分母。

19. **引用正确就一定答对吗？** 不一定。成员ID及原文quote校验只证明来源存在，语义蕴含仍需人工/独立评测。

20. **No-answer测到了什么？** 全25题未做生成；历史6题子集的2个无答案首轮1个成功，空拒答修复后单题通过，不能合并称总体100%。

21. **429怎么处理？** 有限指数退避，尊重Retry-After但单次等待封顶10秒；最多配置3次默认尝试。401/403/400不盲目重试。

22. **timeout和重试如何影响评测？** 真实超时耗尽后整场失败，按空预测保留FN；HTTP请求数含重试，未知费用不写零成本。

23. **为什么改成证据行号？** 真实口语文本的改写/换行让复制quote失败；模型选择起止行，服务器重建原文，越界拒绝。定位可靠仍不保证选中Gold行动句。

24. **AliMeeting怎么对齐评分？** 连续证据精确匹配所有出现位置，映射所有重叠句ID；按(会议ID,句ID)集合计算TP/FP/FN，不能靠模糊人工评分。

25. **AliMeeting Leakage怎么处理？** 已知Train M3298与Dev M8016近重复，派生排除Train项、保留Dev；原包不改。用于诊断的5场Test1也退出最终holdout。

26. **为什么不报告负责人或deadline准确率？** 原始action_ids没有可靠字段级Gold；只做定性复核，不伪造标注。

27. **服务器怎么部署，Volume如何保数据？** 受审main归档/官方镜像经SSH部署，Compose启动并迁移；PG数据在命名卷，restart/down不带-v后恢复均验证。down -v才永久删卷。

28. **为什么大陆服务器没跑OpenAI？** 实测443连接超时。当前Scope用Mac做真实AI验证，ECS做Linux/Docker/PG/持久化/重启验收，不绕过地区限制、不新增Provider。

29. **如果换Provider怎么改？** 已有客户端统一generate接口与env base URL/key/model，按兼容性设置token参数；更换必须真实验证，本次不增加新Provider。

30. **Git流程和项目收尾是什么？** 真实分支→push→PR→CI→merge；保留历史，不伪造PR。部署证据保存后按授权下线Demo，服务器保留，功能冻结。
