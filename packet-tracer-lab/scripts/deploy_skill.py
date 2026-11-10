#!/usr/bin/env python3
"""Copy this skill to an explicit skills parent; verify bytes and preserve updates."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from datetime import datetime, timezone

NAME = "packet-tracer-lab"


def inventory(root):
    root = Path(root)
    result = {}
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"Bundle contains a symlink: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def validate_bundle(root):
    root = Path(root)
    text = (root / "SKILL.md").read_text(encoding="utf-8")
    if not re.match(r"\A---\r?\nname: packet-tracer-lab\r?\ndescription:", text):
        raise ValueError("Missing or unexpected skill manifest")
    files = inventory(root)
    if "agents/openai.yaml" not in files:
        raise ValueError("Missing agents/openai.yaml")
    for path in root.rglob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if ":" in target or target.startswith("#"):
                continue
            linked = (path.parent / target.split("#", 1)[0]).resolve()
            if not linked.is_relative_to(root.resolve()) or not linked.is_file():
                raise ValueError(f"Broken or escaping reference: {path.name} -> {target}")
    return files


def deploy(source, parent, update=False, check=False):
    source, parent = Path(source).resolve(), Path(parent).absolute()
    if parent.is_symlink():
        raise ValueError("Choose a real skills directory, not a symlink")
    parent = parent.resolve()
    target = parent / NAME
    expected = validate_bundle(source)
    if target.is_symlink():
        raise ValueError(f"Will not replace a symlink: {target}")
    if target.exists() and not target.is_dir():
        raise ValueError(f"Destination is not a directory: {target}")
    actual = inventory(target) if target.exists() else {}
    if check:
        if actual != expected:
            raise ValueError("Installation is missing or differs from this bundle")
        return {"status": "verified", "path": str(target), "files": len(expected)}
    if actual == expected:
        return {"status": "already_current", "path": str(target), "files": len(expected)}
    if target.exists() and not update:
        raise ValueError(f"Existing skill differs: {target}; use --update to retain a backup and replace it")
    if parent == source or parent.is_relative_to(source):
        raise ValueError("Destination cannot be inside the source skill")
    parent.mkdir(parents=True, exist_ok=True)
    backup = None
    with tempfile.TemporaryDirectory(prefix=".pt-skill-stage-", dir=parent) as staging:
        staged = Path(staging) / NAME
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if inventory(staged) != expected:
            raise ValueError("Staged copy does not match source")
        if target.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            # Keep backups outside skills/: avoid discovering an old skill twice.
            backup_parent = parent.parent / "skill-backups"
            backup_parent.mkdir(parents=True, exist_ok=True)
            backup = backup_parent / f"{NAME}-{stamp}"
            target.rename(backup)
        try:
            staged.rename(target)
        except Exception:
            if backup is not None:
                backup.rename(target)
            raise
    return {"status": "installed", "path": str(target), "files": len(expected), "backup": str(backup) if backup else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, required=True, help="Parent skills directory, NOT the skill directory itself")
    parser.add_argument("--update", action="store_true", help="Preserve a differing skill in skill-backups/ before replacement")
    parser.add_argument("--check", action="store_true", help="Read-only byte comparison; do not install")
    args = parser.parse_args()
    try:
        result = deploy(Path(__file__).resolve().parents[1], args.dest, args.update, args.check)
    except (OSError, ValueError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
