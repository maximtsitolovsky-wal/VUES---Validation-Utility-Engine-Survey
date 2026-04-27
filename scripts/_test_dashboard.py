import urllib.request
import json

# Read port file
port = open('output/dashboard.port').read().strip() if __import__('pathlib').Path('output/dashboard.port').exists() else open('ui/dashboard.port').read().strip()
print(f'Testing port: {port}')

# Test JSON fetch
r = urllib.request.urlopen(f'http://127.0.0.1:{port}/team_dashboard_data.json')
data = json.loads(r.read())
print(f'JSON Status: {r.status}')
print(f'Survey records: {len(data.get("survey",{}).get("records",[]))}')
print(f'Scout records: {len(data.get("scout",{}).get("records",[]))}')
print(f'Vendor assignments: {len(data.get("vendor_assignments",{}).get("vendors",[]))}')

# Test HTML fetch
r2 = urllib.request.urlopen(f'http://127.0.0.1:{port}/survey.html')
html = r2.read().decode()
print(f'HTML status: {r2.status}, size: {len(html)} chars')

# Test scout HTML
r3 = urllib.request.urlopen(f'http://127.0.0.1:{port}/scout.html')
html3 = r3.read().decode()
print(f'Scout HTML status: {r3.status}, size: {len(html3)} chars')
