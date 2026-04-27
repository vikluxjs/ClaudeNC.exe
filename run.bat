@echo off
title ClaudeNC.exe

where python >nul 2>&1
if errorlevel 1 (
    where python3 >nul 2>&1
    if errorlevel 1 (
        echo [FAIL] Python not found in PATH.
        echo Download Python 3.10+ from: https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during install.
        pause
        exit /b 1
    )
    set PYTHON=python3
) else (
    set PYTHON=python
)

%PYTHON% -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Python 3.10+ required.
    %PYTHON% --version
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

%PYTHON% launch.py
if errorlevel 1 pause
