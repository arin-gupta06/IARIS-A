# ✨ IARIS Executable Bundle - Getting Started

You now have everything needed to create a standalone Windows executable for IARIS! Here's what was set up for you.

---

## 🎯 Quick Start (30 seconds)

From your project root (`d:\IARIS`):

```powershell
# Option 1: Double-click this file
build_exe.bat

# Option 2: Run in PowerShell
.\build_exe.ps1

# Option 3: Run Python directly
python build_exe.py
```

**That's it!** Your executable will be created in `frontend\dist-electron\`.

---

## 📋 What Was Created

### Build Automation
| File | Purpose |
|------|---------|
| `build_exe.py` | Main build orchestrator (~350 lines) |
| `build_exe.bat` | Windows batch wrapper - **easiest** ⭐ |
| `build_exe.ps1` | PowerShell wrapper with colored output |
| `build_diagnostics.py` | Validate your environment before building |

### Documentation
| File | Purpose |
|------|---------|
| `BUILD_EXE_GUIDE.md` | Complete build guide with troubleshooting |
| `BUILD_QUICK_REFERENCE.md` | One-page quick reference |
| `DEPLOYMENT_CHECKLIST.md` | Step-by-step deployment workflow |
| `README.md` (updated) | Added build instructions section |

### Code Changes
| File | Change |
|------|--------|
| `frontend/electron/main.js` | Enhanced resource path handling |

---

## 🚀 Three Steps to Your Executable

### Step 1: Validate Setup (2 minutes)
```powershell
python build_diagnostics.py
```
This checks if you have Python 3.11+, Node.js 18+, and all dependencies.

**Expected output:**
```
✓ Python: Python 3.11.x
✓ Node.js: vX.X.X
✓ npm: X.X.X
✓ venv directory exists
✓ All checks passed! You're ready to build.
```

### Step 2: Build Executable (3-5 minutes)
```powershell
build_exe.bat
```

**What it does:**
- Builds React frontend (Vite)
- Packages Python backend
- Creates Windows installer with electron-builder
- Outputs: `frontend\dist-electron\IARIS Setup 1.0.0.exe`

### Step 3: Distribute (0 minutes)
Share the `.exe` file with users:
- Email it directly
- Host on GitHub Releases
- Upload to file sharing service
- Place on company intranet

---

## 📊 What's Bundled in Your EXE

```
IARIS Setup 1.0.0.exe (~150-200 MB)
├─ Electron Shell (desktop app framework)
├─ React UI (built with Vite)
├─ Python Runtime (venv with all dependencies)
├─ IARIS Backend (FastAPI server)
├─ WebSocket Stream (real-time updates)
└─ Windows Installer (NSIS)
```

When users run the `.exe`:
1. Windows installer launches
2. Files are extracted to Program Files
3. Start Menu and Desktop shortcuts created
4. Double-clicking shortcut starts the app
5. Frontend and backend start automatically
6. Dashboard loads with real-time system metrics

---

## ✅ Testing Your Build

After building:

```powershell
# 1. Navigate to output folder
cd frontend\dist-electron

# 2. Double-click the .exe file
# OR run from command line:
& ".\IARIS Setup 1.0.0.exe"

# 3. Follow installer
# 4. Launch from Start Menu or Desktop
# 5. Wait for dashboard to load (5-15 seconds)
# 6. Should show system processes and live metrics
```

**Test checklist:**
- ✓ Installer launches
- ✓ Installation completes
- ✓ App launches
- ✓ Dashboard loads
- ✓ Real-time data streams
- ✓ Can close app cleanly

---

## 🛠️ Build Options

### Standard Build (30-60 seconds)
```powershell
python build_exe.py
```
Reuses previously built artifacts where possible.

### Clean Build (3-5 minutes)
```powershell
python build_exe.py --clean
```
Removes old builds and rebuilds everything from scratch.
Use this if:
- First time building
- Significant code changes
- Build seems corrupted

---

## 📚 Documentation Guide

| When You Want To... | Read This |
|---|---|
| Just build it quickly | `BUILD_QUICK_REFERENCE.md` |
| Understand the full process | `BUILD_EXE_GUIDE.md` |
| Deploy to users | `DEPLOYMENT_CHECKLIST.md` |
| Update the code | `BUILD_EXE_GUIDE.md` → Section "Version & Updates" |
| Fix build problems | `BUILD_EXE_GUIDE.md` → Section "Troubleshooting" |
| Validate environment | Run `python build_diagnostics.py` |

---

## 🎯 Next Steps

1. **Validate** your setup:
   ```powershell
   python build_diagnostics.py
   ```

2. **Build** your first executable:
   ```powershell
   build_exe.bat
   ```

3. **Test** locally:
   - Double-click the .exe
   - Walk through installer
   - Launch and verify functionality

4. **Deploy** to users:
   - Share the .exe file
   - Provide installation instructions
   - Direct them to `BUILD_EXE_GUIDE.md` if they have questions

---

## 🔧 Architecture Overview

```
User Double-Clicks IARIS.exe
    ↓
Windows Installer (NSIS)
    ↓
Extracts to C:\Program Files\IARIS\
    ↓
Creates shortcuts
    ↓
User Launches from Shortcut
    ↓
Electron Main Process starts
    ├─ Shows loading window
    ├─ Spawns Python backend (uvicorn on port 8000)
    └─ Polls health endpoint
    ↓
Backend responds
    ↓
Electron loads React UI (dist/index.html)
    ↓
React connects to backend via WebSocket
    ↓
Dashboard displays live system metrics
    ↓
Real-time data streaming begins
```

---

## 💡 Pro Tips

1. **Speed up rebuilds**: Don't use `--clean` unless necessary
2. **Better debugging**: Check `frontend/electron/main.js` logs
3. **Port conflicts**: If port 8000 is busy, close the conflicting app
4. **Antivirus issues**: Whitelist the .exe if security software blocks it
5. **Distribution**: Host on GitHub Releases for easy updates

---

## ❓ Troubleshooting

### "Python not found"
```powershell
# Install Python 3.11+ from python.org
# Then run diagnostics:
python build_diagnostics.py
```

### "Build failed"
```powershell
# Run diagnostics to identify the issue:
python build_diagnostics.py

# Clean build often fixes things:
python build_exe.py --clean
```

### "App won't start"
```powershell
# Check port 8000 isn't in use:
netstat -ano | findstr :8000

# Check antivirus isn't blocking:
Whitelist C:\Program Files\IARIS\ in your antivirus
```

**For detailed solutions**, see `BUILD_EXE_GUIDE.md` → Troubleshooting section.

---

## 📞 Key Files to Know

```
d:\IARIS\
├─ build_exe.bat                 ← Click this to build! ⭐
├─ build_exe.ps1                 ← Or this
├─ build_exe.py                  ← Or run this
├─ build_diagnostics.py          ← Validate first
├─ BUILD_EXE_GUIDE.md            ← Full documentation
├─ BUILD_QUICK_REFERENCE.md      ← Quick reference
├─ DEPLOYMENT_CHECKLIST.md       ← Distribution guide
├─ README.md                      ← Project overview (updated)
└─ frontend/
    ├─ electron/
    │   ├─ main.js              ← Enhanced for packaging
    │   └─ icon.ico             ← Installer icon
    ├─ package.json             ← Build configuration
    ├─ dist/                    ← Built React app
    └─ dist-electron/           ← Final .exe output ⭐
```

---

## 🎉 You're All Set!

Everything is ready. Just run:

```powershell
build_exe.bat
```

Or any of the alternatives above. Your executable will be created in `frontend\dist-electron\` ready to distribute.

**Good luck! 🚀**
