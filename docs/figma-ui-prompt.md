# UI Requirements Extraction

For active roadmap, implementation status, and commit workflow, refer to [`development.md`](../development.md).

## 1. App Sections

- **Airtable “Submissions” Table (Grid View)**
  - Type: page (external UI)
  - Purpose: Primary data-entry + status tracking grid for submissions (rows) and pipeline write-backs
  - Parent Section: Unclear from current app (Airtable base navigation not shown)

- **Dashboard: “SiteOwlQA — Vendor Metrics”**
  - Type: page (static HTML)
  - Purpose: View vendor performance summary metrics in a table
  - Parent Section: Dashboards (implicit; opened as standalone HTML file)

- **Dashboard: “SiteOwlQA — Processing Summary”**
  - Type: page (static HTML)
  - Purpose: View daily processing breakdown metrics in a table
  - Parent Section: Dashboards (implicit; opened as standalone HTML file)

- **Pipeline App Console Window**
  - Type: window (terminal/console)
  - Purpose: Run the application process and display log output
  - Parent Section: Unclear from current app (OS-level)

## 2. Screen-by-Screen UI Requirements

### 2.1 Airtable “Submissions” (Grid)

- **Screen Name:** Submissions (Airtable grid)
- **Purpose:** Enter submissions and display pipeline results per row
- **Visible UI Components:**
  - Spreadsheet-like grid with row numbers at left
  - Column headers across the top
  - Top toolbar controls visible: “Hide fields”, “Filter”, “Group”, “Sort”, “Color”, “Share and sync” (labels as seen)
- **Input Fields (editable by user in Airtable):**
  - Unclear from current app which columns are editable vs computed vs filled by automation; see Field Inventory for column list.
- **Display Fields (visible in the grid):**
  - All columns listed in Field Inventory
- **Buttons / Actions:**
  - Toolbar actions: Hide fields, Filter, Group, Sort, Color, Share and sync
  - Per-cell actions: Unclear from current app (standard Airtable behavior not documented here)
- **Tables / Lists / Cards:**
  - One table (grid) of submission records
- **Filters / Search / Sort controls:**
  - Filter / Group / Sort controls exist in toolbar (exact configs unclear)
- **Empty States:** Unclear from current app (not shown)
- **Loading States:** Unclear from current app (not shown)
- **Error States:** Unclear from current app (not shown)
- **Disabled / Read-only States:** Unclear from current app (not shown)
- **Validation indicators visible in UI:** Unclear from current app (not shown)
- **Layout Notes:**
  - Standard Airtable grid layout with fixed header row, left row index column, and multiple data columns.

### 2.2 Dashboard Page: “SiteOwlQA — Vendor Metrics”

- **Screen Name:** SiteOwlQA — Vendor Metrics
- **Purpose:** Display vendor performance summary
- **Visible UI Components:**
  - Page title: “SiteOwlQA — Vendor Metrics”
  - Subtitle line (paragraph): “Vendor performance summary • X vendor(s)” (X is a number)
  - Data table with header row and body rows
  - Footer line: “Generated: <timestamp> • SiteOwlQA Automation Pipeline”
- **Input Fields:** None (static HTML display)
- **Display Fields (Table Columns):**
  - Vendor Email
  - Vendor Name
  - Total
  - Pass
  - Fail
  - Error
  - Pass Rate %
  - Fail Rate %
  - Avg Score (Fail)
  - Latest Submission
  - Avg Turnaround (s)
- **Buttons / Actions:** None shown
- **Tables / Lists / Cards:**
  - One table
- **Filters / Search / Sort controls:** None shown
- **Empty States:**
  - Unclear from current app (HTML shown includes table rows)
- **Loading States:** None shown (static HTML)
- **Error States:** None shown (static HTML)
- **Disabled / Read-only States:** Read-only display
- **Validation indicators visible in UI:** None
- **Layout Notes:**
  - Light gray page background
  - Table uses full width, white background, subtle box shadow
  - Table header uses dark blue background with white text
  - Row hover highlight (light blue)
  - Some body rows show a light red background color in the provided HTML output (exact condition for this is unclear from current app)

### 2.3 Dashboard Page: “SiteOwlQA — Processing Summary”

- **Screen Name:** SiteOwlQA — Processing Summary
- **Purpose:** Display daily processing breakdown
- **Visible UI Components:**
  - Page title: “SiteOwlQA — Processing Summary”
  - Subtitle line: “Daily breakdown • X day(s) • Y total submission(s)”
  - Data table with header row and body rows
  - Footer line: “Generated: <timestamp> • SiteOwlQA Automation Pipeline”
- **Input Fields:** None (static HTML display)
- **Display Fields (Table Columns):**
  - Date
  - Total
  - Pass
  - Fail
  - Error
  - Pass Rate %
  - Unique Vendors
  - Unique Sites
- **Buttons / Actions:** None shown
- **Tables / Lists / Cards:** One table
- **Filters / Search / Sort controls:** None shown
- **Empty States:** Unclear from current app (not shown)
- **Loading States:** None shown
- **Error States:** None shown
- **Disabled / Read-only States:** Read-only display
- **Validation indicators visible in UI:** None
- **Layout Notes:**
  - Same overall styling pattern as Vendor Metrics page (background, header styling, table styling, hover behavior)

### 2.4 Pipeline App Console Window

- **Screen Name:** Console (app running)
- **Purpose:** Shows runtime logs/status
- **Visible UI Components:** Unclear from current app (console UI not provided visually; logs exist)
- **Input Fields:** None (unless the user types Ctrl+C etc; unclear)
- **Buttons / Actions:** Unclear from current app
- **States:** Unclear from current app

## 3. Field Inventory

### 3.1 Airtable “Submissions” Grid Fields (from screenshot)

- **Submission ID**
  - Label shown in UI: “Submission ID”
  - Field Type: table cell (text)
  - Required/Optional: Unclear from current app
  - Editable/Read-only: Unclear from current app
  - Default: Unclear from current app
  - Placeholder: Unclear from current app
  - Validation rules visible in UI: Unclear from current app
  - Related Screen / Component: Airtable Submissions grid
  - Possible values/options: Unclear from current app
  - Notes: 

- **Surveyor Email**
  - Label: “Surveyor Email”
  - Type: table cell (email/text)
  - Required: Unclear from current app
  - Editable: Unclear from current app
  - Default: Unclear from current app
  - Placeholder: Unclear from current app
  - Validation rules: Unclear from current app
  - Related: Airtable Submissions grid
  - Options: N/A

- **Upload File**
  - Label: “Upload File”
  - Type: table cell (file attachment)
  - Required: Unclear from current app
  - Editable: Unclear from current app
  - Default: Unclear from current app
  - Placeholder: Unclear from current app
  - Validation rules: Unclear from current app
  - Related: Airtable Submissions grid

- **Comments**
  - Label: “Comments”
  - Type: table cell (text or textarea; unclear)
  - Required: Unclear from current app
  - Editable: Unclear from current app
  - Default: Unclear from current app
  - Placeholder: Unclear from current app
  - Validation rules: Unclear from current app
  - Related: Airtable Submissions grid

- **Select**
  - Label: “Select”
  - Type: table cell (select; exact options unclear)
  - Required: Unclear from current app
  - Editable: Unclear from current app
  - Default: Unclear from current app
  - Placeholder: Unclear from current app
  - Validation rules: Unclear from current app
  - Related: Airtable Submissions grid
  - Possible values: Unclear from current app

- **Score**
  - Label: “Score”
  - Type: table cell (text)
  - Required: Unclear from current app
  - Editable: Unclear from current app (appears written by automation)
  - Default: Unclear from current app
  - Placeholder: Unclear from current app
  - Validation rules: Unclear from current app
  - Related: Airtable Submissions grid
  - Possible values observed: “PASS”, “0.0%”, “32.0%”

- **Fail Summary**
  - Label: “Fail Summary”
  - Type: table cell (text/textarea; appears multi-line)
  - Required: Unclear from current app
  - Editable: Unclear from current app (appears written by automation)
  - Default: Unclear from current app
  - Placeholder: Unclear from current app
  - Validation rules: Unclear from current app
  - Related: Airtable Submissions grid

- **Processing Status**
  - Label: “Processing Status”
  - Type: table cell (status text)
  - Required: Unclear from current app
  - Editable: Unclear from current app (appears written by automation)
  - Default: Unclear from current app
  - Placeholder: Unclear from current app
  - Validation rules: Unclear from current app
  - Related: Airtable Submissions grid
  - Possible values observed: PASS, FAIL, ERROR

- **Score Numeric**
  - Label: “Score Numeric”
  - Type: table cell (number; appears computed)
  - Required: Unclear from current app
  - Editable: Unclear from current app (likely read-only/computed; not confirmed)
  - Default: Unclear from current app
  - Placeholder: Unclear from current app
  - Validation rules: Unclear from current app
  - Related: Airtable Submissions grid
  - Possible values observed: 0, 32, 100

### 3.2 Dashboard Fields (Vendor Metrics)

All are read-only table columns on the Vendor Metrics HTML page:
- Vendor Email (text)
- Vendor Name (text)
- Total (number)
- Pass (number)
- Fail (number)
- Error (number)
- Pass Rate % (number; displayed with decimals)
- Fail Rate % (number; displayed with decimals)
- Avg Score (Fail) (number; displayed with decimals)
- Latest Submission (datetime string; ISO-like in sample HTML)
- Avg Turnaround (s) (number; seconds with decimals)

### 3.3 Dashboard Fields (Processing Summary)

All are read-only table columns on the Processing Summary HTML page:
- Date (date string, e.g., YYYY-MM-DD)
- Total (number)
- Pass (number)
- Fail (number)
- Error (number)
- Pass Rate % (number with decimals)
- Unique Vendors (number)
- Unique Sites (number)

## 4. Component Inventory

- **Airtable Grid/Table**
  - Purpose: Row/column display of submissions
  - Inputs/displayed data: Submission fields (see Field Inventory)
  - Available actions: Toolbar actions (Hide fields, Filter, Group, Sort, Color, Share and sync)
  - Possible states: Unclear from current app
  - Where it appears: Airtable Submissions page

- **Dashboard Header**
  - Purpose: Identify dashboard and summarize totals
  - Inputs/displayed data: Page title + subtitle counts
  - Available actions: None
  - Possible states: Read-only
  - Where it appears: Both dashboard pages

- **Dashboard Table**
  - Purpose: Display metric rows/columns
  - Inputs/displayed data: Table columns listed above
  - Available actions: None shown
  - Possible states: Default, hover-highlight; Vendor Metrics rows may appear light red (condition unclear)
  - Where it appears: Both dashboard pages

- **Dashboard Footer**
  - Purpose: Show generation time and app name
  - Inputs/displayed data: Generated timestamp + “SiteOwlQA Automation Pipeline”
  - Available actions: None
  - Possible states: Read-only
  - Where it appears: Both dashboard pages

## 5. Data Display Requirements

- **Submission record fields (Airtable)**
  - Display Name: Submission record row
  - Where shown: Airtable Submissions grid
  - Format shown: Table cells by column
  - Editable: Unclear from current app
  - Conditional visibility: Unclear from current app

- **Processing Status**
  - Where shown: Airtable grid column “Processing Status”
  - Format: Text values (PASS/FAIL/ERROR observed)
  - Editable: Unclear from current app
  - Conditional visibility: Unclear from current app

- **Score (display)**
  - Where shown: Airtable grid column “Score”
  - Format: Either “PASS” or percentage string like “0.0%”, “32.0%”
  - Editable: Unclear from current app
  - Conditional visibility: Unclear from current app

- **Fail Summary**
  - Where shown: Airtable grid column “Fail Summary”
  - Format: Multi-line text; includes “Score: <x>% Issues found: …” pattern visible in screenshot
  - Editable: Unclear from current app
  - Conditional visibility: Unclear from current app

- **Vendor performance metrics**
  - Where shown: Vendor Metrics dashboard table
  - Format: Numeric counts and percentages with decimals; datetime string for Latest Submission
  - Editable: No

- **Daily processing metrics**
  - Where shown: Processing Summary dashboard table
  - Format: Date string + counts + percentages with decimals
  - Editable: No

## 6. Interaction Requirements

(Only interactions clearly present in the current UI evidence.)

- **Open toolbar controls (Airtable)**
  - Trigger Element: Toolbar buttons (“Hide fields”, “Filter”, “Group”, “Sort”, “Color”, “Share and sync”)
  - Source Screen: Airtable Submissions grid
  - Result in UI: Unclear from current app
  - Validation/confirmation: Unclear from current app

- **Open dashboard HTML pages**
  - Trigger Element: Opening `vendor_metrics.html` and `processing_summary.html`
  - Source Screen: OS / file system
  - Result in UI: Dashboard opens in browser

- **Row hover highlight (Dashboards)**
  - Trigger Element: Mouse hover over table row
  - Source Screen: Both dashboards
  - Result in UI: Row background changes to a light blue hover highlight

## 7. Navigation Requirements

- **Airtable navigation**
  - Main navigation items: Unclear from current app
  - Secondary navigation: Top toolbar present with the actions listed above
  - Breadcrumbs: Unclear from current app
  - Entry points to workflows: Airtable base “Submissions” table view (implied by screenshot)

- **Dashboards navigation**
  - Main navigation items: None shown
  - Secondary navigation: None shown
  - Tab systems: None
  - Subpages: Two separate HTML pages (Vendor Metrics, Processing Summary)

## 8. UI States

- **Processing Status values (visible states)**
  - PASS
  - FAIL
  - ERROR
  - QUEUED/PROCESSING: Unclear from current app UI (not visible in screenshot)

- **Dashboard row states**
  - Default
  - Hover-highlight

- **Vendor Metrics row background tint**
  - Light red row background appears in sample HTML output
  - Condition: Unclear from current app

## 9. Design Reconstruction Notes

- **Dashboards share a consistent template**
  - Light gray page background
  - Left-aligned title (large)
  - Subtitle below title in smaller gray text
  - Full-width table with dark blue header row and white header text
  - White table body with subtle shadow
  - Row hover highlight (light blue)
  - Footer with generation timestamp + app name

- **Airtable grid view**
  - Standard spreadsheet/grid layout with row numbers and column headers
  - Top toolbar shows: Hide fields, Filter, Group, Sort, Color, Share and sync
  - Additional Airtable base/table navigation: Unclear from current app
