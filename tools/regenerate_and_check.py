from __future__ import annotations

from pathlib import Path
import sys

# Ensure project root is importable when running from tools/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import dashboard  # noqa: E402
import dashboard_exec  # noqa: E402


def main() -> None:
    print("dashboard.__file__:", dashboard.__file__)
    print("dashboard_exec.__file__:", dashboard_exec.__file__)

    out_dir = Path("output")
    dashboard.refresh_dashboards(out_dir)

    out_html = out_dir / "executive_dashboard.html"
    txt = out_html.read_text(encoding="utf-8", errors="replace")

    has_comment = "IMPORTANT: keep this JS string literal" in txt
    has_join_esc = "join('\\\\n\\\\n')" in txt

    print("output:", out_html)
    print("HAS_COMMENT", has_comment)
    print("HAS_JOIN_ESC", has_join_esc)

    # Also show the exact join line vicinity.
    needle = "return lines.map(row => row.map(csvEscape).join(',')).join("
    idx = txt.find(needle)
    print("RETURN_IDX", idx)
    if idx != -1:
        snippet = txt[idx : idx + 120]
        print("SNIPPET_RAW", repr(snippet))


if __name__ == "__main__":
    main()
