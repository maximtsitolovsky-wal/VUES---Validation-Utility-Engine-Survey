from __future__ import annotations

from pathlib import Path
import sys

# Ensure project root is importable when running from tools/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    p = Path("output/executive_dashboard.html")
    txt = p.read_text(encoding="utf-8", errors="replace")

    print("HAS_COMMENT", "IMPORTANT: keep this JS string literal" in txt)
    print("HAS_JOIN_ESC", "join('\\\\n\\\\n')" in txt)

    needle = "return lines.map(row => row.map(csvEscape).join(',')).join("
    idx = txt.find(needle)
    print("RETURN_IDX", idx)
    if idx != -1:
        snippet = txt[idx : idx + 160]
        snippet = snippet.replace("\r", "<CR>").replace("\n", "<NL>")
        print("SNIPPET", snippet)


if __name__ == "__main__":
    main()
