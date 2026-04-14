from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
SERVED_DIR = ROOT / "served_dashboard"
ASSETS_DIR = "assets"
DASHBOARD_NAME = "executive_dashboard.html"
ARCH_MAP_NAME = "orchestration_map.html"
META_REFRESH = '  <meta http-equiv="refresh" content="60" />\n'


def main() -> None:
    SERVED_DIR.mkdir(exist_ok=True)
    (SERVED_DIR / ASSETS_DIR).mkdir(exist_ok=True)

    src_dashboard = OUTPUT_DIR / DASHBOARD_NAME
    dst_dashboard = SERVED_DIR / DASHBOARD_NAME
    shutil.copy2(src_dashboard, dst_dashboard)

    # Also publish the architecture map if it exists in output/
    src_arch = OUTPUT_DIR / ARCH_MAP_NAME
    if src_arch.exists():
        shutil.copy2(src_arch, SERVED_DIR / ARCH_MAP_NAME)
    else:
        # Fall back to repo root copy
        root_arch = ROOT / ARCH_MAP_NAME
        if root_arch.exists():
            shutil.copy2(root_arch, SERVED_DIR / ARCH_MAP_NAME)

    for asset in (OUTPUT_DIR / ASSETS_DIR).glob("*"):
        if asset.is_file():
            shutil.copy2(asset, SERVED_DIR / ASSETS_DIR / asset.name)

    html = dst_dashboard.read_text(encoding="utf-8")
    html = html.replace(META_REFRESH, "")
    dst_dashboard.write_text(html, encoding="utf-8")

    print(f"Published {dst_dashboard}")
    if (SERVED_DIR / ARCH_MAP_NAME).exists():
        print(f"Published {SERVED_DIR / ARCH_MAP_NAME}")


if __name__ == "__main__":
    main()
