"""Generate individual site markers spread within each state."""
import json
import random
from pathlib import Path

# Load aggregated data
with open('ui/vendor_locations.json') as f:
    data = json.load(f)

# State bounding boxes (approx) for spreading markers
STATE_BOUNDS = {
    'AL': {'lat': (30.2, 35.0), 'lng': (-88.5, -84.9)},
    'AZ': {'lat': (31.3, 37.0), 'lng': (-114.8, -109.0)},
    'AR': {'lat': (33.0, 36.5), 'lng': (-94.6, -89.6)},
    'CA': {'lat': (32.5, 42.0), 'lng': (-124.4, -114.1)},
    'CO': {'lat': (37.0, 41.0), 'lng': (-109.0, -102.0)},
    'CT': {'lat': (41.0, 42.1), 'lng': (-73.7, -71.8)},
    'DE': {'lat': (38.5, 39.8), 'lng': (-75.8, -75.0)},
    'FL': {'lat': (24.5, 31.0), 'lng': (-87.6, -80.0)},
    'GA': {'lat': (30.4, 35.0), 'lng': (-85.6, -80.8)},
    'HI': {'lat': (18.9, 22.2), 'lng': (-160.2, -154.8)},
    'ID': {'lat': (42.0, 49.0), 'lng': (-117.2, -111.0)},
    'IL': {'lat': (37.0, 42.5), 'lng': (-91.5, -87.5)},
    'IN': {'lat': (37.8, 41.8), 'lng': (-88.1, -84.8)},
    'IA': {'lat': (40.4, 43.5), 'lng': (-96.6, -90.1)},
    'KS': {'lat': (37.0, 40.0), 'lng': (-102.0, -94.6)},
    'KY': {'lat': (36.5, 39.1), 'lng': (-89.6, -82.0)},
    'LA': {'lat': (29.0, 33.0), 'lng': (-94.0, -89.0)},
    'ME': {'lat': (43.1, 47.5), 'lng': (-71.1, -66.9)},
    'MD': {'lat': (38.0, 39.7), 'lng': (-79.5, -75.0)},
    'MA': {'lat': (41.2, 42.9), 'lng': (-73.5, -69.9)},
    'MI': {'lat': (41.7, 46.5), 'lng': (-90.4, -82.4)},
    'MN': {'lat': (43.5, 49.4), 'lng': (-97.2, -89.5)},
    'MS': {'lat': (30.2, 35.0), 'lng': (-91.6, -88.1)},
    'MO': {'lat': (36.0, 40.6), 'lng': (-95.8, -89.1)},
    'MT': {'lat': (45.0, 49.0), 'lng': (-116.0, -104.0)},
    'NE': {'lat': (40.0, 43.0), 'lng': (-104.0, -95.3)},
    'NV': {'lat': (35.0, 42.0), 'lng': (-120.0, -114.0)},
    'NH': {'lat': (42.7, 45.3), 'lng': (-72.6, -70.7)},
    'NJ': {'lat': (38.9, 41.4), 'lng': (-75.6, -73.9)},
    'NM': {'lat': (31.3, 37.0), 'lng': (-109.0, -103.0)},
    'NY': {'lat': (40.5, 45.0), 'lng': (-79.8, -71.9)},
    'NC': {'lat': (33.8, 36.6), 'lng': (-84.3, -75.5)},
    'ND': {'lat': (45.9, 49.0), 'lng': (-104.0, -96.6)},
    'OH': {'lat': (38.4, 42.0), 'lng': (-84.8, -80.5)},
    'OK': {'lat': (33.6, 37.0), 'lng': (-103.0, -94.4)},
    'OR': {'lat': (42.0, 46.3), 'lng': (-124.6, -116.5)},
    'PA': {'lat': (39.7, 42.3), 'lng': (-80.5, -74.7)},
    'RI': {'lat': (41.1, 42.0), 'lng': (-71.9, -71.1)},
    'SC': {'lat': (32.0, 35.2), 'lng': (-83.4, -78.5)},
    'SD': {'lat': (42.5, 45.9), 'lng': (-104.0, -96.4)},
    'TN': {'lat': (35.0, 36.7), 'lng': (-90.3, -81.6)},
    'TX': {'lat': (25.8, 36.5), 'lng': (-106.6, -93.5)},
    'UT': {'lat': (37.0, 42.0), 'lng': (-114.0, -109.0)},
    'VT': {'lat': (42.7, 45.0), 'lng': (-73.4, -71.5)},
    'VA': {'lat': (36.5, 39.5), 'lng': (-83.7, -75.2)},
    'WA': {'lat': (45.5, 49.0), 'lng': (-124.8, -116.9)},
    'WV': {'lat': (37.2, 40.6), 'lng': (-82.6, -77.7)},
    'WI': {'lat': (42.5, 47.1), 'lng': (-92.9, -86.8)},
    'WY': {'lat': (41.0, 45.0), 'lng': (-111.0, -104.0)},
    'DC': {'lat': (38.8, 39.0), 'lng': (-77.1, -76.9)},
    'PR': {'lat': (17.9, 18.5), 'lng': (-67.3, -65.6)},
}

# Generate individual markers
individual_markers = []
random.seed(42)  # Reproducible

for marker in data['markers']:
    state = marker['state']
    vendor = marker['vendor']
    count = marker['count']
    base_lat, base_lng = marker['location']
    
    bounds = STATE_BOUNDS.get(state)
    
    for i in range(count):
        if bounds:
            # Spread within state bounds
            lat = random.uniform(bounds['lat'][0], bounds['lat'][1])
            lng = random.uniform(bounds['lng'][0], bounds['lng'][1])
        else:
            # Fallback: small jitter around centroid
            lat = base_lat + random.uniform(-0.5, 0.5)
            lng = base_lng + random.uniform(-0.5, 0.5)
        
        individual_markers.append({
            'vendor': vendor,
            'state': state,
            'lat': round(lat, 4),
            'lng': round(lng, 4)
        })

# Save
output = {
    'markers': individual_markers,
    'vendor_totals': data.get('vendor_totals', {}),
    'total': len(individual_markers)
}

with open('ui/site_markers.json', 'w') as f:
    json.dump(output, f)

print(f"Generated {len(individual_markers)} individual markers")
print(f"Vendors: {set(m['vendor'] for m in individual_markers)}")
