import pandas as pd

df = pd.read_csv('output/vendor_metrics.csv')

print("=" * 70)
print("VENDOR METRICS - ALL VENDORS")
print("=" * 70)
print()

for i, row in df.iterrows():
    name = row["vendor_name"]
    total = int(row["total_submissions"])
    passes = int(row["total_pass"])
    fails = int(row["total_fail"])
    errors = int(row["total_error"])
    pass_rate = row["pass_rate_pct"]
    
    print(f"{name}:")
    print(f"  Total: {total} submissions")
    print(f"  PASS:  {passes} ({pass_rate:.1f}%)")
    print(f"  FAIL:  {fails}")
    print(f"  ERROR: {errors}")
    print()

print("=" * 70)
print(f"TOTAL: {df['total_submissions'].sum()} submissions across {len(df)} vendors")
print("=" * 70)
