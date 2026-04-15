"""
Scout Airtable Image Downloader  —  RISK-003 mitigation
========================================================
Downloads all images from the Scout Airtable into:
  OUT_ROOT/<Site Number>/<filename>
  OUT_ROOT/<Site Number>/site_info.json

Network note (settled 2026-04-15):
  Python requests CANNOT reach v5.airtableusercontent.com on Walmart network
  (DNS blocked at WinSock level).  PowerShell Invoke-WebRequest CAN reach it
  via WinINet (browser proxy/PAC stack).  Downloads go through PowerShell
  subprocess; API calls stay in requests — both are proven working paths.

Schedule: Mon-Fri 10:00 AM and 3:00 PM via Windows Task Scheduler.
Register:  ops/windows/register_scout_task.ps1  (run as admin, once)
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY   = "patPR0WWxXCE0loRO.d18126548ad25b8aaf9fd43e2ac69479b1378e46d7f8c6efbdd88f7197a4d495"
BASE_ID   = "appAwgaX89x0JxG3Z"
TABLE_ID  = "tblC4o9AvVulyxFMk"
IMAGE_COL = "Upload Images"
SITE_COL  = "Site Number"

OUT_ROOT  = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Documents\BaselinePrinter\Scout Files")
LOG_FILE  = Path(__file__).resolve().parents[1] / "logs" / "scout_downloader.log"

AIRTABLE_URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
AIRTABLE_HDR = {"Authorization": f"Bearer {API_KEY}"}


# ── Helpers ───────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(msg, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} {msg}\n")
    except Exception:
        pass


def sanitize(name: str) -> str:
    """Strip characters Windows won't allow in file/folder names."""
    return re.sub(r'[\\/:*?"<>|]', "_", str(name)).strip()


def fetch_records() -> list[dict]:
    """Page through all Airtable records. API calls work fine via requests."""
    records, params = [], {}
    while True:
        resp = requests.get(AIRTABLE_URL, headers=AIRTABLE_HDR,
                            params=params, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        records.extend(body.get("records", []))
        offset = body.get("offset")
        if not offset:
            break
        params = {"offset": offset}
        time.sleep(0.2)
    return records


def ps_download(url: str, dest: Path, retries: int = 2) -> bool:
    """
    Download via PowerShell Invoke-WebRequest (WinINet/browser stack).
    Python requests can't reach v5.airtableusercontent.com on Walmart network
    due to DNS blocking at WinSock level — WinINet bypasses this via PAC/auto-proxy.
    Retries handle intermittent WinINet DNS cache expiry between downloads.
    """
    cmd = (
        f"Invoke-WebRequest -Uri '{url}' -OutFile '{dest}' "
        f"-UseBasicParsing -TimeoutSec 30"
    )
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, text=True, timeout=45
            )
            if result.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
                return True
            err = (result.stderr or result.stdout or "unknown").strip()[:120]
            log(f"   [WARN] attempt {attempt}: {err}")
        except subprocess.TimeoutExpired:
            log(f"   [WARN] attempt {attempt}: subprocess timed out")
        if attempt < retries:
            time.sleep(2)
    log(f"   [ERR] {dest.name}: all {retries} attempts failed")
    return False


def save_site_info(site_dir: Path, record: dict) -> None:
    """Append/merge this record's field data into site_info.json."""
    info_path = site_dir / "site_info.json"
    existing = []
    if info_path.exists():
        try:
            data = json.loads(info_path.read_text(encoding="utf-8"))
            existing = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            pass
    existing.append({
        "airtable_id": record["id"],
        "created":     record["createdTime"],
        "fields":      record.get("fields", {}),
    })
    info_path.write_text(json.dumps(existing, indent=2, default=str),
                         encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    log(f"[START] {datetime.now().isoformat()}")

    log("[*] Fetching records from Airtable...")
    records = fetch_records()
    log(f"[OK]  {len(records)} records\n")

    ok = err = skip = 0

    for i, rec in enumerate(records, 1):
        fields      = rec.get("fields", {})
        site        = sanitize(str(fields.get(SITE_COL, f"UNKNOWN_{rec['id']}")))
        attachments = fields.get(IMAGE_COL) or []

        if not attachments:
            continue

        site_dir = OUT_ROOT / site
        site_dir.mkdir(parents=True, exist_ok=True)

        # Save survey field data alongside the images
        save_site_info(site_dir, rec)

        log(f"[{i}/{len(records)}] Site {site} — {len(attachments)} image(s)")
        for att in attachments:
            filename = sanitize(att.get("filename") or att.get("id", "file"))
            dest     = site_dir / filename
            if dest.exists() and dest.stat().st_size > 0:
                log(f"   [SKIP] {filename}")
                skip += 1
                continue
            if ps_download(att["url"], dest):
                log(f"   [OK]   {filename}  ({dest.stat().st_size:,} bytes)")
                ok += 1
            else:
                err += 1

    log(f"\n[DONE] OK={ok}  SKIP={skip}  ERR={err}")
    log(f"[DIR]  {OUT_ROOT}")
    sys.exit(1 if err and not ok else 0)


if __name__ == "__main__":
    main()
