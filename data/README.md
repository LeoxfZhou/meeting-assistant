# 数据说明

AliMeeting4MUG 用于 Evaluation、Benchmark、Bad Case 分析及数据工程能力证明，不是本项目必须先完成的训练任务。原始数据默认不随仓库重新分发。

## 已审计规模

| 划分 | 会议 | 句子 | 行动 ID | 显式空标签会议 |
|---|---:|---:|---:|---:|
| Train | 295 | 213235 | 1014 | 67 |
| Dev | 65 | 45869 | 222 | 10 |
| Test1 | 82 | 43228 | 236 | 32 |
| 合计 | 442 | 302332 | 1472 | 109 |

这是本地包的可见划分，不代表存在 Test2。空标签不自动代表完整可靠的负例；action_ids 不提供负责人/截止日期的字段级 Gold。

## 文件和来源

- raw/：用户提供的只读原包，不改写或删除。
- processed/：clean split manifest、标准化数据等派生产物；已生成 clean_split.json，默认不公开。
- annotations/：未来人工标注，默认不公开。
- 原包名：cccdbe6d-87c3-4314-908e-f735073412a9.zip。
- SHA-256：666899476df91a0791b3b5e83994463c2a40e83d6d02e2b50cf2d32a556fec70。
- 候选来源：https://www.modelscope.cn/datasets/modelscope/Alimeeting4MUG 。实际下载 URL、日期、版本/修订号和适用许可待用户确认，不能凭文件结构确认来源或再分发授权。

合法获取对应包后放入 raw/，在项目根运行 `uv run python scripts/audit_alimeeting4mug.py`，生成本地报告与会议清单。脚本只读 ZIP，但会重建派生报告；要保留已有报告可用 --report/--inventory 指定其他位置。已有原报告含会议原文，不能默认公开；本 README 不复制原始正文。

## 已实施 clean split

Train M3298 / Dev M8016 共享 40 句长文本，相似度 0.877。scripts/clean_split.py 已从派生 Train 排除 M3298，保留 Dev M8016；processed/clean_split.json 记录原划分、原包 hash、规则、排除原因和最终规模 Train294/Dev65/Test1 82，不改 raw。排除记录也不得进入提示词示例。其余近重复风险尚未全面排除。

本批测试使用代码中明确标记的合成会议，不依赖 AliMeeting 下载或许可结论。

company_docs/ 中12份资料为原创 Synthetic/Fictional，evaluation/中另有3场合成会议和25道RAG题；与AliMeeting评估数据隔离。真实AliMeeting评估需合法取得原包，不由RAG ingestion自动导入。

Dataset redistribution license requires manual verification before repository is made public.
