# Resume Evidence — feature frozen

单公司内部系统模拟，非商业生产。AI协作实现；不伪造本人逐行手写、企业用户收益、吞吐或账单节省。

## Implemented

- FastAPI/SQLAlchemy2/Alembic/PostgreSQL六张业务表，JWT/Argon2和Creator/Owner权限。代码：app/api、models、core；测试：tests/test_auth.py、test_meetings.py。
- Structured LLM Output、编号行证据重建、有限纠正/重试；app/llm/extraction.py、client.py；tests/test_llm.py。
- Human Review、revision、事务/锁/UNIQUE幂等Task；app/services/actions.py；tests/test_actions.py。
- 受控LangGraph与确定性工具，SQL持久pending边界；app/workflow；tests/test_workflow.py。非原生interrupt/checkpointer、非自由Agent。
- CPU E5 384维+pgvector、权限先于TopK、引用回查；app/rag；tests/test_rag.py。
- Docker/Linux部署、持久化、重启和主动下线；Dockerfile/Compose及DEPLOYMENT。

## Measured

| 项目 | 真实结果 | 证据 |
|---|---|---|
| P0审计 | 442 / 302332 / 1472 / 109空标签 | evaluation/evidence/data_audit_public.md |
| clean split | Train294 / Dev65 / Test1 82 | scripts/clean_split.py与原包hash |
| pytest | 82 passed；真实PG/CPU，LLM错误路径Mock | tests与最终GitHub CI |
| Action extraction | 30场未用于调试的Test1；micro P=0.0479、R=0.4366、F1=0.0864（TP=31 / FP=616 / FN=40） | evaluation/evidence/action_item_metrics.json、action_item_sentence_results.jsonl |
| Synthetic RAG | 25题；22有答案Hit@5=1、Recall@5=1、MRR=0.893939 | evaluation/evidence/rag_retrieval.json |
| Synthetic Generation | 历史6题首轮5/6；无答案1/2，单题修复复测通过 | synthetic_provider_round1.json |
| 最终30场API用量 | 75次尝试；301895输入/78886输出 tokens | action_item_metrics.json；开发阶段另见run_accounting.json |
| 云端 | 基础部署、卷/重启/SSH Tunnel、主动下线 | cloud_validation.json、DEPLOYMENT |

这是小规模、分层平衡的诊断评测，不是总体效果估计。AliMeeting缺负责人/日期/标准任务文字Gold，不报告这些字段准确率。严格句级标注与模型行动范围有差异，误报和漏报均保留，不以工程完整性冒充高抽取质量。

## Planned / Optional

字段人工Ground Truth、独立企业数据、大规模/性能/费用评测、真人UI Demo与坏例抽查尚未完成；不影响本次功能冻结。ASR/TTS/QLoRA/Multi-Agent不实施，不增加Provider或公网入口。云端Generation是明确不在Scope，非待完成阻塞。

## 可用简历表达

“基于FastAPI/PostgreSQL构建中文会议行动助手，实现结构化LLM候选、人工审核及事务幂等任务创建；集成CPU multilingual E5+pgvector权限检索和LangGraph受控工作流，完成82项测试、30场AliMeeting句级评测与阿里云Docker部署/持久化/重启/下线验证。”

如引用RAG数字，必须加“小型自编Synthetic集22个有答案题”；引用抽取指标必须同时说明30场、句ID对齐和真实低分，不写成高准确率卖点。无可靠定价，estimated_cost=null。PR/CI证据见GITHUB_WORKFLOW。
