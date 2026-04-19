@echo off
REM IARIS Executable Bundle Builder - Windows Batch Script
REM This is a convenient alternative to using the Python build script
REM Usage: build_exe.bat [--clean]

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║      IARIS Executable Bundle Builder for Windows           ║
echo ║      Run this script from the project root directory       ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check if we're in the right directory
if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml not found!
    echo Please run this script from the IARIS project root directory.
    pause
    exit /b 1
)

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH!
    echo Please install Python 3.11+ and add it to your PATH.
    pause
    exit /b 1
)

REM Check for Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found in PATH!
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

REM Parse arguments
set CLEAN=0
if "%1"=="--clean" set CLEAN=1

echo [BUILD] Checking Python environment...
if not exist ".venv" if not exist "venv" (
    echo [BUILD] Virtual environment not found. Please run:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -e .
    pause
    exit /b 1
)

echo [BUILD] Virtual environment found.
echo.

REM Run the Python build script
echo [BUILD] Starting build process...
echo.

if %CLEAN%==1 (
    python build_exe.py --clean
) else (
    python build_exe.py
)

if errorlevel 1 (
    echo.
    echo ERROR: Build failed! Check the output above for details.
    pause
    exit /b 1
)

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              BUILD COMPLETED SUCCESSFULLY!                 ║
echo ║                                                            ║
echo ║  Your executable is ready in: frontend\dist-electron\     ║
echo ║  Double-click the .exe file to install IARIS              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Optional: Open the output folder
if exist "frontend\dist-electron" (
    echo.
    set /p OPEN="Open output folder now? (y/n) "
    if /i "!OPEN!"=="y" (
        start "" "frontend\dist-electron"
    )
)

pause
