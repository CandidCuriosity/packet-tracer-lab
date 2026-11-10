#!/usr/bin/env python3
"""Install a .pts asset without overwriting an existing module or leaving partial files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.request import Request, urlopen


def read_url(url):
    if not url.startswith("https://"):
        raise ValueError("Asset URL must use HTTPS")
    with urlopen(Request(url, headers={"User-Agent": "packet-tracer-lab", "Accept": "application/vnd.github+json"}), timeout=60) as response:
        return response.read()


def select_asset(release, pattern):
    assets = [item for item in release.get("assets", []) if re.search(pattern, item.get("name", ""))]
    if len(assets) != 1:
        raise ValueError(f"Expected one matching .pts asset, found {len(assets)}; specify --asset-re")
    item = assets[0]
    name = item.get("name", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.pts", name) or name.startswith("."):
        raise ValueError("Unsafe or invalid asset filename")
    digest = item.get("digest")
    if digest is not None and not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise ValueError("Unsupported or malformed release digest")
    return name, item["browser_download_url"], digest.split(":", 1)[1].lower() if digest else None


def install_bytes(data, dest, name, expected=None, replace=False):
    dest = Path(dest)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.pts", name) or name.startswith("."):
        raise ValueError("Unsafe or invalid extension filename")
    if not data:
        raise ValueError("Empty extension")
    actual = hashlib.sha256(data).hexdigest()
    if expected and actual != expected.lower():
        raise ValueError(f"SHA256 mismatch: expected {expected.lower()}, got {actual}")
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    if target.is_symlink():
        raise ValueError("Will not replace a symlink")
    backup = None
    if target.exists():
        old = target.read_bytes()
        if old == data:
            return {"path": str(target), "sha256": actual, "bytes": len(data), "status": "already_current", "checksum_verified": bool(expected)}
        if not replace:
            raise ValueError("An existing extension differs; mount it first or use --replace to keep a backup")
        backup = dest / (name + "." + hashlib.sha256(old).hexdigest()[:12] + ".bak")
        if backup.exists() and backup.read_bytes() != old:
            raise ValueError("Backup conflict; existing files were preserved")
        if not backup.exists():
            shutil.copy2(target, backup)
    with tempfile.NamedTemporaryFile(prefix=".pts-", dir=dest, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": str(target), "sha256": actual, "bytes": len(data), "status": "installed", "checksum_verified": bool(expected), "backup": str(backup) if backup else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="source", type=Path)
    parser.add_argument("--dest", type=Path, default=Path(os.environ.get("PT_BASE", "/mnt/workspace/software/packettracer")) / "ext-modules")
    parser.add_argument("--repo", default=os.environ.get("REPO", "Mats2208/MCP-Packet-Tracer"))
    parser.add_argument("--tag", help="Pin a release tag instead of querying latest")
    parser.add_argument("--asset-re", default=os.environ.get("ASSET_RE", r"\.pts$"))
    parser.add_argument("--sha256", help="Trusted 64-character checksum (required when release has no digest)")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.sha256 and not re.fullmatch(r"[0-9a-fA-F]{64}", args.sha256):
        parser.error("--sha256 must have 64 hexadecimal characters")
    try:
        if args.source:
            name = args.source.name
            if not re.fullmatch(r"[A-Za-z0-9_.-]+\.pts", name) or name.startswith("."):
                raise ValueError("Local source must have a safe .pts filename")
            data, expected = args.source.read_bytes(), args.sha256
            if not expected:
                print("WARN: local file has no trusted checksum; only its local hash will be recorded")
        else:
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
                raise ValueError("Invalid owner/repository")
            if args.tag and not re.fullmatch(r"[A-Za-z0-9_.-]+", args.tag):
                raise ValueError("Invalid release tag")
            route = f"tags/{args.tag}" if args.tag else "latest"
            release = json.loads(read_url(f"https://api.github.com/repos/{args.repo}/releases/{route}"))
            name, url, published = select_asset(release, args.asset_re)
            expected = args.sha256 or published
            if not expected:
                raise ValueError("Release has no SHA256 digest; supply --sha256 from a trusted source")
            if args.sha256 and published and args.sha256.lower() != published:
                raise ValueError("Supplied checksum disagrees with release digest")
            data = read_url(url)
            print(f"Release: {release.get('tag_name', '?')}")
        print(json.dumps(install_bytes(data, args.dest, name, expected, args.replace), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, re.error) as error:
        parser.exit(1, f"ERROR: {error}\n")
    print("\nNext: Extensions -> Scripting -> Configure PT Script Modules -> Add…")
    print("Select the printed .pts path, Start the module, then open Extensions -> MCP BUILDER.")
    print("Discover current tools; pt_bridge_status must confirm a working bridge before topology changes.")
    print("Installing a skill or downloading .pts does not register MCP or mount the module.")


if __name__ == "__main__":
    main()
