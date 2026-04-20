"""Analyze network bandwidth requirements for SiteOwlQA pipeline."""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
import json

def format_bytes(b):
    """Format bytes as human-readable."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

def main():
    print("=" * 70)
    print("VUES Network Bandwidth Analysis")
    print("=" * 70)
    
    print("\n## Per-Submission Network Traffic\n")
    
    # Typical submission sizes (based on real data)
    avg_xlsx_size_kb = 50  # Average vendor XLSX file
    max_xlsx_size_kb = 500  # Large submission
    
    # Airtable API calls per submission
    airtable_calls = {
        "fetch_pending": 1,      # List records (~2KB response)
        "status_updates": 3,     # QUEUED, PROCESSING, PASS/FAIL (~500B each)
        "download_attachment": 1, # The actual file
        "patch_results": 1,      # Score, True Score, Fail Summary (~1KB)
    }
    
    # BigQuery per submission
    bq_query_size_kb = 5  # Typical query response for one site
    
    print("### Inbound (Download)")
    print(f"  Airtable record list:     ~2 KB")
    print(f"  Vendor attachment (avg):  ~{avg_xlsx_size_kb} KB")
    print(f"  Vendor attachment (max):  ~{max_xlsx_size_kb} KB")
    print(f"  BigQuery reference data:  ~{bq_query_size_kb} KB")
    print(f"  ---")
    print(f"  Total per submission:     ~{2 + avg_xlsx_size_kb + bq_query_size_kb} KB (avg)")
    print(f"                            ~{2 + max_xlsx_size_kb + bq_query_size_kb} KB (max)")
    
    print("\n### Outbound (Upload)")
    print(f"  Status updates (3x):      ~1.5 KB")
    print(f"  Result patch:             ~1 KB")
    print(f"  ---")
    print(f"  Total per submission:     ~2.5 KB")
    
    print("\n## Polling Overhead (Background)\n")
    poll_interval_sec = 60
    polls_per_hour = 3600 / poll_interval_sec
    poll_response_kb = 2  # Empty or small response
    
    print(f"  Poll interval:            {poll_interval_sec} seconds")
    print(f"  Polls per hour:           {polls_per_hour:.0f}")
    print(f"  Bytes per poll (idle):    ~{poll_response_kb} KB")
    print(f"  Hourly idle traffic:      ~{polls_per_hour * poll_response_kb:.0f} KB/hr")
    print(f"  Daily idle traffic:       ~{polls_per_hour * poll_response_kb * 24 / 1024:.1f} MB/day")
    
    print("\n## Estimated Usage Scenarios\n")
    
    scenarios = [
        ("Light (10 submissions/day)", 10),
        ("Medium (50 submissions/day)", 50),
        ("Heavy (200 submissions/day)", 200),
    ]
    
    for name, subs_per_day in scenarios:
        download_mb = subs_per_day * (avg_xlsx_size_kb + bq_query_size_kb + 2) / 1024
        upload_mb = subs_per_day * 2.5 / 1024
        idle_mb = polls_per_hour * poll_response_kb * 24 / 1024
        total_mb = download_mb + upload_mb + idle_mb
        
        print(f"  {name}:")
        print(f"    Submissions:    {download_mb:.1f} MB download + {upload_mb:.1f} MB upload")
        print(f"    Polling:        {idle_mb:.1f} MB")
        print(f"    Daily Total:    {total_mb:.1f} MB/day ({total_mb * 30:.0f} MB/month)")
        print()
    
    print("## Minimum Requirements\n")
    print("  Connection:       Any broadband (1+ Mbps)")
    print("  Latency:          <500ms to Airtable/GCP (US regions)")
    print("  Monthly data:     <5 GB for typical usage")
    print("  Concurrent:       1-3 parallel connections")
    print()
    
    print("## Peak Bandwidth\n")
    print("  Downloading large XLSX:   ~500 KB")
    print("  BigQuery query:           ~5 KB")
    print("  At 3 workers parallel:    ~1.5 MB burst")
    print("  Recommended minimum:      5 Mbps download")
    print()
    
    print("## External Services\n")
    print("  Airtable API:     api.airtable.com (US-East)")
    print("  BigQuery:         bigquery.googleapis.com")
    print("  GCS (optional):   storage.googleapis.com")
    print()
    print("  Firewall ports:   443 (HTTPS) outbound only")
    print("  Proxy support:    HTTP_PROXY / HTTPS_PROXY env vars")

if __name__ == "__main__":
    main()
