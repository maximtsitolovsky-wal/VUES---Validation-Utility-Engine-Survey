#!/usr/bin/env python3
"""Bake JSON data directly into HTML files so dashboard works WITHOUT a server.

This solves the 'Loading...' problem by embedding data inline.
After running this, viewers can even double-click the HTML files directly.
"""

import sys
import json
import re
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

REPO_ROOT = Path(__file__).parent.parent.resolve()
UI_DIR = REPO_ROOT / "ui"

# JSON files to embed
DATA_FILES = {
    "team_dashboard_data.json": "TEAM_DASHBOARD_DATA",
    "survey_routing_data.json": "SURVEY_ROUTING_DATA",
}

# HTML files to update
HTML_FILES = ["index.html", "survey.html", "scout.html", "summary.html",
              "analytics.html", "routing.html", "howitworks.html"]


def load_data():
    """Load all JSON data files."""
    data = {}
    for fname, var_name in DATA_FILES.items():
        path = UI_DIR / fname
        if path.exists():
            data[var_name] = json.loads(path.read_text(encoding='utf-8'))
            print(f"  [OK] Loaded {fname} ({path.stat().st_size // 1024} KB)")
        else:
            print(f"  [SKIP] {fname} not found")
            data[var_name] = {}
    return data


def inject_data_into_html(html_path: Path, data: dict) -> bool:
    """Inject JSON data as window.* globals before any fetch calls."""
    if not html_path.exists():
        print(f"  [SKIP] {html_path.name} not found")
        return False
    
    content = html_path.read_text(encoding='utf-8')
    
    # Build the injection script
    from datetime import datetime
    version = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    inject_lines = ["<script>"]
    inject_lines.append("// === EMBEDDED DATA (auto-generated, do not edit) ===")
    inject_lines.append(f"window.VUES_BAKED_VERSION = '{version}';")
    inject_lines.append(f"console.log('[VUES] Baked data loaded:', '{version}');")
    for var_name, payload in data.items():
        # Use JSON.parse for performance with large objects
        json_str = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
        inject_lines.append(f"window.{var_name} = {json_str};")
    inject_lines.append("// === END EMBEDDED DATA ===")
    inject_lines.append("</script>")
    inject_block = "\n".join(inject_lines)
    
    # Remove any previous injection
    pattern = re.compile(
        r'<script>\s*//\s*===\s*EMBEDDED DATA.*?//\s*===\s*END EMBEDDED DATA\s*===\s*</script>',
        re.DOTALL
    )
    content = pattern.sub('', content)
    
    # Inject right before </head> (or </body> if no head)
    if '</head>' in content:
        content = content.replace('</head>', f'{inject_block}\n</head>', 1)
    elif '</body>' in content:
        content = content.replace('</body>', f'{inject_block}\n</body>', 1)
    else:
        print(f"  [WARN] {html_path.name} has no </head> or </body> tag")
        return False
    
    # Patch fetch() calls to use embedded data first
    # Replace: fetch('team_dashboard_data.json...') with a polyfill
    fetch_polyfill = """
// === FETCH POLYFILL: use embedded data when available ===
(function() {
  const _origFetch = window.fetch;
  window.fetch = function(url, opts) {
    const u = String(url).split('?')[0].split('/').pop();
    if (u === 'team_dashboard_data.json' && window.TEAM_DASHBOARD_DATA) {
      return Promise.resolve(new Response(JSON.stringify(window.TEAM_DASHBOARD_DATA), {
        status: 200, headers: { 'Content-Type': 'application/json' }
      }));
    }
    if (u === 'survey_routing_data.json' && window.SURVEY_ROUTING_DATA) {
      return Promise.resolve(new Response(JSON.stringify(window.SURVEY_ROUTING_DATA), {
        status: 200, headers: { 'Content-Type': 'application/json' }
      }));
    }
    return _origFetch.apply(this, arguments);
  };
})();
"""
    # Add polyfill after embedded data
    content = content.replace(
        '// === END EMBEDDED DATA ===',
        f'// === END EMBEDDED DATA ==={fetch_polyfill}'
    )
    
    html_path.write_text(content, encoding='utf-8')
    return True


def main():
    print("")
    print("  ============================================")
    print("   VUES - Bake Data Into HTML")
    print("  ============================================")
    print("")
    
    # Load all data
    print("  Loading data files...")
    data = load_data()
    print("")
    
    if not any(data.values()):
        print("  [FATAL] No data files found in ui/")
        sys.exit(1)
    
    # Inject into each HTML
    print("  Injecting data into HTML files...")
    for html_name in HTML_FILES:
        html_path = UI_DIR / html_name
        if inject_data_into_html(html_path, data):
            size = html_path.stat().st_size
            print(f"  [OK] {html_name} updated ({size // 1024} KB)")
    
    print("")
    print("  ============================================")
    print("   Done! Dashboard now works WITHOUT a server.")
    print("   Viewers can even double-click the HTML files.")
    print("  ============================================")
    print("")


if __name__ == "__main__":
    main()
