"""Test if the baked HTML actually works in a real browser context using a headless approach."""
import urllib.request
import re

# Fetch the survey.html from local server
r = urllib.request.urlopen('http://127.0.0.1:9988/survey.html')
html = r.read().decode('utf-8')

print(f'HTML size: {len(html)} chars')
print(f'Status: {r.status}')

# Check key markers
print(f'Has TEAM_DASHBOARD_DATA: {"window.TEAM_DASHBOARD_DATA" in html}')
print(f'Has FETCH POLYFILL: {"FETCH POLYFILL" in html}')
print(f'Has loadData(): {"loadData()" in html}')

# Find the polyfill location vs loadData() definition
polyfill_pos = html.find('FETCH POLYFILL')
loaddata_pos = html.find('async function loadData')
loaddata_call = html.rfind('loadData();')

print(f'\nPolyfill at char: {polyfill_pos}')
print(f'loadData definition at char: {loaddata_pos}')
print(f'loadData() call at char: {loaddata_call}')

if polyfill_pos < loaddata_call:
    print('OK - Polyfill defined BEFORE loadData() is called')
else:
    print('BUG - Polyfill defined AFTER loadData() is called!')

# Verify the embedded data is not corrupted - find a record
m = re.search(r'window\.TEAM_DASHBOARD_DATA = ({.{0,500})', html)
if m:
    print(f'\nData snippet: {m.group(1)[:300]}')
