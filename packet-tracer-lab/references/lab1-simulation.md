# 实验1：广播与并发取证

广播泛洪、终端回复和共享介质冲突分别取证。ARP缺项可使部分回复缓冲，实际碰撞协议可能为ARP；执行时保存自己的配置、参数、trace和截图。

## 准备与分段

1. 读原实验1，复核 PC0–PC3 的 192.168.1.1–4/24、四条 straight 链路、Hub 真实端口和半双工状态。
   原工程可能附带 Power Distribution Device；按设备身份及链路验收，不能仅因总数为6就认定错误或删除它。
2. 先留存基线 ping 的真实输出。成功 ping 会影响 ARP 状态；记录发生过哪些测试，不能断言所有终端 ARP 缓存为空或都已预热。
3. 进入 Simulation 并暂停捕获，在最新画面中确认 Reset Simulation、过滤器和 Capture/Forward 的位置。
   广播与并发分段清理事件，保留模式；事件重置不证明 ARP 缓存已清空。
4. GUI 当前只显示 ICMP 时，读完整 trace 仍可能发现 ARP。调查 ARP 时保存现有过滤器再按需要显示 ARP；注明显示范围。
   每次输入后用当前画面和读回确认生效，不能用工具的 ok 或截图文件名代替验证。

## 广播：分别证明泛洪、回复、冲突

按原文在 PC0 Desktop > Traffic Generator 设置 PING、目标255.255.255.255、源192.168.1.1、Sequence=1、Single Shot。
保存最终参数画面，再 Send 和单步。每步读取当前暴露的 packet trace 工具，保留 decisions；工具名和参数先发现。

| 子项 | 验收证据 |
|---|---|
| 泛洪 | Hub 从源端口接收并向其余三端口转发；三个接收端实际处理广播 ICMP Echo Request |
| 回复 | 对每个接收端分别检查 Echo Reply 创建、ARP 查询、buffered/sent 及端口发送决策；创建回复不等于帧已经发出 |
| 共享介质冲突 | `collided_at_device` / `collided_on_link` 为 true 或明确 Layer 1 碰撞决策；标明实际帧协议 |
| 教材的三台 ICMP 回复同时冲突 | 三台回复实际发出且有对应碰撞序列，证据不足时记部分符合或未证实 |

碰撞的每一帧都要核对实际协议和设备位置，不能用教材预期替代观察。
不能把这些 ARP 帧改写为三台终端同时发出的 ICMP 回复，也不能仅凭 trace 的 source/destination 标签推断回复方向；结合 previous_device、in_port 与分层决策。
默认保留实际现象。若原文要求研究缓存影响，另开新副本做有记录的对照，逐次只改一项，不能回写此前结果。

## 并发：同一暂停时钟排队，再单步

1. 重置该段模拟事件、确认暂停并读回空事件；不依赖上一段残留帧。
2. 在 PC0 Command Prompt 提交 `ping 192.168.1.3`。确认请求实际进入 trace，再到 PC1 提交 `ping 192.168.1.4`，中间不推进模拟时钟。
3. 保存两条源端 ICMP 请求的 source、destination 和相同 sim_time。墙钟上几秒内连续输入不能证明模拟同时发送。
4. Capture/Forward 后分别保存 Hub 与端点帧。核对两条请求在 Hub 的碰撞标记、Layer 1 的 “This frame collided” 和端点的 “receives a collided frame”。
5. 普通目的 MAC 不匹配的 dropped 属正常单播过滤，不能计为冲突。trace 的 `clean:false`、`failures[]` 可能正是冲突实验所需结果；与 timeout/断连/桥接身份拒绝区分。

用当前两条源请求的相同sim_time与后续碰撞决策证明并发；GUI PDU Details与原始trace交叉核对，不使用旧截图替代当前证据。

## GUI 与交付边界

- Linux 的 Host 工具可能返回 API ping 成功，同时提示 GUI 展示只支持 Windows。按 API 输出验收 ping；需要命令窗口截图时单独用桌面工具打开，不盲目重发流量。
- 命令窗口输入后先确认实际入队。该轮曾有输入后 trace 仍为空，后续重新聚焦/提交才出现请求；不要凭“已输入”开始推进时间。
- 原生另存 ASCII 基名工程，核对返回路径、实际文件、metadata 与拓扑；报告分别列通过、部分符合、未完成。
- 当前结果 ZIP 如未附交付清单，只能验证 ZIP CRC 和包内文件一致性。历史 source_before 是来源基线，不能当本轮文件清单。
- 发布前核对报告引用的每个文件。并发 trace 可只在 tools.jsonl 里，若未另存独立 JSON，报告应指向实际 label；记录真实扩展加载和桥接修复操作。
