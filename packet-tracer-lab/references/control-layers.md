# 控制通道：无障碍树、脚本引擎、坐标

三条通道各有边界。选错通道是这类任务最常见的失败原因，所以先看这张表再动手。

| 通道 | 能做什么 | 做不到什么 |
|---|---|---|
| PT 脚本引擎，走 pt_* 工具 | 建设备、连线、装模块、配置 IOS、读回、发 PDU、存档；当前schema可提供模拟单步/trace | 要求的GUI截图、部分只存在于GUI的对话框 |
| 无障碍树，AT-SPI | 菜单、菜单项、对话框、按钮、文本框、面板、窗口聚焦 | 拓扑画布上的设备和连线，自绘控件通常没有节点 |
| 坐标加截图 | 画布点击、模拟模式工具栏、没有节点的控件 | 点击回执不能证明生效；需截图及可用状态读回，坐标依赖窗口和缩放 |

## 为什么画布不能指望无障碍树

Packet Tracer 用的是 Qt Widgets，标准控件会通过 AT-SPI 暴露，但工作区是自绘的，
设备图标和连线不是控件，树上不会出现对应的节点。所以：

- 建拓扑一律走脚本引擎，坐标由代码给出，不需要人去点画布。
- 无障碍树的真正价值在菜单和对话框，例如首次挂载 `.pts` 扩展的那次点击。
- 树里若能看到设备名或端口名，说明 PT 版本暴露得比预期多，可以扩大它的用途，但要先验证。

## 怎么探测树里有什么

在 Notebook 里，优先用 agent 自己的工具，因为那才是它实际能看到的东西：

```
# 以下是历史 schema 示例；先发现当前桌面工具与参数
get_app_state(app_name_or_bundle_identifier="PacketTracer")
get_app_state(window_title="Cisco Packet Tracer", include_screenshot=false, interactive_only=true)
```

读结果时关注这几个字段：

| 字段 | 含义 |
|---|---|
| `tree_scoped` | false 表示没有限定到目标应用，拿到的是整个桌面，容易撑爆上下文 |
| `accessibility_tree_truncated` | true 表示树不完整，需要缩小范围或提高 `max_nodes`、`max_depth` |
| `element_index` | 后续点击用的句柄，重新快照就会失效 |
| `accessibility_tree_spill.path` | 树太大时落盘的完整 JSON，直接搜索这个文件而不是再请求一次 |

没有 MCP 客户端时，用 `scripts/probe_a11y.py` 做同样的事情，它需要 `desktop-run` 包裹：

```bash
bash /mnt/workspace/desktop/bin/desktop-run python3 "<skill目录>/scripts/probe_a11y.py" --json --tree
```

输出中的 truncated=true 表示命中节点或深度上限。截断时只能说明已遍历部分未发现节点，
不能证明整棵树不存在设备。设备选择面板也可能出现 PC、Router 等名字，这只是线索；
实际动作与读回成功后才能依赖。

## 模块挂载

通过Extensions → Scripting → Configure PT Script Modules检查当前实例列表，缺失时才Add已有.pts并Start。
已运行模块直接复用；面板按钮/连接文字按实际版本判断，随后取真实bridge和拓扑读回。

## 坐标兜底的纪律

坐标回执不能证明生效，要用截图和当前工具支持的读回确认：

1. **每次动作后立刻截图确认**，不要连续盲点两次。
2. **坐标来自最近一次截图**，schema要求整数就使用整数。若调整窗口大小或缩放，先重新截图再定位。
3. **优先点语义元素**，只有确实没有节点时才用坐标。
4. **点偏了不要微调着试**，重新截图重新定位，避免累积误差。
5. **同一个操作第二次失败就换思路**，改用脚本引擎或 `pt_cli` 绕过 GUI。

Notebook 实测还发现：语义 New 匹配多个节点时必须用最新 element_index 并验证新工程真的为空；
Add/文件选择器需各自的 window ID。截图 PC 子窗口时别 raise PT 主窗口遮住它，先聚焦子窗口，
必要时用工具支持的 full_screen=true、raise_window=false。按截图与读回决定是否成功，不能凭 ok 回执或文件名。
本轮设备IP面板点击回执成功却仍选中Global Settings；先验证当前面板再操作。
UnknownObject或旧element_index失败后刷新树和子窗口ID。拖动因缺ydotool失败时，检查已有desktop-run/xdotool通道，
不为一个不可用后端重复安装工具。

## GUI证据与原生辅助

实验要求的界面证据仍需GUI；当前实际暴露的API可辅助读回与单步，不能虚构截图：

- **模拟模式相关**：确认 `Simulation Mode`、`Edit Filters`与暂停状态；当前schema提供原生单步时可辅助推进，每步检查新事件及游标，详见 [实验2模拟取证](lab2-simulation.md)。
- **Inspect 工具**：查看 `MAC Table` 等面板。
- **Traffic Generator**：PC 的 `Desktop > Traffic Generator`，构造广播和并发发送。
- **Command Prompt 截图**：PC命令用当前暴露的 `pt_host_command` 或GUI，IOS用 `pt_cli`。
  API命令已执行时，独立打开 `Desktop > Command Prompt` 中已有输出并验证画面；
  不为截图重复ping或改变模拟缓存。若界面没有该结果，保留API输出并注明截图尚未取得。
- **挂载脚本模块**：`Extensions → Scripting → Configure PT Script Modules → Add…`，当前实例缺失才加载，已启动时复用。

这几步之前先把窗口摆正、最大化或按实验图缩放，截出来的图才能直接进报告。
