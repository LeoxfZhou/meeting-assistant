# 真实问题与处理记录

更新：2026-11-18。仅记实际观察到的问题，不把计划测试或未来可能的 Bug 当作已发生事故。

## MA-001：Train/Dev 内容泄漏风险（已做派生隔离）

- 现象：Train M3298 与 Dev M8016 共享 40 个长句，全文字符顺序相似度 0.877。
- 根因：内容高度重合但会议 ID、分句和行动标签不同，可能同源转写；实际来源关系尚待确认。
- 排查：P0 脚本检查会议 ID、精确/去空白全文 hash、长句匹配；本轮重跑结果一致。仅 ID 去重无法发现此对。
- 解决方式：scripts/clean_split.py 已派生 manifest，排除 Train M3298、保留 Dev M8016，禁止被排除会议作为提示词示例；规则和输入 hash 已记录，raw 不变。其他近重复尚未穷尽。
- 学到什么：精确重复为零不等于不存在泄漏；无需训练也要隔离提示词开发集与测试集。

## MA-002：旧规划状态过时且路线改变（当前入口已纠正）

- 现象：旧 README 写“尚未下载数据”，旧路线要求先微调、再正式联调，与已完成 P0 和最新求职主线冲突。
- 根因：旧文档是 2026-10-27 的规划快照，未同步后续数据审计与本次目标变化。
- 排查：对照所有四份旧文档、原始包、审计产物和当前用户要求。
- 解决方式：保留旧文件不改写历史；新增 MASTER_GOAL/PROJECT_STATE 声明替代关系，QLoRA Optional。
- 学到什么：历史设计、当前目标、实际实现需有独立且明确的入口。

## MA-003：Docker 服务不可连接（本轮已恢复验证）

- 现象：docker info 报用户目录下 .docker/run/docker.sock 不存在；Compose 命令可运行。
- 根因：当前没有可连接的 Docker daemon socket；尚未确认是 Desktop 未启动还是上下文问题。
- 排查：运行只读 docker info 与 docker compose version，未自动启动或改配置。
- 解决方式：Batch 1 前启动 Docker Desktop，复查 daemon/context，或提供本机 PostgreSQL。尚未解决，不声称 DB 测试通过。
- 学到什么：CLI 安装成功不等于服务可用。

## MA-004：P0 报告含数据集原文（公开前待处理）

- 现象：outputs/audits/data_audit.md 的 Train 样例包含原文；仓库尚无 .gitignore。
- 根因：审计报告为本地数据理解生成，尚未建立公开产物边界。
- 排查：读取报告和 example_markdown()，核对 raw ZIP 与发布文件范围。未发生推送或已知泄露。
- 解决方式：保留本地原件，公开前排除该报告并生成无原文摘要，或在许可明确后审核发布；raw 默认不上传。
- 学到什么：衍生 Markdown 也可能包含受限内容，不能仅排除 data/raw。


### MA-003 本批补充

2026-11-18 复查首次得到 permission denied，不能据此判断 Docker 未启动。获准访问后 docker info 返回 29.8.0；Compose 启动 PostgreSQL 16.16 并 healthy，迁移与测试通过。原先 socket 不存在的状态已变化，本轮遇到的是工具访问限制。不要把权限错误误诊为服务停机。

## MA-005：uv 默认缓存访问与网络限制（已解决）

- 现象：uv python list 在默认缓存报 Operation not permitted；普通环境下载依赖报 DNS 请求失败。
- 根因：当前执行环境的缓存目录和网络访问边界，不是依赖不兼容。
- 排查：将 UV_CACHE_DIR 指向本任务临时缓存，使用已安装 Python 3.13.9；获准联网后重试。
- 解决：成功生成 uv.lock，32 个依赖包安装到 .venv；31 项测试通过。未更改系统 Python。
- 学到什么：先区分环境权限、网络和代码错误，避免无依据降级依赖。

## MA-006：TestClient 上游弃用提示（未处理，非测试失败）

- 现象：31 passed，出现一条 StarletteDeprecationWarning，提示 TestClient 的 httpx 集成将弃用，建议 httpx2。
- 根因：当前锁定 FastAPI 0.163.2 / Starlette 1.10.0 的测试适配迁移提示。
- 排查：核对真实测试输出；请求与数据库断言均通过。
- 处理：不隐藏警告、不为此扩展本批依赖迁移；保留锁文件，后续兼容性升级时验证替换。
- 学到什么：测试通过和依赖维护提示要分别记录，不能把警告说成已修复。


## MA-007：系统 Python 的 HTTPS CA 不完整（已解决）

- 现象：urllib 查询公开模型版本时出现 CERTIFICATE_VERIFY_FAILED。
- 根因：本机 Python 的默认 CA 路径不能验证远端证书链，不是模型需要登录。
- 排查：换用项目 httpx 的受信任 CA，TLS 验证正常，取得固定模型 revision。
- 修复：模型下载使用 httpx、保留 TLS 校验、固定 commit 和 SHA-256；从不 verify=False。
- 学到什么：网络错误不能用关闭证书验证掩盖。

## MA-008：结构化错误日志被错误降级（已解决）

- 现象：数据库失败接口仍返回 503，但回归测试捕捉不到 OperationalError 日志。
- 根因：统一 log_event 初版无条件使用 INFO，默认日志过滤可能丢失失败事件。
- 排查：保留失败断言，检查 caplog 与日志函数，而非删除测试。
- 修复：status=failed 使用 ERROR，正常事件使用 INFO；脱敏和 request_id 字段保留。完整回归通过。
- 学到什么：日志格式正确不等于错误可观测，级别也是行为契约。

## MA-009：容器基础镜像下载失败（排查记录）

- 现象：Docker Hub 匿名令牌访问超时；尝试的 uv+Python 组合标签返回 not found。
- 根因：前者为临时外部网络问题，后者为未存在的镜像标签；不能当作应用代码失败。
- 排查：保留构建日志于 outputs/checks；恢复已核验的官方 Python + uv 两阶段来源，单独 pull 官方 Python 镜像成功。
- 修复：不使用未知镜像站、不关闭 TLS；最终构建结果以 PROJECT_STATE 的最新验证为准。
- 学到什么：先区分网络、标签和构建依赖问题，镜像可访问性需真实验证。

## MA-010：测试客户端弃用提示消失（MA-006 后续）

LangGraph 的锁定依赖引入 httpx2 后，Starlette TestClient 使用了新的适配路径；最新 71 项测试输出无该弃用提示。没有通过过滤 warning 隐藏问题，旧记录保留作为历史。

## MA-011：内置浏览器预览工具连接超时（环境问题）

创建预览页和读取浏览器状态均超时，未操作个人浏览器。改用 Chrome headless 独立临时 profile 检查本机页面，结果以 outputs/checks 的实际截图为准；不把工具连接失败等同于后端不可用。

### MA-009 验证补充

官方 Python + uv 两阶段镜像已成功构建；本地 Compose API/PG 均 healthy，重启持久化及CRUD/审核冒烟通过。未将本地成功当作云部署成功。

## MA-012：恢复上下文时误用旧 Batch 边界（已纠正）

- 现象：上一轮将已包含后续功能的工作区当作 Batch 1 范围冲突并停止。
- 根因：未先读取持续目标附件，使用了旧批次指令。
- 排查：get_goal 返回 active 目标指针，完整读取附件，确认完整主线是当前目标。
- 修复：按附件继续，重写当前状态，保留代码和历史提交，补齐验收及面试文档。
- 学到什么：恢复任务必须先核验权威目标，不能靠摘要缩小范围。

## MA-013：真实模型拒绝旧生成参数（已修复）

- 现象：gpt-6-luna返回HTTP400，unsupported_parameter=max_tokens，要求max_completion_tokens。
- 根因：兼容客户端沿用旧参数，Mock未覆盖当前Provider契约。
- 排查：首条合成请求保存脱敏HTTP/错误字段，对照官方参数文档；不是Key或账单问题。
- 修复：默认max_completion_tokens，可显式兼容max_tokens；默认省略temperature；增加当前/旧参数回归，真实Smoke和后续链路通过。
- 学到什么：OpenAI-compatible不代表所有参数跨模型通用；不能凭Mock宣称真实兼容。

## MA-014：真实RAG拒答为空字符串（已修复并单题复测）

- 现象：q24私人手机号问题HTTP200，no_answer=true但answer为空，Pydantic拒绝；首轮和诊断复测均失败。
- 根因：prompt要求拒答却没明确拒答文本非空，模型输出与min_length=1契约不一致。
- 排查：仅对合成问题记录脱敏响应，确认不是JSON语法错误或Provider refusal字段。
- 修复：prompt要求非空说明；保留严格Schema，添加空拒答回归，真实同题复测一次通过。
- 学到什么：HTTP200不代表业务成功；保留首轮5/6及无答案1/2，不用单题修复结果改写总体指标。

## MA-015：真实请求观测器绕过系统代理（已修复）

- 现象：自定义HTTPTransport首条ConnectTimeout，默认httpx无凭据请求却收到HTTP401。
- 根因：自定义Transport未继承macOS系统HTTPS代理；不是Provider拒绝Key。
- 排查：只检查代理是否存在，保持TLS；没有输出凭据。
- 修复：观测Transport采用getproxies的HTTPS代理；真实请求到达Provider。Docker独立无凭据连通性也验证401。
- 学到什么：观测工具必须遵循被测客户端网络配置；未收到HTTP不能声称请求已达Provider。

## MA-016：Git未继承系统代理导致远程超时（已解决）

- 现象：git ls-remote经直接连接超时；httpx通过既有系统代理可访问GitHub。
- 根因：Git命令未自动继承macOS系统HTTPS代理，不能据此推断凭据失效。
- 排查：只读远程检查、代理存在性与未认证HTTP探测；使用现有代理后远程读取成功。
- 修复：仅为本次Git子进程设置https_proxy，沿用已有凭据；main push成功，API确认Private，真实CI通过。
- 学到什么：区分网络与授权；不打印Token、不改全局代理、不为此安装额外CLI。

## MA-017：服务器Docker Hub连接超时（已通过镜像传输解决）

服务器Head官方pgvector manifest时报i/o timeout。保留原配置，不使用未知镜像站；本机从官方源构建amd64应用并拉取PG镜像，docker save经SSH加载。服务健康、迁移与CPU检索通过。镜像传输与源码部署可分离，不能为网络问题改用不明来源。

## MA-018：云主机无法直连Provider（已按验收Scope关闭）

无凭据urllib探测失败，重启后curl直连api.openai.com:443仍在8秒连接上限超时。未收到HTTP，不能称401/配额/Key错误；没有发送密钥。先完成全部无Key部署、迁移、检索与重启验收，再请用户确定可用连接方案和服务器独立配置。

2026-11-19范围决策：大陆ECS仅验收基础设施，真实Generation在Mac完成；无需新增Provider或处理地区访问限制。

## MA-019：封版评测前本地LLM配置为空（人工恢复）

预检发现三个LLM变量为空，0次HTTP请求。将配置失败保留outputs/checks/finalization_config_preflight，不计模型评测；用户恢复后继续。脚本新增运行前配置检查，不打印值。

## MA-020：真实口语转写证据与连续原文不匹配（行号定位修复已验证）

首轮5场Test1均触发unsupported_evidence；7次HTTP尝试含1次传输失败，真实失败不覆盖。诊断发现换行省略、跨句拼接和改写。用户选择先修复，5场全部退出最终holdout，保留development_v1记录。

修复只允许唯一的去空白完全匹配并恢复原始字符；不使用相似度/模糊匹配接受改写。首次失败最多一次LLM证据纠正，仍失败则整场拒绝，绝不静默保留部分候选。Prompt明确保留口语原话并选短连续片段。新增恢复/歧义拒绝/纠正上限测试。最终30场另选未用于调试的Test1；clean Train用于Smoke。

## MA-021：封版复验时本机PostgreSQL未启动（已恢复）

首轮pytest为25通过48连接错误，RAG连接127.0.0.1:55432拒绝；Docker Engine正常但数据库容器未启动。启动既有Compose postgres后73项旧测试全部通过，固定RAG指标复现，无删除失败测试或清空开发库。

### MA-020 后续实际验证

仅空白恢复+一次纠正仍在Train Smoke的2/5场失败，保留development_v2。进一步使用LocatedExtraction：模型返回窗口起止行号，服务端重建连续原文；兼容旧quote仍严格校验，不模糊接受改写。新的5场Train Smoke全部通过结构/证据校验，但句级F1较低，说明定位成功与识别质量不同。最终30场Test1在此版本冻结后才运行。新增范围/空白/歧义/纠正上限测试，总82项通过。

## MA-022：最终AliMeeting真实读取超时（作为评测失败保留）

M3181在一段读取上连续三次ReadTimeout，达到现有重试上限；整个会议按空预测计分，不保留部分候选或删去失败会议。没有为提高成绩修改最终集超时设置或重跑该会议。用量不含供应商未返回的未知usage，费用仍null。
