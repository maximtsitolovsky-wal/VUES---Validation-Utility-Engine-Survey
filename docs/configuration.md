# Configuration Guide

SiteOwlQA separates sensitive and non-sensitive configuration.

## Quick Start

### 1. Run Setup Wizard (First Time)

```bash
python -m siteowlqa.setup_config
```

This creates your user configuration file at:
```
~/.siteowlqa/config.json
```

The wizard will ask you for:
- SQL Server connection details
- Airtable API tokens and base info
- (Optional) SMTP server for email
- (Optional) LLM Gateway credentials
- (Optional) Reference data Excel file path

### 2. Run the Pipeline

```bash
python main.py
```

Or use the Windows launcher:
```bash
start_pipeline.bat
```

---

## Configuration Files

### ~/.siteowlqa/config.json (Sensitive Data)

**Location:** Your user home directory, NOT in git

**Contains:**
- SQL Server credentials
- Airtable API tokens
- SMTP passwords
- LLM API keys
- File paths

**Permissions:** Read-only by your user (mode 0600 on Unix, restricted on Windows)

**Example structure:**
```json
{
  "sql_server": "localhost\\SITEOWL",
  "sql_database": "SiteOwlQA",
  "sql_driver": "ODBC Driver 17 for SQL Server",
  "airtable_token": "pat_XXXXXXXXXXXXXXXXXXXXX",
  "airtable_base_id": "appXXXXXXXXXXXXXX",
  "airtable_table_name": "Survey Submissions",
  "element_llm_gateway_url": "https://ml.prod.walmart.com:31999/element/genai/project/YOUR_PROJECT/openai/v1",
  "element_llm_gateway_api_key": "sk-XXXXXXXXXXXXXXXXXXXXXX",
  "element_llm_gateway_model": "element:gpt-4o",
  "element_llm_gateway_project_id": "YOUR_PROJECT",
  "wmt_ca_path": "C:/path/to/walmart-ca.crt",
  "reference_workbook_path": "C:/Users/you/OneDrive - Walmart Inc/SQL DB MASTER.xlsx",
  "reference_workbook_sheet": "SQL DB MASTER",
  "reference_workbook_site_id_column": "SelectedSiteID"
}
```

### .env (Non-Sensitive Settings)

**Location:** Repository root (CAN be committed)

**Contains:**
- Poll intervals
- Worker thread count
- Folder paths
- Reference data source
- Feature flags

**Example:**
```
POLL_INTERVAL_SECONDS=60
WORKER_THREADS=3
REFERENCE_SOURCE=sql
TEMP_DIR=C:/SiteOwlQA_App/temp
OUTPUT_DIR=C:/SiteOwlQA_App/output
LOG_DIR=C:/SiteOwlQA_App/logs
ARCHIVE_DIR=C:/SiteOwlQA_App/archive
SUBMISSIONS_DIR=C:/SiteOwlQA_App/archive/submissions
```

---

## Setup Details

### SQL Server

Example:
```
SQL Server: localhost\SITEOWL
Database: SiteOwlQA
Driver: ODBC Driver 17 for SQL Server
```

**Note:** The pipeline uses Windows Integrated Authentication (Trusted Connection).
No username/password needed if your Windows account has SQL access.

### Airtable

**Get Base ID:**
1. Open your Airtable base in browser
2. URL format: `airtable.com/app<BASE_ID>/...`
3. Copy the `<BASE_ID>` part

**Get API Token:**
1. Go to https://airtable.com/create/tokens
2. Create new token with:
   - Read all tables
   - Write data
   - Create table
3. Copy token (starts with `pat_`)

**Table Name:**
- Exact name of your submissions table (case-sensitive)
- Example: "Survey Submissions"

### SMTP (Optional)

If you want the pipeline to send emails directly:

**Office 365:**
```
Server: smtp.office365.com
Port: 587
Username: your.email@company.com
Password: your-app-password
```

**Other providers:** Check with your IT team

### Element LLM Gateway (Optional)

For advanced AI-powered weekly highlights:

1. Get project ID from your Element LLM contact
2. Generate API key at Element dashboard
3. Download Walmart CA certificate
4. Provide all three values in config

If not configured, the system uses deterministic summaries.

### Reference Data (Optional)

**Option 1: SQL Server (Default)**
```
REFERENCE_SOURCE=sql
```
The pipeline fetches reference data from `dbo.vw_ReferenceExport` view.

**Option 2: Excel Workbook**
```
REFERENCE_SOURCE=excel
```
Provide path to Excel file with schema:
- First column: Site ID
- Other columns: Reference values

**Option 3: Auto (Preferred)**
```
REFERENCE_SOURCE=auto
```
Uses Excel if configured, falls back to SQL.

---

## Changing Configuration

### Edit User Config

**Do NOT edit ~/.siteowlqa/config.json by hand.** Instead, run setup again:

```bash
python -m siteowlqa.setup_config
```

This will:
- Ask for new values
- Update file with proper permissions
- Validate all inputs

### Edit .env

You can edit `.env` directly. Changes take effect on next pipeline restart.

```bash
# Edit the file
code .env

# Restart pipeline
stop_pipeline.bat
start_pipeline.bat
```

---

## Troubleshooting

### "User configuration not found"

**Solution:** Run setup wizard
```bash
python -m siteowlqa.setup_config
```

### "Failed to load user config"

**Possible causes:**
- File permissions too open (security risk)
- JSON syntax error
- Missing required fields

**Solution:** Delete and recreate
```bash
rm ~/.siteowlqa/config.json
python -m siteowlqa.setup_config
```

### "SQL Server connection failed"

**Check:**
1. SQL Server name is correct
2. Database name is correct
3. Windows account has database access
4. SQL Server allows Windows auth

**Test connection:**
```bash
python -c "from siteowlqa.config import load_config; c=load_config(); print(c.sql_connection_string)"
```

### "Airtable authentication failed"

**Check:**
1. Token starts with `pat_`
2. Token has read/write permissions
3. Token hasn't expired
4. Base ID is correct
5. Table name matches exactly (case-sensitive)

**Regenerate token:**
- Go to https://airtable.com/create/tokens
- Create new token
- Update config with: `python -m siteowlqa.setup_config`

---

## Security

### Sensitive Data Protection

✅ **What we do:**
- Store tokens/passwords only in `~/.siteowlqa/config.json`
- Restrict file permissions (mode 0600 / Windows restricted)
- Never commit sensitive data to git
- Never log sensitive values

❌ **What NOT to do:**
- Don't put tokens in .env file
- Don't commit config.json
- Don't share your API tokens
- Don't put passwords in environment variables

### File Locations

```
Your User Directory (~)
└── .siteowlqa/
    └── config.json        ← Sensitive data (0600 permissions)

Repository Root
├── .env                   ← Non-sensitive settings (CAN commit)
├── .env.example           ← Template (CAN commit)
├── README.md              ← Documentation
└── src/siteowlqa/
    ├── config.py          ← Config loader
    ├── user_config.py     ← User config handler
    └── setup_config.py    ← Setup wizard
```

---

## Advanced: Manual JSON Editing

If you must edit `~/.siteowlqa/config.json` by hand:

1. **Backup first:**
   ```bash
   cp ~/.siteowlqa/config.json ~/.siteowlqa/config.json.bak
   ```

2. **Edit:**
   ```bash
   # Windows
   notepad %USERPROFILE%/.siteowlqa/config.json
   
   # Mac/Linux
   nano ~/.siteowlqa/config.json
   ```

3. **Validate JSON syntax** (paste into https://jsonlint.com/)

4. **Test configuration:**
   ```bash
   python -m siteowlqa.setup_config
   ```
   Choose "no" when asked to save. This validates without overwriting.

5. **Restart pipeline:**
   ```bash
   stop_pipeline.bat
   start_pipeline.bat
   ```

---

## See Also

- Main documentation: [`README.md`](../README.md)
- Windows automation: [`ops/windows/README.md`](../ops/windows/README.md)
- Development guide: [`development.md`](../development.md)
- Source code: [`src/siteowlqa/config.py`](../src/siteowlqa/config.py)
