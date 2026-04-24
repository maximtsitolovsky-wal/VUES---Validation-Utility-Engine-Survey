"""
HTML Data Verification Agent

Verifies that all values displayed in HTML match the source data.
No incorrect, stale, fabricated, or unverifiable data should appear.

HTML is NOT trusted - it is only the final display layer.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup
import logging

log = logging.getLogger(__name__)


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerificationStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    UNVERIFIABLE = "UNVERIFIABLE"


@dataclass
class FieldCheck:
    """Result of checking a single field."""
    field_id: str
    field_label: str
    source_path: str | None
    formula_id: str | None
    expected_value: Any
    computed_value: Any
    html_value: str
    normalized_html_value: Any
    status: str  # PASS, FAIL, WARNING, UNVERIFIABLE
    issue: str | None = None
    severity: Severity | None = None
    required_fix: str | None = None


@dataclass
class FormulaRule:
    """Definition of a calculation formula."""
    id: str
    output_path: str
    input_paths: list[str]
    operation: str  # sum, count, avg, pct, subtract, custom
    field: str | None = None
    rounding: dict | None = None
    custom_fn: Any = None  # For complex calculations


@dataclass
class ToleranceRules:
    """Allowed tolerances for comparisons."""
    decimal_places: int = 2
    percentage_tolerance: float = 0.01  # 1% tolerance
    allow_rounding: bool = True
    rounding_method: str = "standard"


@dataclass 
class VerificationResult:
    """Final verification report."""
    status: VerificationStatus
    checked_at: str
    total_fields_checked: int
    passed_fields: int
    failed_fields: int
    warning_fields: int
    html_data_approved: bool
    failures: list[FieldCheck] = field(default_factory=list)
    warnings: list[FieldCheck] = field(default_factory=list)
    passed: list[FieldCheck] = field(default_factory=list)


class HTMLDataVerifier:
    """
    Verifies HTML displayed values against source data.
    
    Priority order (source of truth):
    1. User-approved source data
    2. Approved database/export/API payload  
    3. Formula or transformation specification
    4. Computed/transformed data
    5. HTML output (NEVER trusted as source)
    """
    
    def __init__(
        self,
        source_data: dict[str, Any],
        formula_rules: list[FormulaRule] | None = None,
        tolerance_rules: ToleranceRules | None = None,
    ):
        self.source_data = source_data
        self.formula_rules = formula_rules or []
        self.tolerance = tolerance_rules or ToleranceRules()
        self.formula_registry = {f.id: f for f in self.formula_rules}
        
    def _get_nested_value(self, data: dict, path: str) -> Any:
        """Get a value from nested dict using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                value = value[int(key)] if int(key) < len(value) else None
            else:
                return None
            if value is None:
                return None
        return value
    
    def _normalize_value(self, html_value: str) -> Any:
        """Normalize HTML display value for comparison."""
        if not html_value:
            return None
            
        original = html_value
        val = html_value.strip()
        
        # Remove common formatting
        val = val.replace(",", "").replace("$", "").replace("%", "")
        val = val.replace("—", "").replace("–", "").replace("-", "")
        val = re.sub(r"\s+", " ", val).strip()
        
        # Handle special values
        if val.lower() in ("", "n/a", "null", "none", "loading...", "—"):
            return None
            
        # Try to parse as number
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            pass
            
        return original.strip()
    
    def _normalize_percentage(self, val: Any) -> float | None:
        """Normalize percentage values."""
        if val is None:
            return None
        if isinstance(val, str):
            val = val.replace("%", "").strip()
            try:
                return float(val)
            except ValueError:
                return None
        return float(val)
    
    def _values_match(self, expected: Any, actual: Any) -> bool:
        """Compare values with tolerance."""
        if expected is None and actual is None:
            return True
        if expected is None or actual is None:
            return False
            
        # Both are numbers
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            if self.tolerance.allow_rounding:
                # Round both to specified decimal places
                exp_rounded = round(expected, self.tolerance.decimal_places)
                act_rounded = round(actual, self.tolerance.decimal_places)
                return abs(exp_rounded - act_rounded) <= self.tolerance.percentage_tolerance
            return expected == actual
            
        # String comparison
        return str(expected).strip().lower() == str(actual).strip().lower()
    
    def _recompute_formula(self, formula: FormulaRule) -> Any:
        """Recompute a formula from source data."""
        inputs = []
        for path in formula.input_paths:
            val = self._get_nested_value(self.source_data, path)
            inputs.append(val)
            
        if formula.operation == "sum":
            if formula.field and isinstance(inputs[0], list):
                total = sum(item.get(formula.field, 0) or 0 for item in inputs[0])
            else:
                total = sum(v or 0 for v in inputs if isinstance(v, (int, float)))
            return total
            
        elif formula.operation == "count":
            if isinstance(inputs[0], list):
                return len(inputs[0])
            return inputs[0] if isinstance(inputs[0], int) else 0
            
        elif formula.operation == "avg":
            vals = [v for v in inputs if isinstance(v, (int, float))]
            return sum(vals) / len(vals) if vals else 0
            
        elif formula.operation == "pct":
            if len(inputs) >= 2 and inputs[1]:
                return (inputs[0] or 0) / inputs[1] * 100
            return 0
            
        elif formula.operation == "subtract":
            if len(inputs) >= 2:
                return (inputs[0] or 0) - (inputs[1] or 0)
            return inputs[0] or 0
            
        elif formula.operation == "custom" and formula.custom_fn:
            return formula.custom_fn(self.source_data, inputs)
            
        return None
    
    def verify_field(
        self,
        field_id: str,
        field_label: str,
        html_value: str,
        source_path: str | None = None,
        formula_id: str | None = None,
    ) -> FieldCheck:
        """Verify a single field against source data."""
        expected_value = None
        computed_value = None
        normalized_html = self._normalize_value(html_value)
        
        # Get expected value from source or formula
        if formula_id and formula_id in self.formula_registry:
            formula = self.formula_registry[formula_id]
            expected_value = self._recompute_formula(formula)
            computed_value = expected_value
        elif source_path:
            expected_value = self._get_nested_value(self.source_data, source_path)
            computed_value = expected_value
            
        # Handle percentage normalization
        if formula_id and "pct" in formula_id.lower() or (source_path and "rate" in source_path.lower()):
            normalized_html = self._normalize_percentage(html_value)
            
        # Compare values
        if expected_value is None and source_path:
            return FieldCheck(
                field_id=field_id,
                field_label=field_label,
                source_path=source_path,
                formula_id=formula_id,
                expected_value=expected_value,
                computed_value=computed_value,
                html_value=html_value,
                normalized_html_value=normalized_html,
                status="UNVERIFIABLE",
                issue=f"Source data not found at path: {source_path}",
                severity=Severity.HIGH,
                required_fix=f"Ensure source data exists at {source_path}",
            )
            
        if self._values_match(expected_value, normalized_html):
            return FieldCheck(
                field_id=field_id,
                field_label=field_label,
                source_path=source_path,
                formula_id=formula_id,
                expected_value=expected_value,
                computed_value=computed_value,
                html_value=html_value,
                normalized_html_value=normalized_html,
                status="PASS",
            )
        else:
            # Determine severity
            severity = Severity.HIGH
            if "total" in field_id.lower() or "rate" in field_id.lower():
                severity = Severity.CRITICAL
                
            return FieldCheck(
                field_id=field_id,
                field_label=field_label,
                source_path=source_path,
                formula_id=formula_id,
                expected_value=expected_value,
                computed_value=computed_value,
                html_value=html_value,
                normalized_html_value=normalized_html,
                status="FAIL",
                issue=f"Value mismatch: expected {expected_value}, got {normalized_html}",
                severity=severity,
                required_fix=f"Update HTML to display {expected_value}",
            )
    
    def verify_html(self, html_content: str, field_mappings: list[dict]) -> VerificationResult:
        """
        Verify all fields in HTML content.
        
        Args:
            html_content: The HTML string to verify
            field_mappings: List of dicts with keys:
                - field_id: Unique identifier
                - field_label: Human-readable label  
                - selector: CSS selector or element ID to find the value
                - source_path: Path in source_data (dot notation)
                - formula_id: ID of formula rule (optional)
        """
        soup = BeautifulSoup(html_content, "html.parser")
        
        passed = []
        failed = []
        warnings = []
        
        for mapping in field_mappings:
            field_id = mapping["field_id"]
            field_label = mapping.get("field_label", field_id)
            selector = mapping.get("selector")
            source_path = mapping.get("source_path")
            formula_id = mapping.get("formula_id")
            
            # Extract HTML value
            html_value = ""
            if selector:
                if selector.startswith("#"):
                    elem = soup.find(id=selector[1:])
                else:
                    elem = soup.select_one(selector)
                if elem:
                    html_value = elem.get_text(strip=True)
                    
            # Verify field
            check = self.verify_field(
                field_id=field_id,
                field_label=field_label,
                html_value=html_value,
                source_path=source_path,
                formula_id=formula_id,
            )
            
            if check.status == "PASS":
                passed.append(check)
            elif check.status == "WARNING":
                warnings.append(check)
            else:
                failed.append(check)
                
        # Determine overall status
        total = len(passed) + len(failed) + len(warnings)
        
        has_critical = any(f.severity == Severity.CRITICAL for f in failed)
        has_high = any(f.severity == Severity.HIGH for f in failed)
        
        if not field_mappings:
            status = VerificationStatus.UNVERIFIABLE
            approved = False
        elif has_critical or has_high:
            status = VerificationStatus.FAIL
            approved = False
        elif failed:
            status = VerificationStatus.FAIL
            approved = False
        elif warnings:
            status = VerificationStatus.PASS_WITH_WARNINGS
            approved = True
        else:
            status = VerificationStatus.PASS
            approved = True
            
        return VerificationResult(
            status=status,
            checked_at=datetime.now().isoformat(),
            total_fields_checked=total,
            passed_fields=len(passed),
            failed_fields=len(failed),
            warning_fields=len(warnings),
            html_data_approved=approved,
            failures=failed,
            warnings=warnings,
            passed=passed,
        )


def get_scout_field_mappings() -> list[dict]:
    """Field mappings for scout.html."""
    return [
        {"field_id": "statTotal", "field_label": "Total Submissions", "selector": "#statTotal", "source_path": "scout.total_submissions"},
        {"field_id": "statUnique", "field_label": "Unique Sites", "selector": "#statUnique", "source_path": "scout.unique_submissions"},
        {"field_id": "statComplete", "field_label": "Completed", "selector": "#statComplete", "source_path": "scout.completed"},
        {"field_id": "statRemaining", "field_label": "Remaining", "selector": "#statRemaining", "source_path": "scout.remaining"},
        {"field_id": "statRate", "field_label": "Completion Rate", "selector": "#statRate", "source_path": "scout.completion_rate"},
    ]


def get_survey_field_mappings() -> list[dict]:
    """Field mappings for survey.html."""
    return [
        {"field_id": "statTotal", "field_label": "Total Submissions", "selector": "#statTotal", "formula_id": "survey_total"},
        {"field_id": "statPassed", "field_label": "Passed", "selector": "#statPassed", "formula_id": "survey_passed"},
        {"field_id": "statFailed", "field_label": "Failed", "selector": "#statFailed", "formula_id": "survey_failed"},
        {"field_id": "statRate", "field_label": "Pass Rate", "selector": "#statRate", "formula_id": "survey_rate"},
    ]


def get_summary_field_mappings() -> list[dict]:
    """Field mappings for summary.html."""
    return [
        {"field_id": "surveyRate", "field_label": "Survey Pass Rate", "selector": "#surveyRate", "formula_id": "survey_rate"},
        {"field_id": "surveyTotal", "field_label": "Survey Total", "selector": "#surveyTotal", "formula_id": "survey_total"},
        {"field_id": "surveyPass", "field_label": "Survey Passed", "selector": "#surveyPass", "formula_id": "survey_passed"},
        {"field_id": "surveyFail", "field_label": "Survey Failed", "selector": "#surveyFail", "formula_id": "survey_failed"},
        {"field_id": "scoutRate", "field_label": "Scout Completion Rate", "selector": "#scoutRate", "source_path": "scout.completion_rate"},
        {"field_id": "scoutTotal", "field_label": "Scout Total Sites", "selector": "#scoutTotal", "source_path": "scout.excel_total"},
        {"field_id": "scoutDone", "field_label": "Scout Completed", "selector": "#scoutDone", "source_path": "scout.completed"},
        {"field_id": "scoutRemaining", "field_label": "Scout Remaining", "selector": "#scoutRemaining", "source_path": "scout.remaining"},
    ]


def get_formula_rules(source_data: dict) -> list[FormulaRule]:
    """Define formula rules for calculated fields."""
    survey_records = source_data.get("survey", {}).get("records", [])
    
    return [
        FormulaRule(
            id="survey_total",
            output_path="survey.total",
            input_paths=["survey.records"],
            operation="count",
        ),
        FormulaRule(
            id="survey_passed",
            output_path="survey.passed",
            input_paths=["survey.records"],
            operation="custom",
            custom_fn=lambda d, i: len([r for r in d.get("survey", {}).get("records", []) if r.get("processing_status") == "PASS"]),
        ),
        FormulaRule(
            id="survey_failed",
            output_path="survey.failed",
            input_paths=["survey.records"],
            operation="custom",
            custom_fn=lambda d, i: len([r for r in d.get("survey", {}).get("records", []) if r.get("processing_status") == "FAIL"]),
        ),
        FormulaRule(
            id="survey_rate",
            output_path="survey.rate",
            input_paths=["survey.records"],
            operation="custom",
            custom_fn=lambda d, i: (
                round(len([r for r in d.get("survey", {}).get("records", []) if r.get("processing_status") == "PASS"]) 
                / len(d.get("survey", {}).get("records", [])) * 100)
                if d.get("survey", {}).get("records") else 0
            ),
            rounding={"allowed": True, "decimals": 0, "method": "standard"},
        ),
    ]


def verify_dashboard_html(
    source_data_path: str | Path,
    html_files: dict[str, str | Path],
) -> dict[str, VerificationResult]:
    """
    Verify all dashboard HTML files against source data.
    
    Args:
        source_data_path: Path to team_dashboard_data.json
        html_files: Dict mapping file names to paths
            e.g. {"scout": "output/scout.html", "survey": "output/survey.html"}
    
    Returns:
        Dict mapping file names to VerificationResult
    """
    # Load source data
    source_data_path = Path(source_data_path)
    if not source_data_path.exists():
        raise FileNotFoundError(f"Source data not found: {source_data_path}")
        
    with open(source_data_path, encoding="utf-8") as f:
        source_data = json.load(f)
        
    # Get formula rules
    formula_rules = get_formula_rules(source_data)
    
    # Create verifier
    verifier = HTMLDataVerifier(
        source_data=source_data,
        formula_rules=formula_rules,
        tolerance_rules=ToleranceRules(decimal_places=1, allow_rounding=True),
    )
    
    results = {}
    
    # Mapping of file names to field mapping functions
    mapping_fns = {
        "scout": get_scout_field_mappings,
        "survey": get_survey_field_mappings,
        "summary": get_summary_field_mappings,
    }
    
    for name, path in html_files.items():
        path = Path(path)
        if not path.exists():
            log.warning(f"HTML file not found: {path}")
            continue
            
        html_content = path.read_text(encoding="utf-8")
        
        # Get field mappings for this file
        mapping_fn = mapping_fns.get(name)
        if not mapping_fn:
            log.warning(f"No field mappings defined for: {name}")
            continue
            
        field_mappings = mapping_fn()
        
        # Verify
        result = verifier.verify_html(html_content, field_mappings)
        results[name] = result
        
    return results


def print_verification_report(results: dict[str, VerificationResult]) -> None:
    """Print a human-readable verification report."""
    print("\n" + "=" * 70)
    print("HTML DATA VERIFICATION REPORT")
    print("=" * 70)
    print(f"Checked at: {datetime.now().isoformat()}")
    print()
    
    all_approved = True
    
    for name, result in results.items():
        status_icon = "[PASS]" if result.html_data_approved else "[FAIL]"
        print(f"\n{status_icon} {name.upper()}.html")
        print("-" * 40)
        print(f"Status: {result.status.value}")
        print(f"Fields Checked: {result.total_fields_checked}")
        print(f"Passed: {result.passed_fields} | Failed: {result.failed_fields} | Warnings: {result.warning_fields}")
        print(f"Approved: {result.html_data_approved}")
        
        if result.failures:
            print("\n>> FAILURES:")
            for f in result.failures:
                print(f"  * {f.field_label} ({f.field_id})")
                print(f"    Expected: {f.expected_value}")
                print(f"    Got: {f.normalized_html_value} (raw: '{f.html_value}')")
                print(f"    Issue: {f.issue}")
                print(f"    Severity: {f.severity.value if f.severity else 'N/A'}")
                
        if result.warnings:
            print("\n>> WARNINGS:")
            for w in result.warnings:
                print(f"  * {w.field_label}: {w.issue}")
                
        if result.passed and not result.failures:
            print("\n>> All fields verified successfully")
            for p in result.passed:
                print(f"  * {p.field_label}: {p.expected_value} [OK]")
                
        if not result.html_data_approved:
            all_approved = False
            
    print("\n" + "=" * 70)
    if all_approved:
        print("[PASS] ALL HTML DATA APPROVED")
    else:
        print("[FAIL] HTML DATA VERIFICATION FAILED - DO NOT PUBLISH")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # Run verification
    results = verify_dashboard_html(
        source_data_path="output/team_dashboard_data.json",
        html_files={
            "scout": "output/scout.html",
            "survey": "output/survey.html",
            "summary": "output/summary.html",
        },
    )
    print_verification_report(results)
