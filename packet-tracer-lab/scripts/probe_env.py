#!/usr/bin/env python3
"""Read-only Notebook checks. Installation readiness is distinct from live readiness."""
import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from pt_runtime import matching_windows


def run(command, timeout=15):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 124, ""


def accessibility_address(raw):
    try:
        value = ast.literal_eval(raw)
        if isinstance(value, tuple) and len(value) == 1 and isinstance(value[0], str) and value[0].startswith("unix:"):
            return value[0]
    except (SyntaxError, ValueError):
        pass
    raise ValueError("AT-SPI GetAddress returned no usable unix address")


def doctor_checks(raw):
    data = json.loads(raw)
    ready = data.get("readiness") if isinstance(data, dict) else None
    if not isinstance(ready, dict):
        raise ValueError("doctor returned no readiness object")
    checks = []
    for key in ("can_build_accessibility_tree", "can_capture_screenshots"):
        checks.append((ready.get(key) is True, f"readiness.{key}"))
    blockers = ready.get("blockers")
    checks.append((isinstance(blockers, list) and not blockers, "readiness.blockers is an empty list"))
    return checks


def probe(workspace, phase="ready", documents=None):
    workspace = Path(workspace)
    desktop = Path(os.environ.get("DESKTOP_DIR", str(workspace / "desktop")))
    pt = Path(os.environ.get("PT_BASE", str(workspace / "software/packettracer")))
    runner = desktop / "bin/desktop-run"
    cul = desktop / "bin/computer-use-linux-session"
    checks = []

    def add(name, passed, detail="", runtime=False):
        status = "PASS" if passed else "WARN" if runtime and phase == "installed" else "FAIL"
        checks.append({"name": name, "status": status, "detail": detail})

    def session(*args):
        return run(["bash", str(runner), *args])

    add("linux_host", sys.platform.startswith("linux"), sys.platform)
    add("workspace", workspace.is_dir(), str(workspace))
    entrypoints = list(pt.glob("*/squashfs-root/AppRun"))
    add("pt_appimage_entry", bool(entrypoints), str(pt))
    add("desktop_start_script", (workspace / "start-desktop.sh").is_file())
    add("pt_recover_script", (workspace / "recover-packettracer.sh").is_file())
    uvx = shutil.which("uvx")
    add("uvx_in_current_path", bool(uvx), uvx or "source boot.sh or use the persistent uvx path")
    codex_home = os.environ.get("CODEX_HOME", "")
    add("persistent_codex_home", Path(codex_home).resolve() == (workspace / ".codex").resolve() if codex_home else False,
        "CODEX_HOME is checked in the current shell; it is not silently overridden")
    # Accept the discovered location; do not create a symlink just to satisfy a probe.
    candidates = [Path(documents)] if documents else [workspace / "Cisco_Packet_Tracer_实验步骤", workspace / "111/Cisco_Packet_Tracer_实验步骤"]
    found_documents = next((path for path in candidates if path.is_dir()), None)
    add("experiment_documents", found_documents is not None,
        str(found_documents) if found_documents else "Set --documents to the actual directory")
    for name in ("packet-tracer", "packet-tracer-lab"):
        locations = [workspace / ".agents/skills" / name, workspace / ".codex/skills" / name]
        add(f"skill_{name}", any((root / "SKILL.md").is_file() for root in locations),
            "Presence does not prove discovery; confirm in a fresh Codex session")

    runnable = runner.is_file() and os.access(runner, os.X_OK)
    add("desktop_run", runnable, str(runner), runtime=True)
    add("session_env", (desktop / "run/session.env").is_file(), runtime=True)
    add("cul_session", cul.is_file() and os.access(cul, os.X_OK), runtime=True)
    if runnable:
        code, windows = session("wmctrl", "-lp", "-x")
        pid_code, pids = run(["pgrep", "-x", "PacketTracer"])
        matches = matching_windows(windows, pids) if code == 0 and pid_code == 0 else []
        add("x_session", code == 0, "wmctrl -lp -x", runtime=True)
        add("pt_window", bool(matches), "WM_CLASS=PacketTracer and matching live PID required; browser title is insufficient", runtime=True)
        code, enabled = session("gdbus", "call", "--session", "--dest", "org.a11y.Bus", "--object-path", "/org/a11y/bus",
                                "--method", "org.freedesktop.DBus.Properties.Get", "org.a11y.Status", "IsEnabled")
        add("atspi_enabled", code == 0 and "true" in enabled, runtime=True)
        code, raw_address = session("gdbus", "call", "--session", "--dest", "org.a11y.Bus", "--object-path", "/org/a11y/bus",
                                    "--method", "org.a11y.Bus.GetAddress")
        try:
            if code != 0:
                raise ValueError("GetAddress failed")
            address = accessibility_address(raw_address)
            code, names = session("gdbus", "call", "--address", address, "--dest", "org.freedesktop.DBus", "--object-path", "/org/freedesktop/DBus",
                                  "--method", "org.freedesktop.DBus.ListNames")
            add("atspi_registry", code == 0 and "org.a11y.atspi.Registry" in names,
                "Registry queried on its accessibility bus, not on the session bus", runtime=True)
        except ValueError as error:
            add("atspi_registry", False, str(error), runtime=True)
    if cul.is_file() and os.access(cul, os.X_OK):
        code, output = run(["bash", str(cul), "doctor"], timeout=60)
        try:
            if code != 0:
                raise ValueError(f"doctor exited {code}")
            for passed, name in doctor_checks(output):
                add(name, passed, runtime=True)
        except (ValueError, TypeError) as error:
            add("cul_doctor", False, str(error), runtime=True)

    add("extension_downloaded", any((pt / "ext-modules").glob("*.pts")),
        "File presence does not prove that PT has mounted it", runtime=True)
    if shutil.which("codex"):
        code, servers = run(["codex", "mcp", "list"])
        for name in ("packet-tracer", "computer-use-linux"):
            add(f"mcp_registered_{name}", code == 0 and name in servers,
                "Registration only; live connection and tools must be checked inside Codex", runtime=True)
    else:
        add("codex_command", False, runtime=True)
    return {"phase": phase, "checks": checks, "passed": sum(c["status"] == "PASS" for c in checks),
            "failed": sum(c["status"] == "FAIL" for c in checks), "warnings": sum(c["status"] == "WARN" for c in checks),
            "live_bridge_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path("/mnt/workspace"))
    parser.add_argument("--phase", choices=("installed", "ready"), default="ready")
    parser.add_argument("--documents", type=Path, help="Actual experiment document directory; overrides path candidates")
    parser.add_argument("--json", action="store_true", help="JSON to stdout; no files are modified")
    args = parser.parse_args()
    result = probe(args.workspace, args.phase, args.documents)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for check in result["checks"]:
            print(f"[{check['status']}] {check['name']}: {check['detail']}")
        print(f"PASS {result['passed']}, FAIL {result['failed']}, WARN {result['warnings']}")
        print("Next: confirm actual MCP connection/tools and pt_bridge_status inside Notebook Codex.")
    return int(result["failed"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
