# GitHub Issues - jt196/tradebacklinks

**AUTO-GENERATED DOCUMENTATION** - Do not edit manually

Last synced: 2026-01-20T10:14:07.991321Z

Total issues: 17

## Quick Stats

- **Open:** 17
- **Closed:** 0
- **Total:** 17

**Labels:** Emails, enhancement

## All Issues

| # | Title | State | Labels | Assignees | Comments | Updated |
|---|-------|-------|--------|-----------|----------|---------|
| [51](51.md) | No OG image for Homepage | 🟢 OPEN | - | jt196 | 1 | 1/7/2026 |
| [47](47.md) | No guard or response if email already exists | 🟢 OPEN | - | - | 0 | 12/20/2025 |
| [45](45.md) | Prettier emails | 🟢 OPEN | Emails | - | 0 | 1/14/2026 |
| [39](39.md) | Email header/footer templates | 🟢 OPEN | Emails | - | 0 | 12/19/2025 |
| [38](38.md) | Mail improvements | 🟢 OPEN | Emails | - | 0 | 12/19/2025 |
| [35](35.md) | Hide the Postmark domain fix away | 🟢 OPEN | - | - | 0 | 1/16/2026 |
| [34](34.md) | When click to add an excluded domain it just ads it to my keywords. | 🟢 OPEN | - | - | 0 | 12/16/2025 |
| [25](25.md) | Oblige customers to enter card details | 🟢 OPEN | - | jt196 | 0 | 11/25/2025 |
| [24](24.md) | Email confirmation | 🟢 OPEN | enhancement, Emails | - | 0 | 12/19/2025 |
| [15](15.md) | Help section / docs | 🟢 OPEN | - | jt196 | 0 | 11/10/2025 |
| [14](14.md) | GDPR | 🟢 OPEN | - | jt196 | 0 | 11/10/2025 |
| [13](13.md) | Internal Chatbot - customer service | 🟢 OPEN | - | jt196 | 0 | 11/10/2025 |
| [12](12.md) | jamestorr Twitter campaign... | 🟢 OPEN | - | jt196 | 0 | 11/10/2025 |
| [11](11.md) | Email response shuts down compensation plan | 🟢 OPEN | Emails | jt196 | 0 | 12/19/2025 |
| [10](10.md) | Use the user settings to generate the emails | 🟢 OPEN | - | jt196 | 0 | 11/10/2025 |
| [9](9.md) | Autoblogging | 🟢 OPEN | - | jt196 | 0 | 11/10/2025 |
| [7](7.md) | Domain monitoring subscription button | 🟢 OPEN | - | jt196 | 0 | 11/10/2025 |

---

## Open Issues

### Black Friday

- [#25](25.md): Oblige customers to enter card details 

### No Milestone

- [#51](51.md): No OG image for Homepage 
- [#47](47.md): No guard or response if email already exists 
- [#45](45.md): Prettier emails `Emails`
- [#39](39.md): Email header/footer templates `Emails`
- [#38](38.md): Mail improvements `Emails`
- [#35](35.md): Hide the Postmark domain fix away 
- [#34](34.md): When click to add an excluded domain it just ads it to my keywords. 
- [#24](24.md): Email confirmation `enhancement` `Emails`
- [#15](15.md): Help section / docs 
- [#14](14.md): GDPR 
- [#13](13.md): Internal Chatbot - customer service 
- [#12](12.md): jamestorr Twitter campaign... 
- [#11](11.md): Email response shuts down compensation plan `Emails`
- [#10](10.md): Use the user settings to generate the emails 
- [#9](9.md): Autoblogging 
- [#7](7.md): Domain monitoring subscription button 

---

## Usage with Claude

### Reading Issues

```bash
# Read a specific issue
cat issues/33.md

# View all open issues
cat issues/README.md
```

### Working on an Issue

1. Read the issue file: `issues/{number}.md`
2. View screenshots (images are in `issues/images/`)
3. Create a branch: `git checkout -b issue-{number}-description`
4. Implement changes
5. Reference issue in commit: `Fixes #{number}: Description`

### Syncing Issues

```bash
# Sync issues from GitHub
python sync_issues.py

# Force re-download all images
python sync_issues.py --force-images

# Preview changes without writing
python sync_issues.py --dry-run
```
