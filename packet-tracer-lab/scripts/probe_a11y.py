#!/usr/bin/env python3
"""探测 Packet Tracer 在 AT-SPI 无障碍树里暴露了什么。

用途：回答"无障碍树能不能用来操控 PT"这件事。重点是看树里有没有
菜单、对话框、面板，以及有没有画布、设备名、端口名这类节点。

用法（必须在桌面会话里跑，否则看不到 DISPLAY 和 AT-SPI 总线）：
    bash /mnt/workspace/desktop/bin/desktop-run python3 scripts/probe_a11y.py
    bash /mnt/workspace/desktop/bin/desktop-run python3 scripts/probe_a11y.py --max-nodes 800

依赖 python3-pyatspi（或 gir1.2-atspi-2.0）。缺失时本脚本只打印安装命令并退出 2。
输出：先一段结论，再一段树摘要。只读，不点击、不输入。
"""

import argparse
import json
import re
import sys

# 这些名字出现，说明树里能看到拓扑相关内容
DEVICE_HINT = re.compile(
    r"(PC\d|Router\d|Switch\d|Server\d|Laptop\d|Fa0|GigabitEthernet|Serial0|console|topology)",
    re.IGNORECASE,
)
# 这些角色出现，说明画布之类的东西也可能有节点
CANVAS_HINT = re.compile(r"(canvas|drawing|graphic|scene|viewport)", re.IGNORECASE)


def load_atspi():
    try:
        import pyatspi  # noqa: F401
        return "pyatspi"
    except ImportError:
        pass
    try:
        import gi

        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi  # noqa: F401
        return "gi"
    except Exception:
        return None


def name_of(node):
    for attr in ("name", "get_name"):
        try:
            v = getattr(node, attr)
            return v() if callable(v) else v
        except Exception:
            continue
    return None


def role_of(node):
    for attr in ("getRoleName", "get_role_name"):
        try:
            return getattr(node, attr)()
        except Exception:
            continue
    r = getattr(node, "getRole", None)
    if r:
        try:
            return str(r())
        except Exception:
            pass
    return "?"


def children_of(node):
    # pyatspi exposes childCount + getChildAtIndex; GI uses snake_case methods.
    try:
        n = node.childCount
    except Exception:
        n = None
    if n is not None:
        out = []
        for i in range(n):
            try:
                child = node.getChildAtIndex(i)
            except Exception:
                continue
            if child is not None:
                out.append(child)
        return out
    for attr in ("getChildCount", "get_child_count"):
        fn = getattr(node, attr, None)
        if not fn:
            continue
        try:
            n = fn()
        except Exception:
            return []
        out = []
        for i in range(n):
            for getter in ("getChildAtIndex", "getChildAt", "get_child_at_index"):
                g = getattr(node, getter, None)
                if not g:
                    continue
                try:
                    c = g(i)
                except Exception:
                    c = None
                if c is not None:
                    out.append(c)
                    break
        return out
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-nodes", type=int, default=400, help="最多打印多少个节点")
    ap.add_argument("--max-depth", type=int, default=8, help="最大递归深度")
    ap.add_argument("--tree", action="store_true", help="打印节点列表（可能截断）")
    ap.add_argument("--json", action="store_true", help="只输出结构化 JSON")
    args = ap.parse_args()
    if args.max_nodes < 1 or args.max_depth < 0:
        ap.error("max-nodes 必须大于 0，max-depth 不能小于 0")

    flavor = load_atspi()
    if flavor is None:
        if args.json:
            print(json.dumps({"error": "AT-SPI bindings missing", "tree_scoped": False}, ensure_ascii=False))
            return 2
        print("找不到 AT-SPI 绑定。先装：apt-get install -y python3-pyatspi")
        print("或：apt-get install -y gir1.2-atspi-2.0")
        return 2
    if not args.json:
        print(f"AT-SPI 绑定：{flavor}")

    if flavor == "pyatspi":
        import pyatspi

        desktop = pyatspi.Registry.getDesktop(0)
    else:
        from gi.repository import Atspi

        desktop = Atspi.get_desktop(0)

    apps = children_of(desktop)
    if not args.json:
        print(f"注册表里的应用数：{len(apps)}")
    target = None
    for a in apps:
        nm = name_of(a) or ""
        if "tracer" in nm.lower():
            target = a
            if not args.json:
                print(f"找到目标应用：{nm}")
        else:
            if not args.json:
                print(f"  - {nm}")
    if target is None:
        if args.json:
            print(json.dumps({"error": "Packet Tracer is not registered", "tree_scoped": False}, ensure_ascii=False))
            return 1
        print("\n没有名字含 tracer 的应用。确认 PT 正在运行，并且本命令在桌面会话里执行。")
        print("也可以打开任意界面元素后重试，Qt 应用有时要等窗口真正绘制才注册。")
        return 1

    stats = {"nodes": 0, "device_names": [], "canvas_roles": [], "roles": {}, "truncated": False,
             "tree_scoped": True, "application": name_of(target), "binding": flavor}
    lines = []

    def walk(node, depth, idx_path):
        if stats["nodes"] >= args.max_nodes or depth > args.max_depth:
            stats["truncated"] = True
            return
        stats["nodes"] += 1
        role = role_of(node)
        nm = name_of(node) or ""
        stats["roles"][role] = stats["roles"].get(role, 0) + 1
        if nm and DEVICE_HINT.search(nm) and len(stats["device_names"]) < 40:
            stats["device_names"].append(f"{role}: {nm}")
        if CANVAS_HINT.search(role) and len(stats["canvas_roles"]) < 20:
            stats["canvas_roles"].append(f"{role}: {nm}")
        if args.tree:
            lines.append(f"{'  ' * depth}{idx_path} {role} | {nm[:70]}")
        for i, c in enumerate(children_of(node)):
            walk(c, depth + 1, f"{idx_path}.{i}")

    walk(target, 0, "0")

    if args.json:
        stats["tree"] = lines
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    print(f"\n遍历节点数：{stats['nodes']}（上限 {args.max_nodes}，深度上限 {args.max_depth}）")
    print(f"是否截断：{stats['truncated']}。截断时不能用未发现节点证明其不存在。")
    roles = sorted(stats["roles"].items(), key=lambda kv: -kv[1])
    print("角色分布（前 15）：")
    for role, cnt in roles[:15]:
        print(f"  {cnt:5d}  {role}")
    print("\n画布类角色：")
    print("  没有" if not stats["canvas_roles"] else "\n".join(f"  {s}" for s in stats["canvas_roles"]))
    print("\n疑似设备或端口的名字：")
    print("  没有" if not stats["device_names"] else "\n".join(f"  {s}" for s in stats["device_names"]))

    print("\n判断：")
    if stats["device_names"] or stats["canvas_roles"]:
        print("  树里能看到拓扑相关节点。可以试着用元素定位做画布操作，但仍要先验证再依赖。")
    else:
        print("  当前已遍历的节点中未发现画布和设备节点；截断时不能判断整棵树。")
        print("  拓扑一律走脚本引擎，GUI 只用于菜单、对话框和模拟模式这类没有 API 的步骤。")
    if args.tree and lines:
        print("\n节点列表（截断）：")
        print("\n".join(lines[: args.max_nodes]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
