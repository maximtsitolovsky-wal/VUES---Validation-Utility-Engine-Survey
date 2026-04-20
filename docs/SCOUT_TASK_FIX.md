# Scout Task Automation - Fix Instructions

## 🔍 Problems Detected (April 17, 2026 - 10:00 AM)

### Problem 1: ScoutCompletionSync Failed ❌
```
Last Run: 4/17/2026 10:00:01 AM
Exit Code: 1 (FAILED)
Error: 401 Unauthorized - Airtable API
```

**Root Cause:** The scheduled task doesn't have `SCOUT_AIRTABLE_API_KEY` in its environment.

### Problem 2: Scout Downloader Didn't Run 🔋
```
Last Run: 4/16/2026 10:00:00 AM (yesterday)
Next Run: 4/20/2026 10:00:00 AM (Sunday)
Battery: On battery (96% charge)
Setting: "Stop On Battery Mode, No Start On Batteries"
```

**Root Cause:** Laptop is on battery and the task is configured to not run on battery power.

---

## ✅ Fixes Applied

### 1. Created Environment Loader
**File:** `ops/windows/run_scout_completion_sync_task.bat`
- Loads Scout API credentials from `.env.local`
- Wraps the Python script execution
- Logs to `logs/scout_completion_sync.log`

### 2. Created Secure Credentials File
**File:** `.env.local` (gitignored)
```
SCOUT_AIRTABLE_API_KEY=patPR0WWxXCE0loRO...
SCOUT_AIRTABLE_BASE_ID=appAwgaX89x0JxG3Z
SCOUT_AIRTABLE_TABLE_ID=tblC4o9AvVulyxFMk
```

### 3. Created Fix Script
**File:** `ops/windows/fix_scout_tasks.ps1`
- Updates all Scout tasks to run on battery
- Updates ScoutCompletionSync to use new wrapper
- Removes "Stop On Battery Mode" restriction

---

## 🚀 How to Fix (Run This Once)

### Step 1: Run the Fix Script (Admin Required)

1. Right-click **PowerShell** or **Windows Terminal**
2. Select **"Run as Administrator"**
3. Run:
   ```powershell
   cd C:\VUES
   .\ops\windows\fix_scout_tasks.ps1
   ```

### Step 2: Verify the Fix

1. Open **Task Scheduler** (Start → Task Scheduler)
2. Find these tasks in the root folder:
   - `ScoutCompletionSync`
   - `SiteOwlQA Scout Downloader 10AM`
   - `SiteOwlQA Scout Downloader 3PM`

3. For each task, click and check **Properties → Settings**:
   - ✅ **"Run whether user is logged on or not"** should be enabled
   - ✅ **"Stop if the computer switches to battery power"** should be **UNCHECKED**
   - ✅ **"Start the task only if the computer is on AC power"** should be **UNCHECKED**

4. For `ScoutCompletionSync`, check **Actions** tab:
   - Command should be: `cmd`
   - Arguments should be: `/c C:\VUES\ops\windows\run_scout_completion_sync_task.bat`

---

## 🧪 Manual Test (Before Waiting for Next Schedule)

Test the sync immediately:

```bat
cd C:\VUES
ops\windows\run_scout_completion_sync.bat
```

Check the log:
```bat
type logs\scout_completion_sync.log
```

You should see:
```
[OK] Fetched X records from Airtable
[OK] Saved X updates + Y outliers to ScoutSurveyLab.xlsm
[DONE] Updated=X  Skipped=Y  Errors=0
```

---

## 📅 Schedule After Fix

After running the fix script, the tasks will run:

| Task | Schedule | Next Run |
|------|----------|----------|
| **ScoutCompletionSync** | Mon-Fri 10:00 AM & 3:00 PM | Today 3:00 PM |
| **Scout Downloader 10AM** | Mon-Fri 10:00 AM | Tomorrow 10:00 AM |
| **Scout Downloader 3PM** | Mon-Fri 3:00 PM | Tomorrow 3:00 PM |

---

## 🔒 Security Note

The `.env.local` file contains your Airtable API key and is **gitignored**.
- ✅ Safe to keep on your local machine
- ❌ Never commit to git
- ⚠️ If you clone the repo on another machine, you must recreate `.env.local`

---

## 🐛 Troubleshooting

### If the fix script fails:
1. Make sure you're running PowerShell **as Administrator**
2. Check if the tasks are currently running (Task Scheduler → check Status column)
3. Try stopping the tasks first: Right-click → End

### If tasks still fail after fix:
1. Check the log: `logs\scout_completion_sync.log`
2. Verify `.env.local` exists and contains your API key
3. Test manually: `ops\windows\run_scout_completion_sync.bat`

### If you get "Permission Denied":
Run this in admin PowerShell:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

**Created:** 2026-04-17  
**Version:** 7.0.0  
**Status:** Ready to apply
