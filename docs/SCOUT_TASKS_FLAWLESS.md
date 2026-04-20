# 🔧 SCOUT TASKS - FLAWLESS OPERATION GUIDE

## 🎯 Goal
Make Scout automation tasks run **100% reliably** on schedule, regardless of battery status.

---

## ⚡ QUICK FIX (2 Minutes)

### Option 1: Double-Click Fix (Easiest)
1. Navigate to: `C:\SiteOwlQA_App\ops\windows\`
2. **Right-click** `FIX_SCOUT_TASKS.bat`
3. Select **"Run as administrator"**
4. Wait for completion (shows green checkmarks)
5. Done! ✅

### Option 2: PowerShell Command
```powershell
# Right-click PowerShell → Run as Administrator, then:
cd C:\SiteOwlQA_App
.\ops\windows\fix_scout_tasks_bulletproof.ps1
```

---

## ✅ What the Fix Does

### 1. Updates ScoutCompletionSync
- ✅ Uses new wrapper script that loads API credentials from `.env.local`
- ✅ Removes battery restrictions
- ✅ Verifies the command path is correct

### 2. Updates Scout Downloader Tasks
- ✅ Removes "Stop On Battery Mode" restriction
- ✅ Removes "Don't Start On Battery" restriction
- ✅ Both 10AM and 3PM tasks fixed

### 3. Tests Everything
- ✅ Runs a live test sync
- ✅ Verifies all tasks show "Ready" status
- ✅ Checks next scheduled run times

---

## 📋 Task Schedule After Fix

| Task | Days | Times | What It Does |
|------|------|-------|--------------|
| **ScoutCompletionSync** | Mon-Fri | 10:00 AM<br>3:00 PM | Syncs completion status from Airtable to Excel |
| **Scout Downloader 10AM** | Mon-Fri | 10:00 AM | Downloads Scout images |
| **Scout Downloader 3PM** | Mon-Fri | 3:00 PM | Downloads Scout images |

---

## 🧪 Manual Test (Optional)

Want to test RIGHT NOW without waiting for the schedule?

### Test ScoutCompletionSync:
```bat
cd C:\SiteOwlQA_App
ops\windows\run_scout_completion_sync_task.bat
```

### Check the results:
```bat
type logs\scout_completion_sync.log
```

**Expected last line:**
```
[DONE] Updated=X  Skipped=Y  Errors=0
```

---

## 🔍 Verification Checklist

After running the fix script:

### Open Task Scheduler
1. Press `Win + R`
2. Type: `taskschd.msc`
3. Press Enter

### Check Each Task
For **ScoutCompletionSync**:
- [ ] Status shows: `Ready`
- [ ] Next Run Time shows: Today 3:00 PM (or tomorrow 10:00 AM)
- [ ] Actions tab shows: `cmd /c C:\SiteOwlQA_App\ops\windows\run_scout_completion_sync_task.bat`
- [ ] Settings → Power tab:
  - [ ] "Stop if computer switches to battery power" is **UNCHECKED** ✓
  - [ ] "Start task only if computer is on AC power" is **UNCHECKED** ✓

For **Scout Downloader** tasks (both 10AM & 3PM):
- [ ] Status shows: `Ready`
- [ ] Settings → Power tab:
  - [ ] "Stop if computer switches to battery power" is **UNCHECKED** ✓
  - [ ] "Start task only if computer is on AC power" is **UNCHECKED** ✓

---

## 📊 Monitoring After Fix

### Real-Time Log Monitoring
```bat
powershell -Command "Get-Content -Wait C:\SiteOwlQA_App\logs\scout_completion_sync.log -Tail 20"
```

### Check Last Run Status
```bat
schtasks /query /tn "ScoutCompletionSync" /fo LIST /v | findstr "Last Run Time" "Last Result"
```

**Exit codes:**
- `0` = Success ✅
- `1` = Failed ❌

---

## 🐛 Troubleshooting

### If tasks still fail:

#### Problem: "401 Unauthorized" in logs
**Fix:** Check that `.env.local` contains your API key:
```bat
type C:\SiteOwlQA_App\.env.local
```

Should show:
```
SCOUT_AIRTABLE_API_KEY=patPR0WWxXCE0loRO...
SCOUT_AIRTABLE_BASE_ID=appAwgaX89x0JxG3Z
SCOUT_AIRTABLE_TABLE_ID=tblC4o9AvVulyxFMk
```

#### Problem: Task shows "Running" but never completes
**Fix:** Excel file might be open. Close `ScoutSurveyLab.xlsm` and try again.

#### Problem: "Access Denied" when running fix script
**Fix:** Right-click PowerShell → "Run as Administrator"

#### Problem: Tasks run but nothing happens
**Fix:** Check log file for errors:
```bat
notepad C:\SiteOwlQA_App\logs\scout_completion_sync.log
```

---

## 🎯 Success Indicators

You'll know everything is working when:

1. ✅ Task Scheduler shows all tasks as "Ready"
2. ✅ Next run times are scheduled for today or tomorrow
3. ✅ Manual test completes with exit code 0
4. ✅ Log shows: `[DONE] Updated=X Skipped=Y Errors=0`
5. ✅ Excel file gets updated with new completion statuses

---

## 📞 Support

**Files to check if something goes wrong:**
- `logs\scout_completion_sync.log` - Detailed sync log
- `.env.local` - API credentials (should exist and have your token)
- `ops\windows\run_scout_completion_sync_task.bat` - Task wrapper script

**Quick health check:**
```bat
cd C:\SiteOwlQA_App
test_env_loader.bat
```

Should show:
```
[OK] Environment variables loaded successfully!
```

---

**Last Updated:** 2026-04-17 (VUES v7.0.0)  
**Status:** ✅ Tested and verified working
