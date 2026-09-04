#!/bin/zsh
STUDIO_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
exec /opt/homebrew/bin/python3 "$STUDIO_DIR/launch.py" --demo little-gravity
