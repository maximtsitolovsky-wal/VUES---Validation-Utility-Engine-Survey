# 🎯 Force Section Override - User Guide

## What It Does

**Force Section** lets you **manually move any site to ANY tab**, overriding the automatic routing logic based on survey type.

---

## 🔧 How to Use It

### Step 1: Open the Routing Page
```
http://localhost:60630/routing.html
```

### Step 2: Click Any Site
- Click any row in any tab to open the edit modal

### Step 3: Set "Force Section"
At the top of the modal, you'll see:
```
Force Section: ⚡ Override automatic routing
```

**Dropdown options:**
- **AUTO** (default) — Use survey type logic (normal behavior)
- **CCTV Surveys** — Force to CCTV tab
- **FA/Intrusion Surveys** — Force to FA tab
- **Both Surveys (Upgrade)** — Force to Upgrade tab
- **No Survey (Full Upgrade)** — Force to No Survey tab
- **Needs Review** — Force to Review tab
- **Awaiting Scout** — Force to Scout tab
- **Complete** — Force to Complete tab

### Step 4: Save Changes
- Click **"Save Changes"**
- Site immediately moves to the selected tab
- Backend saves `section_override` field to JSON

---

## 📊 Use Cases

### Example 1: Manual Review Override
**Scenario:** Site 12345 is in "Needs Review" but you've made a decision.

**Steps:**
1. Click site 12345 in "Needs Review" tab
2. Set **Force Section** → `CCTV Surveys`
3. Set **Survey Type** → `CCTV Only`
4. Save

**Result:** Site moves to CCTV tab, ready for vendor assignment

---

### Example 2: Mark as Complete
**Scenario:** Site 67890 survey is done but not marked complete.

**Steps:**
1. Find site 67890 (any tab)
2. Set **Force Section** → `Complete`
3. Save

**Result:** Site moves to Complete tab immediately

---

### Example 3: Reset to Automatic
**Scenario:** You forced a site to the wrong tab, need to undo.

**Steps:**
1. Click the site
2. Set **Force Section** → `AUTO`
3. Save

**Result:** Site returns to automatic routing based on survey_type

---

## ⚠️ Important Notes

### Precedence
**Force Section ALWAYS wins:**
```
section_override > survey_type > survey_required > scout status
```

If `section_override` is set, it ignores all other logic.

### Data Persistence
- Saved to: `survey_routing_data.json` → `section_override` field
- Backend API: `/api/survey-routing/update`
- Persists across refreshes

### Survey Type vs Force Section
**Best Practice:** Set BOTH if needed
- **Survey Type** — Determines vendor requirements (CCTV vs FA)
- **Force Section** — Determines which tab to display in

Example:
- Survey Type: `BOTH` (needs CCTV + FA)
- Force Section: `Awaiting Scout` (not ready yet)

---

## 🔍 How to Check Overrides

### In the UI
1. Click a site → check "Force Section" dropdown
2. If **not** set to "AUTO", it's oridden

### In the JSON
```json
{
  "site": "12345",
  "survey_type": "CCTV",
  "section_override": "cctv"  // ← Override active
}
```

### Clear All Overrides
Currently manual — click each site → set to AUTO → save.
(Future: bulk clear button?)

---

## 🎯 Quick Reference

| Force Section Value | Tab Displayed | Common Use |
|---------------------|---------------|------------|
| `""` (AUTO) | Based on survey_type | Normal operation |
| `cctv` | CCTV Surveys | Manual review decision |
| `fa` | FA/Intrusion | Manual review decision |
| `upgrade` | Both Surveys | Needs both types |
| `nosurvey` | No Survey | Full equipment upgrade |
| `review` | Needs Review | Park for later decision |
| `scout` | Awaiting Scout | Need scout data first |
| `complete` | Complete | Survey finished |

---

## 💡 Pro Tips

### Tip 1: Use AUTO by Default
Only override when automatic routing is wrong or you need manual control.

### Tip 2: Review Tab as Parking
Use "Force Section → Needs Review" to park sites that need executive decision.

### Tip 3: Bulk Workflow
1. Export sites from a tab
2. Make decisions in Excel
3. Re-import and force sections in bulk (future feature)

---

**Status:** ✅ Live and working  
**Last Updated:** 2026-04-27 by Code Puppy 🐶
