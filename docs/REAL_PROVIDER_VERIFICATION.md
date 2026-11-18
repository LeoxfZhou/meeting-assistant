# 真实 Provider 验证：2026-11-18

本轮用户明确授权最多约20–30次请求，实际按20次累计上限执行，完成18次生成尝试。所有内容均为原创合成会议/公司资料，AliMeeting云调用为0。模型 gpt-6-luna，官方HTTPS Provider；密钥只来自被忽略的.env，不写入报告或日志。

## Real API Verified

- 首条成功Smoke：HTTP200，5196ms，输入139/输出108/合计247 tokens；结构化候选通过Pydantic，证据定位原文。
- 5类合成抽取5/5通过：单项、多项、无行动、缺负责人、缺日期。中文原文；未知字段null。结果逐条人工式代码审查，不计算大样本F1。
- 真实LLM→候选pending→API编辑/确认→Task通过；确认前tasks为空，重复确认同Task，My Tasks可见。
- 确认由用户授权的自动API测试执行，**不是用户本人UI点击**。隔离评估库结束后删除。
- RAG：真实CPU embedding + PostgreSQL pgvector Top5 + 合成上下文 + 云生成 + 引用回查。
- Docker重建加载当前.env，容器内真实云抽取、确认、重复确认通过；该请求HTTP200、3244ms、输入133/输出79/合计212 tokens；临时用户、会议、候选、任务已清理。

## Measured：保留首次失败，不用重试结果覆盖

6道RAG子集为q01/q02/q08/q20/q23/q24，覆盖事实、混淆、跨文档、历史会议和无答案。

- 首轮5/6通过。4个有答案问题都提供合法来源与原文引用，已核对预期答案点；这不是总体答案准确率。
- 首轮2个无答案问题中1个通过。q24 HTTP200但answer=""，触发Schema min_length校验。
- 同题诊断复查仍失败，保存了实际结构：no_answer=true、citations=[]、answer为空；不是无凭据/配额问题。
- 提示词补充“拒答也必须给出非空说明”；不放宽Schema、不自动把异常转为空成功。q24修复后复测1次通过。
- 没有重跑全6题修复后集合，不能宣称“修复后6/6”或“拒答准确率100%”。完整25题生成指标仍未测。

18次生成尝试：1次连接超时、1次HTTP400参数错误、16次HTTP200（其中2次无效结构）。Provider返回的合计用量为输入12363、输出1491、总计13854 tokens，包含结构失败的响应。无可靠定价，estimated_cost=null；这不是账单。

## 三个真实发现与修复

1. 观测工具自定义HTTPTransport最初绕过macOS系统代理而超时；默认httpx无凭据连通性探测收到401，说明网络可达。观测Transport显式遵循现有系统HTTPS代理，未关闭TLS。
2. 旧max_tokens参数被当前模型HTTP400拒绝。客户端默认改max_completion_tokens，可通过LLM_TOKEN_LIMIT_PARAMETER=max_tokens兼容旧服务；默认不发送temperature，必要时显式配置。依据Provider实际错误及[官方Chat Completions参数文档](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)。
3. RAG空拒答经严格Schema阻止；改prompt并添加回归，保持answer最短长度1。真实复测通过。

## Mock Tested / Real API Verified / Planned

- Mock Tested：timeout、429、5xx、401/403不重试、非法JSON/字段、空拒答拒绝、参数兼容；未人为消耗配额制造真实429。
- Real API Verified：上述小样本成功链路、400参数错误、空拒答失败、Docker出站生成。
- Measured：上述样本数、首次失败、tokens、延迟；73项pytest通过，22.98秒。alembic check无差异。
- Planned：完整AliMeeting模型P/R/F1、全25题RAG生成、用户UI人工审核与Bad Case抽查；GitHub/远程CI/云Linux部署仍未执行。

## 可复查文件与命令

本地报告在 outputs/evaluations/provider_round1/：summary.json、requests.json、extraction.json、workflow-rag.json、rag-recheck_before_prompt_fix.json、rag-recheck.json、docker.json。初始Smoke在outputs/checks/provider_round1/。输出全部被Git忽略，原始失败保留。

显式授权后才运行 `uv run python -m scripts.verify_real_provider --stage extraction`，再运行 `--stage workflow-rag`。默认复用该输出目录的持久请求账本，累计上限20；重复运行仍占预算。新一轮使用新--output目录并单独约定预算，不能删账本冒充本轮额度重置。此脚本不会被pytest自动运行。

观测脚本仅向真实Provider发送合成内容，少量脱敏模型响应保存在本地评估文件；生产日志不记录会议原文或模型正文。真实确认用API自动化验证与用户UI体验验收需要分别表述。
