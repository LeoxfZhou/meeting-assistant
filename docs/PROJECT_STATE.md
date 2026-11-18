# 项目状态

最后核验：2026-11-18（北京时间）。阶段：P0 已完成，本轮方向调整及文档完成，Batch 1 未开始。

## 实际文件与成果

本轮修改前共有 11 个文件（含 3 个 .DS_Store），10,334,399 bytes。完整业务文件如下：

- docs/project-plan/README.md、01-准备清单.md、02-项目介绍.md、03-项目思路与实施路线.md：旧路线历史方案，原地保留；不再作为当前执行入口。
- scripts/audit_alimeeting4mug.py：唯一 Python 脚本，标准库数据审计。
- data/raw/cccdbe6d-87c3-4314-908e-f735073412a9.zip：10,180,149 bytes，只读。
- outputs/audits/data_audit.md 与 meeting_inventory.csv：P0 报告、442 场会议清单。

没有根 README、app、tests、依赖配置、数据库模型、迁移、Dockerfile、CI、训练代码或模型权重。data/processed 尚未建立。现有 README 仅位于 docs/project-plan/。

## 本轮验证

读取全部旧文档和审计脚本，重新解析全部原始数据（外层 ZIP → 三个 ZIP → Tab CSV → JSON），CRC 校验由脚本执行。用 --report/--inventory 指定系统临时目录，避免覆盖已有成果。重建报告与清单均和原文件逐字节一致。

原包 SHA-256：666899476df91a0791b3b5e83994463c2a40e83d6d02e2b50cf2d32a556fec70。

| split | 会议 | 句子 | Action IDs | 显式空标签会议 |
|---|---:|---:|---:|---:|
| Train | 295 | 213235 | 1014 | 67 |
| Dev | 65 | 45869 | 222 | 10 |
| Test1 | 82 | 43228 | 236 | 32 |
| 合计 | 442 | 302332 | 1472 | 109 |

未发现解析失败、未匹配行动 ID；这不代表语义标注完美。M3298/M8016 共享 40 个长句，SequenceMatcher 相似度 0.877，泄漏尚未处理。没有生成新的评估指标。

## 当前 API / 数据库 / 测试 / 环境

- API：无；FastAPI 尚未安装到项目环境或实现。
- 数据库：无业务 schema、Alembic migration 或已验证连接。
- 测试：无 pytest suite；本轮通过的是现有审计脚本的全量复现，不是后端测试。
- 默认 python3：3.9.10；uv 可用；PATH 未发现 python3.11/python3.12 或 psql。
- Docker CLI 可用，Compose v5.5.1；docker info 连接失败，用户 Docker socket 不存在，服务未证实启动。
- 未安装依赖、启动服务、调用付费 API 或访问网络。

## 旧路线处置

| 内容 | 处置 |
|---|---|
| 原始包、P0 脚本、报告、清单 | 完整保留，用于评估和数据工程证据 |
| 人工确认、证据定位、事务与幂等、未知日期处理 | 保留并作为主线业务规则 |
| QLoRA、Qwen 1.5B、训练窗口与 GPU 计划 | 降为 Optional，未发现对应实现，无需搬迁 |
| docs/project-plan/ 四份文档 | 逻辑归档，原地保留；本状态文档声明其已被 MASTER_GOAL 替代 |
| RAG/pgvector/Embedding、LangSmith、会议问答 | 暂不处理，不作为 MVP 前置 |
| 一个自由选工具 Agent、复杂状态和多张辅助表 | 改为受控 LangGraph + 三张业务表逐批实现 |
| GPU 部署、正式微调联调门槛 | 改为云 API + CPU Linux 应用部署 |

## Git 与公开准备

git rev-parse 返回 not a git repository（本目录及父级未识别 Git 仓库）。未初始化 Git；无 branch、tracked files、commit、remote；未提交更改状态不适用。没有 .gitignore。本轮未创建仓库、分支、提交或 Remote。

已对现有文本文件进行私钥头、常见 Key 和凭据赋值模式扫描，未发现命中；未发现 .env/私钥文件。这只是有限静态检查，不能替代首次提交的暂存区审查。

发布前需：
1. 增加 .gitignore/.dockerignore，排除 raw/processed、私密 outputs、.env（仅放行纯占位 .env.example）、私钥、DB 文件/卷、日志、缓存与模型权重。
2. 现有 data_audit.md 含 Train 原文，先保留本地；准备不含原文的公开摘要或先确认许可。不可直接 git add . 后推送。
3. 增加根 README 和 data/README.md，补实际来源/下载时间/版本及许可记录；许可未确认不阻塞合成样例后端开发。
4. 初始化本目录独立仓库，安全基线提交后进入 feature/backend-skeleton；发布前复核暂存文件、敏感模式和文件大小。
5. 用户确认 GitHub 账号、仓库名、公开性与 Remote；再建立真实 Issue/PR/CI，不补造历史。

## 下一 Batch：最小实现计划（待批准）

1. 独立 Python 3.11 环境与依赖锁定；建立根 README、data/README、忽略规则和仅占位的 .env.example。核验依赖兼容性后安装，不沿用默认 3.9 作为未经测试的主环境。
2. Git 安全初始化与 feature/backend-skeleton；GitHub 尚未批准时用本地任务清单，不伪装已创建 Issue/PR。
3. FastAPI 最小结构：app/main.py、config.py、db.py、models/meeting.py、schemas/meeting.py、api/meetings.py；单一同步 SQLAlchemy Session，避免无必要异步 DB 复杂度。
4. PostgreSQL 开发实例与首个 Alembic migration，仅 meetings 表。字段建议 UUID id、title、content、可空 meeting_date/timezone、created_at/updated_at。业务需要时再增加 source_hash/revision。
5. API：GET /health；POST/GET /meetings；GET/PATCH/DELETE /meetings/{id}；POST /meetings/upload 支持 UTF-8 TXT/MD、明确大小上限、空文本拒绝。删除在 Batch 1 无关联记录时实现；Batch 2 增加关联前明确禁止删除或软删除规则。
6. pytest：创建/列表/读取/更新/删除、404、空白/非法输入、上传大小和编码；用合成会议。以独立 PostgreSQL 测试库验证持久化、事务和 Alembic 空库 upgrade，不用 SQLite 通过冒充 PostgreSQL 验证。
7. 验收：新环境按 README 启动；迁移成功；CRUD 测试通过；更新状态、Code Map、问题记录，展示真实执行证据。无 Docker/PostgreSQL 时可推进代码但必须标明集成测试未验证。

为便于本地 PostgreSQL，可在 Batch 1 加仅 DB 的开发 Compose；完整应用镜像、生产 Compose 与服务器部署仍属于 Batch 6。Batch 1 不接 LLM、不实现 Task/LangGraph，不要求 API Key 或云服务器。

## 已知问题 / 人工事项 / 阻塞

真实问题见 issues_and_fixes.md。本轮无阻塞，已结束。下一阶段需要用户明确批准 Batch 1；真实 PostgreSQL 测试需可用数据库（建议用户启动 Docker Desktop）。后续人工确认数据来源、clean split 策略、云 API 与 GitHub 发布；API Key 不发聊天、不写文档。购买、SSH 登录、验证码、DNS 等到部署阶段处理。
