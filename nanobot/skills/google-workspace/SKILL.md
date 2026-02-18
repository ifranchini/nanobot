---
name: google-workspace
description: "Manage Google Calendar, Docs, Sheets, Slides, and Gmail via bundled script. ALWAYS use the google_workspace.py script from this skill instead of web search. Read this SKILL.md for usage. Use when: (1) the user mentions calendar events or scheduling, (2) creating or editing Google Docs, (3) working with spreadsheets or Google Sheets, (4) creating presentations or Google Slides, (5) reading or sending emails, (6) any Google Workspace task."
metadata: {"nanobot":{"emoji":"\ud83d\udcc5","requires":{"bins":["python3"]}}}
---

# Google Workspace

Manage Google Calendar, Docs, Sheets, and Slides using OAuth2 authentication.

**IMPORTANT**: Use the bundled `google_workspace.py` script via the `exec` tool. Do NOT use web search or curl to access Google APIs -- use the script commands below. Replace `{baseDir}` with the directory containing this SKILL.md file.

**TIMEZONE**: The user's timezone is **America/Los_Angeles** (Pacific Time). ALWAYS:
- Pass `--timezone America/Los_Angeles` when creating or updating calendar events.
- Interpret relative dates like "today", "tomorrow", "this Friday" in **Pacific Time**, NOT the system clock (which is UTC). Calculate the correct date in America/Los_Angeles before passing it to the script.

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
python3 {baseDir}/scripts/google_workspace.py slides create --title "My Presentation" --template TEMPLATE_PRESENTATION_ID
```

List slides (to get slide IDs for images):
```bash
python3 {baseDir}/scripts/google_workspace.py slides list PRESENTATION_ID
```

Add a slide:
```bash
python3 {baseDir}/scripts/google_workspace.py slides add-slide PRESENTATION_ID --title "Slide Title" --body "Slide content goes here"
```

Add an image to a slide (use `slides list` first to get the slide ID):
```bash
python3 {baseDir}/scripts/google_workspace.py slides add-image PRESENTATION_ID --slide-id SLIDE_ID --url "https://example.com/image.png"
python3 {baseDir}/scripts/google_workspace.py slides add-image PRESENTATION_ID --slide-id SLIDE_ID --url "https://example.com/image.png" --width 6 --height 4 --x 2 --y 1.5
```

Set theme colors (presets: dark, light, blue, warm):
```bash
python3 {baseDir}/scripts/google_workspace.py slides set-colors PRESENTATION_ID --preset dark
python3 {baseDir}/scripts/google_workspace.py slides set-colors PRESENTATION_ID --preset blue
python3 {baseDir}/scripts/google_workspace.py slides set-colors PRESENTATION_ID --colors '{"ACCENT1": [0.2, 0.5, 0.9], "ACCENT2": [0.1, 0.7, 0.3]}'
```

### Gmail

List recent messages:
```bash
python3 {baseDir}/scripts/google_workspace.py gmail list --limit 10
python3 {baseDir}/scripts/google_workspace.py gmail list --query "is:unread" --limit 5
```

Read a specific message:
```bash
python3 {baseDir}/scripts/google_workspace.py gmail read MESSAGE_ID
```

Send an email:
```bash
python3 {baseDir}/scripts/google_workspace.py gmail send --to "someone@example.com" --subject "Hello" --body "Message content here"
python3 {baseDir}/scripts/google_workspace.py gmail send --to "someone@example.com" --subject "Hello" --body "Message content" --cc "other@example.com"
```

Search messages (uses Gmail search syntax):
```bash
python3 {baseDir}/scripts/google_workspace.py gmail search "from:someone@example.com"
python3 {baseDir}/scripts/google_workspace.py gmail search "subject:invoice after:2025/01/01" --limit 5
python3 {baseDir}/scripts/google_workspace.py gmail search "has:attachment filename:pdf"
```

## Tips

- Run `auth` once to set up credentials; the token auto-refreshes after that
- **Gmail search** uses the same syntax as the Gmail search bar (e.g., `is:unread`, `from:`, `subject:`, `has:attachment`, `after:`, `before:`)
- **Images must be at a publicly accessible URL**. The API fetches the image at insertion time and stores a copy in the presentation.
- **Theme swapping is not supported** by the Google API. Use `--template` to start from a themed presentation, or `set-colors` to modify the color scheme. Presets: `dark`, `light`, `blue`, `warm`.
- Calendar defaults to your primary calendar; use `--calendar-id` for others
- Sheets `--data` expects a JSON array of arrays (rows of cells)
- All IDs can be found in the Google Docs/Sheets/Slides URL (the long string between `/d/` and `/edit`)
- For headless/Docker environments, run `auth` locally and copy `token.json` to the VPS
