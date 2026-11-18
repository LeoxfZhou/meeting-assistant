# GitHub Private 仓库与真实 CI

2026-11-18。仓库由用户人工创建并添加Remote；本轮GitHub API核实private=true，默认分支main。未修改仓库可见性，没有创建公开仓库。

- 仓库：https://github.com/LeoxfZhou/meeting-assistant
- 首次推送：b7cd07ebf554854078e55f0631395f5eef4dd4c2。
- 首次真实CI：[Actions 44308229328](https://github.com/LeoxfZhou/meeting-assistant/actions/runs/44308229328)，completed/success，73 passed in 14.73s。
- Linux runner使用真实PostgreSQL/pgvector服务、固定Python/uv与锁文件、固定revision向量模型；外部LLM为Mock。未把真实LLM Key放入GitHub Secrets。
- 本轮docs/github-ci-handoff分支修正文档中的旧“无Remote/CI”状态；通过真实PR检查和合并。最终PR链接与状态以GitHub为准，不补造历史PR。

## 复现工作方式

1. 从最新main创建有实际任务的分支。
2. 修改、运行适用测试、审阅diff；检查git status以及暂存内容。
3. 执行 `uv run python -m scripts.audit_public_repo`。该检查包含index和所有本地历史；不能替代数据许可/人工审查。
4. push分支，创建描述真实问题/变更/测试的PR。
5. 等待该PR当前HEAD对应CI通过，再review diff并merge；不以旧commit的绿灯代替新HEAD。
6. 更新本地main；部署为单独后续步骤，不自动发布服务。

Git凭据仅通过已有credential helper在内存使用；不保存或打印Token，未安装gh。网络使用本机已有系统HTTPS代理，仅设置子进程环境，没有改变全局Git设置。

.env、raw/processed、含受限原文的outputs/audits、模型、数据库卷和虚拟环境均不在提交历史中。推送前扫描155个不同blob通过。Private不代表可以随意上传受限数据；公开前仍需许可、个人信息和许可证复核。

尚未完成：CPU Linux Server部署、用户UI人工审核与Bad Case抽查。不要把CI通过写成云部署成功，也不要把AI自审写成多人独立Review。
