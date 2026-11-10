---
name: packet-tracer-lab
description: >
  在魔搭 Notebook 的 XFCE 桌面里搭建、配置、验收和排查 Cisco Packet Tracer 网络实验，
  使用 packet-tracer MCP 读回结果、保存证据并生成报告。
  Use for Packet Tracer labs, PT 实验、已有拓扑故障、实验截图与报告；不用于仅解释网络概念。
license: MIT
metadata:
  compatibility: "claude-code, codex"
  language: zh-CN
  version: "1.0.0"
---

# Packet Tracer 实验执行

你是实验操作员：把一份实验步骤文档变成可验证的结果，并留下证据。
不要只讲原理，也不要只截图不验证。

以当前任务的真实读回、截图和原生存档作为验收依据；参考流程不代表某项实验已经执行。

## 何时使用，何时不用

- 使用：搭建或修改拓扑、配置 IOS、排查连不通、重做实验、生成实验报告与截图。
- 不用：只解释网络概念，或只写与 PT 实操无关的文章。
- 默认操作目标为用户指定的 Linux 图形桌面；其他系统需先适配控制工具和辅助脚本。

## 环境事实

| 项 | 值 |
|---|---|
| 目标环境 | 魔搭 Notebook，Ubuntu 22.04 |
| Packet Tracer | 9.0.1，免 FUSE 解包的 AppImage |
| 桌面 | XFCE + TigerVNC/noVNC，1600x900，DISPLAY=:1 |
| 桌面控制 | computer-use-linux 0.7.5，提供 AT-SPI 树、窗口定位、截图、xdotool 输入 |
| PT 控制 | packet-tracer MCP 的 pt_* 工具，底层是 PT 自带脚本引擎 |

路径、启动命令、故障处理见 [环境手册](references/env-notebook.md)。第一次接手这个环境先读它。

## 硬规则

1. **先发现，再调用。** 设备型号、端口、模块、线缆、API 名都必须来自工具返回或实验文档，不凭印象写。
2. **每次改动后读回。** 工具提供 `verified` 时检查它；主机配置等未提供该字段时，用独立面板、接口与命令读回验证目标值，不编造字段。工具封装的 `isError:false` 不表示 PT 操作成功，须检查正文的 timeout、NOT connected、rejected 和 error。
3. **原始 JS 只写 [陷阱清单](references/pt-traps.md) 里列出的方法**，并包在 `try/catch` 中。脚本引擎的错误会弹模态框，PT 会一直冻在那里等人点。
4. **不要用 `for...in` 枚举原生对象**，整个 PT 进程会崩溃，`try/catch` 救不了。
5. **仅在实时模式的连线收敛阶段使用 `pt_fast_forward()`**。模拟观察期间按原文单步推进，不在单播、广播、冲突之间额外切模式或快进。
6. **不要手写、解析或注入 `.pkt` 二进制**；成果应通过 PT 自带的存档工具或 GUI 另存。
7. **设备名只用字母、数字、`-`、`_`**，引号和斜杠会让 PT 重开时崩溃。
8. **一次只改一个变量**，失败先复现再修。
9. **卡住就报 blocker**，写清现象、命令、原始返回，不要猜着继续。

## 工作流

### 0. 环境自检

```bash
bash "<skill目录>/scripts/probe_env.sh" --phase installed
```

先定位已安装的本技能绝对目录；下文 `<skill目录>` 都替换成该目录，不能假定当前目录是 skill。
`installed` 只检查安装前置条件，桌面未启动记 WARN。恢复桌面后再跑 `--phase ready`，修复 FAIL 后继续。
`codex mcp list` 只证明注册；工具的连接状态必须在当前 Codex 会话里确认。

### 1. 起会话

```bash
bash "<skill目录>/scripts/start_session.sh"
```

它复用当前可见的 PT；没有窗口才调用已有恢复脚本，并等窗口出现。
识别必须同时匹配 WM_CLASS 与仍存活的 PacketTracer PID，登录浏览器可能同名。
恢复后还要确认短期进程/窗口稳定、bridge 和一次真正的 PT 读回；单凭 CONNECTED 不能验收恢复成功。
长期 PT 还需在启动命令完成并被收取后继续存活；用后续独立命令再次检查。
该 Notebook 的报告记录了仅增加 setsid 的启动修复，适用条件与证据范围见 [启动生命周期](references/launch-lifetime.md)。
保留环境内已修复的恢复脚本，更新 skill 不应覆盖它。
若环境正在由其他会话修复，先只做本地或只读检查，避免并发恢复。PT 在别的会话运行时保留进程，报告冲突。

### 2. 挂 PT 扩展（首次或实例重建后）

```bash
bash "<skill目录>/scripts/install_pts.sh"
```

下载完成后由你用桌面工具点 `Extensions → Scripting → Configure PT Script Modules → Add…`，
在文件选择器里选中 `.pts`。
这一步是 GUI-only，用无障碍树或坐标完成，方法见 [控制通道](references/control-layers.md)；
无障碍树能看见这条菜单，已实测。

两个容易误判的地方：

- **Linux 上不会弹"检测到新脚本模块，是否启用"**。那个提示只在扩展被放进 PT 自己的 extensions
  目录时出现，而 Linux 的 AppImage 没有这个目录。判断是否挂好，看 `Configure PT Script Modules`
  列表里有没有这一项，确认模块已启动（旧版按钮从 Start 变为 Stop），新版以实际面板为准。
- 挂好之后菜单里才会出现 `Extensions → MCP BUILDER`。打开它并确认与 bridge 连接成功，
  再用 `pt_bridge_status` 确认返回 ACTIVE 和 CONNECTED。

已注册且正在运行的模块直接复用；当前实例列表缺失时才加载已有 `.pts`，不要因历史挂载成功就跳过当前列表检查。
若 bridge 正文出现 `NOT this MCP server's bridge` 与 `Refusing to send commands`，暂停 PT 写操作。
先查监听端口所属 PID、命令行及所属会话；不能按同名进程批量结束服务。详细处理见 [Notebook 排障指南](references/troubleshooting.md)。

历史版本存在首次调用未连接的问题。只允许对只读的 `pt_bridge_status` 补试一次；
仍失败就保留原始返回并排障。部署或配置超时后先读回，不能照此规则重复执行。
上游新版已修复首次连接问题，实际行为以安装版本为准。

### 3. 读实验任务

先使用用户提供的实验文档目录。Notebook 可检查 `/mnt/workspace/Cisco_Packet_Tracer_实验步骤/`，其他目录以实际文件为准。
可将已发现的路径传给 probe 的 `--documents`；不要为了通过自检创建链接或移动原文。
远程环境缺少原文时再上传；不要假定它能访问操作端本地磁盘。
先查询当前拓扑与打开的文件。已有内容先确认另存副本成功，再新建实验；不覆盖原稿。
打开 `实验N-*.md`，先抄出一张表：设备与型号、每个接口的 IP、线缆类型、验收点。
每个实验的最小证据集见 [实验手册](references/lab-runbook.md)。
文档中前后不一致处按其标注处理，不要静默改成"确定结论"。

### 4. 搭拓扑

先发现当前工具及参数 schema，并读取已安装的 `packet-tracer` skill；下述工具名是流程示例，未暴露时不要猜参数。
优先 `pt_plan_topology` → `pt_validate_plan` → `pt_live_deploy`，或一次成型的 `pt_full_build`。
手工增补用 `pt_add_device` / `pt_add_link`，调整用 `pt_move_device` / `pt_rename_device`。
部署报告是事实来源，先看 `errors[]`。装模块前先 `pt_list_modules`，装完设备会掉电重启。

### 5. 配置设备

用 `pt_apply_*` 系列；IOS 设备命令用 `pt_cli`，PC 的 Command Prompt 用实际暴露的 `pt_host_command` 或 GUI。
多条 IOS 命令按当前 schema 逐条执行，不要用原始 `enterCommand`。
工具支持 `dry_run` 时先预览，再正式执行，检查工具实际提供的验证字段并独立读回。
主机 IP 用 `pt_read_device_panel` / `ipconfig` 核对；被拒的行按 IOS 原文修，不要盲重发。

### 6. 验收

实验2等要求观察初始MAC/ARP状态时，先按实验手册完成初始表和首次流量取证，再做常规ping验收。
不要用基础连通性流量提前改变待观察的缓存。

读回和实测缺一不可：

- 读回：`pt_read_routes`、`pt_read_vlans`、`pt_read_dhcp_leases`、`pt_inspect_ports` 等。
- 实测：`pt_send_pdu` 拿 PT 自己的分层失败原因，`pt_verify_connectivity` 做端到端确认。
- 基础连通性第一次 ping 或 PDU 可能受 ARP 影响，可补试一次并保留两次结果。Simulation 的广播/并发观察先保存原始 trace，按原文控制缓存和重试，避免额外流量改变时序。

模式切换、时间推进、GUI 输入后先确认实际状态，再做下一项改变。
若正文已返回 timeout 或 NOT connected，即使 isError=false 也暂停后续写操作，先检查进程、窗口和只读 bridge。
实验1按原文保持 Simulation 完成单播、广播和并发观察。崩溃与恢复诊断见 [Notebook 排障指南](references/troubleshooting.md)。
广播泛洪、广播回复序列和并发冲突分别验收；读实际协议、ARP buffering、模拟时间与逐层决策。
冲突实验的 `clean:false` / `failures[]` 可为预期现象，不等同于工具调用失败。
具体取证流程见 [实验1广播与并发](references/lab1-simulation.md)。
实验2的旧Inspect表、待处理终端、过滤器与历史事件游标见 [实验2模拟取证](references/lab2-simulation.md)。

### 7. 证据截图

命名 `lab<N>_<对象>_<动作>.<png|jpg>`，存到该实验的 `截图/` 目录。
截图前把窗口摆好，别截进无关窗口。最小集见实验手册的"证据"列。
设备子窗口截图先聚焦该子窗口，必要时全屏且不 raise 主 PT 窗口；验证画面实际内容，文件名不是证据。

### 8. 报告

按实验手册的清单产出；先查找用户提供的 `实验模版/` 和历史结果的 `原始文档/`。
历史清单记载过模板不能证明当前仍可用，但也不能仅因默认目录没有就认定用户未提供。
结果写入用户指定目录；Notebook 可使用 `/mnt/workspace/pt-lab-output/<实验N>/`，需要下载时保持文件名一致。
报告模板未提供时先生成 Markdown 报告并注明 Word 排版待完成，不假定存在 `实验模版/`。
用户指定Markdown或暂停Word时沿用要求，保留草稿并明确未验收；不为了完成标签恢复已暂停的排版工作。
由 PT 的实际存档工具或 GUI 将成果另存为新 `.pkt`，确认文件存在；禁止手写二进制并不禁止 PT 原生保存。
存档基名优先 ASCII，目录可保留中文；保存工具可能改写中文文件名，以真实返回路径和文件存在为准。
报告必须含：设备与地址表、逐台配置、验收命令与真实输出、截图清单、未完成项及原因。
证据保留原始工具JSONL；索引用行号、label、时间与真实文件定位。交付完整ZIP、逐文件大小/SHA256清单，
清单自身的排除项明确列出，包外ZIP摘要单独提供。原生保存与重开验收分开：未重开就记录未执行，
不能用metadata或文件存在替代重开成功。

## 通道取舍

| 任务 | 用哪条通道 |
|---|---|
| 建拓扑、连线、配 IOS、读回状态 | PT 脚本引擎，走 pt_* 工具 |
| 菜单、对话框、挂扩展、切窗口 | 无障碍树 |
| Edit Filters、Inspect、Traffic Generator及要求的界面截图 | 无障碍树可用时优先，否则坐标加截图 |
| 模拟单步、事件与MAC/ARP读回 | 当前pt_*原生能力可辅助；每步核对真实模式、事件游标和截图 |

分工理由、树探测方法和坐标纪律见 [控制通道](references/control-layers.md)。

## 情况对应参考

| 遇到 | 读 |
|---|---|
| 环境路径、启动恢复、实例重建后异常 | [references/env-notebook.md](references/env-notebook.md) |
| 无障碍树能看见什么、坐标怎么兜底 | [references/control-layers.md](references/control-layers.md) |
| PT 行为诡异、引擎报错、API 不确定 | [references/pt-traps.md](references/pt-traps.md) |
| Notebook 实测的同名浏览器、Host 验证、模式切换退出 | [references/troubleshooting.md](references/troubleshooting.md) |
| 空闲退出、命令回收、nohup/setsid 与跨会话存活 | [references/launch-lifetime.md](references/launch-lifetime.md) |
| 每个实验的设备、地址、验收点、证据清单 | [references/lab-runbook.md](references/lab-runbook.md) |
| 实验1广播回复受ARP影响、同一模拟时钟并发与明确冲突 | [references/lab1-simulation.md](references/lab1-simulation.md) |
| 实验2旧MAC窗口、过滤器历史回放、终端关闭中断与交换机缓存 | [references/lab2-simulation.md](references/lab2-simulation.md) |
| 要转载安装、校验加载与首次验收 | [references/deployment-check.md](references/deployment-check.md) |
| 要在 Notebook 的 Codex 里发起任务 | [references/codex-prompts.md](references/codex-prompts.md) |

## 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/deploy_skill.py` | 显式目标安装、保留旧版、逐文件 SHA256 校验 |
| `scripts/probe_env.sh` / `probe_env.py` | 安装与运行两阶段只读体检；注册与实时连接分开 |
| `scripts/start_session.sh` | 恢复桌面与 PT，并等窗口就绪 |
| `scripts/pt_runtime.py` | 只读匹配窗口 class 与存活 PID，并检查短期稳定性 |
| `scripts/check_pt_reply.py` | 解析捕获的 MCP JSON；识别封装为 isError=false 的 PT 超时／断连 |
| `scripts/install_pts.sh` / `install_pts.py` | 校验 release digest、原子落盘、保留已有扩展 |
| `scripts/probe_a11y.py` | 可选：dump PT 的 AT-SPI 树，判断画布是否可见 |

脚本用 bash 和 python3 标准能力，不依赖宿主专有变量，可以直接在 Notebook 里跑。
