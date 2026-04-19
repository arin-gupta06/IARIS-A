# IARIS Executable Bundle - Deployment Checklist

This checklist guides you through creating and deploying your IARIS executable bundle.

## ✅ Pre-Build Checklist

### System Requirements
- [ ] Python 3.11+ installed (check: `python --version`)
- [ ] Node.js 18+ installed (check: `node --version`)
- [ ] npm available (check: `npm --version`)
- [ ] 5+ GB free disk space
- [ ] Windows 7 or later (for deployment)

### Project Setup
- [ ] Virtual environment exists: `venv/`
- [ ] Python dependencies installed: `pip install -e .`
- [ ] Frontend dependencies exist: `frontend/node_modules/`
- [ ] No processes running on port 8000

### Verification
```powershell
# Run diagnostics to verify everything is ready
python build_diagnostics.py
```

Expected output: ✓ All checks passed! You're ready to build.

---

## 🚀 Build Steps

### Step 1: Validate Environment
```powershell
cd d:\IARIS
python build_diagnostics.py
```
- ✓ Fixes any issues shown

### Step 2: Build Executable
```powershell
# Choose one of:
build_exe.bat                    # Easiest - batch file
# OR
.\build_exe.ps1                  # PowerShell
# OR
python build_exe.py              # Direct Python

# For fresh build (removes old files):
python build_exe.py --clean
```

### Step 3: Monitor Build
The build should output:
```
[BUILD] Building React frontend...
[BUILD] Building Electron executable...
✓ Executable created: frontend\dist-electron\IARIS Setup 1.0.0.exe
```

Expected build time:
- **First build**: 3-5 minutes (slow)
- **Subsequent builds**: 30-60 seconds
- **Just frontend changes**: 10-20 seconds

### Step 4: Locate Executable
```powershell
# Check output folder
explorer frontend\dist-electron\

# Should see: IARIS Setup 1.0.0.exe (or similar)
```

---

## 🧪 Testing Checklist

### Local Testing
- [ ] Double-click the `.exe` file
- [ ] Installer launches with NSIS interface
- [ ] Choose install location (default recommended)
- [ ] Installation completes without errors
- [ ] Shortcut created in Start Menu
- [ ] Shortcut created on Desktop (if selected)

### Launch Testing
- [ ] Click shortcut to launch IARIS
- [ ] Loading window appears with logo
- [ ] Wait for "Starting the intelligence engine..."
- [ ] After ~5-15 seconds, main dashboard loads
- [ ] Dashboard shows system processes
- [ ] WebSocket connection status shows "Connected"
- [ ] Real-time data updates visible (CPU, Memory, etc.)

### Feature Testing
- [ ] Visualization tab loads without errors
- [ ] Processes list populates
- [ ] Can scroll through process table
- [ ] Click on process shows details
- [ ] CPU and Memory charts update in real-time
- [ ] Can switch between dashboard tabs

### Shutdown Testing
- [ ] Click window close button (X)
- [ ] App closes cleanly
- [ ] No background processes remain
  - Verify: `tasklist | findstr python` shows nothing
  - Verify: `netstat -ano | findstr 8000` shows nothing

---

## 📦 Distribution Checklist

### Before Distribution
- [ ] Tested on clean Windows machine (if possible)
- [ ] No sensitive data in executable
- [ ] Version number is correct in `frontend/package.json`
- [ ] Release notes prepared
- [ ] Antivirus scan completed (executable safe)

### Distribution Methods

**Option 1: Direct File Share**
- [ ] Upload `.exe` to file sharing service (Google Drive, OneDrive, etc.)
- [ ] Share link with users
- [ ] Users download and run installer

**Option 2: GitHub Releases** (Recommended)
- [ ] Create GitHub account/repo if needed
- [ ] Upload `.exe` to GitHub Releases
- [ ] Add version tag (e.g., `v1.0.0`)
- [ ] Add release notes
- [ ] Users can download from Release page

**Option 3: Internal Server**
- [ ] Host on company file server
- [ ] Create download page/documentation
- [ ] Share link internally

### User Installation Instructions

Provide users with:
1. The `.exe` file
2. These instructions:

```
Installation:
1. Download IARIS Setup 1.0.0.exe
2. Double-click to run installer
3. Choose installation location (default recommended)
4. Click Install
5. Finish installation
6. Launch from Start Menu or Desktop shortcut

First Run:
1. Loading window appears - this is normal
2. Wait 5-15 seconds for engine to start
3. Dashboard will load automatically
4. System metrics will begin streaming

Troubleshooting:
- If installer fails: Ensure Windows defender/antivirus allows it
- If app fails to start: Check port 8000 isn't in use
- For issues: See BUILD_EXE_GUIDE.md section "Troubleshooting"
```

---

## 🔄 Update Process

When you update the code (Python or React):

### Quick Update
```powershell
# If only React/frontend changed
python build_exe.py

# If only Python code changed
python build_exe.py

# If both changed or unsure
python build_exe.py --clean
```

### Version Bump
1. Update version in `frontend/package.json`
2. Update version in `pyproject.toml`
3. Run build
4. Create new Release on GitHub

---

## 🐛 Common Issues & Fixes

### "Build Failed" Message

**Issue**: Build script exits with error

**Check**:
1. Run diagnostics: `python build_diagnostics.py`
2. Fix issues it reports
3. Try build again

**Common fixes**:
```powershell
# Port in use
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Python issues
pip install --upgrade pip
pip install -e .

# Frontend issues
cd frontend && npm install
```

### "Executable Fails to Start"

**Issue**: App closes immediately after launching

**Check**:
1. Open Command Prompt as Admin
2. Navigate to install folder (usually C:\Program Files\IARIS)
3. Run: `IARIS.exe`
4. Look for error messages

**Common fixes**:
- Whitelist in antivirus
- Port 8000 in use (see above)
- Python venv corrupted (rebuild with --clean)

---

## 📊 Build Artifact Management

### Where to Store
- Keep `.exe` files in: `frontend/dist-electron/`
- Archive old builds if updating frequently

### Size Management
If executable is larger than 300 MB:
```powershell
# Clean up Python cache and optimize
python build_exe.py --clean

# Or manually:
# 1. Delete frontend/dist-electron/ (old builds)
# 2. Delete frontend/node_modules/.vite/
# 3. Delete venv and recreate
```

---

## ✨ Final Checklist

- [ ] Executable created successfully
- [ ] Tested on local machine
- [ ] Installation works
- [ ] App launches properly
- [ ] Dashboard shows live data
- [ ] No errors in console
- [ ] Clean shutdown works
- [ ] Ready for distribution

---

## 📖 Documentation Reference

- **[BUILD_EXE_GUIDE.md](BUILD_EXE_GUIDE.md)** — Full build documentation
- **[BUILD_QUICK_REFERENCE.md](BUILD_QUICK_REFERENCE.md)** — Quick commands
- **[README.md](README.md)** — Main project documentation
- **build_diagnostics.py** — Environment validation

---

**Ready to deploy? Start with the Pre-Build Checklist above! 🚀**
