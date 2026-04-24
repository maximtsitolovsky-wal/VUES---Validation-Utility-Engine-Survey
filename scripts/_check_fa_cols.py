"""Check critical columns for FA/Intrusion."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from siteowlqa.site_validation import _get_critical_columns_for_survey_type

print("FA/Intrusion critical columns:")
print(_get_critical_columns_for_survey_type("FA/Intrusion"))
