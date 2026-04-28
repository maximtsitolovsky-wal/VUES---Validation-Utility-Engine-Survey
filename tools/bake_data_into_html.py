#!/usr/bin/env python3
"""Bake JSON data directly into HTML files so dashboard works WITHOUT a server.

This solves the 'Loading...' problem by embedding data inline.
After running this, viewers can even double-click the HTML files directly.
"""

import sys
import json
import re
import shutil
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

REPO_ROOT = Path(__file__).parent.parent.resolve()
UI_DIR = REPO_ROOT / "ui"
OUTPUT_DIR = REPO_ROOT / "output"

# JSON files to embed
DATA_FILES = {
    "team_dashboard_data.json": "TEAM_DASHBOARD_DATA",
    "survey_routing_data.json": "SURVEY_ROUTING_DATA",
}

# HTML files to update
HTML_FILES = ["index.html", "survey.html", "scout.html", "summary.html",
              "analytics.html", "routing.html", "howitworks.html", "diagnostic.html", 
              "minimal_test.html", "ultra_simple_test.html"]


def sync_data_from_output():
    """Copy fresh data from output/ to ui/ if output has newer files."""
    synced = []
    for fname in DATA_FILES.keys():
        output_file = OUTPUT_DIR / fname
        ui_file = UI_DIR / fname
        
        if output_file.exists():
            # Copy if ui file doesn't exist or output is newer
            if not ui_file.exists() or output_file.stat().st_mtime > ui_file.stat().st_mtime:
                shutil.copy2(output_file, ui_file)
                synced.append(fname)
    
    if synced:
        print(f"  [SYNC] Copied from output/: {', '.join(synced)}")
    return synced


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
    
    # Patch fetch() calls to try live data first, fall back to embedded
    # CRITICAL: On file:// protocol, fetch() is completely blocked by browsers!
    # We must detect file:// and use embedded data immediately.
    fetch_polyfill = """
// === FETCH POLYFILL: detect file:// protocol and use embedded fallback ===
(function() {
  const _origFetch = window.fetch;
  const isFileProtocol = window.location.protocol === 'file:';
  console.log('[VUES] Protocol:', window.location.protocol, isFileProtocol ? '(using embedded data)' : '(trying live fetch)');
  
  function makeResponse(data, source) {
    console.log('[VUES] Serving from ' + source);
    const json = JSON.stringify(data);
    return Promise.resolve({
      ok: true,
      status: 200,
      json: function() { return Promise.resolve(data); },
      text: function() { return Promise.resolve(json); },
      headers: { get: function() { return 'application/json'; } }
    });
  }
  
  function getFallback(filename) {
    if (filename === 'team_dashboard_data.json' && window.TEAM_DASHBOARD_DATA_FALLBACK) {
      return makeResponse(window.TEAM_DASHBOARD_DATA_FALLBACK, 'embedded data (baked ' + window.VUES_BAKED_VERSION + ')');
    }
    if (filename === 'survey_routing_data.json' && window.SURVEY_ROUTING_DATA_FALLBACK) {
      return makeResponse(window.SURVEY_ROUTING_DATA_FALLBACK, 'embedded data (baked ' + window.VUES_BAKED_VERSION + ')');
    }
    return null;
  }
  
  window.fetch = function(url, opts) {
    const u = String(url).split('?')[0].split('/').pop();
    const isFetchingData = (u === 'team_dashboard_data.json' || u === 'survey_routing_data.json');
    
    // On file:// protocol, IMMEDIATELY return fallback - don't even try fetch
    if (isFileProtocol && isFetchingData) {
      const fallback = getFallback(u);
      if (fallback) {
        console.log('[VUES] file:// detected, using embedded data for:', u);
        return fallback;
      }
    }
    
    // For API calls on file://, return a mock 404 to trigger the JSON fallback path
    if (isFileProtocol && String(url).startsWith('/api/')) {
      console.log('[VUES] file:// API call blocked, returning mock 404:', url);
      return Promise.resolve({
        ok: false,
        status: 404,
        statusText: 'File protocol - API unavailable',
        json: function() { return Promise.reject(new Error('No server')); },
        text: function() { return Promise.resolve(''); }
      });
    }
    
    if (!isFetchingData) {
      return _origFetch.apply(this, arguments);
    }
    
    // On http/https, try live fetch first
    return _origFetch.apply(this, arguments)
      .then(function(resp) {
        if (resp.ok) {
          console.log('[VUES] ✓ Fetched live data:', u);
          return resp;
        }
        throw new Error('HTTP ' + resp.status);
      })
      .catch(function(err) {
        console.warn('[VUES] Fetch failed (' + err.message + '), using fallback for:', u);
        const fallback = getFallback(u);
        if (fallback) return fallback;
        console.error('[VUES] No fallback data available for', u);
        throw err;
      });
  };
})();
"""
    # Add polyfill after embedded data
    content = content.replace(
        '// === END EMBEDDED DATA ===',
        f'// === END EMBEDDED DATA ==={fetch_polyfill}'
    )
    
    # No need for auto-render fallback anymore - the fetch polyfill handles it
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
