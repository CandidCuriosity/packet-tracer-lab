#!/usr/bin/env bash
# Standard-library Python implementation; no jq dependency.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/install_pts.py" "$@"
