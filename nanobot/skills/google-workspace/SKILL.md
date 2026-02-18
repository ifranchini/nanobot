---
name: google-workspace
description: "Manage Google Calendar, Docs, Sheets, and Slides via bundled script. ALWAYS use the google_workspace.py script from this skill instead of web search. Read this SKILL.md for usage. Use when: (1) the user mentions calendar events or scheduling, (2) creating or editing Google Docs, (3) working with spreadsheets or Google Sheets, (4) creating presentations or Google Slides, (5) any Google Workspace task."
metadata: {"nanobot":{"emoji":"\ud83d\udcc5","requires":{"bins":["python3"]}}}
---

# Google Workspace

Manage Google Calendar, Docs, Sheets, and Slides using OAuth2 authentication.

**IMPORTANT**: Use the bundled `google_workspace.py` script via the `exec` tool. Do NOT use web search or curl to access Google APIs -- use the script commands below. Replace `{baseDir}` with the directory containing this SKILL.md file.

## Setup

Before first use, the user must set up OAuth2 credentials. See `{baseDir}/references/setup.md` for the full guide.

1. Place `credentials.json` (from Google Cloud Console) in `~/.nanobot/workspace/google-credentials/`
2. Run the auth command:
```bash
python3 {baseDir}/scripts/google_workspace.py auth
```

## Commands

The script is at `{baseDir}/scripts/google_workspace.py` (relative to this SKILL.md file).

### Authentication

```bash
python3 {baseDir}/scripts/google_workspace.py auth
python3 {baseDir}/scripts/google_workspace.py auth --creds-dir /path/to/creds
```

### Calendar

List upcoming events:
```bash
python3 {baseDir}/scripts/google_workspace.py calendar list --days 7
python3 {baseDir}/scripts/google_workspace.py calendar list --start 2025-01-20 --end 2025-01-27
python3 {baseDir}/scripts/google_workspace.py calendar list --calendar-id someone@gmail.com --limit 5
```

Create an event:
```bash
python3 {baseDir}/scripts/google_workspace.py calendar create --title "Team Meeting" --start "2025-01-20 10:00" --end "2025-01-20 11:00"
python3 {baseDir}/scripts/google_workspace.py calendar create --title "Conference" --start 2025-01-20 --end 2025-01-22 --all-day
python3 {baseDir}/scripts/google_workspace.py calendar create --title "Lunch" --start "2025-01-20 12:00" --end "2025-01-20 13:00" --description "At the usual place" --location "123 Main St" --attendees "alice@gmail.com,bob@gmail.com" --timezone "America/New_York"
```

Update an event:
```bash
python3 {baseDir}/scripts/google_workspace.py calendar update EVENT_ID --title "Updated Title" --start "2025-01-20 14:00" --end "2025-01-20 15:00"
```

Delete an event:
```bash
python3 {baseDir}/scripts/google_workspace.py calendar delete EVENT_ID
```

Check for scheduling conflicts:
```bash
python3 {baseDir}/scripts/google_workspace.py calendar conflicts --start "2025-01-20 10:00" --end "2025-01-20 11:00"
```

### Docs

Create a new document:
```bash
python3 {baseDir}/scripts/google_workspace.py docs create --title "My Document"
```

Read document content:
```bash
python3 {baseDir}/scripts/google_workspace.py docs read DOCUMENT_ID
```

Replace document body:
```bash
python3 {baseDir}/scripts/google_workspace.py docs update DOCUMENT_ID --content "New content for the document"
```

Append text to a document:
```bash
python3 {baseDir}/scripts/google_workspace.py docs append DOCUMENT_ID --text "Additional text to append"
```

### Sheets

Create a new spreadsheet:
```bash
python3 {baseDir}/scripts/google_workspace.py sheets create --title "My Spreadsheet"
```

Read a range:
```bash
python3 {baseDir}/scripts/google_workspace.py sheets read SPREADSHEET_ID --range "Sheet1!A1:D10"
```

Write to a range:
```bash
python3 {baseDir}/scripts/google_workspace.py sheets write SPREADSHEET_ID --range "Sheet1!A1" --data '[["Name","Age"],["Alice","30"],["Bob","25"]]'
```

Append rows:
```bash
python3 {baseDir}/scripts/google_workspace.py sheets append SPREADSHEET_ID --range "Sheet1!A1" --data '[["Charlie","35"],["Diana","28"]]'
```

### Slides

Create a new presentation:
```bash
python3 {baseDir}/scripts/google_workspace.py slides create --title "My Presentation"
```

Add a slide:
```bash
python3 {baseDir}/scripts/google_workspace.py slides add-slide PRESENTATION_ID --title "Slide Title" --body "Slide content goes here"
```

## Tips

- Run `auth` once to set up credentials; the token auto-refreshes after that
- Calendar defaults to your primary calendar; use `--calendar-id` for others
- Sheets `--data` expects a JSON array of arrays (rows of cells)
- All IDs can be found in the Google Docs/Sheets/Slides URL (the long string between `/d/` and `/edit`)
- For headless/Docker environments, run `auth` locally and copy `token.json` to the VPS
