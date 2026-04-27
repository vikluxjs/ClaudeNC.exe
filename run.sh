#!/usr/bin/env bash
# ClaudeNC.exe — Launcher for Linux / macOS

set -e

echo ""
echo "  ========================================="
echo "   ClaudeNC.exe  v3.0  --  Launcher"
echo "  ========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Find Python 3.10+ ─────────────────────────────────────────────
PYTHON=""
for cmd in python3 python python3.13 python3.12 python3.11 python3.10; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        MAJOR="${VER%%.*}"
        MINOR="${VER##*.}"
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "  [FAIL] Python 3.10+ не найден."
    echo ""
    OS_TYPE="$(uname -s)"
    if [ "$OS_TYPE" = "Darwin" ]; then
        echo "  macOS: установите через Homebrew:"
        echo "         brew install python@3.12"
    else
        echo "  Linux: установите через пакетный менеджер:"
        echo "         sudo apt install python3.12   # Debian/Ubuntu"
        echo "         sudo dnf install python3.12   # Fedora"
        echo "         sudo pacman -S python          # Arch"
    fi
    echo ""
    exit 1
fi

echo "  [  OK  ] Python $VER ($PYTHON)"

# ── Run universal launcher ────────────────────────────────────────
cd "$SCRIPT_DIR"
exec "$PYTHON" launch.py
