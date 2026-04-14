"""User profile configuration loader for SiteOwlQA.

Sensitive configuration (tokens, passwords, DB credentials) is stored
in the user's home directory at ~/.siteowlqa/config.json rather than
in the monorepo. This keeps secrets safe and out of version control.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserConfig:
    """User profile configuration (sensitive values only)."""
    
    # Required: SQL Server
    sql_server: str
    sql_database: str
    airtable_token: str
    airtable_base_id: str
    airtable_table_name: str
    
    # Optional: SQL Server (with default)
    sql_driver: str = "ODBC Driver 17 for SQL Server"
    
    # Element LLM Gateway (optional)
    element_llm_gateway_url: str = ""
    element_llm_gateway_api_key: str = ""
    element_llm_gateway_model: str = "element:gpt-4o"
    element_llm_gateway_project_id: str = ""
    wmt_ca_path: str = ""
    
    # Reference data Excel (optional)
    reference_workbook_path: str = ""
    reference_workbook_sheet: str = ""
    reference_workbook_site_id_column: str = "SelectedSiteID"

    # Scout Airtable source (optional — separate base/token from Survey)
    # Leaving base_id + table_name blank disables the Scout dashboard tab.
    scout_airtable_token: str = ""   # blank → reuse main airtable_token
    scout_airtable_base_id: str = ""
    scout_airtable_table_name: str = ""
    scout_airtable_view_id: str = ""  # blank → default view


def get_user_config_path() -> Path:
    """Return the user config file path: ~/.siteowlqa/config.json"""
    home = Path.home()
    config_dir = home / ".siteowlqa"
    return config_dir / "config.json"


def load_user_config() -> Optional[UserConfig]:
    """Load user configuration from ~/.siteowlqa/config.json.
    
    Returns:
        UserConfig if file exists and is valid, None otherwise.
    """
    config_path = get_user_config_path()
    
    if not config_path.exists():
        return None
    
    try:
        import dataclasses
        data = json.loads(config_path.read_text(encoding='utf-8'))
        # Filter out keys not in UserConfig (e.g. smtp_* from old configs)
        valid_fields = {f.name for f in dataclasses.fields(UserConfig)}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return UserConfig(**filtered)
    except Exception as e:
        log.warning(f"Failed to load user config from {config_path}: {e}")
        return None


def save_user_config(config: UserConfig) -> None:
    """Save user configuration to ~/.siteowlqa/config.json."""
    config_path = get_user_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Make file readable only by owner (600 permissions)
    data = {
        'sql_server': config.sql_server,
        'sql_database': config.sql_database,
        'sql_driver': config.sql_driver,
        'airtable_token': config.airtable_token,
        'airtable_base_id': config.airtable_base_id,
        'airtable_table_name': config.airtable_table_name,
        'element_llm_gateway_url': config.element_llm_gateway_url,
        'element_llm_gateway_api_key': config.element_llm_gateway_api_key,
        'element_llm_gateway_model': config.element_llm_gateway_model,
        'element_llm_gateway_project_id': config.element_llm_gateway_project_id,
        'wmt_ca_path': config.wmt_ca_path,
        'reference_workbook_path': config.reference_workbook_path,
        'reference_workbook_sheet': config.reference_workbook_sheet,
        'reference_workbook_site_id_column': config.reference_workbook_site_id_column,
        'scout_airtable_token': config.scout_airtable_token,
        'scout_airtable_base_id': config.scout_airtable_base_id,
        'scout_airtable_table_name': config.scout_airtable_table_name,
        'scout_airtable_view_id': config.scout_airtable_view_id,
    }
    
    config_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    
    # On Windows, use icacls to restrict permissions
    import platform
    if platform.system() == 'Windows':
        import subprocess
        try:
            subprocess.run(
                ['icacls', str(config_path), '/inheritance:r', '/grant:r', f'{Path.home().name}:F'],
                check=False,
                capture_output=True
            )
        except Exception as e:
            log.warning(f"Could not set file permissions: {e}")
    else:
        # Unix-like systems
        try:
            config_path.chmod(0o600)
        except Exception as e:
            log.warning(f"Could not set file permissions: {e}")
    
    log.info(f"User config saved to {config_path}")


def create_user_config_interactive() -> UserConfig:
    """Interactively prompt user to create configuration.
    
    This is called by setup scripts and provides a guided wizard.
    """
    import sys
    
    print("\n" + "="*70)
    print("SiteOwlQA Configuration Setup")
    print("="*70)
    print("\nThis wizard will create your user configuration file at:")
    print(f"  {get_user_config_path()}")
    print("\nYour sensitive data (tokens, passwords, credentials) will be stored")
    print("in your user home directory, NOT in the git repository.")
    print("\n" + "-"*70)
    
    # SQL Server
    print("\n[1/7] SQL Server Configuration")
    sql_server = input("  SQL Server (e.g., localhost\\SITEOWL): ").strip()
    sql_database = input("  SQL Database name (e.g., SiteOwlQA): ").strip()
    sql_driver = input("  SQL Driver [default: ODBC Driver 17 for SQL Server]: ").strip()
    if not sql_driver:
        sql_driver = "ODBC Driver 17 for SQL Server"
    
    # Airtable
    print("\n[2/7] Airtable Configuration")
    airtable_token = input("  Airtable API Token (from https://airtable.com/create/tokens): ").strip()
    airtable_base_id = input("  Airtable Base ID (from URL airtable.com/app<BASE_ID>/...): ").strip()
    airtable_table_name = input("  Airtable Table Name (exact name, case-sensitive): ").strip()
    
    # Element LLM Gateway
    print("\n[3/6] Element LLM Gateway (optional - leave blank to skip)")
    element_llm_gateway_url = input("  LLM Gateway URL: ").strip()
    element_llm_gateway_api_key = ""
    element_llm_gateway_project_id = ""
    wmt_ca_path = ""
    
    if element_llm_gateway_url:
        element_llm_gateway_api_key = input("  LLM Gateway API Key: ").strip()
        element_llm_gateway_project_id = input("  LLM Gateway Project ID: ").strip()
        wmt_ca_path = input("  Walmart CA Certificate Path: ").strip()
    
    # Reference Workbook
    print("\n[4/6] Reference Data Workbook (optional)")
    reference_workbook_path = input("  Excel file path (leave blank to use SQL Server): ").strip()
    reference_workbook_sheet = ""
    reference_workbook_site_id_column = "SelectedSiteID"

    if reference_workbook_path:
        reference_workbook_sheet = input("  Sheet name [default: SQL DB MASTER]: ").strip()
        if not reference_workbook_sheet:
            reference_workbook_sheet = "SQL DB MASTER"
        reference_workbook_site_id_column = input("  Site ID column [default: SelectedSiteID]: ").strip()
        if not reference_workbook_site_id_column:
            reference_workbook_site_id_column = "SelectedSiteID"

    # Scout Airtable
    print("\n[5/6] Scout Airtable Source (for Scout dashboard tab)")
    print("  Leave base ID + table blank to disable the Scout tab.")
    scout_airtable_base_id = input("  Scout Base ID (app...): ").strip()
    scout_airtable_table_name = ""
    scout_airtable_token = ""
    scout_airtable_view_id = ""

    if scout_airtable_base_id:
        scout_airtable_table_name = input("  Scout Table Name (exact, case-sensitive): ").strip()
        scout_airtable_token = input("  Scout API Token (leave blank to reuse Survey token): ").strip()
        scout_airtable_view_id = input("  Scout View ID (viw..., leave blank for default): ").strip()

    # Confirm
    print("\n" + "-"*70)
    print("[6/6] Review Configuration")
    print("-"*70)
    print(f"  SQL Server:        {sql_server} / {sql_database}")
    print(f"  Survey Airtable:   {airtable_base_id} / {airtable_table_name}")
    if scout_airtable_base_id:
        print(f"  Scout Airtable:    {scout_airtable_base_id} / {scout_airtable_table_name}")
    else:
        print(f"  Scout Airtable:    (disabled)")
    if element_llm_gateway_url:
        print(f"  LLM Gateway:       Configured")
    if reference_workbook_path:
        print(f"  Reference:         {reference_workbook_path}")

    confirm = input("\nSave configuration? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        sys.exit(0)

    config = UserConfig(
        sql_server=sql_server,
        sql_database=sql_database,
        sql_driver=sql_driver,
        airtable_token=airtable_token,
        airtable_base_id=airtable_base_id,
        airtable_table_name=airtable_table_name,
        element_llm_gateway_url=element_llm_gateway_url,
        element_llm_gateway_api_key=element_llm_gateway_api_key,
        element_llm_gateway_project_id=element_llm_gateway_project_id,
        wmt_ca_path=wmt_ca_path,
        reference_workbook_path=reference_workbook_path,
        reference_workbook_sheet=reference_workbook_sheet,
        reference_workbook_site_id_column=reference_workbook_site_id_column,
        scout_airtable_token=scout_airtable_token,
        scout_airtable_base_id=scout_airtable_base_id,
        scout_airtable_table_name=scout_airtable_table_name,
        scout_airtable_view_id=scout_airtable_view_id,
    )
    
    save_user_config(config)
    print(f"\n✓ Configuration saved to: {get_user_config_path()}")
    return config
