"""
HTML Data Verification Agent - Selenium/Edge Version

Uses Selenium with Microsoft Edge to render HTML pages and verify
displayed values match source data.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


def verify_html_with_selenium(base_url: str = "http://localhost:8888") -> dict:
    """Verify rendered HTML values using Selenium + Edge."""
    
    # Load source data
    source_path = Path("output/team_dashboard_data.json")
    if not source_path.exists():
        return {"error": f"Source data not found: {source_path}"}
    
    source_data = json.loads(source_path.read_text(encoding="utf-8"))
    
    # Calculate expected values
    scout = source_data.get("scout", {})
    survey_records = source_data.get("survey", {}).get("records", [])
    vendors = source_data.get("vendor_assignments", {}).get("vendors", [])
    
    survey_total = len(survey_records)
    survey_passed = len([r for r in survey_records if r.get("processing_status") == "PASS"])
    survey_failed = len([r for r in survey_records if r.get("processing_status") == "FAIL"])
    survey_rate = round(survey_passed / survey_total * 100) if survey_total else 0
    
    # Expected values for each page
    pages_to_check = {
        "scout": {
            "fields": {
                "statTotal": str(scout.get("total_submissions", 0)),
                "statUnique": str(scout.get("unique_submissions", 0)),
                "statComplete": str(scout.get("completed", 0)),
                "statRemaining": str(scout.get("remaining", 0)),
                "statRate": f"{scout.get('completion_rate', 0)}%",
            }
        },
        "survey": {
            "fields": {
                "statTotal": str(survey_total),
                "statPassed": str(survey_passed),
                "statFailed": str(survey_failed),
                "statRate": f"{survey_rate}%",
            }
        },
        "summary": {
            "fields": {
                "surveyRate": f"{survey_rate}%",
                "surveyTotal": str(survey_total),
                "surveyPass": str(survey_passed),
                "surveyFail": str(survey_failed),
                "scoutRate": f"{scout.get('completion_rate', 0)}%",
                "scoutTotal": str(scout.get("excel_total", 0)),
                "scoutDone": str(scout.get("completed", 0)),
                "scoutRemaining": str(scout.get("remaining", 0)),
            }
        },
    }
    
    results = {
        "checked_at": datetime.now().isoformat(),
        "base_url": base_url,
        "overall_status": "PASS",
        "pages": [],
        "summary": {"total": 0, "passed": 0, "failed": 0}
    }
    
    # Setup Edge browser
    options = EdgeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    try:
        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(15)
    except Exception as e:
        return {"error": f"Failed to start Edge browser: {e}"}
    
    try:
        for page_name, page_config in pages_to_check.items():
            url = f"{base_url}/{page_name}.html"
            page_result = {
                "name": page_name,
                "url": url,
                "status": "PASS",
                "fields": [],
                "errors": []
            }
            
            try:
                driver.get(url)
                time.sleep(3)  # Wait for JS to render
                
                # Check for console errors
                logs = driver.get_log('browser')
                js_errors = [log for log in logs if log.get('level') in ('SEVERE', 'ERROR')]
                if js_errors:
                    page_result["errors"].extend([f"JS: {log.get('message', '')}" for log in js_errors])
                
                for field_id, expected in page_config["fields"].items():
                    results["summary"]["total"] += 1
                    
                    try:
                        elem = driver.find_element(By.ID, field_id)
                        actual = elem.text.strip()
                        
                        # Normalize for comparison
                        exp_norm = str(expected).strip().lower()
                        act_norm = actual.lower()
                        
                        if exp_norm == act_norm:
                            status = "PASS"
                            issue = None
                            results["summary"]["passed"] += 1
                        else:
                            status = "FAIL"
                            issue = f"Expected '{expected}', got '{actual}'"
                            results["summary"]["failed"] += 1
                            page_result["status"] = "FAIL"
                            results["overall_status"] = "FAIL"
                            
                    except NoSuchElementException:
                        status = "FAIL"
                        actual = "ELEMENT NOT FOUND"
                        issue = f"Element #{field_id} not found"
                        results["summary"]["failed"] += 1
                        page_result["status"] = "FAIL"
                        results["overall_status"] = "FAIL"
                        
                    page_result["fields"].append({
                        "field_id": field_id,
                        "expected": expected,
                        "actual": actual,
                        "status": status,
                        "issue": issue
                    })
                    
            except Exception as e:
                page_result["status"] = "FAIL"
                page_result["errors"].append(str(e))
                results["overall_status"] = "FAIL"
                
            results["pages"].append(page_result)
            
    finally:
        driver.quit()
        
    return results


def print_results(results: dict) -> None:
    """Print verification results."""
    print("\n" + "=" * 70)
    print("HTML DATA VERIFICATION REPORT")
    print("=" * 70)
    print(f"Checked: {results.get('checked_at', 'N/A')}")
    print(f"URL: {results.get('base_url', 'N/A')}")
    print(f"Status: {results.get('overall_status', 'UNKNOWN')}")
    
    if results.get("error"):
        print(f"\n[ERROR] {results['error']}")
        return
        
    s = results.get("summary", {})
    print(f"Fields: {s.get('total', 0)} total | {s.get('passed', 0)} passed | {s.get('failed', 0)} failed")
    
    for page in results.get("pages", []):
        icon = "[PASS]" if page["status"] == "PASS" else "[FAIL]"
        print(f"\n{icon} {page['name'].upper()}.html")
        print("-" * 40)
        
        for f in page.get("fields", []):
            if f["status"] == "PASS":
                print(f"  [OK] {f['field_id']}: {f['actual']}")
            else:
                print(f"  [FAIL] {f['field_id']}")
                print(f"         Expected: {f['expected']}")
                print(f"         Actual:   {f['actual']}")
                if f.get("issue"):
                    print(f"         Issue:    {f['issue']}")
                    
        for err in page.get("errors", []):
            print(f"  [ERROR] {err}")
            
    print("\n" + "=" * 70)
    if results.get("overall_status") == "PASS":
        print("[PASS] ALL HTML DATA VERIFIED SUCCESSFULLY")
    else:
        print("[FAIL] HTML DATA VERIFICATION FAILED - FIX REQUIRED")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print("Starting HTML verification...")
    print("Make sure local server is running: python -m http.server 8888 --directory output")
    
    results = verify_html_with_selenium()
    print_results(results)
    
    # Save results
    Path("output/html_verification_results.json").write_text(
        json.dumps(results, indent=2),
        encoding="utf-8"
    )
    print("Results saved to: output/html_verification_results.json")
