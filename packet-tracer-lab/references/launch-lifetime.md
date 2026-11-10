# PT 与启动命令的生命周期

仅在PT由短期命令启动、命令结果收取后进程消失时使用；不为普通实验配置改写启动环境。

## 诊断与最小修复

nohup忽略SIGHUP，不能抵抗SIGKILL。先取得实际信号或退出状态，检查父进程、进程组、会话以及宿主资源限制。
如果证据支持进程被启动会话回收，实际恢复脚本可考虑仅在PT启动行增加setsid，例如：

```diff
- nohup env -u APPIMAGE "$app" > "$base/packettracer-launch.log" 2>&1 < /dev/null &
+ nohup setsid env -u APPIMAGE "$app" > "$base/packettracer-launch.log" 2>&1 < /dev/null &
```

先读当前脚本、确认工具和既有修复、备份后再修改；不要把示例当固定补丁。
setsid用于分离启动命令的进程组/会话，不保证绕过宿主或cgroup清理。
不要给所有桌面命令套setsid，也不要为更新Skill覆盖健康的恢复脚本或停止健康PT。

## 跨独立调用确认

1. 启动时记录主PT的PID/PPID/PGID/SID，交叉确认窗口class与存活PID。
2. 启动命令完成并收取后，另一次独立命令再确认主进程、窗口与只读bridge。
3. 分段采样，记录实际时长和缺口；最后取得真正的拓扑或metadata。

辅助progress-bar-server不能替代主工作区。一次脚本内部的检查不证明命令回收后的存活。
没有wait返回时不要宣称exit137；取得的是信号就报告信号。读不到内核/audit日志时不能据空记录排除OOM。
有限空闲观察也不能替代Simulation和完整实验验收，发信者未知时明确保留未知。
