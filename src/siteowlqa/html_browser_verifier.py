"""
HTML Data Verification Agent - Browser-Based

Uses Playwright to actually render HTML pages and verify displayed values
match the source data. This catches JS rendering bugs.
"""

import json
import asyncio
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FieldVerification:
    field_id: str
    label: str
    expected: str | int | float
    actual: str
    status: str  # PASS, FAIL, MISMATCH
    issue: str | None = None


@dataclass
class PageVerification:
    page_name: str
    url: str
    status: str  # PASS, FAIL
    fields: list[FieldVerification]
    errors: list[str]


async def verify_rendered_html(base_url: str = "http://localhost:8888") -> dict:
    """
    Verify rendered HTML values against source data using Playwright.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"error": "Playwright not installed. Run: uv pip install playwright && playwright install chromium"}
    
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
    expected = {
        "scout": {
            "statTotal": str(scout.get("total_submissions", 0)),
            "statUnique": str(scout.get("unique_submissions", 0)),
            "statComplete": str(scout.get("completed", 0)),
            "statRemaining": str(scout.get("remaining", 0)),
            "statRate": f"{scout.get('completion_rate', 0)}%",
        },
        "survey": {
            "statTotal": str(survey_total),
            "statPassed": str(survey_passed),
            "statFailed": str(survey_failed),
            "statRate": f"{survey_rate}%",
        },
        "summary": {
            "surveyRate": f"{survey_rate}%",
            "surveyTotal": str(survey_total),
            "surveyPass": str(survey_passed),
            "surveyFail": str(survey_failed),
            "scoutRate": f"{scout.get('completion_rate', 0)}%",
            "scoutTotal": str(scout.get("excel_total", 0)),
            "scoutDone": str(scout.get("completed", 0)),
            "scoutRemaining": str(scout.get("remaining", 0)),
        },
    }
    
    results = {
        "checked_at": datetime.now().isoformat(),
        "source_data_valid": True,
        "pages": [],
        "overall_status": "PASS",
        "summary": {
            "total_fields": 0,
            "passed": 0,
            "failed": 0,
        }
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        for page_name, fields in expected.items():
            page_result = PageVerification(
                page_name=page_name,
                url=f"{base_url}/{page_name}.html",
                status="PASS",
                fields=[],
                errors=[],
            )
            
            try:
                page = await context.new_page()
                await page.goto(f"{base_url}/{page_name}.html", wait_until="networkidle", timeout=10000)
                
                # Wait a bit for JS to render
                await page.wait_for_timeout(1500)
                
                for field_id, expected_value in fields.items():
                    try:
                        elem = await page.query_selector(f"#{field_id}")
                        if elem:
                            actual_value = await elem.inner_text()
                            actual_value = actual_value.strip()
                            
                            # Normalize for comparison
                            exp_normalized = str(expected_value).strip().lower()
                            act_normalized = actual_value.lower()
                            
                            if exp_normalized == act_normalized:
                                status = "PASS"
                                issue = None
                                results["summary"]["passed"] += 1
                            else:
                                status = "FAIL"
                                issue = f"Expected '{expected_value}', got '{actual_value}'"
                                results["summary"]["failed"] += 1
                                page_result.status = "FAIL"
                                results["overall_status"] = "FAIL"
                        else:
                            status = "FAIL"
                            actual_value = "ELEMENT NOT FOUND"
                            issue = f"Element #{field_id} not found in DOM"
                            results["summary"]["failed"] += 1
                            page_result.status = "FAIL"
                            results["overall_status"] = "FAIL"
                            
                        page_result.fields.append(FieldVerification(
                            field_id=field_id,
                            label=field_id,
                            expected=expected_value,
                            actual=actual_value,
                            status=status,
                            issue=issue,
                        ))
                        results["summary"]["total_fields"] += 1
                        
                    except Exception as e:
                        page_result.errors.append(f"Error checking {field_id}: {e}")
                        
                await page.close()
                
            except Exception as e:
                page_result.status = "FAIL"
                page_result.errors.append(f"Page load error: {e}")
                results["overall_status"] = "FAIL"
                
            results["pages"].append({
                "name": page_result.page_name,
                "url": page_result.url,
                "status": page_result.status,
                "fields": [
                    {
                        "field_id": f.field_id,
                        "expected": f.expected,
                        "actual": f.actual,
                        "status": f.status,
                        "issue": f.issue,
                    }
                    for f in page_result.fields
                ],
                "errors": page_result.errors,
            })
            
        await browser.close()
        
    return results


def print_verification_results(results: dict) -> None:
    """Print verification results in a readable format."""
    print("\n" + "=" * 70)
    print("HTML DATA VERIFICATION REPORT (Browser Rendered)")
    print("=" * 70)
    print(f"Checked at: {results.get('checked_at', 'N/A')}")
    print(f"Overall Status: {results.get('overall_status', 'UNKNOWN')}")
    print(f"Total: {results['summary']['total_fields']} fields | "
          f"Passed: {results['summary']['passed']} | "
          f"Failed: {results['summary']['failed']}")
    
    if results.get("error"):
        print(f"\n[ERROR] {results['error']}")
        return
        
    for page in results.get("pages", []):
        status_icon = "[PASS]" if page["status"] == "PASS" else "[FAIL]"
        print(f"\n{status_icon} {page['name'].upper()}.html")
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
        print("[FAIL] HTML DATA VERIFICATION FAILED")
    print("=" * 70 + "\n")


async def main():
    print("Starting HTML verification (requires local server at localhost:8888)...")
    results = await verify_rendered_html()
    print_verification_results(results)
    
    # Save results
    Path("output/html_verification_results.json").write_text(
        json.dumps(results, indent=2, default=str),
        encoding="utf-8"
    )
    print("Results saved to: output/html_verification_results.json")


if __name__ == "__main__":
    asyncio.run(main())
