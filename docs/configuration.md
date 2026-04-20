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
- Airtable API tokens and base info
- (Optional) LLM Gateway credentials
- (Optional) Reference data Excel file path

### 2. Configure BigQuery (Required)

Set these in your `.env` file:

```env
REFERENCE_SOURCE=bigquery
SITEOWLQA_GCP_PROJECT=wmt-ww-ess-gsoc-prod
SITEOWLQA_BIGQUERY_DATASET=ww_ess_gsoc_siteowl_dl_secure
GOOGLE_APPLICATION_CREDENTIALS=C:/path/to/your-service-account.json
```

### 3. Run the Pipeline

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
- Airtable API tokens
- LLM API keys
- File paths

**Example structure:**
```json
{
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
- BigQuery project/dataset

**Example:**
```env
POLL_INTERVAL_SECONDS=60
WORKER_THREADS=3
REFERENCE_SOURCE=bigquery

# BigQuery
SITEOWLQA_GCP_PROJECT=wmt-ww-ess-gsoc-prod
SITEOWLQA_BIGQUERY_DATASET=ww_ess_gsoc_siteowl_dl_secure
GOOGLE_APPLICATION_CREDENTIALS=C:/path/to/service-account.json

# Directories
TEMP_DIR=C:/SiteOwlQA_App/temp
OUTPUT_DIR=C:/SiteOwlQA_App/output
LOG_DIR=C:/SiteOwlQA_App/logs
ARCHIVE_DIR=C:/SiteOwlQA_App/archive
SUBMISSIONS_DIR=C:/SiteOwlQA_App/archive/submissions
```

---

## Setup Details

### BigQuery (Required)

The pipeline fetches reference data from `device_survey_task_details` in BigQuery.

**Configuration:**
```env
REFERENCE_SOURCE=bigquery
SITEOWLQA_GCP_PROJECT=wmt-ww-ess-gsoc-prod
SITEOWLQA_BIGQUERY_DATASET=ww_ess_gsoc_siteowl_dl_secure
```

**Credentials:**
- Set `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON key file
- Or use Application Default Credentials (gcloud auth)

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

### Email Notifications

**Email is handled entirely by Airtable automations.**

The pipeline writes PASS/FAIL/ERROR to the `Processing Status` field. An Airtable automation rule watches that field and sends vendor emails independently.

There is no SMTP code in this codebase.

### Element LLM Gateway (Optional)

For advanced AI-powered weekly highlights:

1. Get project ID from your Element LLM contact
2. Generate API key at Element dashboard
3. Download Walmart CA certificate
4. Provide all three values in config

If not configured, the system uses deterministic summaries.

### Reference Data Sources

**Option 1: BigQuery (Default)**
```env
REFERENCE_SOURCE=bigquery
```
The pipeline fetches reference data from `device_survey_task_details` (GSOC production table).

**Option 2: Excel Workbook**
```env
REFERENCE_SOURCE=excel
```
Provide path to Excel file in your user config:
```json
{
  "reference_workbook_path": "C:/path/to/workbook.xlsx",
  "reference_workbook_sheet": "Sheet1",
  "reference_workbook_site_id_column": "SelectedSiteID"
}
```

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

### "BigQuery connection failed"

**Check:**
1. GCP project ID is correct
2. Dataset name is correct
3. Service account has BigQuery Data Viewer role
4. `GOOGLE_APPLICATION_CREDENTIALS` points to valid JSON key

**Test connection:**
```bash
python -c "from siteowlqa.config import load_config; from siteowlqa.reference_data import fetch_reference_rows; cfg=load_config(); print(fetch_reference_rows(cfg, '3654'))"
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

## See Also

- Main documentation: [`README.md`](../README.md)
- Windows automation: [`ops/windows/README.md`](../ops/windows/README.md)
- Development guide: [`development.md`](../development.md)
- Source code: [`src/siteowlqa/config.py`](../src/siteowlqa/config.py)
