# Scout Vendor Assignment Tracking

## Overview

The Scout section now includes real-time vendor assignment progress tracking, showing how many sites each vendor has completed versus their total assignments. This feature provides visibility into completion velocity and helps identify top performers.

## Features

### 1. Vendor Assignment Pills
Visual indicators under "Scout weekly production" showing:
- **Vendor Name**: Wachter, Techwise, SAS, Everon, CEI
- **Remaining Assignments**: Sites left to complete
- **Completion Progress**: Completed/Total (percentage)
- **Average Completion Time**: Days per site (when available)
- **Color Coding**:
  - 🟢 Green: ≥80% complete (on track)
  - 🟡 Yellow: 50-79% complete (moderate progress)
  - 🔴 Red: <50% complete (needs attention)

### 2. Weekly Highlights Integration
The Weekly Highlights section now includes:
- Total Scout assignments remaining across all vendors
- Overall completion percentage
- Top-performing vendor by completion rate
- Credit recognition for vendors exceeding expectations

### 3. KPI Tracking
Automatically calculates:
- **Completion Rate**: Percentage of assigned sites completed
- **Velocity**: Average days to complete an assignment
- **Remaining Workload**: Sites pending completion
- **Performance Ranking**: Comparative vendor performance

## Configuration

### Required Excel File
The system reads vendor assignments from an Excel workbook. Default path:
```
C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\Excel\Vendor ASSIGN. 4.2.26.xlsx
```

### Custom Path (Optional)
Override the default by setting an environment variable in `.env`:
```bash
VENDOR_ASSIGNMENT_FILE=C:/path/to/your/vendor/assignments.xlsx
```

### Excel File Format
The Excel file should contain:
- **Site Number/Store Number**: Unique site identifier
- **Vendor/Company**: Vendor name (Wachter, Techwise, SAS, Everon, CEI)
- **Assigned Date** (optional): Assignment timestamp for velocity calculation

Example:
| Site Number | Vendor Name | Assigned Date |
|-------------|-------------|---------------|
| 1234        | Wachter     | 2026-04-01    |
| 5678        | Techwise    | 2026-04-02    |
| 9012        | SAS         | 2026-04-03    |

## How It Works

### 1. Data Loading
- `VendorAssignmentTracker` reads the Excel file at dashboard refresh time
- Automatically detects column headers (flexible naming)
- Normalizes vendor names to match known vendors

### 2. Completion Matching
- Compares assigned sites against Scout Airtable comed submissions
- Matches by site number
- Tracks completion dates for velocity calculation

### 3. Dashboard Rendering
- Pills render dynamically based on latest data
- JavaScript updates on every dashboard refresh
- No manual intervention required

### 4. Weekly Highlights
- Insights automatically generated from vendor stats
- Top performers highlighted
- Progress trends included in executive summary

## Implementation Details

### New Files
- `src/siteowlqa/vendor_assignment_tracker.py`: Core tracking logic
  - `VendorAssignmentTracker`: Manages assignment data
  - `VendorStats`: Per-vendor statistics
  - `VendorAssignment`: Individual assignment records

### Modified Files
- `src/siteowlqa/team_dashboard_data.py`: 
  - Integrated vendor assignment data collection
  - Added `_build_vendor_assignments_payload()` function
  
- `src/siteowlqa/dashboard_exec.py`:
  - Added vendor pills HTML container
  - Added `renderVendorAssignmentPills()` JavaScript function
  - Integrated rendering into Scout section initialization
  
- `src/siteowlqa/weekly_highlights.py`:
  - Enhanced insights with vendor assignment progress
  - Added top performer recognition

- `.env.example`:
  - Documented `VENDOR_ASSIGNMENT_FILE` configuration

## Usage

### View Vendor Progress
1. Open the Executive Dashboard
2. Navigate to the Scout section
3. Scroll to "Scout weekly production"
4. View vendor pills showing real-time progress

### Download Reports
The Weekly Highlights CSV export includes:
- Vendor assignment completion metrics
- Top performer details
- Completion velocity trends

### Monitor Velocity
- Green pills indicate healthy progress (≥80% complete)
- Yellow pills suggest moderate progress (50-79%)
- Red pills flag vendors needing attention (<50%)

## Troubleshooting

### Pills Not Showing
**Cause**: Excel file not found or not configured  
**Solution**: 
- Verify `VENDOR_ASSIGNMENT_FILE` path in `.env`
- Check file exists and is accessible
- Review logs for error messages

### Incorrect Completion Counts
**Cause**: Site number mismatch between Excel and Airtable  
**Solution**:
- Ensure site numbers are consistent
- Check for leading/trailing spaces
- Verify vendor names match exactly

### Missing Velocity Data
**Cause**: No assigned dates in Excel file  
**Solution**:
- Add "Assigned Date" column to Excel
- Populate with assignment timestamps
- Dashboard will calculate average completion days

## Design Principles

### DRY (Don't Repeat Yourself)
- Single source of truth: Excel file
- Reusable `VendorAssignmentTracker` class
- Shared data payload across dashboard and highlights

### YAGNI (You Aren't Gonna Need It)
- No over-engineered database solution
- Simple Excel file parsing
- Minimal dependencies (openpyxl only)

### SOLID
- **Single Responsibility**: Tracker handles assignments, dashboard handles rendering
- **Open/Closed**: Extensible for new vendors without modifying core logic
- **Dependency Inversion**: Dashboard depends on tracker abstraction, not implementation

## Future Enhancements

Potential improvements (not implemented):
- Historical velocity trending (week-over-week)
- Vendor capacity planning (projected completion dates)
- Email alerts for vendors falling behind schedule
- Mobile-optimized pill layout
- Interactive drill-down by vendor

## Credits

This feature gives credit where it's due by highlighting top-performing vendors in both the dashboard pills and weekly executive summaries. Leadership can quickly identify vendors exceeding expectations and those needing support.

---

**Version**: 1.0  
**Date**: 2026-04-17  
**Author**: Code Puppy 🐶
