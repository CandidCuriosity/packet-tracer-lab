# 部署与加载

Skill只提供流程和辅助脚本；Packet Tracer、MCP服务与桌面环境需单独准备。

## 安装文件

使用完整packet-tracer-lab目录，SKILL.md直接位于目录下，保留agents、references、scripts。
解压到新staging目录，再指定实际技能父目录部署，例如：

```bash
python3 packet-tracer-lab/scripts/deploy_skill.py --dest /mnt/workspace/.agents/skills
python3 packet-tracer-lab/scripts/deploy_skill.py --dest /mnt/workspace/.agents/skills --check
```

原环境用.codex/skills时明确指定原父目录；不要为了安装同时重复部署多份。
--check只读比较；相同内容重复安装返回already_current；内容不同默认保留，明确更新加--update并备份旧版到扫描目录之外。
不为安装Skill覆盖现有boot脚本、MCP配置或恢复脚本。

## 当前会话加载与工具

重开Agent会话，显式调用$packet-tracer-lab，报告实际读取的SKILL.md路径与版本，确认相对参考和脚本存在。
检查当前实际扫描目录与客户端支持的技能发现方式，见 [Codex技能说明](https://developers.openai.com/codex/skills)。
分别确认技能已读取、MCP已注册、当前工具已连接、PT模块已启动。注册清单、文件存在或短暂CONNECTED不能混为一项。
先只读取bridge及真正拓扑/metadata，再按任务进入配置。只读首次连接可有限补试；改变超时后先读回，不盲重发。

环境与恢复见 [Notebook环境](env-notebook.md)、[排障指南](troubleshooting.md)。
交付自己的实验证据；网络、报告格式、原生保存与重开分项记录，不把未执行项写成通过。
