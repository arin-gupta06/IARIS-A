#!/usr/bin/env python3
"""
IARIS Executable Bundle Builder
================================
Builds a complete standalone Windows executable with both frontend and backend.

Usage:
    python build_exe.py [--clean]
    
This script:
    1. Builds the React frontend (npm run build)
    2. Prepares the Python environment
    3. Packages everything using electron-builder
    4. Creates the final .exe installer in dist-electron/
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from typing import Optional

# Color output for clarity
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_step(msg: str):
    print(f"{Colors.BOLD}{Colors.CYAN}[BUILD]{Colors.END} {msg}")

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def run_command(
    cmd: list[str],
    cwd: Optional[str] = None,
    check: bool = True,
    env: Optional[dict[str, str]] = None,
) -> bool:
    """Run a shell command and return success status."""
    try:
        print(f"  $ {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=False, env=env)
        return result.returncode == 0
    except Exception as e:
        print_error(f"Failed to run: {' '.join(cmd)}")
        print_error(str(e))
        return False

def find_npm() -> Optional[str]:
    """Find npm executable in common locations."""
    common_paths = [
        Path("C:/Program Files/nodejs/npm.cmd"),
        Path("C:/Program Files (x86)/nodejs/npm.cmd"),
        Path("D:/Node/npm.cmd"),
        Path("D:/nodejs/npm.cmd"),
    ]
    
    for path in common_paths:
        if path.exists():
            return str(path)
    
    # Try PATH
    try:
        result = subprocess.run(["where", "npm"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    return None


def resolve_venv_path(project_root: Path) -> Optional[Path]:
    """Resolve virtual environment path, preferring .venv then venv."""
    candidates = [project_root / ".venv", project_root / "venv"]
    for candidate in candidates:
        if (candidate / "Scripts" / "python.exe").exists():
            return candidate
    return None

def main():
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)

    print(f"\n{Colors.HEADER}{Colors.BOLD}╔══════════════════════════════════════════════════════╗")
    print(f"║         IARIS Executable Bundle Builder v1.0         ║")
    print(f"╚══════════════════════════════════════════════════════╝{Colors.END}\n")

    # Find npm
    npm_exe = find_npm()
    if not npm_exe:
        print_error("npm not found. Please install Node.js from https://nodejs.org/")
        return 1
    
    print_success(f"Found npm at: {npm_exe}\n")

    # Parse arguments
    clean = "--clean" in sys.argv

    if clean:
        print_step("Cleaning previous builds...")
        for path in ["frontend/dist", "dist-electron", "frontend/node_modules/.vite"]:
            if Path(path).exists():
                print(f"  Removing {path}...")
                shutil.rmtree(path, ignore_errors=True)
        print_success("Clean complete")

    # Step 1: Install/update backend dependencies
    print_step("Ensuring Python environment...")
    venv_path = resolve_venv_path(project_root)
    if not venv_path:
        print("  Virtual environment not found. Please run:")
        print("    python -m venv .venv")
        print_error("Setup required before building")
        return 1
    print_success(f"Python venv exists: {venv_path.name}")

    # Step 2: Build frontend
    print_step("Building React frontend...")
    frontend_root = project_root / "frontend"
    
    if not (frontend_root / "node_modules").exists():
        print("  Installing npm dependencies...")
        if not run_command([npm_exe, "install"], cwd=str(frontend_root)):
            print_error("npm install failed")
            return 1
    
    if not run_command([npm_exe, "run", "build"], cwd=str(frontend_root)):
        print_error("Frontend build failed")
        return 1
    
    if not (frontend_root / "dist").exists():
        print_error("Frontend build did not produce dist/ folder")
        return 1
    print_success("Frontend built successfully")

    # Step 3: Package Python backend with PyInstaller
    print_step("Preparing Python environment for packaging...")
    
    # Upgrade pip in venv
    python_exe = venv_path / "Scripts" / "python.exe"
    pip_exe = venv_path / "Scripts" / "pip.exe"
    
    if not python_exe.exists():
        print_error(f"Python executable not found at {python_exe}")
        return 1
    
    # Ensure pip is up to date
    print("  Upgrading pip...")
    run_command([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], check=False)
    
    # Install PyInstaller if not present
    print("  Checking for PyInstaller...")
    run_command([str(python_exe), "-m", "pip", "install", "pyinstaller>=6.0.0"], check=False)
    
    print_success("Python environment ready")

    # Step 4: Configure electron-builder
    print_step("Configuring electron-builder...")
    
    # Verify electron-builder configuration in package.json
    package_json_path = frontend_root / "package.json"
    with open(package_json_path, 'r') as f:
        package_json = json.load(f)
    
    if "build" not in package_json:
        print_error("electron-builder configuration not found in package.json")
        return 1
    
    print_success("electron-builder configured")

    # Step 5: Build Electron app
    print_step("Building Electron executable...")
    
    electron_build_env = {**os.environ, "CSC_IDENTITY_AUTO_DISCOVERY": "false"}
    if not run_command([npm_exe, "run", "electron:build"], cwd=str(frontend_root), env=electron_build_env):
        print_error("Electron build failed")
        return 1
    
    # Check for output
    dist_electron = frontend_root / "dist-electron"
    if not dist_electron.exists():
        print_error("Build output not found at dist-electron/")
        return 1
    
    # Find the .exe file
    exe_files = list(dist_electron.glob("*.exe"))
    if exe_files:
        exe_path = exe_files[0]
        print_success(f"Executable created: {exe_path.relative_to(project_root)}")
        print_success(f"Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print_error("No .exe file found in build output")
        return 1

    print(f"\n{Colors.GREEN}{Colors.BOLD}╔══════════════════════════════════════════════════════╗")
    print(f"║              BUILD SUCCESSFUL! ✓                     ║")
    print(f"╚══════════════════════════════════════════════════════╝{Colors.END}\n")

    print("📦 Your executable is ready!")
    print(f"📍 Location: {dist_electron.relative_to(project_root)}/")
    print(f"🚀 Next step: Double-click the .exe to run IARIS\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
