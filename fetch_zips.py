"""Fetch zip code coordinates from free dataset."""
import json
import urllib.request
import csv
from pathlib import Path
from io import StringIO

# Try to get zip codes from a free source
# Using simplemaps free US zip code database (CSV format)
# URL: https://simplemaps.com/static/data/us-zips/1.82/basic/simplemaps_uszips_basicv1.82.zip

# Alternative: Use a minimal embedded dataset for the ~750 zips we need
# Let's extract unique zips first

with open('ui/site_markers.json') as f:
    data = json.load(f)

unique_zips = set()
for m in data['markers']:
    z = m.get('zip', '')
    if z and len(z) >= 5:
        unique_zips.add(z[:5])

print(f"Need coordinates for {len(unique_zips)} unique zip codes")

# Try to fetch from a free API (limited but works)
# Using zippopotam.us - free, no key needed

zip_coords = {}
errors = []

print("Fetching zip coordinates (this may take a minute)...")

for i, zipcode in enumerate(sorted(unique_zips)):
    if i % 50 == 0:
        print(f"  Progress: {i}/{len(unique_zips)}")
    
    try:
        url = f"https://api.zippopotam.us/us/{zipcode}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            lat = float(data['places'][0]['latitude'])
            lng = float(data['places'][0]['longitude'])
            zip_coords[zipcode] = [lat, lng]
    except Exception as e:
        errors.append(zipcode)

print(f"Fetched {len(zip_coords)} zip coordinates")
print(f"Errors: {len(errors)}")

# Save cache
with open('ui/zip_coords.json', 'w') as f:
    json.dump(zip_coords, f)

print("Saved to ui/zip_coords.json")
