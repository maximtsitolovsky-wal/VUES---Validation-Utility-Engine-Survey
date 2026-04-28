#!/usr/bin/env python3
"""Fix loadData() in all HTML files to be bulletproof with visible error handling."""

import re
from pathlib import Path

UI_DIR = Path(__file__).parent.parent / "ui"

# New bulletproof loadData function
NEW_LOAD_DATA = '''async function loadData() {
  const errorBox = document.createElement('div');
  errorBox.id = 'vues-error-box';
  errorBox.style.cssText = 'position:fixed;top:0;left:0;right:0;padding:15px;background:#4e1d1d;color:#fff;text-align:center;z-index:9999;display:none;font-family:system-ui;';
  document.body.appendChild(errorBox);
  
  function showError(msg) {
    errorBox.innerHTML = '⚠️ ' + msg + ' <button onclick="location.reload()" style="margin-left:10px;padding:5px 10px;cursor:pointer;">Retry</button>';
    errorBox.style.display = 'block';
  }
  
  function showStaleWarning() {
    errorBox.innerHTML = '⚠️ Using cached data (baked ' + (window.VUES_BAKED_VERSION || 'unknown') + '). <a href="diagnostic.html" style="color:#ffc220;">Run diagnostic</a>';
    errorBox.style.display = 'block';
    errorBox.style.background = '#4e4e1d';
  }
  
  let data = null;
  let source = 'none';
  
  // Try fetch first
  try {
    const response = await fetch(`team_dashboard_data.json?t=${Date.now()}`, { cache: 'no-store' });
    if (response.ok) {
      data = await response.json();
      source = 'fetch';
      console.log('[VUES] ✓ Loaded data via fetch');
    }
  } catch (error) {
    console.warn('[VUES] Fetch failed:', error.message);
  }
  
  // Fallback to embedded data
  if (!data && window.TEAM_DASHBOARD_DATA_FALLBACK) {
    data = window.TEAM_DASHBOARD_DATA_FALLBACK;
    source = 'fallback';
    console.log('[VUES] Using embedded fallback data');
    showStaleWarning();
  }
  
  // No data available
  if (!data) {
    showError('No data available. Please run: git pull');
    return;
  }
  
  // Try to render
  try {
    renderAll(data);
    console.log('[VUES] ✓ Rendered successfully from ' + source);
  } catch (error) {
    console.error('[VUES] Render error:', error);
    showError('Render error: ' + error.message + '. Check console for details.');
  }
}'''

# Pattern to match existing loadData function
LOAD_DATA_PATTERN = re.compile(
    r'async function loadData\(\)\s*\{.*?^\}',
    re.MULTILINE | re.DOTALL
)

def fix_file(html_path: Path) -> bool:
    """Fix loadData in a single HTML file."""
    content = html_path.read_text(encoding='utf-8')
    
    # Find and replace loadData function
    match = LOAD_DATA_PATTERN.search(content)
    if not match:
        print(f"  [SKIP] {html_path.name} - no loadData function found")
        return False
    
    # Replace the function
    new_content = content[:match.start()] + NEW_LOAD_DATA + content[match.end():]
    
    html_path.write_text(new_content, encoding='utf-8')
    print(f"  [OK] {html_path.name} - loadData fixed")
    return True

def main():
    print("\n  ============================================")
    print("   VUES - Fix loadData Error Handling")
    print("  ============================================\n")
    
    html_files = ["index.html", "survey.html", "scout.html", "summary.html",
                  "analytics.html", "routing.html", "howitworks.html"]
    
    fixed = 0
    for fname in html_files:
        path = UI_DIR / fname
        if path.exists():
            if fix_file(path):
                fixed += 1
    
    print(f"\n  Fixed {fixed} files")
    print("  Now run: python tools/bake_data_into_html.py")
    print("  Then: git add ui/*.html && git commit && git push\n")

if __name__ == "__main__":
    main()
