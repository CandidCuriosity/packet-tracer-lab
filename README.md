# Packet Tracer Lab Skill

## 这个 Skill 是干什么的

`packet-tracer-lab` 是一个面向 Cisco Packet Tracer 网络实验的 Agent Skill。它让 Codex 或 Claude Code 根据实验文档规划拓扑、连接设备、配置交换机/路由器/主机、验证通信，并在模拟模式中观察单播、广播、MAC 学习、ARP 和冲突等过程。

Skill 结合 Packet Tracer MCP、无障碍树和截图操作完成图形桌面中的实验，能够排查配置与连接问题，保存实验截图、Packet Tracer 原生工程和报告。技能文件位于 `packet-tracer-lab/`。s

## 使用前置

- 使用能够读取 Agent Skill、调用 MCP 和桌面控制工具的 Codex 或 Claude Code。
- 准备好 Cisco Packet Tracer，完成所需登录，并在当前 PT 实例中加载、启动 Packet Tracer MCP 的 `.pts` 模块。
- Agent 能访问 PT 所在的图形桌面，具备窗口定位、截图、键鼠输入及无障碍树读取能力。
- 安装 Python 3.9+、Bash，以及 MCP 和桌面工具所需的依赖；使用 uv 安装/运行 MCP 时，需准备 uv/uvx。
- 提供实验步骤文档，并让 Agent 能读取文档、写入实验结果目录。
- 随附环境脚本按 Linux Notebook 编写，需要已有桌面启动/恢复脚本及 `desktop-run` 包装器，实际路径按自己的环境配置。

## 理论上适用的环境

核心流程依赖“可运行的 Packet Tracer + MCP 连接 + Agent 可操作的图形桌面”，因此理论上可用于具备这些条件的 Linux 本机、虚拟机、带桌面的容器、云服务器或 Notebook。

魔搭并非理论上的唯一平台。其他平台需要适配目录、启动命令和桌面控制工具；Windows / macOS 只有在提供等价工具并适配 Linux 辅助脚本后，才可复用这套流程。它们尚未在本项目中实际验证。

## 实际使用的 Linux 环境和软件

实际环境为 **Ubuntu 22.04，XFCE 图形桌面**。

| 软件或组件 | 实际环境及用途 |
|---|---|
| Cisco Packet Tracer 9.0.1 | 解包的 AppImage，在 Linux 桌面中搭建和模拟网络 |
| Packet Tracer MCP | 提供拓扑、配置、状态读回与存档等 `pt_*` 工具，PT 内加载 `.pts` 模块 |
| computer-use-linux 0.7.5 | 读取 AT-SPI 无障碍树、控制窗口、截图与键鼠输入 |
| XFCE | 图形桌面，使用分辨率为 1600 × 900 |
| TigerVNC / noVNC | 访问 Notebook 的远程桌面 |
| GNOME Web（Epiphany） | Packet Tracer 登录所用浏览器 |
| Python、Bash、uv/uvx | 运行辅助脚本和 MCP 服务 |
| Codex | 实际执行实验的 Agent；Skill 结构同时面向 Claude Code |

以上是实际环境记录，理论可适配的环境与已经实际使用的环境分开说明。Skill 提供执行方法和辅助脚本，相关软件需要单独准备。
