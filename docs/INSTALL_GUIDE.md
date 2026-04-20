# VUES Installation Guide

**Validation Utility Engine Survey** - One-click setup for your machine.

---

## Prerequisites

- ✅ Walmart VPN or Eagle WiFi connected
- ✅ Git installed ([Download Git](https://git-scm.com/download/win) if needed)
- ✅ Windows 10/11

---

## Quick Install (2 minutes)

### Step 1: Open PowerShell

Press `Win + X` → Click **"Windows PowerShell"** or **"Terminal"**

### Step 2: Run This Command

Copy and paste this entire line, then press Enter:

```powershell
git clone https://gecgithub01.walmart.com/vn59j7j/VUES---Validation-Utility-Engine-Survey C:\VUES; C:\VUES\ops\windows\FRESH_INSTALL.bat
```

### Step 3: Wait for Setup

The installer will:
- ✅ Clone the repository
- ✅ Check/install Python
- ✅ Install all dependencies
- ✅ Create desktop shortcuts
- ✅ Configure credentials automatically

### Step 4: Launch the App

Double-click **"SiteOwlQA Launcher"** on your desktop.

That's it! 🎉

---

## What Gets Installed

| Item | Location |
|------|----------|
| Application | `C:\VUES` |
| Desktop Shortcut | `SiteOwlQA Launcher` |
| Admin Tool | `FIX SCOUT TASKS` |

---

## Desktop Shortcuts

### SiteOwlQA Launcher
The main application launcher. Double-click to:
- Start the VUES pipeline
- Open the executive dashboard
- Launch git autopush (auto-saves your work)

### FIX SCOUT TASKS
Admin tool for fixing Scout scheduled tasks. Right-click → **Run as Administrator** if needed.

---

## Troubleshooting

### "git is not recognized"

Git isn't installed. Install it:
1. Download from: https://git-scm.com/download/win
2. Run installer with default options
3. Restart PowerShell and try again

### "Access denied" or "Failed to clone"

You're not on VPN:
1. Connect to **Walmart VPN** or **Eagle WiFi**
2. Try again

### Python not found

The installer tries to auto-install Python. If it fails:
1. Download Python 3.12+ from https://www.python.org/downloads/
2. **Important:** Check ✅ "Add Python to PATH" during install
3. Restart PowerShell and re-run the install command

### Dashboard doesn't open

1. Check if the pipeline is running (look for Python in Task Manager)
2. Try running the launcher again
3. Check logs at: `C:\VUES\logs\vues.stdout.log`

---

## Updating VUES

To get the latest version:

```powershell
cd C:\VUES
git pull
```

---

## Making Code Changes

This repo requires PR approval for changes to `main`.

1. **Create a branch:**
   ```powershell
   cd C:\VUES
   git checkout -b my-feature-name
   ```

2. **Make your changes**

3. **Commit and push:**
   ```powershell
   git add -A
   git commit -m "Description of changes"
   git push origin my-feature-name
   ```

4. **Open a Pull Request:**
   - Go to: https://gecgithub01.walmart.com/vn59j7j/VUES---Validation-Utility-Engine-Survey
   - Click "Compare & pull request"
   - Submit for review

5. **Wait for approval** from the repo owner

---

## Support

Having issues? Contact the repo owner or check the README at `C:\VUES\README.md`.

---

*Last updated: April 2026*
