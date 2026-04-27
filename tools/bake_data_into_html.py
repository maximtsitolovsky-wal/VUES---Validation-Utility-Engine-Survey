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
    """Inject JSON data as window.* globals WITH fetch-first-fallback logic."""
    if not html_path.exists():
        print(f"  [SKIP] {html_path.name} not found")
        return False
    
    content = html_path.read_text(encoding='utf-8')
    
    # Build the injection script
    from datetime import datetime
    version = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    inject_lines = ["<script>"]
    inject_lines.append("// === EMBEDDED DATA (FALLBACK for offline viewing, auto-generated) ===")
    inject_lines.append(f"window.VUES_BAKED_VERSION = '{version}';")
    inject_lines.append(f"console.log('[VUES] Fallback data available:', '{version}');")
    for var_name, payload in data.items():
        # Store as _FALLBACK to make it clear this is backup data
        json_str = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
        inject_lines.append(f"window.{var_name}_FALLBACK = {json_str};")
    inject_lines.append("// === END EMBEDDED DATA ===")
    inject_lines.append("</script>")
    inject_block = "\n".join(inject_lines)
    
    # Remove ANY previous injections (handle multiple if file got bloated)
    pattern = re.compile(
        r'<script>\s*//\s*===\s*EMBEDDED DATA.*?</script>',
        re.DOTALL
    )
    while pattern.search(content):
        content = pattern.sub('', content, count=1)
    
    # Also remove previous fallback scripts
    fallback_pattern = re.compile(
        r'<script>\s*//\s*===\s*FALLBACK AUTO-RENDER.*?</script>',
        re.DOTALL
    )
    while fallback_pattern.search(content):
        content = fallback_pattern.sub('', content, count=1)
    
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
  function makeResponse(data) {
    const json = JSON.stringify(data);
    return Promise.resolve({
      ok: true,
      status: 200,
      json: function() { return Promise.resolve(data); },
      text: function() { return Promise.resolve(json); },
      headers: { get: function() { return 'application/json'; } }
    });
  }
  window.fetch = function(url, opts) {
    const u = String(url).split('?')[0].split('/').pop();
    if (u === 'team_dashboard_data.json' && window.TEAM_DASHBOARD_DATA) {
      console.log('[VUES] Serving team_dashboard_data.json from embedded data');
      return makeResponse(window.TEAM_DASHBOARD_DATA);
    }
    if (u === 'survey_routing_data.json' && window.SURVEY_ROUTING_DATA) {
      console.log('[VUES] Serving survey_routing_data.json from embedded data');
      return makeResponse(window.SURVEY_ROUTING_DATA);
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
    
    # Add fallback auto-render at end of body (in case polyfill doesn't fire)
    fallback_render = """
<script>
// === FALLBACK AUTO-RENDER: directly use embedded data if fetch didn't work ===
(function() {
  function tryRender() {
    var data = window.TEAM_DASHBOARD_DATA;
    if (!data) { console.log('[VUES] No embedded data, skipping fallback'); return; }
    
    // Check if page still shows Loading... (means fetch/polyfill failed)
    var body = document.body ? document.body.innerHTML : '';
    if (body.indexOf('>Loading...<') === -1 && body.indexOf('>Loading vendor') === -1) {
      console.log('[VUES] Data already rendered, skipping fallback');
      return;
    }
    
    console.log('[VUES] Fallback: directly rendering embedded data');
    
    // Try to call page-specific render functions
    try {
      if (typeof renderAll === 'function') {
        var records = data.survey?.records || data.scout?.records || [];
        renderAll(records);
        console.log('[VUES] renderAll() called with', records.length, 'records');
      }
      if (typeof loadData === 'function') {
        // loadData uses fetch internally, but polyfill should intercept
        loadData();
        console.log('[VUES] loadData() re-triggered');
      }
    } catch(e) {
      console.error('[VUES] Fallback render error:', e);
    }
  }
  
  // Run after a delay to let page scripts initialize
  if (document.readyState === 'complete') {
    setTimeout(tryRender, 500);
  } else {
    window.addEventListener('load', function() { setTimeout(tryRender, 500); });
  }
})();
</script>
"""
    # Inject fallback before </body>
    if '</body>' in content:
        content = content.replace('</body>', f'{fallback_render}</body>', 1)
    
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
