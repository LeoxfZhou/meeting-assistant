# 项目 Walkthrough（持续更新）

更新：2026-11-18。供后续项目教学和面试使用。当前仅 P0 审计真实实现；下述后端均是设计，不能作为完成能力描述。

## 1. Business Problem

会议中安排分散，用户需要带证据的候选事项，并控制是否进入正式任务。我们模拟单用户工作流，没有真实企业使用或上线收益数据。

## 2. Architecture

计划：FastAPI 接收会议 → httpx 云 LLM Client → Pydantic 校验 → PostgreSQL 候选 → Human Review → 事务创建 Task。LangGraph 在 Batch 4 编排这些服务。只有抽取步骤依赖模型，确认与数据库写入由代码控制。

## 3. End-to-End Data Flow

当前真实链路：只读原始 ZIP → 嵌套 ZIP → Tab CSV 的 content JSON → 字段/标签/重复审计 → Markdown + CSV。

目标链路：粘贴/上传文本 → 保存 Meeting → 抽取 task/owner/deadline/evidence → pending 候选 → 编辑/拒绝/确认 → confirmed 与 Task 同事务保存 → 跟踪状态。空结果是正常结果；抽取失败不得生成伪任务。

## 4. Code Map（现有真实代码）

当前只有 scripts/audit_alimeeting4mug.py，没有业务 class。

| 函数 | 实际职责 |
|---|---|
| main | 解析 archive/report/inventory 参数，协调审计和写出 |
| sha256_file / sha256_bytes | 文件与内容指纹 |
| inspect_archive | 检查双层 ZIP、CRC、分隔符与 JSON，汇总会议 |
| detect_table_delimiter | 从 idx/content 表头识别分隔符 |
| audit_record | 单会话字段、句子/行动 ID、缺失/null/空标签与 inventory |
| canonical_id | 统一数字 ID 表示，区别布尔等异常类型 |
| cross_split_overlaps | 会议 ID 和全文 hash 跨划分精确比较 |
| cross_split_long_sentence_pairs | 共享长句聚合成跨划分会议对 |
| example_markdown | 从 Train 选例生成原文窗口，公开时需审查 |
| render_report | 统计、重复风险、样例和局限说明 |
| percentile / distribution | 长度分布，不是 tokenizer 统计 |

输入：data/raw/cccdbe6d-87c3-4314-908e-f735073412a9.zip。
输出：outputs/audits/data_audit.md、meeting_inventory.csv。默认运行会重写派生报告；本轮使用 --report/--inventory 临时路径保留原件。后续每 Batch 在此补真实模块/class/function，不把计划路径列为已存在代码。

## 5. Database Schema

尚未实现。计划 meetings(id,title,content,meeting_date,timezone,created_at,updated_at)；action_items(id,meeting_id,task,owner,deadline,evidence,status,...)；tasks(id,source_action_item_id UNIQUE,title,assignee,due_date,status,created_at,updated_at)。保留外键和数据库唯一约束；users 暂缓。Batch 1 只建 meetings，Alembic 管理增量。

## 6. API Design

尚无 API。Batch 1 拟实现 /health、/meetings、/meetings/{id}、/meetings/upload。Batch 2 增加抽取和候选读取；Batch 3 加编辑/confirm/reject 和任务接口，具体契约随实现记录。

## 7. LLM Provider

尚未选定或调用真实 Provider。计划通过 LLM_API_KEY/LLM_BASE_URL/LLM_MODEL 配置一个 OpenAI-compatible client，由小接口隔离业务与 HTTP 协议。支持程度需要真实联调，不承诺所有兼容服务完全一致。

## 8. Structured Output

计划必填 task、owner、deadline、evidence，其中 owner/deadline 可 null。Pydantic 拒绝缺字段与错误类型，结构有效后仍要检查证据支持。JSON 合法不等于任务事实正确。缺 JSON、无效 JSON 与合法空数组分开处理。

## 9. Human-in-the-loop

pending 允许编辑；用户确认或拒绝；未经确认不能生成 Task。模型与会议文本无权批准自己。未知日期保持原话；确认时可由用户补充，不能伪称数据原本提供。

## 10. LangGraph

Batch 4 实现确定性抽取、校验、等待、分支和创建。使用 Workflow 是因为流程边界明确且写入需要人类授权；自由 Agent 不适合自行决定是否建任务。持久化和恢复必须用真实测试验证，不因使用框架就宣称可靠。

## 11. Tool Calling

计划 create_task、update_task、get_meeting。工具调用是受控函数入口，不能把模型参数当权限凭证。人类确认后的写工具与 API 共享业务服务，避免绕过状态检查。

## 12. Reliability

尚未实现。分层处理连接/读取超时、429/5xx 的有限退避、401/403 的立即失败、非法 JSON；request_id 串联日志，记录 model/meeting_id/latency/status/error_type/token，不记录完整会议和 Key。

## 13. Idempotency

尚未实现。核心是数据库 UNIQUE(source_action_item_id) + 确认与任务同事务，不仅在 Python 中先查再写。重复点击与并发请求、数据库失败回滚、Graph 重放均需测试；不宣称跨系统恰好一次。

## 14. Evaluation

现有证据是数据审计：442 场、302332 句、1472 个行动 ID、109 场显式空标签；不是模型效果。无 Precision/Recall/F1 实测。未来按句级证据 ID 评估检测，字段级需人工 Gold。先处理 M3298/M8016、冻结 clean split；不要在 Test1 调提示词。长会议需要覆盖策略，不得静默截断后报告全场 Recall。

## 15. Bad Cases

目前没有模型输出，也没有模型失败集。P0 已记录 Train M1989 的背景式正例、M0099 的含行动线索空标签，属于标注复核候选，不是已证实错标或模型 Bug。以后保存真实失败预测、配置、来源、原因和人工结论；公开版脱敏与许可审核。

## 16. Deployment

尚未部署。计划 CPU Linux + FastAPI + PostgreSQL + Docker Compose，练习 SSH、环境变量、持久卷、端口、日志、重启。Docker CLI 存在但 daemon 当前不可连接；无服务器购买、登录或部署记录。API Key 与账号操作由用户负责。

## 17. Issues & Fixes

见 issues_and_fixes.md：泄漏风险、旧文档过时、Docker 服务不可连接、报告原文发布风险。只记录真实现象；尚无应用 Bug 修复记录。

## 18. Git Workflow

当前非 Git 仓库；没有 commit/branch/PR/CI。Batch 1 建安全基线和 feature/backend-skeleton，远程操作待确认。面试只能展示从实施日起真实记录。

## 19. AI 与人工分工

本轮用户明确目标与约束；AI 读取全部项目文本、运行 P0 全量复核、检查本地环境和 Git、编写四份新文档。未实施后端。后续 AI 负责代码/测试/文档，用户负责凭据、真实部署、评估 Bad Case 复核与核心链路讲解，不声称用户手写了 AI 生成代码。

## 20. 当前可诚实使用的面试表达

“项目已完成中文会议数据审计，核验了 442 场会议并发现一对跨划分内容重合。现在以云 LLM 结构化抽取、人工确认和幂等任务创建为应用主线；后端与部署正在计划中。”

完成 Batch 3、真实评估和部署后再更新介绍。最终 Cheatsheet 在 Batch 7 编制，不提前填入不存在的效果、Bug 或上线成果。
