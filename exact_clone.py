"""
Create EXACT clone of local VUES app as single HTML file.
Each page becomes a section, navigation shows/hides sections.
NO TABS. Looks identical to the original multi-page version.
"""
import re
import json
from pathlib import Path

OUTPUT_DIR = Path('output')

# All pages to include
PAGES = ['index', 'survey', 'scout', 'routing', 'analytics', 'orchestration_map', 'summary', 'howitworks']

def read_file(name):
    path = OUTPUT_DIR / f'{name}.html'
    return path.read_text(encoding='utf-8') if path.exists() else ''

def read_json(name):
    path = OUTPUT_DIR / f'{name}.json'
    return path.read_text(encoding='utf-8') if path.exists() else '{}'

# Read all HTML files
html_files = {p: read_file(p) for p in PAGES}

# Read JSON data
team_data = read_json('team_dashboard_data')
routing_data = read_json('survey_routing_data')

# Extract full HTML for each page and convert links
def process_page(name, html):
    if not html:
        return f'<div style="padding:40px;text-align:center;color:#9EB1D4;">Page {name} not found</div>'
    
    # Get everything inside <body>
    match = re.search(r'<body[^>]*>(.*)</body>', html, re.DOTALL)
    if not match:
        return html
    
    body = match.group(1)
    
    # Convert href="X.html" to onclick="goTo('X')"
    body = re.sub(r'href="(\w+)\.html"', r'href="#" onclick="goTo(\'\1\'); return false;"', body)
    
    # Convert back links
    body = re.sub(r'href="index\.html"', r'href="#" onclick="goTo(\'index\'); return false;"', body)
    
    return body

# Extract all styles from all pages (deduplicated)
all_styles = []
seen_styles = set()
for name, html in html_files.items():
    for match in re.finditer(r'<style[^>]*>(.*?)</style>', html, re.DOTALL):
        style = match.group(1).strip()
        style_hash = hash(style[:500])  # Use first 500 chars as key
        if style_hash not in seen_styles:
            seen_styles.add(style_hash)
            all_styles.append(f'/* === {name}.html === */\n{style}')

# Extract all scripts
all_scripts = {}
for name, html in html_files.items():
    scripts = re.findall(r'<script>([^<]*(?:(?!</script>)<[^<]*)*)</script>', html, re.DOTALL)
    if scripts:
        combined = '\n'.join(scripts)
        # Remove star generation (we'll do it once globally)
        combined = re.sub(r"const stars = document\.getElementById\(['\"]stars['\"]\);[\s\S]*?stars\.appendChild\(star\);\s*\}", '', combined)
        combined = re.sub(r"for \(let i = 0; i < \d+; i\+\+\) \{[^}]*star[^}]*\}", '', combined)
        all_scripts[name] = combined

# Build the final HTML
output = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VUES · Command Center</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
'''
output += '\n'.join(all_styles)
output += '''
    
    /* Page sections */
    .page-section { display: none; }
    .page-section.active { display: block; }
    
    /* Fix body for sections */
    body { 
      display: block !important; 
      align-items: initial !important; 
      justify-content: initial !important;
      overflow: auto !important;
    }
    .page-section[data-page="index"] body,
    .page-section[data-page="index"] { 
      display: flex; 
      align-items: center; 
      justify-content: center; 
      min-height: 100vh;
    }
    .page-section.active[data-page="index"] {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }
  </style>
</head>
<body>
  <div class="stars" id="stars"></div>
'''

# Add each page as a section
for name in PAGES:
    active = 'active' if name == 'index' else ''
    content = process_page(name, html_files[name])
    output += f'\n  <div class="page-section {active}" data-page="{name}" id="page-{name}">\n{content}\n  </div>\n'

# Add scripts
output += '''
<script>
// Embedded data
const teamData = ''' + team_data + ''';
const routingData = ''' + routing_data + ''';

// Override fetch
const _fetch = window.fetch;
window.fetch = function(url) {
  if (typeof url === 'string') {
    if (url.includes('team_dashboard_data')) return Promise.resolve({ok:true, json:()=>Promise.resolve(teamData)});
    if (url.includes('survey_routing_data')) return Promise.resolve({ok:true, json:()=>Promise.resolve(routingData)});
  }
  return _fetch.apply(this, arguments);
};

// Navigation
function goTo(page) {
  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  const target = document.getElementById('page-' + page);
  if (target) {
    target.classList.add('active');
    window.scrollTo(0, 0);
    // Re-init charts if needed
    if (window['initPage_' + page]) window['initPage_' + page]();
  }
}

// Stars
const stars = document.getElementById('stars');
for (let i = 0; i < 80; i++) {
  const s = document.createElement('span');
  s.className = 'star';
  s.style.cssText = 'position:absolute;border-radius:50%;background:white;box-shadow:0 0 6px rgba(255,255,255,0.5);top:'+Math.random()*100+'%;left:'+Math.random()*100+'%;width:'+(1+Math.random()*2)+'px;height:'+(1+Math.random()*2)+'px;opacity:'+(0.2+Math.random()*0.5)+';animation:twinkle '+(2+Math.random()*4)+'s ease-in-out infinite;animation-delay:'+Math.random()*5+'s;';
  stars.appendChild(s);
}

// Twinkle animation
const twinkleStyle = document.createElement('style');
twinkleStyle.textContent = '@keyframes twinkle { 0%, 100% { opacity: 0.2; } 50% { opacity: 0.8; } }';
document.head.appendChild(twinkleStyle);

'''

# Add page scripts
for name, script in all_scripts.items():
    output += f'\n// === {name} ===\n(function(){{\ntry{{\n{script}\n}}catch(e){{console.log("{name} error:",e);}}\n}})();\n'

output += '''
</script>
</body>
</html>'''

# Write
out_path = OUTPUT_DIR / 'vues_exact_clone.html'
out_path.write_text(output, encoding='utf-8')
print(f'Created: {out_path}')
print(f'Size: {len(output):,} bytes')
print(f'Pages: {", ".join(PAGES)}')
