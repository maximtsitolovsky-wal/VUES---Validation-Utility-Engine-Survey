# VUES Dashboard - Viewer Setup Guide

## Quick Start (3 Steps)

1. **Install Git** (if you don't have it)
2. **Clone the repo**
3. **Run the dashboard**

---

## Step 1: Install Git

### Check if Git is Already Installed

Open **Command Prompt** or **PowerShell** and type:

```bash
git --version
```

If you see something like `git version 2.40.0`, skip to Step 2. If you get an error, install Git below.

### Install Git on Windows (Walmart)

**Option A: Software Center (Recommended)**

1. Open **Software Center** (search in Start menu)
2. Search for **"Git"**
3. Click **Install**
4. Wait for installation to complete
5. Restart your terminal

**Option B: Manual Download**

1. Go to: https://generic.ci.artifacts.walmart.com/artifactory/github-releases-generic-release-remote/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe
2. Run the installer
3. Click **Next** through all prompts (defaults are fine)
4. Restart your terminal

### Verify Git Installed

```bash
git --version
```

Should show: `git version 2.x.x`

---

## Step 2: Clone the Repository

Open **Command Prompt** or **PowerShell** and run:

```bash
cd %USERPROFILE%\Documents
git clone https://gecgithub01.walmart.com/vn59j7j/VUES---Validation-Utility-Engine-Survey.git
cd VUES---Validation-Utility-Engine-Survey
```

**If prompted for credentials:**
- Username: Your Walmart ID (e.g., `vn59j7j`)
- Password: Your Walmart password (or GitHub token)

---

## Step 3: Run the Dashboard

### Option A: Double-Click (Easiest)

1. Open the folder: `VUES---Validation-Utility-Engine-Survey`
2. Double-click: `VUES Preview.lnk` (or run the install script first)

### Option B: Command Line

```bash
cd %USERPROFILE%\Documents\VUES---Validation-Utility-Engine-Survey
python tools\serve_dashboard.py
```

**Browser opens automatically → You'll see the VUES Dashboard!**

---

## What You'll See

- **Scout Program:** 376+ submissions (live data)
- **Survey Routing:** Site assignments and status
- **Analytics:** Charts and metrics

**Data auto-syncs every hour** while the dashboard is open.

---

## Troubleshooting

### "git is not recognized"

Git isn't installed. Follow Step 1 above.

### "python is not recognized"

Python isn't installed. Install from Software Center or:
1. Open Software Center
2. Search for "Python"
3. Install Python 3.11+

### "Access denied" or "Authentication failed"

You need access to the repo. Contact Maxim Tsitolovsky (vn59j7j) for access.

### "Dashboard shows old data"

Run this to get the latest:
```bash
cd %USERPROFILE%\Documents\VUES---Validation-Utility-Engine-Survey
git pull
python tools\serve_dashboard.py
```

---

## Getting Updates

The dashboard auto-syncs every hour. To manually update:

```bash
cd %USERPROFILE%\Documents\VUES---Validation-Utility-Engine-Survey
git pull
```

---

## Need Help?

Contact: **Maxim Tsitolovsky** (vn59j7j)
- Teams: Search "Maxim Tsitolovsky"
- Email: vn59j7j@homeoffice.wal-mart.com

---

## TL;DR (Copy-Paste This)

```bash
# Install git from Software Center first, then:
cd %USERPROFILE%\Documents
git clone https://gecgithub01.walmart.com/vn59j7j/VUES---Validation-Utility-Engine-Survey.git
cd VUES---Validation-Utility-Engine-Survey
python tools\serve_dashboard.py
```

**Done! Dashboard opens in your browser.** 🎉
