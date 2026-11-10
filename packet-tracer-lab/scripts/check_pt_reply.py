#!/usr/bin/env python3
"""Inspect a captured MCP reply; a non-error envelope does not prove a PT operation succeeded."""
import argparse
import json
from pathlib import Path


def unwrap(capture):
    reply = capture
    if isinstance(reply, dict) and reply.get("status") == "fulfilled":
        reply = reply["value"]
    if isinstance(reply, dict) and "tool" in reply and "result" in reply:
        reply = reply["result"]
    envelope_error = isinstance(reply, dict) and reply.get("isError") is True
    if isinstance(reply, dict) and "structuredContent" in reply:
        structured = reply["structuredContent"]
        payload = structured.get("result", structured) if isinstance(structured, dict) else structured
    elif isinstance(reply, dict) and "content" in reply:
        payload = "\n".join(item["text"] for item in reply["content"] if item.get("type") == "text")
    else:
        payload = reply
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            pass
    return payload, envelope_error


def inspect(capture):
    payload, envelope_error = unwrap(capture)
    # These are observed PT failure replies, including ones marked isError:false.
    text = payload if isinstance(payload, str) else ""
    lowered = text.lower()
    disconnected = "not connected" in lowered
    timeout = "no response from pt" in lowered
    bridge_ownership_conflict = "not this mcp server's bridge" in lowered and "refusing to send commands" in lowered
    explicit_failure = isinstance(payload, dict) and (payload.get("ok") is False or payload.get("verified") is False or bool(payload.get("error")))
    status = "failed" if envelope_error or disconnected or timeout or bridge_ownership_conflict or explicit_failure else "response_received"
    verification = payload.get("verified") if isinstance(payload, dict) else None
    return {"status": status, "envelope_is_error": envelope_error, "pt_timeout": timeout,
            "disconnected": disconnected, "bridge_ownership_conflict": bridge_ownership_conflict,
            "reported_verified": verification,
            "independent_readback_required": True, "payload": payload}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reply", type=Path, help="Captured tool result JSON (read-only)")
    args = parser.parse_args()
    try:
        result = inspect(json.loads(args.reply.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"ERROR: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["status"] == "failed")


if __name__ == "__main__":
    raise SystemExit(main())
