#!/usr/bin/env python3
"""Read-only PT identity check: match WM_CLASS and window PID to a live PT process."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time


def matching_windows(window_text, pid_text):
    pids = {int(line) for line in pid_text.splitlines() if line.strip().isdigit()}
    matches = []
    # wmctrl -lp -x: window-id, desktop, pid, instance.class, hostname, title.
    for line in window_text.splitlines():
        fields = line.split(None, 5)
        if len(fields) < 5 or not fields[2].isdigit():
            continue
        pid = int(fields[2])
        classes = fields[3].lower().split(".")
        if "packettracer" in classes and pid in pids:
            matches.append({"window_id": fields[0], "pid": pid, "wm_class": fields[3],
                            "title": fields[5] if len(fields) > 5 else ""})
    return matches


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return result.returncode, result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 124, ""


def snapshot(desktop):
    runner = Path(desktop) / "bin/desktop-run"
    code, windows = command(["bash", str(runner), "wmctrl", "-lp", "-x"])
    pid_code, pids = command(["bash", str(runner), "pgrep", "-x", "PacketTracer"])
    matches = matching_windows(windows, pids) if code == 0 and pid_code == 0 else []
    return {"ready": bool(matches), "windows": matches, "window_query_exit": code, "process_query_exit": pid_code,
            "live_bridge_verified": False}


def wait_for_runtime(desktop, timeout, stable_seconds, take_snapshot=snapshot, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    since = None
    identity = None
    while True:
        state = take_snapshot(desktop)
        current = tuple(sorted((window["pid"], window["window_id"]) for window in state["windows"]))
        now = clock()
        if state["ready"] and current:
            if current != identity:
                identity, since = current, now
            if now - since >= stable_seconds:
                state["stable_seconds"] = now - since
                return state
        else:
            identity, since = None, None
        if now >= deadline:
            # A transient window at the deadline does not satisfy the stability check.
            state["ready"] = False
            state["error"] = "PT process/window identity was not stable before timeout"
            return state
        sleep(min(0.5, deadline - now))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desktop", type=Path, default=Path(os.environ.get("DESKTOP_DIR", "/mnt/workspace/desktop")))
    parser.add_argument("--once", action="store_true", help="One identity snapshot; does not prove persistence")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--stable-seconds", type=float, default=2)
    args = parser.parse_args()
    if args.timeout <= 0 or args.stable_seconds < 0 or args.stable_seconds > args.timeout:
        parser.error("Require timeout > 0 and 0 <= stable-seconds <= timeout")
    state = snapshot(args.desktop) if args.once else wait_for_runtime(args.desktop, args.timeout, args.stable_seconds)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return int(not state["ready"])


if __name__ == "__main__":
    raise SystemExit(main())
