# IARIS Executable Bundle - Build & Deployment Guide

This guide walks you through creating a complete, standalone Windows executable that bundles both the IARIS frontend (Electron/React) and backend (Python FastAPI) together.

## 📋 Prerequisites

Ensure your system has the following installed:

- **Python 3.11+** - Download from [python.org](https://www.python.org/)
- **Node.js 18+** - Download from [nodejs.org](https://nodejs.org/)
- **Git** (optional, for version control)

Verify installation:
```powershell
python --version
node --version
npm --version
```

## 🚀 Quick Start: Build Your Executable

### Step 1: Verify Your Environment

```powershell
# Navigate to project root
cd d:\IARIS

# Activate the Python virtual environment
.\venv\Scripts\Activate.ps1

# Verify Python environment
python -m pip list | grep -E "fastapi|uvicorn|psutil"
```

If the venv doesn't exist, create it:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .
```

### Step 2: Run the Build Script

From the project root, run:

```powershell
# Option A: Clean build (removes old builds)
python build_exe.py --clean

# Option B: Incremental build (reuses previous artifacts where possible)
python build_exe.py
```

**What the script does:**
1. ✅ Builds the React frontend (`npm run build`)
2. ✅ Verifies the Python environment
3. ✅ Installs PyInstaller for Python packaging
4. ✅ Packages everything with `electron-builder`
5. ✅ Outputs a standalone `.exe` installer

### Step 3: Locate Your Executable

After a successful build, your installer will be at:

```
d:\IARIS\frontend\dist-electron\IARIS Setup 1.0.0.exe
(or similar - exact name depends on your version)
```

### Step 4: Install & Run

1. **Double-click the `.exe` file** to launch the installer
2. Follow the installation wizard
3. The installer will create a Start Menu shortcut and (optionally) a Desktop shortcut
4. Launch IARIS from the Start Menu or Desktop

## 🛠️ Build Architecture

### What Gets Bundled?

```
┌─────────────────────────────────────────────────┐
│            IARIS Executable Bundle              │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  Electron Main Process (main.js)        │   │
│  │  • Manages app lifecycle                │   │
│  │  • Spawns Python backend                │   │
│  │  • Handles window management            │   │
│  └─────────────────────────────────────────┘   │
│                         ↓                      │
│  ┌─────────────────────────────────────────┐   │
│  │  Built React Frontend (dist/)           │   │
│  │  • Bundled with Vite                    │   │
│  │  • Optimized & minified                 │   │
│  │  • ~15-25 MB                            │   │
│  └─────────────────────────────────────────┘   │
│                         ↔                      │
│  ┌─────────────────────────────────────────┐   │
│  │  Python FastAPI Backend (iaris/)        │   │
│  │  • Core engine                          │   │
│  │  • API server (port 8000)               │   │
│  │  • WebSocket streaming                  │   │
│  └─────────────────────────────────────────┘   │
│                         ↑                      │
│  ┌─────────────────────────────────────────┐   │
│  │  Bundled Python Environment (venv/)     │   │
│  │  • psutil, fastapi, uvicorn, etc.       │   │
│  │  • ~800 MB (pre-optimized)              │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Communication Flow

```
User clicks IARIS.exe
    ↓
Electron spawns Python backend (uvicorn process)
    ↓
Loading window shows with logo
    ↓
Electron polls http://127.0.0.1:8000/api/state
    ↓
Backend starts processing & responds to health check
    ↓
Electron loads React UI (dist/index.html)
    ↓
React connects to backend via WebSocket for real-time updates
    ↓
Dashboard displays live system metrics
    ↓
User closes window → Electron kills backend → App exits
```

## 📦 Bundle Contents

Inside the packaged executable:

| Component | Path in Bundle | Size | Purpose |
|-----------|---|---|---|
| Frontend React | `dist/` | ~3 MB | Web UI |
| Python venv | `venv/` | ~800 MB | Python runtime + deps |
| IARIS package | `iaris/` | ~2 MB | Core engine code |
| Electron | (built-in) | ~150 MB | Desktop shell |

**Total Download Size:** ~150-200 MB (exact size depends on venv optimization)

## 🔧 Customization & Advanced Options

### Custom Port

To use a different port for the backend API, modify `frontend/electron/main.js`:

```javascript
const PORT = 8001;  // Change from 8000 to 8001
```

### Disable Health Check Polling

If you want to skip the loading screen health polling, in `main.js`:

```javascript
const POLL_TIMEOUT_MS = 5000;  // Reduce from 15000ms to 5000ms
```

### Custom Installer Icon

Place your icon at:
```
frontend/electron/icon.ico
```

The build script will automatically use it.

### Modify Installer Behavior

Edit the `build.nsis` section in `frontend/package.json`:

```json
"nsis": {
  "oneClick": false,
  "allowToChangeInstallationDirectory": true,
  "installerIcon": "electron/icon.ico",
  "createDesktopShortcut": true,
  "createStartMenuShortcut": true
}
```

## 🐛 Troubleshooting

### Build Failed: Python Not Found

**Error:** `Python runtime not found`

**Solution:**
```powershell
# Ensure venv exists
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -e .

# Try build again
python build_exe.py --clean
```

### Build Failed: Node.js/npm Issues

**Error:** `npm: command not found` or `npm install failed`

**Solution:**
```powershell
# Reinstall Node.js from nodejs.org
# Or ensure it's in PATH:
node --version

# Clear npm cache
npm cache clean --force

# Try again
python build_exe.py --clean
```

### Executable Fails to Start

**Error:** App closes immediately or shows error dialog

**Check these:**
1. **Antivirus**: Whitelist the .exe or add exception
2. **Admin rights**: Right-click → "Run as Administrator"
3. **Python path**: Check `frontend/electron/main.js` for path resolution

**Debug mode:**
```powershell
# Run from command line to see error output
& "C:\Users\YourName\AppData\Local\Programs\IARIS\IARIS.exe"
```

### Backend Fails to Start (15-second timeout)

**Error:** "Engine Failed to Start" message

**Causes:**
- Port 8000 already in use
- Python dependencies missing
- Corrupted venv

**Solutions:**
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill the process if needed (replace PID with actual number)
taskkill /PID <PID> /F

# Rebuild with fresh venv
python build_exe.py --clean
```

### Executable Size Too Large

If the bundle exceeds 500 MB, optimize the venv:

```powershell
# Remove unnecessary packages
pip uninstall -y dev-tools pytest sphinx

# Clean pip cache
pip cache purge

# Rebuild
python build_exe.py --clean
```

## 📝 Version & Updates

### Updating IARIS Code

After updating Python code or frontend, simply rebuild:

```powershell
python build_exe.py --clean
```

### Auto-Update (Advanced)

For production deployments, consider:
- **Electron Updater**: [electron-updater](https://www.electron.build/auto-update)
- **Version Check in API**: Add `/api/version` endpoint
- **GitHub Releases**: Host installers there

## 🔐 Security Notes

- **Never ship with debug mode enabled** - Set log-level to 'warning'
- **Always validate backend responses** - Frontend should sanitize API data
- **Use HTTPS in production** - Currently uses localhost HTTP only
- **Code signing** (Advanced): Add certificate in `package.json` → `build.win`

## 📊 Build Performance

Typical build times:
- **Clean build**: 3-5 minutes (first time, slow)
- **Incremental build**: 30-60 seconds (if deps unchanged)
- **Just frontend update**: 10-20 seconds

To speed up, avoid using `--clean`:
```powershell
python build_exe.py   # Incremental - much faster
```

## 📞 Support

If you encounter issues:

1. Check the error message in the console
2. Review the "Troubleshooting" section above
3. Check `frontend/electron/main.js` logs for path resolution
4. Ensure Python venv is properly initialized

---

**Happy building! 🚀**
