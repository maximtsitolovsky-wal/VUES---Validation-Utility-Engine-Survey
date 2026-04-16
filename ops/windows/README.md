# Windows Operations Scripts

These batch files and PowerShell scripts automate SiteOwlQA pipeline deployment and operation on Windows.

## Quick Start

### Option 1: Run Manually (Daily Use)

**Double-click:**
```
start_pipeline.bat
```

This will:
- Start the pipeline in the background (if not already running)
- Open the dashboard in your browser
- Show you the log file location

### Option 2: Automatic on Startup (24/7 Operation)

**Run as Administrator:**
```
setup_scheduler.bat
```

This will:
- Create a Windows Task Scheduler task
- Configure it to run at system startup
- Pipeline runs automatically, even when nobody is logged in

---

## Scripts Explained

### 🚀 start_pipeline.bat
**Purpose:** User-friendly launcher for daily operation

**What it does:**
- Starts System Bottleneck Auditor (background)
- Starts Git Autopush (visible window - auto-commits changes)
- Starts Docker Platform Engineer (background)
- Starts Specialist Output Validator (background, 90s delay)
- Starts the SiteOwlQA pipeline in background
- Waits for dashboard to be generated
- Opens the dashboard in your default browser
- Shows log file location
- Detects if pipeline is already running (avoids duplicates)

**Usage:**
```bash
start_pipeline.bat
```

**Returns:**
- Exit code 0 = success
- Exit code 1 = error (check console output)

---

### 🛑 stop_pipeline.bat
**Purpose:** Gracefully terminate the running pipeline

**What it does:**
- Finds the Python process running the pipeline
- Terminates it cleanly

**Usage:**
```bash
stop_pipeline.bat
```

---

### ⚙️ setup_scheduler.bat
**Purpose:** Configure automatic startup (requires admin)

**What it does:**
- Creates a Windows Task Scheduler task
- Configures it to run at system startup
- Sets it to run as SYSTEM account (even when logged off)
- Allows the pipeline to run 24/7

**Usage:**
- Right-click → "Run as administrator"
- Or open CMD as admin and run: `setup_scheduler.bat`

**Requirements:**
- Must run with Administrator privileges
- Windows Task Scheduler service must be enabled

**After Setup:**
- Restart your computer to test
- Pipeline should start automatically
- Check logs at: `C:\SiteOwlQA_App\logs\siteowlqa.stdout.log`

---

### 🏃 run_siteowlqa.bat
**Purpose:** Foreground launcher (for testing/debugging)

**What it does:**
- Starts pipeline in foreground
- Shows real-time output in console
- Pipeline stops when you close the window

**Usage:**
```bash
run_siteowlqa.bat
```

**Use this for:**
- Testing configuration changes
- Debugging startup issues
- Verifying imports/dependencies

---

## Logs

All logs are saved to:
```
C:\SiteOwlQA_App\logs\siteowlqa.stdout.log
```

View in real-time:
```bash
tail -f C:\SiteOwlQA_App\logs\siteowlqa.stdout.log
```

Or open in Notepad:
```bash
C:\SiteOwlQA_App\logs\siteowlqa.stdout.log
```

---

## Troubleshooting

### "Python not found at C:\\Python314\\python.exe"

**Solution:** Update the `PYTHON` variable in the batch file(s).

**Find your Python:**
```bash
where python
```

Then edit the batch file and change:
```batch
set PYTHON=C:\Python314\python.exe
```

to match your actual installation path.

---

### "Failed to change directory to C:\\SiteOwlQA_App"

**Solution:** Update the `WORKDIR` variable to match your actual installation path.

---

### Pipeline keeps crashing or not starting

**Check logs:**
```
C:\SiteOwlQA_App\logs\siteowlqa.stdout.log
C:\SiteOwlQA_App\logs\siteowlqa.stderr.log
```

**Test with foreground launcher:**
```bash
run_siteowlqa.bat
```

This shows real-time errors.

---

### "This script must be run as Administrator"

**Solution for setup_scheduler.bat:**

1. Right-click `setup_scheduler.bat`
2. Select "Run as administrator"
3. Click "Yes" when prompted

Or open CMD as admin first:
```bash
Windows+R → cmd → Ctrl+Shift+Enter
cd C:\SiteOwlQA_App\ops\windows
setup_scheduler.bat
```

---

## Advanced: Manual Task Scheduler Setup

If `setup_scheduler.bat` doesn't work, you can create the task manually:

1. Press `Windows+R`, type: `taskschd.msc`
2. Click "Create Task"
3. Set:
   - **Name:** SiteOwlQA Pipeline
   - **Description:** Automated vendor QA pipeline
   - **Security:** Run with highest privileges
   - **Trigger:** At startup
   - **Action:**
     - Program: `C:\Python314\python.exe`
     - Arguments: `-u main.py`
     - Start in: `C:\SiteOwlQA_App`

---

## File Reference

| File | Purpose | Run As |
|------|---------|--------|
| `start_pipeline.bat` | Daily launcher + dashboard | Normal user |
| `stop_pipeline.bat` | Stop the pipeline | Normal user |
| `run_siteowlqa.bat` | Foreground test launcher | Normal user |
| `setup_scheduler.bat` | Auto-startup configuration | **Admin** |
| `launch_siteowlqa_dashboard.ps1` | PowerShell dashboard launcher | Normal user |
| `start_siteowlqa_background.ps1` | PowerShell background start | Normal user |
| `SiteOwlQA.xml` | Task Scheduler XML (legacy) | Internal |

---

## See Also

- Main pipeline: `python main.py` (from `C:\SiteOwlQA_App`)
- README: `C:\SiteOwlQA_App\README.md`
- Development guide: `C:\SiteOwlQA_App\development.md`
