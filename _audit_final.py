"""Final enterprise-ready audit for SiteOwlQA UI + backend."""
from pathlib import Path
import re, sys, io, importlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
results = []

def chk(label, ok, detail=""):
    sym = "PASS" if ok else "FAIL"
    results.append((sym, label, detail))
    mark = "[OK]" if ok else "[!!]"
    print(f"  {mark} {label}" + (f"  -- {detail}" if detail else ""))

def warn(label, detail=""):
    results.append(("WARN", label, detail))
    print(f"  [WW] {label}" + (f"  -- {detail}" if detail else ""))

# =============================================================================
print("\n=== orchestration_map.html ===")
om_path = ROOT / "orchestration_map.html"
chk("File exists", om_path.exists())
om = om_path.read_text(encoding="utf-8")

# Back link
m = re.search(r'id="back-btn"[^>]+href="([^"]+)"', om)
href = m.group(1) if m else None
chk("back-btn href present", href is not None)
if href:
    resolved = (ROOT / href).resolve()
    chk(f"back-btn target exists ({href})", resolved.exists())

# UI elements
chk("Guide toggle button", 'id="guide-btn"' in om)
chk("Guide panel", 'id="guide"' in om)
chk("toggleGuide() defined", "function toggleGuide" in om)
chk("Canvas element", "<canvas" in om)
chk("NODES array", "const NODES" in om)
chk("EDGES array", "const EDGES" in om)
chk("Animation loop (rAF)", "requestAnimationFrame" in om)
chk("function tick() present", "function tick" in om)
chk("Clock element + setInterval", 'id="clock"' in om and "setInterval" in om)
chk("HUD present", 'id="hud"' in om)
chk("Hover panel present", 'id="panel"' in om)
chk("Legend present", 'id="legend"' in om)
chk("Guide stage sections (7)", om.count("g-section-title") >= 7)
chk("Guide has learning loop section", "Learning Loop" in om)
chk("Guide has edge legend section", "what the lines mean" in om)

# Data counts
node_ids = re.findall(r"\{id:'([^']+)'", om)
edges_m = re.search(r"const EDGES\s*=\s*\[(.*?)\];", om, re.DOTALL)
edge_count = len(re.findall(r"\{f:'", edges_m.group(1))) if edges_m else 0
chk(f"Node count = 23", len(node_ids) == 23, f"found {len(node_ids)}")
chk(f"Edge count = 27", edge_count == 27, f"found {edge_count}")

# HUD stat correct
chk("HUD shows 27 edges", '"stat-n">27</div><div class="stat-l">Edges' in om)

# Brace balance
scripts = re.findall(r"<script[^>]*>(.*?)</script>", om, re.DOTALL)
for i, sc in enumerate(scripts):
    ob, cb = sc.count("{"), sc.count("}")
    chk(f"Script block {i+1} brace balance ({ob}/{cb})", ob == cb)

# No broken local refs
broken = []
for pat in [r'src="([^"]+)"', r'href="([^"]+)"']:
    for m2 in re.finditer(pat, om):
        v = m2.group(1)
        if v.startswith(("http", "#", "javascript", "data:", "mailto")):
            continue
        p = (ROOT / v).resolve()
        if p.suffix in (".html", ".js", ".css", ".png", ".ico") and not p.exists():
            broken.append(v)
chk("No broken local refs", len(broken) == 0, str(broken) if broken else "")

# Line count
lc = om.count("\n") + 1
chk(f"Under 600 lines ({lc})", lc <= 600)

# =============================================================================
print("\n=== ui/executive_dashboard.html (source template) ===")
ed_path = ROOT / "ui" / "executive_dashboard.html"
chk("File exists", ed_path.exists())
ed = ed_path.read_text(encoding="utf-8")

chk("Architecture nav link present", "Architecture" in ed)
arch_m = re.search(r'href="([^"]*orchestration[^"]*)"', ed)
if arch_m:
    ahref = arch_m.group(1)
    resolved_a = (ROOT / "ui" / ahref).resolve()
    chk(f"Architecture href resolves to existing file", resolved_a.exists(), ahref)
else:
    chk("Architecture href found", False)

for nav in ["#overview", "#performance", "#metrics", "#scout", "#weekly-highlights", "#admin"]:
    chk(f"Nav link {nav} present", nav in ed)

# Brace balance
scripts_ed = re.findall(r"<script[^>]*>(.*?)</script>", ed, re.DOTALL)
for i, sc in enumerate(scripts_ed):
    ob, cb = sc.count("{"), sc.count("}")
    chk(f"Script block {i+1} brace balance", ob == cb)

broken_ed = []
for m3 in re.finditer(r'src="([^"]+)"', ed):
    v = m3.group(1)
    if v.startswith(("http", "data:", "//")):
        continue
    p = (ROOT / "ui" / v).resolve()
    if p.suffix in (".png", ".jpg", ".svg", ".ico", ".webp") and not p.exists():
        broken_ed.append(v)
chk("No broken image srcs", len(broken_ed) == 0, str(broken_ed) if broken_ed else "")

# =============================================================================
print("\n=== served_dashboard/ ===")
for fname in ["executive_dashboard.html", "executive_dashboard_puppy_inline.html"]:
    sd_p = ROOT / "served_dashboard" / fname
    chk(f"{fname} exists", sd_p.exists())
    if sd_p.exists():
        sd = sd_p.read_text(encoding="utf-8")
        chk(f"Architecture link in {fname}", "Architecture" in sd)
        chk(f"Admin link in {fname}", "#admin" in sd)
        for sid in ["metrics", "scout", "weekly-highlights"]:
            chk(f'id="{sid}" in {fname}', f'id="{sid}"' in sd)

# =============================================================================
print("\n=== Backend modules ===")
mods = [
    "src.siteowlqa.config", "src.siteowlqa.models", "src.siteowlqa.sql",
    "src.siteowlqa.memory", "src.siteowlqa.file_processor",
    "src.siteowlqa.python_grader", "src.siteowlqa.airtable_client",
    "src.siteowlqa.emailer", "src.siteowlqa.archive", "src.siteowlqa.reviewer",
    "src.siteowlqa.post_pass_correction", "src.siteowlqa.poll_airtable",
    "src.siteowlqa.metrics", "src.siteowlqa.dashboard_exec",
    "src.siteowlqa.local_dashboard_server", "src.siteowlqa.weekly_highlights",
    "src.siteowlqa.dashboard",
]
for mod in mods:
    try:
        importlib.import_module(mod)
        chk(f"import {mod.split('.')[-1]}", True)
    except Exception as e:
        chk(f"import {mod.split('.')[-1]}", False, str(e)[:80])

# =============================================================================
print("\n=== Key paths ===")
for p in [".env", "pyproject.toml", "main.py", "MEMORY.md",
          "src/siteowlqa/__init__.py", "archive", "output", "logs", "temp",
          "tools/run_dashboard_server.py", "ui/assets/camera_assembled.png"]:
    fp = ROOT / p
    chk(f"{p}", fp.exists())

# =============================================================================
print("\n=== .env config keys (names from config.py) ===")
env_text = (ROOT / ".env").read_text(encoding="utf-8")
expected_keys = [
    "POLL_INTERVAL_SECONDS", "REFERENCE_SOURCE", "TEMP_DIR",
    "OUTPUT_DIR", "LOG_DIR", "ARCHIVE_DIR", "SUBMISSIONS_DIR",
]
for key in expected_keys:
    present = key in env_text
    val_m = re.search(rf"^{key}=(.+)$", env_text, re.MULTILINE)
    val = val_m.group(1).strip() if val_m else ""
    chk(f"{key} set", present and bool(val))

# =============================================================================
print("\n=== SUMMARY ===")
passes = sum(1 for r in results if r[0] == "PASS")
fails  = sum(1 for r in results if r[0] == "FAIL")
warns  = sum(1 for r in results if r[0] == "WARN")
total  = len(results)
pct = round(100 * passes / total) if total else 0
print(f"  {passes}/{total} checks passed ({pct}%)  |  FAIL={fails}  WARN={warns}")

if fails:
    print("\n  FAILURES to fix:")
    for r in results:
        if r[0] == "FAIL":
            print(f"    !! {r[1]}  {r[2]}")
if warns:
    print("\n  Warnings (non-blocking):")
    for r in results:
        if r[0] == "WARN":
            print(f"    WW {r[1]}  {r[2]}")

sys.exit(0 if fails == 0 else 1)
