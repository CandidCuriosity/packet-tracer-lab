# 魔搭 Notebook 环境手册

本文件记录目标环境的事实。路径和命令按实测整理，环境变过就以 `scripts/probe_env.sh` 的输出为准。

## 环境构成

| 项 | 值 |
|---|---|
| 系统 | Ubuntu 22.04，Notebook 容器，root 终端 |
| 持久盘 | `/mnt/workspace` |
| 桌面 | XFCE，通过 TigerVNC 和 noVNC 暴露，固定 1600x900，`DISPLAY=:1` |
| 桌面控制 | computer-use-linux 0.7.5，源码编译安装 |
| Packet Tracer | 9.0.1，AppImage 已用 `--appimage-extract` 解包，免 FUSE |
| 浏览器 | GNOME Web (Epiphany)，用于 PT 登录 |

## 关键路径

| 路径 | 内容 |
|---|---|
| `/mnt/workspace/software/packettracer/appimage-9.0.1/squashfs-root/AppRun` | PT 启动入口 |
| `/mnt/workspace/software/packettracer/user-data` | PT 用户数据，`/root/.local/.packettracer` 软链到此 |
| `/mnt/workspace/software/packettracer/xdg-config`、`xdg-data` | PT 私有 XDG 目录 |
| `/mnt/workspace/software/packettracer/ext-modules` | 本 skill 存放 `.pts` 扩展的目录 |
| `/mnt/workspace/desktop` | 桌面状态、日志、`bin/` 入口 |
| `/mnt/workspace/desktop/bin/desktop-run` | 在桌面会话里执行命令的包装器 |
| `/mnt/workspace/desktop/bin/computer-use-linux-session` | 操控工具的会话入口，带 `mcp` 子命令 |
| `/mnt/workspace/software/computer-use-linux` | 操控工具本体和 Rust 工具链 |
| `/mnt/workspace/.codex` | Notebook 内 Codex 的 `CODEX_HOME` |
| `/mnt/workspace/111/CiscoPacketTracer_901_Ubuntu_64bit.deb` | 原始安装包，重建时可重新解包 |

## 入口命令

```bash
# 恢复桌面并启动原 Packet Tracer，成功会打印 PID 和 DISPLAY
bash /mnt/workspace/recover-packettracer.sh

# 桌面管理
bash /mnt/workspace/start-desktop.sh status     # 查看 vnc / desktop / novnc / tunnel
bash /mnt/workspace/start-desktop.sh doctor     # 能力检查并实际截图
bash /mnt/workspace/start-desktop.sh setup-mcp  # 注册到 Notebook Codex
bash /mnt/workspace/start-desktop.sh stop       # 改端口或分辨率前必须先停

# 在桌面会话里跑命令（截图、wmctrl、xdotool 都需要）
bash /mnt/workspace/desktop/bin/desktop-run <命令>
```

## 无障碍与操控环境

`desktop-session.sh` 在建会话时已经导出并激活：

```bash
export NO_AT_BRIDGE=0 GTK_MODULES=gail:atk-bridge
export QT_ACCESSIBILITY=1 QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
export COMPUTER_USE_LINUX_SCREENSHOT_BACKEND=x11
export COMPUTER_USE_LINUX_FORCE_XDOTOOL_KEYBOARD=1
gsettings set org.gnome.desktop.interface toolkit-accessibility true
gdbus call --session --dest org.a11y.Bus --object-path /org/a11y/bus \
  --method org.freedesktop.DBus.Properties.Set org.a11y.Status IsEnabled '<true>'
```

这些值也会写进 `/mnt/workspace/desktop/run/session.env`，只在会话存活期间有效。
所以任何依赖 DISPLAY 或 AT-SPI 的命令都要走 `desktop-run`，不要在裸终端里跑。

## 首次安装清单

```bash
# 1. uv，含自带的 Python。装到持久盘，/root 下的东西重建实例就没了
curl -fsSL https://astral.sh/uv/install.sh -o /tmp/pt-uv-install.sh
UV_INSTALL_DIR=/mnt/workspace/software/uv/bin UV_NO_MODIFY_PATH=1 sh /tmp/pt-uv-install.sh
# 把该目录加进开机加载的脚本；必要时用绝对路径 /mnt/workspace/software/uv/bin/uvx

# 2. packet-tracer MCP server 自带的 skill。
#    Codex 默认扫 ~/.agents/skills，而那是 /root 下；用 --dest 指到持久盘的 CODEX_HOME
uvx packet-tracer-mcp install-skill --dest /mnt/workspace/.codex/skills
uvx packet-tracer-mcp install-skill            # Claude Code，装到 ~/.claude/skills

# 3. 本技能转载使用明确目标与摘要校验，已有不同版本默认不覆盖
python3 packet-tracer-lab/scripts/deploy_skill.py --dest /mnt/workspace/.codex/skills
python3 packet-tracer-lab/scripts/deploy_skill.py --dest /mnt/workspace/.codex/skills --check

# 4. 注册成 Codex 的 MCP server，然后重开 Codex 用 /mcp 确认
env CODEX_HOME=/mnt/workspace/.codex codex mcp add packet-tracer -- /mnt/workspace/software/uv/bin/uvx packet-tracer-mcp --stdio
# codex 不在 PATH 上时直接写 /mnt/workspace/.codex/config.toml，命令用持久盘绝对路径：
#   [mcp_servers.packet-tracer]
#   command = "/mnt/workspace/software/uv/bin/uvx"
#   args = ["packet-tracer-mcp", "--stdio"]
# 入口点已核对：pt-mcp 和 packet-tracer-mcp 都指向 packet_tracer_mcp.server:main

# 5. PT 扩展
bash "<skill目录>/scripts/install_pts.sh"
```

## 两阶段自检

先定位已安装 skill 的绝对目录，用 `scripts/probe_env.sh --phase installed` 检查安装；
恢复桌面后用 `--phase ready` 检查运行状态。可加 `--json` 只向 stdout 输出结构化结果。
未启动桌面在 installed 阶段记 WARN，在 ready 阶段记 FAIL。
AT-SPI 注册表要通过 `org.a11y.Bus.GetAddress` 查询到的无障碍总线检查，不能在 session bus 上查。
doctor 必须有 readiness 对象与所需的布尔能力；缺字段不能算通过。
`codex mcp list` 仅是注册清单，下载 .pts 仅是文件存在，二者都不是实时连接证明。
0.2.1 用窗口 WM_CLASS 与存活 PacketTracer PID 交叉判断 PT，避免同名登录浏览器误报。
原文探测支持 `/mnt/workspace/111/Cisco_Packet_Tracer_实验步骤/`；其他位置用 `--documents` 传入实际目录。
PATH 缺 uvx/codex 时先发现已安装的可执行文件，只为这次命令设置 PATH 或使用绝对路径，不为通过 probe 重装工具。

## 已知故障

| 现象 | 原因 | 处理 |
|---|---|---|
| 启动 PT 报 `fuse: device not found` | 容器没有 FUSE | 用解包版 `squashfs-root/AppRun`，不要直接跑 AppImage |
| 点击登录提示 `Failed to execute default Web Browser` | PT 用私有 XDG 目录，找不到浏览器 | 恢复脚本会把 Epiphany 的 desktop 文件同步到 PT 的私有 `xdg-data`，重跑恢复脚本 |
| 桌面起不来、D-Bus 相关报错 | 容器装了 dbus 但不保证起系统总线 | 脚本会检测并用 `dbus-daemon --system --fork` 拉起，看 `logs/system-dbus.log` |
| 实例重建后 PT 报缺库 | AppImage 依赖随镜像丢失 | 对实际 ELF 文件跑 `ldd` 找缺的库，装包后重新解包 |
| 提示旧 PT 在其他图形会话运行 | 有遗留进程占着同一用户数据 | 先保存并关闭旧软件，脚本不会替你杀进程 |
| Codex 里 `/mcp` 看不到工具 | 注册后没重开 Codex | 重开 Codex；确认 `CODEX_HOME=/mnt/workspace/.codex` 一致 |
| 会话里 `pt_*` 全部"未注册"，同时 `/mnt/workspace` 也读不到 | 这个会话不在 Notebook 里，或者没 source `boot.sh` 就启动，`CODEX_HOME` 没生效，Codex 的沙箱也没覆盖 `/mnt/workspace` | 见下面的 [Codex 会话恢复](#codex-会话恢复) |
| 技能列表里只有 `packet-tracer`，没有 `packet-tracer-lab` | skill 位置或当前客户端扫描规则不匹配 | 检查实际扫描目录；项目技能可放 `/mnt/workspace/.agents/skills`，不要重复安装多份 |

## Codex 会话恢复

Codex 进程继承启动时 shell 的环境变量。`/mcp` 看不到 server、`pt_*` 未注册或目录无法访问时，
先区分当前主机、环境变量、目录权限、MCP 配置与连接错误，不能直接认定根因。

先用普通终端（不是 Codex 里）判断三件事：

```bash
pwd                                  # 应该在 /mnt/workspace 或它的子目录下
echo "CODEX_HOME=$CODEX_HOME"        # 应该是 /mnt/workspace/.codex，空的就是没 source
ls /mnt/workspace/.codex/config.toml && grep -A3 mcp_servers /mnt/workspace/.codex/config.toml
```

`ls /mnt/workspace` 失败时先检查当前主机、目录是否挂载与访问权限；
确认在 Windows 或其他主机时，再换 Notebook 内的终端。三件事正常，再从加载过 `boot.sh` 的 shell 启动：

```bash
source /mnt/workspace/boot.sh          # 加载 CODEX_HOME、PATH、密钥
command -v uvx                         # 应是 /mnt/workspace/software/uv/bin/uvx
cd /mnt/workspace && codex
```

启动后先 `/mcp` 确认 `packet-tracer` 和 `computer-use-linux` 都在，再看 `pt_list_devices` 有没有设备目录。

## 持久化注意

**`/root` 下的东西不随实例重建保留，`/mnt/workspace` 才保留。** 所以下面这些必须落在持久盘，
否则重建实例后 MCP、skill、扩展全都会消失，只剩 `/mnt/workspace` 里的文件：

| 东西 | 应放位置 | 不要放 |
|---|---|---|
| uv 和 uvx 二进制 | `/mnt/workspace/software/uv/bin`，用 `UV_INSTALL_DIR` 指定 | `/root/.local/bin` |
| uv 的缓存、托管的 Python 和工具目录 | `UV_CACHE_DIR`、`UV_PYTHON_INSTALL_DIR`、`UV_TOOL_DIR`、`UV_TOOL_BIN_DIR` 指到 `/mnt/workspace/software/uv/` 下 | 默认的 `/root/.cache`、`/root/.local/share` |
| Codex 的技能目录 | 项目内 `/mnt/workspace/.agents/skills/`，或当前客户端确认的 `/mnt/workspace/.codex/skills/`；不要自动替换既有链接 | 只放 `/root/.agents/skills`，重建后消失 |
| MCP 扩展 `.pts` | `/mnt/workspace/software/packettracer/ext-modules/` | 任何 `/root` 下的路径 |
| Codex 的 MCP 配置 | `/mnt/workspace/.codex/config.toml`，里面的命令用持久盘绝对路径 | 依赖 PATH 或 `/root` 路径 |

PT 的用户数据在持久盘上，所以脚本模块的注册**可能**跨实例重建保留，这需要实测确认：
重建后直接看 `Extensions` 菜单里还有没有已注册的模块，`scripts/probe_env.sh` 会检查痕迹。
`/mnt/workspace` 之外的一切（`/root` 下的非软链内容、`/tmp`）都会随实例消失。

## 网络注意事项

`raw.githubusercontent.com` 在容器里可能被重置连接，报 `OpenSSL SSL_connect: 连接被对方重置`。
换成 GitHub API 即可：`curl -fsSL https://api.github.com/repos/<owner>/<repo>/contents/<path>`，
返回内容在 `.content` 字段里、是 base64。`api.github.com` 和 release 附件的下载链接本身可用。

## 部署与启动

技能安装见 [部署说明](deployment-check.md)，常见问题见 [排障指南](troubleshooting.md)。
短期命令启动后的跨调用存活确认见 [启动生命周期](launch-lifetime.md)。
路径为参考Notebook布局，环境变化时使用实际路径；不随Skill发布用户配置、密钥或运行日志。
