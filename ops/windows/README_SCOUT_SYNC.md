# Scout Completion Sync

Automatically syncs completion status from Scout Airtable to the Excel tracker.

## How It Runs

This sync runs in **TWO WAYS** for redundancy:

1. **Integrated into Main App** (Recommended)
   - Runs automatically when you start `python main.py`
   - Syncs 60 seconds after startup
   - Then syncs **every 6 hours** continuously
   - Stops gracefully when you stop the main app

2. **Standalone Scheduled Task** (Backup)
   - Windows Task Scheduler runs it independently
   - Also at 10 AM & 3 PM Monday-Friday
   - Runs even if main app is stopped

## What It Does

- Fetches all records from Scout Airtable (appAwgaX89x0JxG3Z/tblC4o9AvVulyxFMk)
- Matches Airtable `Site Number` → Excel `Store Number`
- When Airtable `Complete?` = True → Sets Excel `Completed Scout` = True
- Fills Excel `Confirmed by` column with "code puppy (YYYY-MM-DD HH:MM:SS)"

## Files

**Main App Integration:**
- **`src/vues/scout_completion_sync_worker.py`** - Worker thread (runs in main.py)
- **`src/vues/main.py`** - Starts the worker on app startup

**Standalone/Backup:**
- **`scripts/scout_completion_sync_com.py`** - Standalone script (COM automation)
- **`ops/windows/ScoutCompletionSync_Task.xml`** - Task Scheduler definition
- **`ops/windows/run_scout_completion_sync.bat`** - Manual test runner

**Deprecated:**
- **`scripts/scout_completion_sync.py`** - ⚠️ DEPRECATED (openpyxl breaks data models)

## Setup

### Method 1: Use Main App (Easiest)

Just start the main vues app:

```bash
python main.py
```

The sync worker starts automatically! Look for:
```
ScoutCompletionSyncWorker started. Will sync completion status 60s after startup, then every 6h.
```

### Method 2: Standalone Scheduled Task (Optional Backup)

### Method 2: Standalone Scheduled Task (Optional Backup)

Run as **Administrator**:

```batch
schtasks /Create /XML "ops\windows\ScoutCompletionSync_Task.xml" /TN "ScoutCompletionSync" /F
```

This creates a Windows scheduled task that runs independently:
- **Monday-Friday** at **10:00 AM** and **3:00 PM**
- Runs even if main app is stopped

### Method 3: Verify Installation

```powershell
Get-ScheduledTask -TaskName "ScoutCompletionSync"
```

## Manual Testing

To test immediately without waiting for the schedule:

```batch
ops\windows\run_scout_completion_sync.bat
```

Or directly:

```batch
python scripts\scout_completion_sync_com.py
```

## Logs

Logs are written to:
```
logs/scout_completion_sync.log
```

View recent logs:
```powershell
Get-Content logs\scout_completion_sync.log -Tail 50
```

## Important Notes

⚠️ **Close Excel Before Running**
- The script cannot modify ScoutSurveyLab.xlsm if it's open in Excel
- OneDrive sync can also lock the file temporarily
- The script retries 3 times with 2-second delays

🔐 **API Key**
- Hardcoded in the script (same as scout_downloader.py)
- Read-only access to Scout Airtable

📊 **Excel Columns**
- Expects headers: `Store Number`, `Completed Scout`, `Confirmed by`
- Updates only rows where Airtable shows `Complete? = True`
- Preserves all other data and formatting

## Troubleshooting

**"Permission denied" error**
- Close `ScoutSurveyLab.xlsm` in Excel
- Wait for OneDrive sync to complete (green checkmark icon)
- Run again

**No updates happening**
- Check that Airtable has records with `Complete? = True`
- Verify Site Number in Airtable matches Store Number in Excel
- Check logs for detailed matching info

**Task not running**
- Make sure computer is on Mon-Fri at 10 AM / 3 PM
- Task won't run if not on VPN or Eagle WiFi (Airtable API requires network)

## Uninstall

To remove the scheduled task:

```powershell
Unregister-ScheduledTask -TaskName "ScoutCompletionSync" -Confirm:$false
```

## Technical Details

- **Language**: Python 3.11+
- **Dependencies**: requests, pywin32
- **Automation**: Windows COM (Excel.Application) - preserves data models/VBA/formulas
- **Scheduler**: Windows Task Scheduler (native)
- **Excel Format**: .xlsm (macro-enabled, fully preserved)
- **Airtable Pagination**: Handles unlimited records via offset
- **Smart Normalization**: Vendor-proof ("0038" = "38" = "Store 38")
