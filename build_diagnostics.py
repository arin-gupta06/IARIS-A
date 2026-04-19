#!/usr/bin/env python3
"""
IARIS Build Diagnostics Module
==============================
Helps validate your setup and diagnose build issues.

Usage:
    python -m iaris.build_diagnostics
    or
    python build_diagnostics.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Optional, Tuple

class Diagnostics:
    """Diagnostic tool for IARIS build setup."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.issues = []
        self.warnings = []
        self.info = []
    
    def log_info(self, msg: str):
        """Log informational message."""
        self.info.append(msg)
        print(f"ℹ  {msg}")
    
    def log_warning(self, msg: str):
        """Log warning message."""
        self.warnings.append(msg)
        print(f"⚠  {msg}")
    
    def log_issue(self, msg: str):
        """Log issue message."""
        self.issues.append(msg)
        print(f"✗  {msg}")
    
    def log_success(self, msg: str):
        """Log success message."""
        print(f"✓  {msg}")
    
    def check_python(self) -> bool:
        """Check Python version and packages."""
        print("\n━━━ Python Environment ━━━")
        try:
            version = subprocess.run(
                ["python", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()
            self.log_success(f"Python: {version}")
            
            # Parse version
            major, minor = map(int, version.split()[-1].split(".")[:2])
            if major < 3 or (major == 3 and minor < 11):
                self.log_issue(f"Python 3.11+ required, found {major}.{minor}")
                return False
            
            return True
        except Exception as e:
            self.log_issue(f"Python check failed: {e}")
            return False
    
    def check_nodejs(self) -> bool:
        """Check Node.js version and npm."""
        print("\n━━━ Node.js Environment ━━━")
        
        # Common Node.js installation locations
        common_paths = [
            Path("C:/Program Files/nodejs/node.exe"),
            Path("C:/Program Files (x86)/nodejs/node.exe"),
            Path("D:/Node/node.exe"),
            Path("D:/nodejs/node.exe"),
        ]
        
        node_exe = None
        for path in common_paths:
            if path.exists():
                node_exe = path
                break
        
        if not node_exe:
            # Try PATH
            try:
                result = subprocess.run(["where", "node"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    node_exe = Path(result.stdout.strip().split('\n')[0])
            except:
                pass
        
        if not node_exe:
            self.log_issue(f"Node.js not found. Expected at one of: {', '.join(str(p) for p in common_paths)}")
            self.log_info("Install Node.js from https://nodejs.org/")
            return False
        
        try:
            node_ver = subprocess.run(
                [str(node_exe), "--version"],
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()
            self.log_success(f"Node.js: {node_ver}")
            
            # npm should be in the same directory
            npm_exe = node_exe.parent / "npm.cmd"
            npm_ver = subprocess.run(
                [str(npm_exe), "--version"],
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()
            self.log_success(f"npm: {npm_ver}")
            
            return True
        except Exception as e:
            self.log_issue(f"Node.js check failed: {e}")
            return False
    
    def check_venv(self) -> bool:
        """Check virtual environment."""
        print("\n━━━ Python Virtual Environment ━━━")
        venv_path = self.project_root / ".venv"
        python_exe = venv_path / "Scripts" / "python.exe"
        
        if not venv_path.exists():
            self.log_issue(f"venv not found at {venv_path}")
            self.log_info("Create it with: python -m venv .venv")
            return False
        
        self.log_success(f"venv directory exists: {venv_path}")
        
        if not python_exe.exists():
            self.log_issue(f"Python executable not found: {python_exe}")
            return False
        
        self.log_success(f"Python executable: {python_exe}")
        
        # Check packages
        print("\n  Checking required packages...")
        required = ["fastapi", "uvicorn", "psutil", "pydantic"]
        missing = []
        
        for pkg in required:
            try:
                result = subprocess.run(
                    [str(python_exe), "-m", "pip", "show", pkg],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.log_success(f"  {pkg} installed")
                else:
                    missing.append(pkg)
            except Exception:
                missing.append(pkg)
        
        if missing:
            self.log_warning(f"Missing packages: {', '.join(missing)}")
            self.log_info("Install with: .venv\\Scripts\\pip install -e .")
            return False
        
        return True
    
    def check_frontend(self) -> bool:
        """Check frontend setup."""
        print("\n━━━ Frontend Setup ━━━")
        frontend_root = self.project_root / "frontend"
        
        if not frontend_root.exists():
            self.log_issue(f"frontend directory not found: {frontend_root}")
            return False
        
        self.log_success(f"frontend directory exists")
        
        # Check package.json
        pkg_json = frontend_root / "package.json"
        if not pkg_json.exists():
            self.log_issue(f"package.json not found: {pkg_json}")
            return False
        
        self.log_success("package.json found")
        
        # Check node_modules
        node_modules = frontend_root / "node_modules"
        if not node_modules.exists():
            self.log_warning("node_modules not found - run: cd frontend && npm install")
            return False
        
        self.log_success("node_modules exists")
        
        # Check for electron-builder
        eb_path = node_modules / "electron-builder"
        if not eb_path.exists():
            self.log_issue("electron-builder not found - reinstall with: npm install")
            return False
        
        self.log_success("electron-builder installed")
        
        return True
    
    def check_ports(self) -> bool:
        """Check if required ports are available."""
        print("\n━━━ Network Ports ━━━")
        
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if "8000" in result.stdout:
                self.log_warning("Port 8000 appears to be in use")
                self.log_info("Kill with: taskkill /PID <PID> /F")
            else:
                self.log_success("Port 8000 is available")
            
            return True
        except Exception as e:
            self.log_warning(f"Could not check ports: {e}")
            return True  # Don't fail on this
    
    def check_disk_space(self) -> bool:
        """Check available disk space."""
        print("\n━━━ Disk Space ━━━")
        
        try:
            result = subprocess.run(
                ["powershell", "-Command", 
                 f"(Get-Volume -DriveLetter {self.project_root.drive[0]}).SizeRemaining / 1GB"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                free_gb = float(result.stdout.strip())
                self.log_success(f"Free disk space: {free_gb:.1f} GB")
                
                if free_gb < 5:
                    self.log_issue("Less than 5GB free - build may fail")
                    return False
            
            return True
        except Exception:
            self.log_warning("Could not determine disk space")
            return True
    
    def run_all_checks(self) -> bool:
        """Run all diagnostic checks."""
        print("\n╔════════════════════════════════════════════════════╗")
        print("║      IARIS Build Environment Diagnostics          ║")
        print("╚════════════════════════════════════════════════════╝")
        
        all_passed = True
        
        all_passed &= self.check_python()
        all_passed &= self.check_nodejs()
        all_passed &= self.check_venv()
        all_passed &= self.check_frontend()
        all_passed &= self.check_ports()
        all_passed &= self.check_disk_space()
        
        # Summary
        print("\n╔════════════════════════════════════════════════════╗")
        print(f"║ Issues: {len(self.issues)} | Warnings: {len(self.warnings)}          ║")
        print("╚════════════════════════════════════════════════════╝\n")
        
        if self.issues:
            print("Critical Issues:")
            for issue in self.issues:
                print(f"  ✗ {issue}")
            print()
        
        if self.warnings:
            print("Warnings:")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
            print()
        
        if all_passed:
            print("✓ All checks passed! You're ready to build.")
            print("  Run: python build_exe.py")
        else:
            print("✗ Fix the issues above before building.")
        
        return all_passed

def main():
    """Run diagnostics."""
    diag = Diagnostics()
    success = diag.run_all_checks()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
