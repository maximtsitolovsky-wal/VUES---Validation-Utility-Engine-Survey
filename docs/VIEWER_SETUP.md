# VUES Dashboard - Viewer Setup Guide

## Choose Your Setup Method

| Method | Best For | Time |
|--------|----------|------|
| **Option A: ZIP Download** | Can't install Git, quick setup | 2 min |
| **Option B: Git Clone** | Regular updates, auto-sync | 5 min |

---

# Option A: ZIP Download (No Git Required)

## Step 1: Download the ZIP

1. Go to: **https://gecgithub01.walmart.com/vn59j7j/VUES---Validation-Utility-Engine-Survey**
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Save to your Downloads folder

## Step 2: Extract the ZIP

1. Go to your Downloads folder
2. Right-click the ZIP file → **"Extract All..."**
3. Extract to: `C:\Users\YourName\Documents\`
4. Click **Extract**

## Step 3: Run the Installer (First Time Only)

1. Open the extracted folder: `VUES---Validation-Utility-Engine-Survey-main`
2. Double-click: **`INSTALL.bat`**
3. Follow the prompts
4. A desktop shortcut will be created

**What INSTALL.bat does:**
- ✅ Checks if Python is installed
- ✅ Creates a virtual environment
- ✅ Installs required packages
- ✅ Creates a "VUES Dashboard" shortcut on your Desktop
- ✅ Launches the dashboard

## Step 4: Run the Dashboard (Every Time)

**Option A:** Double-click **"VUES Dashboard"** shortcut on your Desktop

**Option B:** Double-click **`run_dashboard.bat`** in the VUES folder

**Browser opens → You'll see the VUES Dashboard!**

## If Python is Not Installed

The installer will tell you if Python is missing. To install:

1. Open **Microsoft Store** (search in Start menu)
2. Search for **"Python 3.11"**
3. Click **"Get"** or **"Install"**
4. Wait for installation to complete
5. Run **INSTALL.bat** again

## Updating (ZIP Method)

Since you don't have Git, you'll need to **re-download the ZIP** to get updates:

1. Download fresh ZIP from GitHub
2. Extract to the same location (overwrite old files)
3. Run the dashboard as usual

**Tip:** Bookmark the GitHub page for easy re-downloading.

---

# Option B: Git Clone (Recommended - Auto Updates)

## Step 1: Install Git (if needed)

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

1. Go to: https://git-scm.com/download/win
2. Run the installer
3. Click **Next** through all prompts (defaults are fine)
4. Restart your terminal

## Step 2: Clone the Repository

Open **PowerShell** and run:

```bash
cd $HOME\Documents
git clone https://gecgithub01.walmart.com/vn59j7j/VUES---Validation-Utility-Engine-Survey.git
cd VUES---Validation-Utility-Engine-Survey
```

**If prompted for credentials:**
- Username: Your Walmart ID (e.g., `vn59j7j`)
- Password: Your Walmart password (or GitHub token)

## Step 3: Run the Installer (REQUIRED)

```bash
python tools/install.py
```

**This creates a "VUES Dashboard" shortcut on your Desktop!**

## Step 4: Launch the Dashboard

Double-click **"VUES Dashboard"** on your Desktop!

**Browser opens → You'll see ALL dashboard pages with data!**

---

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
