"""Build a self-contained Puppy Share HTML from the canonical generated dashboard."""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
SHARE_DIR = ROOT / "share"
SOURCE_NAME = "executive_dashboard.html"
TARGET_NAME = "executive_dashboard_live_share.html"

_IMG_SRC_PATTERN = re.compile(r'(<img\b[^>]*\bsrc=")(?P<src>\./assets/[^"#?]+)(")', re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=OUTPUT_DIR / SOURCE_NAME)
    parser.add_argument("--target", type=Path, default=SHARE_DIR / TARGET_NAME)
    return parser.parse_args()


def inline_asset_images(html: str, source_dir: Path) -> str:
    def _replace(match: re.Match[str]) -> str:
        rel_src = match.group("src")
        asset_path = (source_dir / rel_src).resolve()
        if not asset_path.exists() or not asset_path.is_file():
            raise FileNotFoundError(f"Asset referenced by dashboard was not found: {asset_path}")

        mime_type, _ = mimetypes.guess_type(asset_path.name)
        mime_type = mime_type or "application/octet-stream"
        encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
        data_uri = f"data:{mime_type};base64,{encoded}"
        return f'{match.group(1)}{data_uri}{match.group(3)}'

    return _IMG_SRC_PATTERN.sub(_replace, html)


def inject_share_banner(html: str) -> str:
    banner = (
        "<div style=\"position:sticky;top:0;z-index:9999;padding:10px 14px;"
        "background:#0053e2;color:#ffffff;font:600 14px/1.4 Arial,sans-serif;"
        "border-bottom:2px solid #ffc220;box-shadow:0 2px 8px rgba(0,0,0,0.18);\">"
        "Shared dashboard snapshot auto-republished from the live SiteOwlQA output. "
        "Refresh cadence depends on the republish job schedule."
        "</div>"
    )
    return html.replace("<body>", f"<body>\n{banner}", 1)


def build_share_dashboard(source: Path, target: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"Source dashboard does not exist: {source}")

    html = source.read_text(encoding="utf-8")
    html = inline_asset_images(html, source.parent)
    html = inject_share_banner(html)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target


def main() -> None:
    args = parse_args()
    out = build_share_dashboard(source=args.source.resolve(), target=args.target.resolve())
    print(out)


if __name__ == "__main__":
    main()
