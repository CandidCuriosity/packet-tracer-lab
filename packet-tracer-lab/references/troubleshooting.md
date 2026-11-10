# Notebook 排障指南

## 进程、窗口与 bridge 分别确认

登录浏览器可能与PT窗口同名。用WM_CLASS和存活PacketTracer PID交叉匹配，不能仅依赖标题。

```bash
python3 "<skill目录>/scripts/pt_runtime.py" --timeout 10 --stable-seconds 2
```

随后只读确认bridge，再取真正的拓扑或metadata。CONNECTED和短期窗口存在不能替代真实读回。
PT由短期命令启动时，另一次独立调用还要确认主进程仍存在，见 [启动生命周期](launch-lifetime.md)。

## 工具返回与配置读回

- 外层isError=false可包住timeout、NOT connected或桥接归属拒绝；读取正文，识别失败后暂停改变。
- `check_pt_reply.py`退出0仅表示收到未识别为失败的结果，不代表配置已经验收。
- Host配置未提供verified时，用实际字段、面板、ipconfig、接口和链路交叉验证，不虚构verified。
- Hub或Switch的ports可能为空；用当前拓扑与主机peer核对，不因此直接删链路或重建。

桥接正文出现NOT this MCP server's bridge与Refusing to send commands时，先查端口占用者的PID、命令行和会话归属。
不能向未知bridge写配置，也不能批量结束同名服务。保留仍被其他会话使用的实例，遗留实例的处置按当前授权进行。
实例内模块列表缺失时才加载已有.pts并Start，已运行时直接复用。

## GUI状态不一致

- New可能匹配多个节点；用最新具体元素，随后读回新工程确实为空。
- 子窗口有自己的window ID；UnknownObject或旧句柄失败后刷新窗口清单和树。
- AT-SPI点击、Toggle返回成功仍需看实际面板/勾选；要求整数坐标时使用整数。
- 子窗口截图先聚焦子窗口，避免主PT窗遮挡。拖动后端不可用时检查已有desktop-run/xdotool通道。
- API命令已执行时打开已有终端结果截图，不为展示重复发包。
- Inspect旧表、过滤器历史游标与待处理终端恢复见 [实验2取证](lab2-simulation.md)。

## 桌面授权与依赖

xprop出现Authorization required时，先用正确的desktop-run环境；必要时仅从已确认PT进程读取DISPLAY和XAUTHORITY路径后重试只读查询。
不要输出授权cookie或整份进程环境。授权失败不能单独证明PT退出。
PATH缺命令时检查已有绝对路径；不同Python解释器可能装有不同库。缺docx库不能证明模板文件缺失。

## 有限恢复与证据

已有工程先保存。重复的进程退出或工具断连在有限恢复后仍出现时，停止依赖PT的实验，保留原始返回和当前状态。
需要隔离原因时在独立副本中每轮只改一个因素，不根据CORS/system_bus_socket或普通dropped帧猜测根因。
原生保存核对实际路径、文件、metadata与拓扑；最终重开是单独验收项。
