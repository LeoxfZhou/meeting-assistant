# 简历证据：Implemented / Measured / Planned

2026-11-18。本项目是单公司内部系统模拟，不是商业生产系统。AI 参与主要实现，用户负责取舍、真实外部服务与验收；不宣称全部代码手写。

## Implemented（可由代码与测试核对）

- FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL：用户、会议、候选、任务、企业文档、知识片段六表。
- JWT/Argon2id、Creator/Owner 权限；会议人物与系统用户分离。
- 结构化云 LLM 客户端、Pydantic 校验、证据定位、超时/有限退避/错误分类。外部成功行为目前由 Mock 测试。
- 人工编辑/确认/拒绝；revision、事务、行锁与 UNIQUE(source_action_item_id)；重复确认不新增任务。
- CPU multilingual E5 384维 + pgvector；12份原创合成公司文档、授权历史会议、可追溯引用。
- LangGraph 受控流程、四个 schema 工具；SQL 持久人工边界，不声称原生 interrupt 或自由 Agent。
- Docker Compose API/PG、轻量 UI、独立 PostgreSQL 测试库、评估与数据审计工具。

## Measured（实际证据）

| 内容 | 结果 | 本地证据与限制 |
|---|---|---|
| 数据规模 | 442会议 / 302332句 / 1472行动ID / 109空标签 | outputs/audits；原文报告不公开 |
| 派生划分 | Train294 / Dev65 / Test1 82 | data/processed/clean_split.json；raw hash保留 |
| 测试 | 最新71 passed / 15.62s | 当前完整 pytest；真实PG/CPU，外部LLM Mock |
| 抽取 | Dev65空预测基线 P/R/F1均0 | outputs/evaluations/extraction_empty_baseline/report.json；不是模型指标 |
| RAG检索 | Hit@5=1，Recall@5=1，MRR=0.893939 | outputs/evaluations/rag/report.json；22有答案题，自编小集 |
| RAG生成 | citation/no-answer accuracy=null | 无真实Key，不能填准确率 |
| 容器 | API/PG healthy；重启后审核状态保留 | outputs/checks/compose_smoke.json；合成候选fixture |
| 页面 | 注册/会议/索引/检索显示通过 | outputs/checks/ui_smoke.json与截图 |
| Git | 本地branch/commit/merge | git log；无远程PR/CI运行 |

## Planned / 需人工完成

真实云 Provider 兼容性、完整抽取/问答 Demo、真实模型 Bad Cases、字段人工评估、真实成本；GitHub Private repo/PR/CI；CPU Linux 部署/SSH/备份恢复验收。HTTPS、ASR、QLoRA为后续可选，不写成现有能力。

## 可用简历表述

“开发中文会议行动助手，基于 FastAPI/PostgreSQL 实现人工审核到任务创建的事务链路，以唯一约束保证重复确认幂等；构建带访问权限过滤的 CPU multilingual embedding + pgvector 检索与 LangGraph 受控工作流，完成71项测试和本地 Docker Compose 重启验证。”

如写 RAG 数值，必须附“小型自编合成集22个有答案问题”；不得单写“准确率100%”。不得声称生产部署、企业用户收益、真实模型抽取F1、远程CI通过或成本下降。API和实际class/function见 PROJECT_WALKTHROUGH，技术取舍见 INTERVIEW_CHEATSHEET。
