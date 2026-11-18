# Meeting Action Assistant — MASTER GOAL

## 0. 项目位置

继续开发现有项目，不创建 V2 或副本：

`/Users/leozhou/Desktop/ShenLanEdu/NLP_Project/meeting_assistant/`

开始工作前必须阅读并理解现有项目：

- `docs/MASTER_GOAL.md`
- `docs/PROJECT_STATE.md`
- `docs/PROJECT_WALKTHROUGH.md`
- `docs/issues_and_fixes.md`
- 根目录 `README.md`
- 当前 Git log / status / branch
- 当前 `app/`
- 当前 `tests/`
- 当前 `migrations/`
- 当前数据审计成果

如果本 Goal 与旧 `MASTER_GOAL.md` 冲突，以本 Goal 为最新版本，并更新项目内 `docs/MASTER_GOAL.md`。

---

# 1. 项目定位

项目名称：

**Meeting Action Assistant / 中文会议行动助手**

这是一个用于求职的：

**LLM Application + AI Backend + RAG + Agent Workflow + Deployment**

项目。

目标岗位：

- 大模型应用工程师
- AI Backend Engineer
- RAG Engineer
- Agent / Workflow Engineer

项目目标不是研究新模型，也不是以模型训练为核心。

QLoRA、小模型微调、本地 GPU 推理：

**Optional**

不得阻塞主线。

---

# 2. 开发方式：Autonomous Vibe Coding

用户面试在即，开发速度优先。

Codex 可以承担大部分：

- Coding
- CRUD
- Database Models
- Migration
- Tests
- Refactor
- RAG Pipeline
- LangGraph
- Docker
- Documentation
- Evaluation Scripts
- Git operations
- Boilerplate

用户主要亲自处理：

- API Key
- GitHub 登录 / OAuth
- 云服务器购买
- SSH
- DNS / 域名
- 系统密码
- 权限弹窗
- 真实线上部署操作
- Evaluation 人工抽查
- Bad Case Review
- 最终 Demo

原则：

**AI 可以写大部分代码，但用户最终必须能解释完整核心链路。**

---

# 3. Autonomous Execution Rule

不要按 Batch 停止等待确认。

只要任务：

- 本地可逆
- 不涉及付款
- 不需要用户账号登录
- 不需要验证码
- 不需要真实 Secret
- 不涉及破坏用户重要数据
- 可以通过测试自动验证

则自主继续推进。

普通问题例如：

- pytest failure
- Pydantic error
- SQLAlchemy error
- Alembic migration error
- Docker Compose 配置错误
- dependency conflict
- type error
- formatting issue
- code bug

应自行：

inspect
→ diagnose
→ patch
→ rerun
→ verify

不要每遇到普通 Bug 就询问用户。

禁止为了通过而：

- 删除失败测试
- 跳过测试
- 使用 `except Exception: pass`
- 静默吞错
- 伪造运行结果
- 伪造 API 成功
- 伪造 Evaluation
- 伪造 Deployment

---

# 4. Human Intervention Checkpoint

只有真正必须人工介入时才停止。

例如：

- 缺真实 LLM API Key
- Docker Desktop 未启动且无法自行启动
- GitHub 登录 / OAuth
- 验证码
- 购买云服务器
- SSH credential
- DNS
- 域名
- 系统密码
- macOS 权限弹窗
- 付费操作
- 高风险不可逆外部操作

停止时统一输出：

# HUMAN ACTION REQUIRED

并一次性说明：

1. 为什么必须人工
2. 用户需要做什么
3. 具体步骤
4. 成功后应该看到什么
5. 用户完成后回复什么
6. 当前项目已经做到哪里
7. 哪些任务仍被阻塞
8. 是否还有不依赖人工的工作已经全部完成

尽量把人工事项合并，避免频繁打断用户。

---

# 5. Python Environment

项目必须使用独立 Python Environment。

首先检查当前项目是否已有明确属于本项目且可复现的环境。

如果没有：

在项目根目录创建：

`.venv/`

优先使用标准 Python `venv`，不要依赖用户全局 Conda 环境。

要求：

- `.venv/` 加入 `.gitignore`
- 不提交虚拟环境
- 使用一个明确依赖管理方案
- 不维护相互冲突的多份依赖清单
- 记录实际 Python Version
- 安装依赖后真实运行 import / pytest

如果创建 `.venv` 不需要人工权限：

自动完成，不要停止询问用户。

---

# 6. 当前已有成果

P0 数据审计已经完成。

AliMeeting4MUG 当前已确认：

- Train：295 场会议
- Dev：65 场会议
- Test1：82 场会议
- 总计：442 场会议
- 总句子：302,332
- Action Item IDs：1,472
- 显式空标签会议：109

已有资产必须保留：

- 原始 ZIP
- `scripts/audit_alimeeting4mug.py`
- `outputs/audits/data_audit.md`
- `outputs/audits/meeting_inventory.csv`
- 旧规划和历史材料

原始数据不得修改。

P0 发现：

Train `M3298`
与
Dev `M8016`

存在高度相似内容，是潜在 Train/Dev Leakage。

后续必须建立派生 Clean Split。

只能写入：

`data/processed/`

不得修改 `data/raw/`。

---

# 7. 当前 Backend Foundation

此前 Backend Foundation 已完成并验证：

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Meeting CRUD
- TXT / Markdown Upload
- pytest
- 真实 PostgreSQL Integration Tests

此前测试：

31 passed

当前 Git branch：

`feature/backend-foundation`

历史 Commit 包括：

- `d753085` — `chore: initialize project repository`
- `e8ed364` — `feat: add PostgreSQL meeting backend foundation`
- `537953e` — `test: verify PostgreSQL APIs and document backend workflow`

开始后首先：

- 检查 Git status
- 检查 current branch
- 重新运行测试
- 检查 PostgreSQL
- 检查 Migration

如果真实通过：

合理完成本地 merge 到 main。

如果没有 GitHub Remote：

不要伪造 Pull Request。

之后继续正常 Feature Branch 开发。

---

# 8. 最终业务模型

系统模拟：

**一家公司的内部会议行动管理系统。**

采用：

**单公司、多用户**

用户可以：

- 注册
- 登录
- 创建 Meeting
- 上传会议文本
- AI 提取 Action Items
- 人工 Review
- Confirm / Edit / Reject
- Confirm 后创建正式 Task
- 查看 Task Table
- 查看 My Tasks
- 查询企业知识
- 查询历史会议知识

当前不做通知系统。

---

# 9. 系统用户与会议人物必须区分

会议里出现：

“小张周五前完成接口测试。”

并不意味着“小张”已经注册。

LLM 首先提取：

```json
{
  "task": "完成接口测试",
  "assignee_name": "小张",
  "deadline": "周五",
  "evidence": "小张周五前完成接口测试"
}
```

允许：

`assignee_user_id = null`

人工 Review 时：

如果能够匹配系统 User，可以绑定：

`assignee_user_id`

否则继续保留：

`assignee_name`

不要强制会议中的每个人必须先注册。

---

# 10. Authentication / User

实现基础 User System：

- Register
- Login
- Password Hashing
- JWT Authentication
- Current User
- Basic Authorization

保持简单。

不做：

- OAuth
- 邮箱验证码
- 手机验证码
- 找回密码
- Complex RBAC
- 多租户 SaaS

User 至少考虑：

- id
- email
- display_name
- password_hash
- is_active
- basic role / is_owner（如必要）
- created_at

严禁明文密码。

---

# 11. Meeting 权限

Meeting 至少有：

`creator_user_id`

第一版权限：

- Creator 可以访问
- Owner 可以访问全部
- 如果 Participant Relation 实现简单，可以加入 Participant

Historical Meeting RAG 必须遵守同样权限。

禁止通过 Vector Search 绕过正常 Authorization。

---

# 12. Meeting Input

主线支持：

- 直接提交 Meeting Text
- TXT
- Markdown

当前不做：

- PDF
- Audio
- Video

Audio / Whisper 后续 Optional。

---

# 13. LLM Provider

第一版使用 Cloud LLM API。

优先：

OpenAI-compatible API

从环境变量读取：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

真实 Secret：

- 不写进代码
- 不进 Git
- 不打印日志
- 不写 README

如果当前没有真实 API Key：

不要立即停止。

先完成所有不依赖真实 LLM 调用的部分：

- Auth
- Models
- Candidate
- Task
- LLM Client interface
- Mock tests
- RAG
- pgvector
- Company Docs
- LangGraph structure
- Docker
- Evaluation infrastructure
- Documentation

只有当所有不依赖 Key 的工作都已推进完，才统一请求用户配置 API Key。

---

# 14. Structured Action Extraction

Meeting Text：

→ Cloud LLM
→ Structured JSON
→ Pydantic Validation
→ Action Item Candidates

Action Item 至少考虑：

- task
- assignee_name
- assignee_user_id nullable
- deadline / due_date_text
- evidence
- meeting_id
- optional confidence

LLM 输出不能直接成为正式 Task。

---

# 15. LLM Output Validation

必须处理：

- invalid JSON
- missing field
- wrong type
- empty result
- malformed structured output
- timeout
- 429
- 5xx

使用 Pydantic。

不要直接相信模型输出。

---

# 16. Human-in-the-loop

Action Item Candidate 状态至少：

- pending
- confirmed
- rejected

用户可以：

- 查看
- 编辑
- Confirm
- Reject

只有 confirmed Candidate 才能创建正式 Task。

这是核心业务规则。

---

# 17. Task System

正式 Task 至少包含：

- id
- source_action_item_id
- source_meeting_id
- title
- assignee_name
- assignee_user_id nullable
- due_date / due_date_text
- status
- created_at
- updated_at

Status 保持简单：

- todo
- in_progress
- done

---

# 18. Idempotency

同一个 Action Item 重复 Confirm：

不能创建两个 Task。

优先：

数据库唯一约束：

`UNIQUE(source_action_item_id)`

配合：

Transaction + Business Validation

必须有测试。

---

# 19. Task API / 最终展示

至少支持：

- Task List
- My Tasks
- Get Task
- Update Task

最终业务展示类似：

| Assignee | Task | Due Date | Status | Source Meeting |

不是简单输出 metadata。

未绑定 User：

仍然展示 `assignee_name`。

当前不做 CSV Export，除非实现成本极低且主线已完成。

---

# 20. RAG 为 Must Have

RAG 不再是 Optional。

必须做。

RAG 有两个正式数据来源：

## A. Company Knowledge

企业制度、SOP、Project Docs 等。

## B. Historical Meetings

真实系统中积累的历史 Meeting。

---

# 21. Synthetic Company Knowledge

创建：

`data/company_docs/`

生成约：

10～15 个原创 Synthetic Documents。

不得复制真实公司内部文档。

可以包含：

- HR Policy
- Travel Expense
- Remote Work
- Engineering Release Process
- Code Review Policy
- Incident Response
- Deployment SOP
- Meeting Follow-up SOP
- Escalation Policy
- Project Alpha
- Project Beta
- Customer Requirements

需要足够真实。

合理加入：

- 相似概念
- 相似数字
- Cross-document reference
- No-answer
- 少量 Version / Effective Date

GitHub 中必须标明：

Synthetic / Fictional Dataset

---

# 22. Historical Meeting RAG

用户创建的 Meeting：

同时可以用于：

A.

Action Extraction

B.

RAG Index

流程：

Meeting
→ Chunk
→ Embedding
→ pgvector

以后可以回答：

- 上次 Project Alpha 什么时候决定延期？
- 最近几次会议里讨论过哪些上线风险？
- 张三过去负责过哪些事项？

Historical Meeting Citation 必须定位回原 Meeting。

---

# 23. AliMeeting 与 RAG 必须隔离

AliMeeting 主要用于：

Action Extraction Evaluation。

不要把 Evaluation/Test Meetings 随便索引进入 RAG。

禁止：

Evaluation Data
→ RAG
→ 再拿同一数据做评测

避免数据泄漏。

---

# 24. Vector Database

因为项目已经使用 PostgreSQL：

正式 RAG 使用：

**PostgreSQL + pgvector**

不要新增：

- Milvus
- Chroma
- Weaviate
- Pinecone

除非未来有明确需求。

---

# 25. Embedding

选择轻量、低成本、本地 CPU 可运行的 Embedding Model。

因为存在中文会议和企业资料：

优先选择支持中文/英文的 multilingual embedding model。

记录：

- model name
- embedding dimension
- normalization
- query/document prefix requirement

如模型要求：

`query:`

和：

`passage:`

必须正确使用。

Embedding Model 为系统固定配置。

---

# 26. Chunking

Company Documents：

优先：

- Markdown heading
- paragraph-aware
- simple size fallback

Historical Meetings：

优先：

- sentence group
- speaker segment
- limited overlap

不要上复杂 Semantic Chunking Framework。

需要文档化 Chunking 决策。

---

# 27. RAG Metadata

Chunk 至少保存：

- id
- source_type
- source_id
- source_title
- content
- chunk_index
- embedding
- created_at

source_type 至少：

- company_document
- meeting

Meeting Chunk 必须关联 Meeting ID。

---

# 28. Retrieval

第一版：

Question
→ Query Embedding
→ pgvector Similarity Search
→ Authorization Filter
→ Top-K
→ Context

不要主线加入：

- Hybrid Search
- BM25
- Reranker
- Query Rewrite
- HyDE
- GraphRAG

这些以后 Optional。

---

# 29. RAG Answer

Prompt 要求：

- 只根据 Retrieved Context
- Context 不足明确拒答
- 返回 Citation
- 不伪造来源

Response 类似：

```json
{
  "answer": "...",
  "sources": [
    {
      "source_type": "meeting",
      "source_title": "...",
      "source_id": "...",
      "chunk_id": "..."
    }
  ]
}
```

---

# 30. RAG Evaluation Dataset

创建：

`evaluation/rag_questions.jsonl`

约：

20～30 Questions。

覆盖：

- factual
- cross-document
- confusing facts
- historical meeting
- no-answer

Ground Truth 至少：

- expected answer points
- expected sources

不得伪造结果。

---

# 31. RAG Metrics

至少：

- Hit@K 或 Recall@K
- MRR（若实现成本合理）
- Citation / Source Accuracy
- No-answer Behavior

不需要为了项目强行引入完整 RAGAS。

---

# 32. LangGraph 为 Must Have

使用 LangGraph 实现：

**受控 Workflow**

不是自由 Multi-Agent。

Workflow 可包括：

START
→ load meeting
→ extract action items
→ validate
→ optionally retrieve knowledge
→ save candidates
→ human review
→ confirmed?
→ create task
→ END

不要把普通 CRUD 强行包装成 LangGraph Node。

---

# 33. RAG 与 LangGraph

RAG 不必每个 Meeting 都执行。

例如：

“小张周五完成测试。”

不需要 RAG。

如果会议提到：

“按照公司的 P1 Incident Process 执行。”

则可以：

search_knowledge
→ RAG
→ Incident SOP
→ Context

是否调用 Retrieval：

采用简单、受控、可解释的判断。

不要无限循环 Agent。

---

# 34. Tool Calling

至少考虑 Tool：

- `search_knowledge`
- `get_meeting`
- `create_task`
- `update_task`

Tool 参数使用 Schema Validation。

写操作：

`create_task`

必须经过 Human Confirmation。

---

# 35. Reliability

必须考虑：

- Connect Timeout
- Read Timeout
- 429
- 5xx
- Invalid JSON
- Limited Retry
- Exponential Backoff
- Retry Limit

401 / 403：

通常不自动重试。

若 Provider 有 `Retry-After`：

合理使用。

---

# 36. Logging

实现简单 Structured Logging。

至少：

- request_id
- user_id
- meeting_id
- model
- latency_ms
- token usage
- status
- error_type

禁止记录：

- API Key
- Password
- 完整敏感 Meeting Text

当前不需要：

- ELK
- Grafana
- OpenTelemetry 全家桶

---

# 37. Token / Cost

如 Provider 返回：

- input_tokens
- output_tokens
- total_tokens

则记录。

只有 pricing 信息可靠时才计算：

estimated_cost

否则不要伪造成本。

---

# 38. AliMeeting Evaluation

建立可重复运行的 Action Item Evaluation。

至少：

- Precision
- Recall
- F1

正式评测前：

处理：

`M3298 / M8016`

潜在 Leakage。

Raw 不修改。

派生：

`data/processed/`

并记录：

- leakage evidence
- clean split policy
- reproducible script

---

# 39. Structured Field Evaluation

AliMeeting 原始 Action Item Ground Truth 主要基于 Action IDs。

如果原始数据不支持：

- assignee
- deadline
- structured task

完整 Ground Truth：

不得伪造 Accuracy。

这些字段可以：

- 人工抽样
- qualitative review

并在报告里明确限制。

---

# 40. pytest

至少覆盖：

## Auth

- register
- duplicate user
- login
- invalid login
- invalid JWT
- authorization

## Meeting

- CRUD
- upload
- permission

## LLM

- successful structured extraction
- invalid JSON
- timeout
- 429 / 5xx mock

## Candidate

- edit
- confirm
- reject

## Task

- create
- duplicate confirm
- my tasks

## RAG

- ingestion
- retrieval
- citation
- authorization
- no-answer

## Workflow

- main path
- failure path

Database Integration Tests：

继续使用真实 PostgreSQL。

External LLM：

允许 Mock。

---

# 41. Docker

最终 Local Compose 至少：

- FastAPI
- PostgreSQL + pgvector

PostgreSQL：

- Persistent Volume
- Healthcheck

不要默认加入：

- Redis
- Celery
- Kafka

---

# 42. Git Workflow

模拟真实团队流程。

主要 Feature 使用：

Issue / Feature Goal
→ Branch
→ Development
→ Tests
→ Commit
→ Push
→ PR
→ CI
→ Merge

如果当前没有 GitHub Remote：

先使用 Local Branch + Merge。

不要伪造 PR。

后续 GitHub 建立后切换真实 PR。

Commit 使用：

- feat:
- fix:
- test:
- docs:
- refactor:
- chore:

不要制造虚假历史。

---

# 43. GitHub

最终项目计划作为简历公开仓库。

但最初建议 Private。

创建 GitHub Repository / OAuth / 登录：

属于 Human Checkpoint。

未经用户确认：

不要设置 Public。

禁止提交：

- `.env`
- secrets
- raw dataset
- AliMeeting 原始 ZIP
- private user data
- DB volume
- SSH keys
- 含受限大量原文的文件

公开前必须：

- Secret Scan
- Large File Review
- Dataset License Review

---

# 44. CI

GitHub Remote 建立后：

最小 GitHub Actions：

Push / PR
→ install
→ pytest

不要复杂 CD。

---

# 45. Deployment

本地主线完成以后：

准备真实 CPU Linux Server Deployment。

因为 LLM 使用 Cloud API：

不需要 GPU。

部署目标：

- FastAPI
- PostgreSQL + pgvector
- Docker Compose

学习：

- SSH
- Linux
- .env
- Ports
- Volume
- Logs
- Restart

购买服务器属于 Human Checkpoint。

Codex 不得自动购买。

---

# 46. Nginx / HTTPS

服务器基础部署成功后：

如果时间允许：

- Nginx
- Reverse Proxy
- Domain
- HTTPS

涉及：

- Domain Purchase
- DNS
- Certificate Verification

则停止等待人工。

---

# 47. Frontend

非当前核心。

主线后端完成后，如果仍有时间：

做极轻量 UI：

- Login
- Meeting List
- Meeting Input
- Action Review
- Task Table
- My Tasks
- RAG QA

不要投入大量时间。

Streamlit / 简单 Web 即可。

React 非必须。

---

# 48. 明确不做

当前主线不做：

- Email Notification
- 飞书通知
- 企业微信通知
- Push Notification
- TTS
- Voice Clone
- Real-time Meeting
- Complex Multi-Agent
- Kafka
- Kubernetes
- Microservices
- Full RBAC

---

# 49. ASR / Whisper

Optional。

只有在：

- Backend 完成
- LLM 完成
- Task 完成
- RAG 完成
- LangGraph 完成
- Evaluation 完成
- Deployment 完成

以后仍有时间：

再考虑：

Audio
→ Whisper / ASR API
→ Transcript
→ Existing Pipeline

当前不下载大型 ASR 模型。

---

# 50. Outputs 目录规范

不要所有产物平铺。

正式评测：

`outputs/evaluations/`

临时检查：

`outputs/checks/`

旧版 / 废弃实验：

`outputs/archive/`

公开 Demo 证据可单独：

`outputs/demo/`

---

# 51. Documentation

持续真实更新：

## `docs/PROJECT_STATE.md`

包含：

- current branch
- implemented
- current APIs
- current DB tables
- migrations
- test count/results
- RAG status
- LangGraph status
- Docker status
- known issues
- human blockers
- remaining work

## `docs/issues_and_fixes.md`

只记录真实问题：

- Problem
- Symptom
- Root Cause
- Debug Process
- Fix
- Lesson

不得编造 Bug。

## `docs/PROJECT_WALKTHROUGH.md`

持续更新，不要项目结束后凭记忆写。

---

# 52. PROJECT_WALKTHROUGH 最终要求

该文档最终用于交给：

**C老师·项目实战指导**

让一个没有参与开发的人只看这份文档也可以完整教学。

必须包括：

1. Business Problem
2. Final Architecture
3. End-to-End Data Flow
4. Real Code Map
5. Database Schema
6. APIs
7. Authentication
8. LLM Provider
9. Prompt
10. Structured Output
11. Human-in-the-loop
12. Task System
13. Idempotency
14. RAG
15. Embedding
16. pgvector
17. LangGraph
18. Tool Calling
19. Reliability
20. Evaluation
21. Bad Cases
22. Docker
23. Server Deployment
24. Git Workflow
25. Issues & Fixes
26. AI vs Human Contribution

Code Map 必须精确到：

- file
- class
- function

---

# 53. Interview Cheatsheet

最终生成：

`docs/INTERVIEW_CHEATSHEET.md`

用于面试前快速复习。

包含：

- 30 秒项目介绍
- 3 分钟介绍
- Architecture
- Main Data Flow
- 5 个最重要工程点
- 3～5 个真实问题
- AliMeeting Metrics
- RAG Metrics
- Deployment
- 25～30 个高频项目追问 + 参考答案

---

# 54. Resume Evidence

最终生成：

`docs/RESUME_EVIDENCE.md`

必须严格区分：

- Implemented
- Measured
- Planned

记录：

- Dataset Scale
- APIs
- DB
- Tests
- Extraction Metrics
- RAG Metrics
- Deployment Evidence
- Technology Decisions

禁止将 Planned 写成 Implemented。

---

# 55. 当前优先级

面试在即。

严格按照：

1. Backend 基础验证
2. Auth
3. LLM Structured Extraction
4. Human Review
5. Task
6. RAG
7. LangGraph
8. Reliability
9. Evaluation
10. Docker
11. Cloud Deployment
12. GitHub / CI
13. Documentation
14. UI
15. Optional ASR / QLoRA / TTS

不要因为 Optional 拖延主线。

---

# 56. 当前开始执行

现在开始：

1. 阅读项目文件
2. 检查虚拟环境
3. 检查 Git
4. 重新运行现有 31 Tests
5. 检查 PostgreSQL / Migration
6. 完成 Backend Foundation merge
7. 自动继续 Auth
8. 自动继续 LLM Architecture
9. 自动继续 Candidate / Task
10. 自动继续 RAG / pgvector
11. 自动继续 LangGraph
12. 自动继续 Reliability
13. 自动继续 Evaluation
14. 自动继续 Docker
15. 自动继续 Documentation

不要因为一个模块完成就停。

如果缺真实 LLM API Key：

先把所有其他可做工作全部推进完。

如果缺 GitHub：

本地继续。

如果缺服务器：

本地全部完成以后再请求人工。

---

# 57. 最终本地主线成功标准

只有真实满足才能标记完成：

- User Register/Login 可运行
- JWT 可运行
- Meeting CRUD 可运行
- TXT/MD Upload 可运行
- LLM Client 已实现
- Structured Extraction 已真实或待 Key 最终验证
- Candidate Review 可运行
- Confirm → Task 可运行
- Duplicate Confirm 不重复创建 Task
- My Tasks 可运行
- Company Knowledge RAG 可运行
- Historical Meeting RAG 可运行
- pgvector 可运行
- Citation 可追踪
- LangGraph Workflow 可运行
- Reliability Tests 可运行
- AliMeeting Evaluation 可运行
- RAG Evaluation 可运行
- pytest 通过
- Docker Compose 可运行
- 无 Secret 泄漏
- Docs 与真实代码一致

---

# 58. 允许停止的情况

只允许三类停止：

## A. HUMAN ACTION REQUIRED

确实需要用户本人。

## B. 本地主线全部完成

输出完整报告。

## C. 发现严重安全 / 数据风险

继续可能造成不可逆问题。

普通开发阶段完成：

不得停止。

---

# 59. 最终报告

如果完成本地主线，只汇报真实结果：

1. Git branch / commits
2. Implemented Features
3. APIs
4. Database Schema
5. LLM Status
6. Candidate / Task Flow
7. RAG Architecture
8. Company Docs 数量
9. LangGraph Workflow
10. AliMeeting Evaluation
11. RAG Evaluation
12. pytest 数量 / 结果
13. Docker 状态
14. Real Issues / Fixes
15. GitHub 状态
16. Deployment 状态
17. Human Actions Remaining
18. Optional Remaining
19. `PROJECT_WALKTHROUGH.md`
20. `INTERVIEW_CHEATSHEET.md`
21. `RESUME_EVIDENCE.md`

绝对禁止伪造未完成或未运行的结果。

开始执行。