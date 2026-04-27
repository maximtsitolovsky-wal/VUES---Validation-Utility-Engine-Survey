"""
Compile entire VUES app into a single standalone HTML file for Puppy Pages.
"""
import os
import re
import json
from pathlib import Path

OUTPUT_DIR = Path('output')

PAGES = [
    ('index', 'Home', '🏠'),
    ('survey', 'Survey Program', '📋'),
    ('scout', 'Scout Program', '🔭'),
    ('routing', 'Survey Routing', '🔀'),
    ('analytics', 'Analytics Hub', '📊'),
    ('orchestration_map', 'Architecture', '🔷'),
    ('summary', 'Executive Summary', '📄'),
    ('howitworks', 'How It Works', '❓'),
]

def read_file(name):
    path = OUTPUT_DIR / f'{name}.html'
    if path.exists():
        return path.read_text(encoding='utf-8')
    return None

def read_json(name):
    path = OUTPUT_DIR / f'{name}.json'
    if path.exists():
        return path.read_text(encoding='utf-8')
    return '{}'

def extract_body(html):
    if not html:
        return '<div style="padding:40px;text-align:center;">Page not available</div>'
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if not body_match:
        return '<div style="padding:40px;text-align:center;">Could not parse page</div>'
    body = body_match.group(1)
    body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r'href="(\w+)\.html"', r'href="#" onclick="showTab(\'\1\'); return false;"', body)
    return body

def extract_styles(html):
    if not html:
        return ''
    styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL | re.IGNORECASE)
    return '\n'.join(styles)

def extract_scripts(html):
    if not html:
        return ''
    scripts = re.findall(r'<script>([^<]*(?:(?!</script>)<[^<]*)*)</script>', html, re.DOTALL | re.IGNORECASE)
    return '\n'.join(scripts)

# Read all pages
pages_content = {}
all_styles = set()
all_scripts = {}

for page_id, title, icon in PAGES:
    html = read_file(page_id)
    if html:
        pages_content[page_id] = extract_body(html)
        style = extract_styles(html)
        if style:
            all_styles.add(style)
        script = extract_scripts(html)
        if script:
            all_scripts[page_id] = script

# Read JSON data
team_data = read_json('team_dashboard_data')
routing_data = read_json('survey_routing_data')

# Build tabs HTML
tabs_html = ''
for page_id, title, icon in PAGES:
    active = 'active' if page_id == 'index' else ''
    tabs_html += f'    <button class="tab-btn {active}" onclick="showTab(\'{page_id}\')">{icon} {title}</button>\n'

# Build content HTML  
content_html = ''
for page_id, title, icon in PAGES:
    active = 'active' if page_id == 'index' else ''
    content = pages_content.get(page_id, f'<div style="paddpx;">Page not found</div>')
    content_html += f'  <div id="tab-{page_id}" class="tab-content {active}">\n{content}\n  </div>\n\n'

# Build scripts
scripts_html = ''
for page_id, script in all_scripts.items():
    # Remove duplicate star generation
    script = re.sub(r"const stars = document\.getElementById\(['\"]stars['\"]\);", '// stars handled globally', script)
    scripts_html += f'\n// --- {page_id} ---\n(function() {{\n  try {{\n    {script}\n  }} catch(e) {{ console.log("{page_id} init error:", e); }}\n}})();\n'

# Combined styles
combined_styles = '\n'.join(all_styles)

# Write final HTML
compiled = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VUES · Control Console</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
{combined_styles}

/* TAB NAVIGATION */
.tab-nav {{
  position: sticky; top: 0; z-index: 1000;
  display: flex; flex-wrap: wrap; gap: 6px;
  padding: 12px 16px;
  background: rgba(6, 9, 20, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(120, 160, 255, 0.22);
}}
.tab-btn {{
  padding: 8px 14px; border-radius: 8px;
  border: 1px solid rgba(120, 160, 255, 0.22);
  background: transparent; color: #9EB1D4;
  font-size: 12px; font-weight: 600; cursor: pointer;
  transition: all 0.2s; display: flex; align-items: center; gap: 6px;
}}
.tab-btn:hover {{ background: rgba(90,228,255,0.1); border-color: #5AE4FF; color: #5AE4FF; }}
.tab-btn.active {{ background: #0053E2; border-color: #0053E2; color: white; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}
.back-link, .back-btn {{ display: none !important; }}
  </style>
</head>
<body>
  <div class="stars" id="stars"></div>
  
  <nav class="tab-nav">
{tabs_html}  </nav>

{content_html}

<script>
const teamData = {team_data};
const routingData = {routing_data};

const originalFetch = window.fetch;
window.fetch = function(url, options) {{
  if (typeof url === 'string') {{
    if (url.includes('team_dashboard_data.json')) {{
      return Promise.resolve({{ ok: true, json: () => Promise.resolve(teamData) }});
    }}
    if (url.includes('survey_routing_data.json')) {{
      return Promise.resolve({{ ok: true, json: () => Promise.resolve(routingData) }});
    }}
  }}
  return originalFetch(url, options);
}};

function showTab(tabId) {{
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const tab = document.getElementById('tab-' + tabId);
  if (tab) tab.classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(b => {{
    if (b.textContent.toLowerCase().includes(tabId.replace('_', ' ')) || 
        (tabId === 'index' && b.textContent.includes('Home'))) {{
      b.classList.add('active');
    }}
  }});
}}

// Stars
const stars = document.getElementById('stars');
if (stars) {{
  for (let i = 0; i < 80; i++) {{
    const s = document.createElement('span');
    s.className = 'star';
    s.style.cssText = 'top:'+Math.random()*100+'%;left:'+Math.random()*100+'%;width:'+(1+Math.random()*2)+'px;height:'+(1+Math.random()*2)+'px;opacity:'+(0.2+Math.random()*0.5)+';animation:twinkle '+(2+Math.random()*4)+'s ease-in-out infinite;animation-delay:'+Math.random()*5+'s;';
    stars.appendChild(s);
  }}
}}

{scripts_html}
</script>
</body>
</html>
'''

output_path = OUTPUT_DIR / 'vues_compiled.html'
output_path.write_text(compiled, encoding='utf-8')
print(f'Created: {output_path}')
print(f'Size: {len(compiled):,} bytes')
print(f'Pages: {", ".join([p[1] for p in PAGES])}')
