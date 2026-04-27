#!/usr/bin/env python3
"""Remove baked-in data from HTML files to make them live-fetch templates again.

This reverses what bake_data_into_html.py does - removes embedded JSON,
fetch polyfills, and fallback render scripts so pages fetch live data.
"""

import re
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

REPO_ROOT = Path(__file__).parent.parent.resolve()
UI_DIR = REPO_ROOT / "ui"

HTML_FILES = ["index.html", "survey.html", "scout.html", "summary.html",
              "analytics.html", "routing.html", "howitworks.html"]


def unbake_html(html_path: Path) -> bool:
    """Remove all baked-in data and polyfills from an HTML file."""
    if not html_path.exists():
        print(f"  [SKIP] {html_path.name} not found")
        return False
    
    content = html_path.read_text(encoding='utf-8')
    original_size = len(content)
    
    # Remove embedded data blocks
    pattern = re.compile(
        r'<script>\s*//\s*===\s*EMBEDDED DATA.*?</script>',
        re.DOTALL
    )
    while pattern.search(content):
        content = pattern.sub('', content, count=1)
    
    # Remove fallback scripts
    fallback_pattern = re.compile(
        r'<script>\s*//\s*===\s*FALLBACK AUTO-RENDER.*?</script>',
        re.DOTALL
    )
    while fallback_pattern.search(content):
        content = fallback_pattern.sub('', content, count=1)
    
    # Remove fetch polyfill blocks
    polyfill_pattern = re.compile(
        r'//\s*===\s*FETCH POLYFILL:.*?\}\)\(\);',
        re.DOTALL
    )
    content = polyfill_pattern.sub('', content)
    
    # Clean up extra blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    new_size = len(content)
    if original_size == new_size:
        print(f"  [OK] {html_path.name} was already clean ({new_size // 1024} KB)")
        return False
    
    html_path.write_text(content, encoding='utf-8')
    saved_kb = (original_size - new_size) // 1024
    print(f"  [OK] {html_path.name} unbaked! {original_size // 1024} KB → {new_size // 1024} KB (saved {saved_kb} KB)")
    return True


def main():
    print("")
    print("  ============================================")
    print("   VUES - Unbake HTML (Restore Live Fetch)")
    print("  ============================================")
    print("")
    
    total_saved = 0
    modified_count = 0
    
    for html_name in HTML_FILES:
        html_path = UI_DIR / html_name
        if unbake_html(html_path):
            modified_count += 1
            # Track size savings
    
    print("")
    if modified_count > 0:
        print(f"  ✅ Unbaked {modified_count} file(s)!")
        print("  📡 Pages will now fetch LIVE data from team_dashboard_data.json")
        print("")
        print("  Next steps:")
        print("    1. The pipeline will copy these clean templates to output/")
        print("    2. Pages will auto-refresh every 15 seconds from Airtable")
        print("")
    else:
        print("  ✅ All files are already clean - no baked data found!")
        print("")
    
    print("  ============================================")
    print("")


if __name__ == "__main__":
    main()
