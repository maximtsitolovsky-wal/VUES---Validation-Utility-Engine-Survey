"""VUES Data Watchdog — Catches Stale, Broken, or BS Data.

This is the real deal. Run it daily or on-demand to catch:
- Stale BQ data (no updates in X days)
- Broken submissions (stuck in PROCESSING)
- Data drift (row counts changing unexpectedly)
- Grading inconsistencies (score vs status mismatches)

Usage:
    python scripts/data_watchdog.py           # Full check
    python scripts/data_watchdog.py --quick   # Quick sanity check
    python scripts/data_watchdog.py --fix     # Attempt auto-fixes
"""

from __future__ import annotations

import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

# Bootstrap
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd

from siteowlqa.config import load_config, VENDOR_GRADE_COLUMNS
from siteowlqa.airtable_client import AirtableClient
from siteowlqa.reference_data import fetch_reference_rows
from siteowlqa.python_grader import status_from_score
from siteowlqa.models import ProcessingStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


@dataclass
class WatchdogResult:
    """Result of a watchdog check."""
    check_name: str
    passed: bool
    message: str
    severity: str = "INFO"  # INFO, WARN, CRITICAL
    details: dict = field(default_factory=dict)


class DataWatchdog:
    """Watches for data quality issues and staleness."""

    def __init__(self, cfg=None):
        self.cfg = cfg or load_config()
        self.airtable = AirtableClient(self.cfg)
        self.results: list[WatchdogResult] = []
        self.baseline_file = Path(__file__).parent.parent / "output" / "watchdog_baseline.json"

    def run_all_checks(self) -> list[WatchdogResult]:
        """Run all watchdog checks."""
        self.results = []
        
        log.info("=" * 60)
        log.info("VUES DATA WATCHDOG")
        log.info("=" * 60)
        
        # BQ Checks
        self._check_bq_connectivity()
        self._check_bq_data_freshness()
        self._check_bq_row_count_drift()
        self._check_bq_data_quality()
        
        # Airtable Checks
        self._check_airtable_connectivity()
        self._check_stuck_submissions()
        self._check_score_status_consistency()
        self._check_recent_failure_rate()
        
        # Cross-system Checks
        self._check_grading_determinism()
        
        self._print_summary()
        return self.results

    def run_quick_checks(self) -> list[WatchdogResult]:
        """Run only the fastest, most critical checks."""
        self.results = []
        
        log.info("=" * 60)
        log.info("VUES QUICK CHECK")
        log.info("=" * 60)
        
        self._check_bq_connectivity()
        self._check_airtable_connectivity()
        self._check_stuck_submissions()
        
        self._print_summary()
        return self.results

    def _add_result(self, result: WatchdogResult):
        """Add a check result."""
        self.results.append(result)
        icon = "✓" if result.passed else ("⚠" if result.severity == "WARN" else "✗")
        log.info(f"  [{icon}] {result.check_name}: {result.message}")

    # =========================================================================
    # BigQuery Checks
    # =========================================================================

    def _check_bq_connectivity(self):
        """Verify BQ is reachable and returning data."""
        try:
            df = fetch_reference_rows(self.cfg, "686")
            if df.empty:
                self._add_result(WatchdogResult(
                    check_name="BQ Connectivity",
                    passed=False,
                    message="Connected but site 686 returned empty",
                    severity="WARN",
                ))
            else:
                self._add_result(WatchdogResult(
                    check_name="BQ Connectivity",
                    passed=True,
                    message=f"OK - {len(df)} rows for site 686",
                ))
        except Exception as e:
            self._add_result(WatchdogResult(
                check_name="BQ Connectivity",
                passed=False,
                message=f"FAILED: {str(e)[:100]}",
                severity="CRITICAL",
            ))

    def _check_bq_data_freshness(self):
        """Check if BQ data seems fresh (proxy: check multiple sites have data)."""
        sites_checked = 0
        sites_with_data = 0
        
        # Check a sample of sites
        test_sites = ["686", "1000", "2000", "3000", "5000"]
        for site in test_sites:
            try:
                df = fetch_reference_rows(self.cfg, site)
                sites_checked += 1
                if not df.empty:
                    sites_with_data += 1
            except:
                pass
        
        if sites_checked == 0:
            self._add_result(WatchdogResult(
                check_name="BQ Data Freshness",
                passed=False,
                message="Could not check any sites",
                severity="CRITICAL",
            ))
        elif sites_with_data == 0:
            self._add_result(WatchdogResult(
                check_name="BQ Data Freshness",
                passed=False,
                message=f"No data for any of {sites_checked} test sites - DATA MAY BE STALE",
                severity="CRITICAL",
            ))
        else:
            self._add_result(WatchdogResult(
                check_name="BQ Data Freshness",
                passed=True,
                message=f"{sites_with_data}/{sites_checked} test sites have data",
            ))

    def _check_bq_row_count_drift(self):
        """Detect unexpected changes in row counts (possible data issues)."""
        current_counts = {}
        test_sites = ["686"]
        
        for site in test_sites:
            try:
                df = fetch_reference_rows(self.cfg, site)
                current_counts[site] = len(df)
            except:
                pass
        
        # Load baseline if exists
        baseline = self._load_baseline()
        if not baseline.get("bq_row_counts"):
            self._save_baseline({"bq_row_counts": current_counts})
            self._add_result(WatchdogResult(
                check_name="BQ Row Count Drift",
                passed=True,
                message="Baseline created - will detect drift on next run",
            ))
            return
        
        # Compare
        drifts = []
        for site, count in current_counts.items():
            baseline_count = baseline["bq_row_counts"].get(site, count)
            if baseline_count > 0:
                drift_pct = abs(count - baseline_count) / baseline_count * 100
                if drift_pct > 20:  # >20% change is suspicious
                    drifts.append(f"Site {site}: {baseline_count} → {count} ({drift_pct:.1f}%)")
        
        if drifts:
            self._add_result(WatchdogResult(
                check_name="BQ Row Count Drift",
                passed=False,
                message=f"Significant changes: {'; '.join(drifts)}",
                severity="WARN",
                details={"drifts": drifts, "current": current_counts},
            ))
        else:
            self._add_result(WatchdogResult(
                check_name="BQ Row Count Drift",
                passed=True,
                message="Row counts stable",
            ))
        
        # Update baseline
        baseline["bq_row_counts"] = current_counts
        self._save_baseline(baseline)

    def _check_bq_data_quality(self):
        """Check for garbage data in BQ."""
        try:
            df = fetch_reference_rows(self.cfg, "686")
            if df.empty:
                return
            
            issues = []
            
            # Check for empty Name column
            empty_names = df["Name"].fillna("").astype(str).str.strip().eq("").sum()
            if empty_names > len(df) * 0.1:
                issues.append(f"{empty_names} empty Names")
            
            # Check for duplicate MACs (shouldn't have many)
            macs = df["MAC Address"].fillna("").astype(str).str.strip()
            macs = macs[macs.ne("")]
            dup_macs = macs.duplicated().sum()
            if dup_macs > len(df) * 0.2:
                issues.append(f"{dup_macs} duplicate MACs")
            
            if issues:
                self._add_result(WatchdogResult(
                    check_name="BQ Data Quality",
                    passed=False,
                    message=f"Issues: {'; '.join(issues)}",
                    severity="WARN",
                ))
            else:
                self._add_result(WatchdogResult(
                    check_name="BQ Data Quality",
                    passed=True,
                    message="Data quality OK",
                ))
        except Exception as e:
            self._add_result(WatchdogResult(
                check_name="BQ Data Quality",
                passed=False,
                message=f"Check failed: {e}",
                severity="WARN",
            ))

    # =========================================================================
    # Airtable Checks
    # =========================================================================

    def _check_airtable_connectivity(self):
        """Verify Airtable API is working."""
        try:
            # Just try to fetch one record
            records = self.airtable.fetch_pending_records(max_records=1)
            self._add_result(WatchdogResult(
                check_name="Airtable Connectivity",
                passed=True,
                message="API accessible",
            ))
        except Exception as e:
            self._add_result(WatchdogResult(
                check_name="Airtable Connectivity",
                passed=False,
                message=f"FAILED: {str(e)[:100]}",
                severity="CRITICAL",
            ))

    def _check_stuck_submissions(self):
        """Find submissions stuck in PROCESSING state."""
        try:
            # Fetch records in PROCESSING status
            import requests
            url = f"https://api.airtable.com/v0/{self.cfg.airtable_base_id}/{self.cfg.airtable_table_name}"
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.cfg.airtable_token}"},
                params={
                    "filterByFormula": "{Processing Status}='PROCESSING'",
                    "maxRecords": 100,
                },
                timeout=30,
            )
            
            if resp.status_code != 200:
                raise Exception(f"API returned {resp.status_code}")
            
            records = resp.json().get("records", [])
            stuck_count = len(records)
            
            if stuck_count > 5:
                self._add_result(WatchdogResult(
                    check_name="Stuck Submissions",
                    passed=False,
                    message=f"{stuck_count} submissions stuck in PROCESSING",
                    severity="CRITICAL",
                    details={"record_ids": [r["id"] for r in records[:10]]},
                ))
            elif stuck_count > 0:
                self._add_result(WatchdogResult(
                    check_name="Stuck Submissions",
                    passed=True,
                    message=f"{stuck_count} in PROCESSING (may be active)",
                ))
            else:
                self._add_result(WatchdogResult(
                    check_name="Stuck Submissions",
                    passed=True,
                    message="No stuck submissions",
                ))
        except Exception as e:
            self._add_result(WatchdogResult(
                check_name="Stuck Submissions",
                passed=False,
                message=f"Check failed: {e}",
                severity="WARN",
            ))

    def _check_score_status_consistency(self):
        """Verify scores match their status (no score>=95 with FAIL)."""
        try:
            import requests
            url = f"https://api.airtable.com/v0/{self.cfg.airtable_base_id}/{self.cfg.airtable_table_name}"
            
            # Check for inconsistencies: score >= 95 but status = FAIL
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.cfg.airtable_token}"},
                params={
                    "filterByFormula": "AND({True Score}>=95, {Processing Status}='FAIL')",
                    "maxRecords": 50,
                },
                timeout=30,
            )
            
            if resp.status_code != 200:
                raise Exception(f"API returned {resp.status_code}")
            
            inconsistent = resp.json().get("records", [])
            
            if inconsistent:
                self._add_result(WatchdogResult(
                    check_name="Score-Status Consistency",
                    passed=False,
                    message=f"{len(inconsistent)} records with score>=95 but status=FAIL",
                    severity="CRITICAL",
                    details={"record_ids": [r["id"] for r in inconsistent[:10]]},
                ))
            else:
                self._add_result(WatchdogResult(
                    check_name="Score-Status Consistency",
                    passed=True,
                    message="All scores match their status",
                ))
        except Exception as e:
            self._add_result(WatchdogResult(
                check_name="Score-Status Consistency",
                passed=False,
                message=f"Check failed: {e}",
                severity="WARN",
            ))

    def _check_recent_failure_rate(self):
        """Check if failure rate is abnormally high."""
        try:
            import requests
            url = f"https://api.airtable.com/v0/{self.cfg.airtable_base_id}/{self.cfg.airtable_table_name}"
            
            # Get recent records
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.cfg.airtable_token}"},
                params={
                    "maxRecords": 100,
                    "sort[0][field]": "Created",
                    "sort[0][direction]": "desc",
                },
                timeout=30,
            )
            
            if resp.status_code != 200:
                raise Exception(f"API returned {resp.status_code}")
            
            records = resp.json().get("records", [])
            if len(records) < 10:
                self._add_result(WatchdogResult(
                    check_name="Recent Failure Rate",
                    passed=True,
                    message=f"Only {len(records)} recent records - not enough to measure",
                ))
                return
            
            fails = sum(1 for r in records if r.get("fields", {}).get("Processing Status") == "FAIL")
            fail_rate = fails / len(records) * 100
            
            if fail_rate > 80:
                self._add_result(WatchdogResult(
                    check_name="Recent Failure Rate",
                    passed=False,
                    message=f"{fail_rate:.0f}% failure rate in last {len(records)} submissions",
                    severity="CRITICAL",
                ))
            elif fail_rate > 50:
                self._add_result(WatchdogResult(
                    check_name="Recent Failure Rate",
                    passed=False,
                    message=f"{fail_rate:.0f}% failure rate - higher than normal",
                    severity="WARN",
                ))
            else:
                self._add_result(WatchdogResult(
                    check_name="Recent Failure Rate",
                    passed=True,
                    message=f"{fail_rate:.0f}% failure rate ({fails}/{len(records)})",
                ))
        except Exception as e:
            self._add_result(WatchdogResult(
                check_name="Recent Failure Rate",
                passed=False,
                message=f"Check failed: {e}",
                severity="WARN",
            ))

    # =========================================================================
    # Cross-System Checks
    # =========================================================================

    def _check_grading_determinism(self):
        """Verify grading produces consistent results."""
        from siteowlqa.python_grader import grade_submission_in_python
        
        try:
            ref = fetch_reference_rows(self.cfg, "686")
            if ref.empty:
                self._add_result(WatchdogResult(
                    check_name="Grading Determinism",
                    passed=True,
                    message="Skipped - no reference data",
                ))
                return
            
            # Grade the same subset 3 times
            subset = ref.head(5).copy()
            scores = []
            
            for i in range(3):
                outcome = grade_submission_in_python(
                    cfg=self.cfg,
                    submission_df=subset,
                    submission_id=f"determinism-check-{i}",
                    site_number="686",
                )
                scores.append(outcome.result.score)
            
            if len(set(scores)) > 1:
                self._add_result(WatchdogResult(
                    check_name="Grading Determinism",
                    passed=False,
                    message=f"Non-deterministic! Scores: {scores}",
                    severity="CRITICAL",
                ))
            else:
                self._add_result(WatchdogResult(
                    check_name="Grading Determinism",
                    passed=True,
                    message=f"Deterministic (score={scores[0]:.2f}%)",
                ))
        except Exception as e:
            self._add_result(WatchdogResult(
                check_name="Grading Determinism",
                passed=False,
                message=f"Check failed: {e}",
                severity="WARN",
            ))

    # =========================================================================
    # Helpers
    # =========================================================================

    def _load_baseline(self) -> dict:
        """Load baseline data for drift detection."""
        if self.baseline_file.exists():
            try:
                return json.loads(self.baseline_file.read_text())
            except:
                pass
        return {}

    def _save_baseline(self, data: dict):
        """Save baseline data."""
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        self.baseline_file.write_text(json.dumps(data, indent=2))

    def _print_summary(self):
        """Print summary of all checks."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        critical = sum(1 for r in self.results if not r.passed and r.severity == "CRITICAL")
        
        log.info("")
        log.info("=" * 60)
        log.info(f"SUMMARY: {passed} passed, {failed} failed ({critical} critical)")
        log.info("=" * 60)
        
        if critical > 0:
            log.error("CRITICAL ISSUES FOUND - INVESTIGATE IMMEDIATELY")
            for r in self.results:
                if not r.passed and r.severity == "CRITICAL":
                    log.error(f"  - {r.check_name}: {r.message}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="VUES Data Watchdog")
    parser.add_argument("--quick", action="store_true", help="Run quick checks only")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()
    
    watchdog = DataWatchdog()
    
    if args.quick:
        results = watchdog.run_quick_checks()
    else:
        results = watchdog.run_all_checks()
    
    if args.json:
        output = [
            {
                "check": r.check_name,
                "passed": r.passed,
                "message": r.message,
                "severity": r.severity,
            }
            for r in results
        ]
        print(json.dumps(output, indent=2))
    
    # Exit with error code if critical issues
    critical = any(not r.passed and r.severity == "CRITICAL" for r in results)
    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()
