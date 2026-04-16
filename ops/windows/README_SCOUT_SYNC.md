# Scout Completion Sync

Automatically syncs completion status from Scout Airtable to the Excel tracker.

## What It Does

- Fetches all records from Scout Airtable (appAwgaX89x0JxG3Z/tblC4o9AvVulyxFMk)
- Matches Airtable `Site Number` → Excel `Store Number`
- When Airtable `Complete?` = True → Sets Excel `Completed Scout` = True
- Fills Excel `Confirmed by` column with "code puppy (YYYY-MM-DD HH:MM:SS)"

## Files

- **`scripts/scout_completion_sync.py`** - Main sync script
- **`ops/windows/register_scout_completion_sync_task.ps1`** - Task Scheduler registration (PowerShell)
- **`ops/windows/register_scout_completion_sync.bat`** - Task Scheduler registration (Batch wrapper)
- **`ops/windows/run_scout_completion_sync.bat`** - Manual test run

## Setup

### 1. Install (One-Time)

Run as **Administrator**:

```batch
ops\windows\register_scout_completion_sync.bat
```

This creates a Windows scheduled task that runs:
- **Monday-Friday** at **10:00 AM** and **3:00 PM**

### 2. Verify Installation

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
python scripts\scout_completion_sync.py
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
- **Dependencies**: requests, openpyxl (already in requirements.txt)
- **Scheduler**: Windows Task Scheduler (native)
- **Excel Format**: .xlsm (macro-enabled, preserves VBA)
- **Airtable Pagination**: Handles unlimited records via offset
