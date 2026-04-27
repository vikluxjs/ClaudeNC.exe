#!/usr/bin/env python3
"""Universal launcher — checks OS, Python version, dependencies, then starts the app."""
from __future__ import annotations

import importlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ── colors for the launcher console output ────────────────────────────────────
if platform.system() == "Windows":
    os.system("")   # enable ANSI on Windows 10+

OK   = "\033[92m[  OK  ]\033[0m"
FAIL = "\033[91m[ FAIL ]\033[0m"
WARN = "\033[93m[ WARN ]\033[0m"
INFO = "\033[96m[ INFO ]\033[0m"
HEAD = "\033[1;97m"
RST  = "\033[0m"

ROOT = Path(__file__).parent

REQUIRED = {
    "PyQt6":   "PyQt6>=6.4.0",
    "dotenv":  "python-dotenv>=1.0.0",
}

MIN_PY = (3, 10)


def banner() -> None:
    print(f"""
{HEAD}╔══════════════════════════════════════════════════════╗
║           ClaudeNC.exe  v3.0  —  Launcher           ║
╚══════════════════════════════════════════════════════╝{RST}
""")


def check_python() -> None:
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    if v >= MIN_PY:
        print(f"  {OK}  Python {ver}")
    else:
        print(f"  {FAIL}  Python {ver}  (нужен {MIN_PY[0]}.{MIN_PY[1]}+)")
        print(f"\n  Скачать: https://www.python.org/downloads/")
        _pause_exit(1)


def check_os() -> None:
    s = platform.system()
    r = platform.release()
    m = platform.machine()
    print(f"  {OK}  ОС: {s} {r} ({m})")


def check_pip() -> None:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True, check=True,
        )
        print(f"  {OK}  pip доступен")
    except subprocess.CalledProcessError:
        print(f"  {WARN}  pip не найден, пытаюсь установить...")
        try:
            subprocess.run(
                [sys.executable, "-m", "ensurepip", "--upgrade"],
                check=True,
            )
            print(f"  {OK}  pip установлен")
        except Exception as e:
            print(f"  {FAIL}  Не удалось установить pip: {e}")
            _pause_exit(1)


def check_and_install_deps() -> None:
    missing: list[str] = []
    for module, package in REQUIRED.items():
        try:
            importlib.import_module(module)
            print(f"  {OK}  {package}")
        except ImportError:
            print(f"  {WARN}  {package}  — не найден, буду устанавливать...")
            missing.append(package)

    if missing:
        print(f"\n  {INFO}  Устанавливаю: {', '.join(missing)}\n")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing,
        )
        if result.returncode == 0:
            print(f"\n  {OK}  Все зависимости установлены.")
        else:
            print(f"\n  {FAIL}  Ошибка установки. Запустите вручную:")
            print(f"         pip install {' '.join(missing)}")
            _pause_exit(1)


def check_claude_cli() -> None:
    path = shutil.which("claude")
    if path:
        print(f"  {OK}  claude CLI: {path}")
    else:
        print(f"  {WARN}  claude CLI не найден в PATH.")
        print(f"         Установите: https://claude.ai/code")


def launch() -> None:
    app = ROOT / "msdos_claude.py"
    if not app.exists():
        print(f"  {FAIL}  Файл не найден: {app}")
        _pause_exit(1)

    print(f"\n  {INFO}  Запускаю приложение...\n")

    if platform.system() == "Windows":
        # pythonw — запуск без чёрного консольного окна
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        exe = str(pythonw) if pythonw.exists() else sys.executable
    else:
        exe = sys.executable

    os.execv(exe, [exe, str(app)])   # replace this process — no leftover console


def _pause_exit(code: int) -> None:
    if platform.system() == "Windows":
        input("\n  Нажмите Enter для выхода...")
    sys.exit(code)


if __name__ == "__main__":
    banner()
    print("  Проверка окружения:\n")
    check_os()
    check_python()
    check_pip()
    check_and_install_deps()
    check_claude_cli()
    launch()
