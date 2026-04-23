"""Test grading for site 686 submission."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

file_path = Path(r'C:\Users\vn59j7j\Documents\BaselinePrinter\SVG_IN\Silly Upload 2 - 686.xlsx')

print(f"=== TESTING GRADE FOR: {file_path.name} ===")
print(f"File exists: {file_path.exists()}")

if not file_path.exists():
    print("ERROR: File not found!")
    sys.exit(1)

print(f"File size: {file_path.stat().st_size / 1024:.1f} KB")

# Load config
from siteowlqa.config import load_config
cfg = load_config()
print("Config loaded")

# Load the file
from siteowlqa.file_processor import load_vendor_file
result = load_vendor_file(file_path)
df = result.df
print(f"Submission loaded: {len(df)} rows")
print(f"Vendor detected: {result.vendor_name}")
print(f"Columns: {list(df.columns)[:6]}...")
if result.errors:
    print(f"Load warnings: {result.errors}")

# Get reference data
from siteowlqa.reference_data import fetch_reference_rows
site_number = '686'
print(f"\nFetching reference data for site {site_number}...")
ref_rows = fetch_reference_rows(cfg, site_number)
print(f"Reference rows: {len(ref_rows)}")

if not ref_rows:
    print("ERROR: No reference data found for site 686!")
    sys.exit(1)

# Run grader
from siteowlqa.python_grader import grade_submission_in_python
print("Running grader...")
result = grade_submission_in_python(
    raw_df=df,
    site_number=site_number,
    vendor_name='Test',
    cfg=cfg,
)

print(f"\n{'='*40}")
print(f"=== GRADING RESULT ===")
print(f"{'='*40}")
print(f"Score:      {result.score:.1f}%")
print(f"True Score: {result.true_score:.1f}%")
print(f"Matched:    {result.matched_count}")
print(f"Missing:    {result.missing_count}")
print(f"Extra:      {result.extra_count}")
print(f"Errors:     {len(result.errors)}")

if result.errors:
    print("\nFirst 10 errors:")
    for i, e in enumerate(result.errors[:10]):
        print(f"  {i+1}. {e}")

print(f"\n{'='*40}")
print("DONE!")
