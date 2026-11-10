# Packet Tracer 陷阱清单

按 PT 9.0.1 的实测整理。写原始 JS 之前先读这里；不确定的方法一律不要试，先探测。

## 会让 PT 崩溃或冻死的操作

| 操作 | 后果 |
|---|---|
| `for...in` 枚举 PT 原生对象 | **整个 PT 崩溃退出**，不是 JS 异常，`try/catch` 拦不住 |
| 脚本引擎里未捕获的错误 | 弹出模态框，PT 冻住直到有人点掉 |
| 设备名里放引号、斜杠、换行 | 保存后重开 `.pkt` 时 PT 崩溃 |
| 猜一个不存在的 API 方法并直接调用 | 同上，模态框冻死 |

因此在脚本引擎里：

- 只调用本文件列出过的，或工具返回过的 API。
- 每个原生调用都包在 `try/catch` 里，出错返回 false 而不是抛出去。
- 探测未知对象时一次只调一个已知 getter，把结果转成字符串看，不要遍历。
- 出错后先确认 PT 还活着，再继续。

## 脚本引擎的 API 事实

| 事项 | 正确写法 |
|---|---|
| 拿全部设备 | `getDevices(filter)` 返回**名字字符串数组**，不是对象数组 |
| 拿设备对象 | `ipc.network().getDevice("R1")`，**没有全局 `getDevice`**，可能返回 null |
| 拿端口 | `d.getPorts()` 返回**端口名字符串数组**，没有 `size()`、`at()`、`getName()` |
| 单端口 | `d.getPort("GigabitEthernet0/0")` |
| 建设备 | `lw.addDevice(type, model, x, y)`，坐标是图标左上角，约 50x40 px |
| 连线 | `lw.createLink(d1, p1, d2, p2, cableEnum)` |
| 移动 | `d.moveToLocation(x, y)`，读回的坐标和要的会略有差异，PT 自己会调整 |
| 装模块 | `d.addModule(slot, allModuleTypes[model], modelName)`，**slot 是字符串**，如 `"0/0"` |
| 装模块失败 | 返回 `false` 而不是抛错，必须检查返回值 |
| 命令行 | 用 `d.getCommandLine()`，它有 `getOutput()`、`enterCommand()`、`getPrompt()` |
| 主机网关 | `d.getProcess("HostIpProcess").getDefaultGateway()`，设备上直接取是 undefined |
| 判断类型 | `getClassName()` 不可靠，3560 回答 "Router"，2960 回答 "CiscoDevice"，要用 `getModel()` |

## 常见踩坑

- **路由器刚部署出来停在初始配置对话** `Would you like to enter the initial configuration dialog?`，
  此时发 `ping` 会被当成 yes/no 的回答吃掉。先发 `no`，再发一条空命令清掉 `Press RETURN to get started.`。
- **没连 XMLHttpRequest**：脚本引擎没有 `XMLHttpRequest`，HTTP 通道只能放在扩展的 webview 里，
  脚本引擎自己只能读写文件。
- **`runCode` 出错**返回 `false`，错误信息在 `runCodeLastError`，不要指望抛异常。
- **线缆枚举**：交叉线是 `"cross"`，不是 `"crossover"`；`getConnectionType()` 返回的是字符串 `"8100"`、`"8101"`。
- **重名**：把设备改成已存在的名字会被拒绝，早期版本允许并导致其中一个设备无法按名访问。
- **`pt_apply_*` 的返回值**：只有 `verified: true` 表示 IOS 全部接受，
  `verification` 里有 `verified`、`rejected`、`error`、`unverified` 四种，`unverified` 表示根本没回应。
- **主机配置并非这个 schema**：当前 `pt_host_ip_config` 未提供 verified，用面板、接口及 ipconfig 独立读回。
- **isError=false 可包装超时**：仍要检查正文的 No response from PT / NOT connected，失败后先做存活检查。
- **历史版本首次连接失败**：只读的 `pt_bridge_status` 可以补试一次。新版上游已修复首次连接问题；
  仍失败应读取真实错误，不能无限重试，更不能重复部署或配置。
- **首次 ping 或 PDU 会死在 ARP**，重发一次再判断。
- **部署报告只校验设备和连线存在**，主机 IP 可能滞后几秒，用 `pt_read_dhcp_leases` 或设备面板确认。

## `.pkt` 不能当接口用

实测一份 85 KB 的真实实验文件：信息熵 8.00，zlib、gzip、bz2、lzma 全部解不开，
文件里没有任何明文片段。PT 8 以后 `.pkt` 和 `.pka` 都是加密的。

结论：不要写"生成 `.pkt` 再让 PT 打开"的工具，也不要试图改文件注入配置。
要建拓扑就用脚本引擎，要存盘就用 MCP 的存档工具。
中文存档基名曾被转换为 topology.pkt；优先 ASCII 基名，信任实际返回路径并确认文件存在，勿据请求名虚报文件。

## 明确做不到的事

遇到下面这些，直接说明做不到，不要反复试：

- 无线客户端的 WPA/WEP 配置，相关 API 一律抛 "invalid vector subscript"，只能 GUI 手配。
- 2911 上配置 CME 电话服务，换 2811。
- 把 IoT 程序当文件写入，文件管理器对任何路径都返回 "File not exist"。
- 读取 NetFlow 流表，导出器只有配置接口，没有读取接口。
- 通过 API 拿到 QoS 类名，只能从 running-config 里读。
- 手写或注入 `.pkt` 二进制；PT 自带保存、另存或 MCP 原生存档仍可使用。

## 版本核对

陷阱来源是早期 PT/MCP 实测记录，不代表所有新版本。先读取当前安装的 packet-tracer skill 与工具 schema。
上游新版已更新扩展面板与首次 bridge 连接行为，见 [发布记录](https://github.com/Mats2208/MCP-Packet-Tracer/releases)。
