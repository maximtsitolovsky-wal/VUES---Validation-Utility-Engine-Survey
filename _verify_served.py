from pathlib import Path
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

for fname in ['executive_dashboard.html', 'executive_dashboard_puppy_inline.html']:
    p = Path('served_dashboard') / fname
    text = p.read_text(encoding='utf-8')
    print(f'\n=== {fname} ({len(text):,} chars) ===')
    
    # Find the actual nav HTML element (not CSS)
    m = re.search(r'<div class="nav__links"[^>]*>(.*?)</div>', text, re.DOTALL)
    if m:
        print(f'nav__links HTML element:')
        print(repr(m.group(0)[:400]))
    else:
        print('WARNING: nav__links HTML element not found')
    
    print(f'\nArchitecture in text: {"Architecture" in text}')
    print(f'#admin in text: {"#admin" in text}')
