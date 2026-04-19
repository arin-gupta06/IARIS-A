# IARIS Build Quick Reference

## 📦 Create Executable in 3 Steps

### Option 1: Batch File (Easiest - Windows)
```batch
build_exe.bat
```

### Option 2: PowerShell
```powershell
.\build_exe.ps1
```

### Option 3: Python Script
```powershell
python build_exe.py
```

---

## ⚡ Quick Commands

| Task | Command |
|------|---------|
| **Setup Python** | `python -m venv venv && venv\Scripts\pip install -e .` |
| **Setup Frontend** | `cd frontend && npm install` |
| **Build EXE** | `python build_exe.py` |
| **Clean Build** | `python build_exe.py --clean` |
| **Find Executable** | `frontend\dist-electron\*.exe` |

---

## 🏃 Quick Start for Existing Setup

```powershell
# From project root
.\venv\Scripts\Activate.ps1
python build_exe.py
```

Output: `frontend\dist-electron\IARIS Setup 1.0.0.exe`

---

## 🐛 Common Issues

| Issue | Fix |
|-------|-----|
| `Python not found` | Install Python 3.11+ from python.org |
| `npm not found` | Install Node.js 18+ from nodejs.org |
| `venv not found` | Run: `python -m venv venv && venv\Scripts\pip install -e .` |
| `Backend timeout` | Check port 8000 isn't in use: `netstat -ano \| findstr :8000` |

---

## 📋 What Gets Bundled

- ✅ React frontend (built with Vite)
- ✅ Python backend (FastAPI + uvicorn)
- ✅ Python dependencies (psutil, textual, etc.)
- ✅ Electron desktop shell
- ✅ WebSocket for real-time updates

**Total Size:** ~150-200 MB

---

## 📖 For More Details

See [BUILD_EXE_GUIDE.md](BUILD_EXE_GUIDE.md) for:
- Prerequisites
- Detailed troubleshooting
- Customization options
- Architecture diagrams
- Security notes

---

**Happy building! 🚀**
