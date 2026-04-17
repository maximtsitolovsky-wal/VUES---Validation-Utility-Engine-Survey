# VUES v7.0.0 Release Notes

**Release Date:** 2026-04-17  
**Project Rename:** SiteOwlQA → VUES (Validation Utility Engine Survey)

---

## 🎯 Major Changes

### 1. Project Rebrand
- **New Name:** VUES - Validation Utility Engine Survey
- **Package Name:** `vues` (was `siteowlqa`)
- **Version:** 7.0.0 (major version bump for rebrand)

### 2. Git Repository Migration
- ✅ Migrated from public GitHub to Walmart internal GitHub (gecgithub01.walmart.com)
- ✅ Removed hardcoded Airtable API tokens (security fix)
- ✅ Autopush system configured for new remote
- **New Repo:** https://gecgithub01.walmart.com/vn59j7j/VUES---Validation-Utility-Engine-Survey

### 3. Puppy Pages Update
- **New Page Name:** `vues-validation-utility-engine-survey`
- **New URL:** https://puppy.walmart.com/sharing/vn59j7j/vues-validation-utility-engine-survey
- **Version:** 7 (incremented from previous versions)
- **Access Level:** business

---

## 🔧 Configuration Changes

### Environment Variables
New required environment variables for Scout sync features:
- `SCOUT_AIRTABLE_API_KEY` - Airtable token for Scout table
- `SCOUT_AIRTABLE_BASE_ID` - Base ID (default: appAwgaX89x0JxG3Z)
- `SCOUT_AIRTABLE_TABLE_ID` - Table ID (default: tblC4o9AvVulyxFMk)

### Git Remote
```bash
# Old (public GitHub)
origin  https://github.com/maximtsitolovsky-wal/VUES---Validation-Utility-Engine-Survey.git

# New (Walmart GitHub)
origin  https://gecgithub01.walmart.com/vn59j7j/VUES---Validation-Utility-Engine-Survey
```

---

## 🛡️ Security Improvements

### Removed Hardcoded Secrets
Fixed GitHub push protection violations by moving hardcoded Airtable tokens to environment variables:
- `scripts/scout_completion_sync.py`
- `scripts/scout_completion_sync_com.py`
- `src/siteowlqa/scout_completion_sync_worker.py`
- `src/siteowlqa/scout_sync_worker.py`

---

## 📦 Autopush System

The git autopush system is now fully configured and operational:
- **Script:** `scripts/git_autopush.py`
- **Debounce:** 10 seconds (default)
- **Remote:** origin (Walmart GitHub)
- **Branch:** main
- **Status:** ✅ Active and pushing automatically

### Usage
```bash
# Start autopush watcher (optional - already running)
python scripts/git_autopush.py

# Custom debounce time
python scripts/git_autopush.py --debounce 5

# Dry run mode
python scripts/git_autopush.py --dry-run
```

---

## 📋 Migration Checklist

- [x] Update version to 7.0.0 in `pyproject.toml`
- [x] Rename package from `siteowlqa` to `vues`
- [x] Update display name in banner and README
- [x] Remove hardcoded Airtable tokens
- [x] Switch git remote to Walmart GitHub
- [x] Configure autopush for new remote
- [x] Update puppy pages config with new name
- [x] Push all changes to Walmart GitHub
- [ ] Publish new version to Puppy Pages (run republish script)
- [ ] Update team documentation with new URLs
- [ ] Notify stakeholders of rebrand

---

## 🚀 Next Steps

1. **Publish to Puppy Pages:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\republish_dashboard.ps1
   ```

2. **Verify New URL:**
   Visit: https://puppy.walmart.com/sharing/vn59j7j/vues-validation-utility-engine-survey

3. **Update Team Links:**
   - Update bookmarks
   - Update documentation
   - Update automation scripts that reference old URLs

---

## 🐛 Known Issues

None at this time.

---

## 📞 Support

- **Team:** https://teams.microsoft.com/l/channel/[channel-id]
- **Slack:** https://walmart.enterprise.slack.com/archives/[channel-id]
- **GitHub:** https://gecgithub01.walmart.com/vn59j7j/VUES---Validation-Utility-Engine-Survey

---

**End of Release Notes**
