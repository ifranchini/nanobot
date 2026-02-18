#!/usr/bin/env python3
"""Google Workspace integration: Calendar, Docs, Sheets, Slides via OAuth2."""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

DEFAULT_CREDS_DIR = os.path.expanduser("~/.nanobot/workspace/google-credentials")

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive.file",
]


def _get_creds_dir(args) -> str:
    return getattr(args, "creds_dir", None) or DEFAULT_CREDS_DIR


def _load_credentials(args):
    """Load and return valid Google OAuth2 credentials."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        print(
            "Error: Google auth libraries not installed.\n"
            "Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib",
            file=sys.stderr,
        )
        sys.exit(1)

    creds_dir = _get_creds_dir(args)
    token_path = os.path.join(creds_dir, "token.json")

    if not os.path.exists(token_path):
        print(
            f"Error: No token found at {token_path}\nRun the 'auth' command first to authenticate.",
            file=sys.stderr,
        )
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        except Exception as e:
            print(
                f"Error: Failed to refresh token: {e}\nDelete token.json and run 'auth' again.",
                file=sys.stderr,
            )
            sys.exit(1)

    if not creds.valid:
        print(
            "Error: Token is invalid. Delete token.json and run 'auth' again.",
            file=sys.stderr,
        )
        sys.exit(1)

    return creds


def _build_service(args, service_name: str, version: str):
    """Build a Google API service client."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        print(
            "Error: google-api-python-client not installed.\n"
            "Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib",
            file=sys.stderr,
        )
        sys.exit(1)

    creds = _load_credentials(args)
    return build(service_name, version, credentials=creds)


def _handle_api_error(e):
    """Handle Google API errors with user-friendly messages."""
    try:
        from googleapiclient.errors import HttpError

        if isinstance(e, HttpError):
            status = e.resp.status
            if status == 401:
                print(
                    "Error: Authentication expired. Run 'auth' command again.",
                    file=sys.stderr,
                )
            elif status == 403:
                print(
                    "Error: Permission denied. Check that you have access to this resource.",
                    file=sys.stderr,
                )
            elif status == 404:
                print("Error: Resource not found. Check the ID and try again.", file=sys.stderr)
            elif status == 409:
                print("Error: Conflict. The resource may have been modified.", file=sys.stderr)
            elif status == 429:
                print("Error: Rate limited. Try again in a moment.", file=sys.stderr)
            else:
                print(f"Error: Google API returned HTTP {status}: {e}", file=sys.stderr)
            sys.exit(1)
    except ImportError:
        pass
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)


# ── Auth ─────────────────────────────────────────────────────────────────


def cmd_auth(args):
    """Authenticate with Google and save token."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print(
            "Error: google-auth-oauthlib not installed.\n"
            "Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib",
            file=sys.stderr,
        )
        sys.exit(1)

    creds_dir = _get_creds_dir(args)
    creds_path = os.path.join(creds_dir, "credentials.json")
    token_path = os.path.join(creds_dir, "token.json")

    if not os.path.exists(creds_path):
        print(
            f"Error: credentials.json not found at {creds_path}\n"
            "Download it from Google Cloud Console and place it there.\n"
            "See the setup guide for instructions.",
            file=sys.stderr,
        )
        sys.exit(1)

    os.makedirs(creds_dir, exist_ok=True)

    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)

    try:
        creds = flow.run_local_server(port=0)
    except OSError:
        # Fallback for headless environments
        print("Browser-based auth not available. Use the URL below to authorize:")
        creds = flow.run_console()

    with open(token_path, "w") as f:
        f.write(creds.to_json())

    print(f"Authentication successful! Token saved to {token_path}")


# ── Calendar ─────────────────────────────────────────────────────────────


def cmd_calendar_list(args):
    """List calendar events."""
    service = _build_service(args, "calendar", "v3")
    calendar_id = args.calendar_id or "primary"

    if args.start:
        time_min = datetime.fromisoformat(args.start).astimezone(timezone.utc).isoformat()
    else:
        time_min = datetime.now(timezone.utc).isoformat()

    if args.end:
        time_max = datetime.fromisoformat(args.end).astimezone(timezone.utc).isoformat()
    else:
        days = args.days or 7
        time_max = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    try:
        result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=args.limit,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except Exception as e:
        _handle_api_error(e)

    events = result.get("items", [])
    if not events:
        print("No events found.")
        return

    print(f"Found {len(events)} event(s):\n")
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date", ""))
        end = event["end"].get("dateTime", event["end"].get("date", ""))
        summary = event.get("summary", "(No title)")
        event_id = event["id"]

        # Format datetime for display
        if "T" in start:
            start_dt = datetime.fromisoformat(start)
            start_display = start_dt.strftime("%Y-%m-%d %H:%M")
            end_dt = datetime.fromisoformat(end)
            end_display = end_dt.strftime("%H:%M")
            time_str = f"{start_display} - {end_display}"
        else:
            time_str = f"{start} (all day)"

        print(f"- **{summary}**")
        print(f"  {time_str}")

        if event.get("location"):
            print(f"  Location: {event['location']}")
        if event.get("description"):
            desc = event["description"]
            if len(desc) > 100:
                desc = desc[:100] + "..."
            print(f"  Description: {desc}")

        attendees = event.get("attendees", [])
        if attendees:
            names = [a.get("email", "") for a in attendees[:5]]
            if len(attendees) > 5:
                names.append(f"+{len(attendees) - 5} more")
            print(f"  Attendees: {', '.join(names)}")

        print(f"  ID: {event_id}")
        print()


def cmd_calendar_create(args):
    """Create a calendar event."""
    service = _build_service(args, "calendar", "v3")

    event_body = {"summary": args.title}

    if args.description:
        event_body["description"] = args.description
    if args.location:
        event_body["location"] = args.location

    tz = args.timezone or "UTC"

    if args.all_day:
        event_body["start"] = {"date": args.start[:10]}
        event_body["end"] = {"date": args.end[:10] if args.end else args.start[:10]}
    else:
        start_dt = datetime.fromisoformat(args.start)
        event_body["start"] = {"dateTime": start_dt.isoformat(), "timeZone": tz}
        if args.end:
            end_dt = datetime.fromisoformat(args.end)
            event_body["end"] = {"dateTime": end_dt.isoformat(), "timeZone": tz}
        else:
            end_dt = start_dt + timedelta(hours=1)
            event_body["end"] = {"dateTime": end_dt.isoformat(), "timeZone": tz}

    if args.attendees:
        event_body["attendees"] = [{"email": e.strip()} for e in args.attendees.split(",")]

    try:
        event = service.events().insert(calendarId="primary", body=event_body).execute()
    except Exception as e:
        _handle_api_error(e)

    print(f"Event created: **{event.get('summary')}**")
    print(f"ID: {event['id']}")
    if event.get("htmlLink"):
        print(f"Link: {event['htmlLink']}")


def cmd_calendar_update(args):
    """Update a calendar event."""
    service = _build_service(args, "calendar", "v3")

    try:
        event = service.events().get(calendarId="primary", eventId=args.event_id).execute()
    except Exception as e:
        _handle_api_error(e)

    if args.title:
        event["summary"] = args.title
    if args.description:
        event["description"] = args.description
    if args.location:
        event["location"] = args.location

    if args.start:
        start_dt = datetime.fromisoformat(args.start)
        if "date" in event["start"] and "dateTime" not in event["start"]:
            event["start"] = {"date": args.start[:10]}
        else:
            tz = event["start"].get("timeZone", "UTC")
            event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": tz}

    if args.end:
        end_dt = datetime.fromisoformat(args.end)
        if "date" in event["end"] and "dateTime" not in event["end"]:
            event["end"] = {"date": args.end[:10]}
        else:
            tz = event["end"].get("timeZone", "UTC")
            event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": tz}

    try:
        updated = (
            service.events()
            .update(calendarId="primary", eventId=args.event_id, body=event)
            .execute()
        )
    except Exception as e:
        _handle_api_error(e)

    print(f"Event updated: **{updated.get('summary')}**")
    print(f"ID: {updated['id']}")


def cmd_calendar_delete(args):
    """Delete a calendar event."""
    service = _build_service(args, "calendar", "v3")

    try:
        service.events().delete(calendarId="primary", eventId=args.event_id).execute()
    except Exception as e:
        _handle_api_error(e)

    print(f"Event deleted: {args.event_id}")


def cmd_calendar_conflicts(args):
    """Check for scheduling conflicts in a time range."""
    service = _build_service(args, "calendar", "v3")

    start_dt = datetime.fromisoformat(args.start).astimezone(timezone.utc)
    end_dt = datetime.fromisoformat(args.end).astimezone(timezone.utc)

    try:
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except Exception as e:
        _handle_api_error(e)

    events = result.get("items", [])
    if not events:
        print(f"No conflicts found between {args.start} and {args.end}.")
        return

    print(f"Found {len(events)} conflicting event(s):\n")
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date", ""))
        summary = event.get("summary", "(No title)")
        print(f"- **{summary}** at {start}")


# ── Docs ─────────────────────────────────────────────────────────────────


def cmd_docs_create(args):
    """Create a new Google Doc."""
    service = _build_service(args, "docs", "v1")

    try:
        doc = service.documents().create(body={"title": args.title}).execute()
    except Exception as e:
        _handle_api_error(e)

    doc_id = doc["documentId"]
    print(f"Document created: **{args.title}**")
    print(f"ID: {doc_id}")
    print(f"Link: https://docs.google.com/document/d/{doc_id}/edit")


def cmd_docs_read(args):
    """Read a Google Doc's content."""
    service = _build_service(args, "docs", "v1")

    try:
        doc = service.documents().get(documentId=args.doc_id).execute()
    except Exception as e:
        _handle_api_error(e)

    title = doc.get("title", "Untitled")
    print(f"# {title}\n")

    content = doc.get("body", {}).get("content", [])
    for element in content:
        paragraph = element.get("paragraph")
        if not paragraph:
            continue

        text_parts = []
        for elem in paragraph.get("elements", []):
            text_run = elem.get("textRun")
            if text_run:
                text_parts.append(text_run.get("content", ""))

        line = "".join(text_parts)
        if line.strip():
            print(line, end="")

    print()


def cmd_docs_update(args):
    """Replace the body of a Google Doc."""
    service = _build_service(args, "docs", "v1")

    # Get the document to find content length
    try:
        doc = service.documents().get(documentId=args.doc_id).execute()
    except Exception as e:
        _handle_api_error(e)

    # Calculate end index (document body starts at index 1)
    content = doc.get("body", {}).get("content", [])
    end_index = 1
    for element in content:
        if "endIndex" in element:
            end_index = max(end_index, element["endIndex"])

    requests = []
    # Delete existing content (if any beyond the initial newline)
    if end_index > 2:
        requests.append(
            {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}}
        )

    # Insert new content
    requests.append({"insertText": {"location": {"index": 1}, "text": args.content}})

    try:
        service.documents().batchUpdate(
            documentId=args.doc_id, body={"requests": requests}
        ).execute()
    except Exception as e:
        _handle_api_error(e)

    print(f"Document updated: {args.doc_id}")


def cmd_docs_append(args):
    """Append text to a Google Doc."""
    service = _build_service(args, "docs", "v1")

    # Get end index
    try:
        doc = service.documents().get(documentId=args.doc_id).execute()
    except Exception as e:
        _handle_api_error(e)

    content = doc.get("body", {}).get("content", [])
    end_index = 1
    for element in content:
        if "endIndex" in element:
            end_index = max(end_index, element["endIndex"])

    # Insert at end (before the trailing newline)
    insert_index = max(1, end_index - 1)

    try:
        service.documents().batchUpdate(
            documentId=args.doc_id,
            body={
                "requests": [
                    {"insertText": {"location": {"index": insert_index}, "text": args.text}}
                ]
            },
        ).execute()
    except Exception as e:
        _handle_api_error(e)

    print(f"Text appended to document: {args.doc_id}")


# ── Sheets ───────────────────────────────────────────────────────────────


def cmd_sheets_create(args):
    """Create a new Google Spreadsheet."""
    service = _build_service(args, "sheets", "v4")

    try:
        spreadsheet = (
            service.spreadsheets().create(body={"properties": {"title": args.title}}).execute()
        )
    except Exception as e:
        _handle_api_error(e)

    ss_id = spreadsheet["spreadsheetId"]
    print(f"Spreadsheet created: **{args.title}**")
    print(f"ID: {ss_id}")
    print(f"Link: https://docs.google.com/spreadsheets/d/{ss_id}/edit")


def cmd_sheets_read(args):
    """Read a range from a Google Spreadsheet."""
    service = _build_service(args, "sheets", "v4")
    range_str = args.range or "Sheet1"

    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=args.spreadsheet_id, range=range_str)
            .execute()
        )
    except Exception as e:
        _handle_api_error(e)

    values = result.get("values", [])
    if not values:
        print("No data found.")
        return

    # Calculate column widths for table formatting
    col_count = max(len(row) for row in values)
    col_widths = [0] * col_count
    for row in values:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print as markdown table
    for row_idx, row in enumerate(values):
        padded = [
            str(row[i]).ljust(col_widths[i]) if i < len(row) else " " * col_widths[i]
            for i in range(col_count)
        ]
        print("| " + " | ".join(padded) + " |")
        if row_idx == 0:
            print("| " + " | ".join("-" * w for w in col_widths) + " |")


def cmd_sheets_write(args):
    """Write data to a range in a Google Spreadsheet."""
    service = _build_service(args, "sheets", "v4")

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON data: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=args.spreadsheet_id,
                range=args.range,
                valueInputOption="USER_ENTERED",
                body={"values": data},
            )
            .execute()
        )
    except Exception as e:
        _handle_api_error(e)

    updated = result.get("updatedCells", 0)
    print(f"Written {updated} cell(s) to {args.range}")


def cmd_sheets_append(args):
    """Append rows to a Google Spreadsheet."""
    service = _build_service(args, "sheets", "v4")

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON data: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=args.spreadsheet_id,
                range=args.range,
                valueInputOption="USER_ENTERED",
                body={"values": data},
            )
            .execute()
        )
    except Exception as e:
        _handle_api_error(e)

    updates = result.get("updates", {})
    updated = updates.get("updatedCells", 0)
    print(f"Appended {updated} cell(s)")


# ── Slides ───────────────────────────────────────────────────────────────


def cmd_slides_create(args):
    """Create a new Google Slides presentation."""
    service = _build_service(args, "slides", "v1")

    try:
        presentation = service.presentations().create(body={"title": args.title}).execute()
    except Exception as e:
        _handle_api_error(e)

    pres_id = presentation["presentationId"]
    print(f"Presentation created: **{args.title}**")
    print(f"ID: {pres_id}")
    print(f"Link: https://docs.google.com/presentation/d/{pres_id}/edit")


def cmd_slides_add_slide(args):
    """Add a slide to a Google Slides presentation."""
    import uuid

    service = _build_service(args, "slides", "v1")

    slide_id = f"slide_{uuid.uuid4().hex[:8]}"
    title_id = f"title_{uuid.uuid4().hex[:8]}"
    body_id = f"body_{uuid.uuid4().hex[:8]}"

    requests = [
        {
            "createSlide": {
                "objectId": slide_id,
                "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
                "placeholderIdMappings": [
                    {
                        "layoutPlaceholder": {"type": "TITLE", "index": 0},
                        "objectId": title_id,
                    },
                    {
                        "layoutPlaceholder": {"type": "BODY", "index": 0},
                        "objectId": body_id,
                    },
                ],
            }
        }
    ]

    if args.title:
        requests.append(
            {
                "insertText": {
                    "objectId": title_id,
                    "text": args.title,
                    "insertionIndex": 0,
                }
            }
        )

    if args.body:
        requests.append(
            {
                "insertText": {
                    "objectId": body_id,
                    "text": args.body,
                    "insertionIndex": 0,
                }
            }
        )

    try:
        service.presentations().batchUpdate(
            presentationId=args.presentation_id,
            body={"requests": requests},
        ).execute()
    except Exception as e:
        _handle_api_error(e)

    print(f"Slide added to presentation: {args.presentation_id}")
    print(f"Slide ID: {slide_id}")


# ── CLI ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Google Workspace: Calendar, Docs, Sheets, Slides")
    parser.add_argument(
        "--creds-dir",
        help=f"Credentials directory (default: {DEFAULT_CREDS_DIR})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── auth ──
    subparsers.add_parser("auth", help="Authenticate with Google OAuth2")

    # ── calendar ──
    cal_parser = subparsers.add_parser("calendar", help="Google Calendar operations")
    cal_sub = cal_parser.add_subparsers(dest="action", required=True)

    # calendar list
    p = cal_sub.add_parser("list", help="List upcoming events")
    p.add_argument("--days", type=int, default=7, help="Number of days to look ahead")
    p.add_argument("--start", help="Start date/time (ISO format)")
    p.add_argument("--end", help="End date/time (ISO format)")
    p.add_argument("--calendar-id", help="Calendar ID (default: primary)")
    p.add_argument("--limit", type=int, default=25, help="Max events to return")

    # calendar create
    p = cal_sub.add_parser("create", help="Create a new event")
    p.add_argument("--title", required=True, help="Event title")
    p.add_argument("--start", required=True, help="Start date/time (ISO format)")
    p.add_argument("--end", help="End date/time (ISO format)")
    p.add_argument("--description", help="Event description")
    p.add_argument("--location", help="Event location")
    p.add_argument("--all-day", action="store_true", help="Create an all-day event")
    p.add_argument("--attendees", help="Comma-separated email addresses")
    p.add_argument("--timezone", help="Timezone (e.g., America/New_York)")

    # calendar update
    p = cal_sub.add_parser("update", help="Update an existing event")
    p.add_argument("event_id", help="Event ID")
    p.add_argument("--title", help="New title")
    p.add_argument("--start", help="New start date/time")
    p.add_argument("--end", help="New end date/time")
    p.add_argument("--description", help="New description")
    p.add_argument("--location", help="New location")

    # calendar delete
    p = cal_sub.add_parser("delete", help="Delete an event")
    p.add_argument("event_id", help="Event ID")

    # calendar conflicts
    p = cal_sub.add_parser("conflicts", help="Check for scheduling conflicts")
    p.add_argument("--start", required=True, help="Start date/time (ISO format)")
    p.add_argument("--end", required=True, help="End date/time (ISO format)")

    # ── docs ──
    docs_parser = subparsers.add_parser("docs", help="Google Docs operations")
    docs_sub = docs_parser.add_subparsers(dest="action", required=True)

    # docs create
    p = docs_sub.add_parser("create", help="Create a new document")
    p.add_argument("--title", required=True, help="Document title")

    # docs read
    p = docs_sub.add_parser("read", help="Read document content")
    p.add_argument("doc_id", help="Document ID")

    # docs update
    p = docs_sub.add_parser("update", help="Replace document body")
    p.add_argument("doc_id", help="Document ID")
    p.add_argument("--content", required=True, help="New content")

    # docs append
    p = docs_sub.add_parser("append", help="Append text to document")
    p.add_argument("doc_id", help="Document ID")
    p.add_argument("--text", required=True, help="Text to append")

    # ── sheets ──
    sheets_parser = subparsers.add_parser("sheets", help="Google Sheets operations")
    sheets_sub = sheets_parser.add_subparsers(dest="action", required=True)

    # sheets create
    p = sheets_sub.add_parser("create", help="Create a new spreadsheet")
    p.add_argument("--title", required=True, help="Spreadsheet title")

    # sheets read
    p = sheets_sub.add_parser("read", help="Read a range")
    p.add_argument("spreadsheet_id", help="Spreadsheet ID")
    p.add_argument("--range", default="Sheet1", help="Range (e.g., Sheet1!A1:D10)")

    # sheets write
    p = sheets_sub.add_parser("write", help="Write to a range")
    p.add_argument("spreadsheet_id", help="Spreadsheet ID")
    p.add_argument("--range", required=True, help="Range (e.g., Sheet1!A1)")
    p.add_argument("--data", required=True, help="JSON array of arrays")

    # sheets append
    p = sheets_sub.add_parser("append", help="Append rows")
    p.add_argument("spreadsheet_id", help="Spreadsheet ID")
    p.add_argument("--range", required=True, help="Range (e.g., Sheet1!A1)")
    p.add_argument("--data", required=True, help="JSON array of arrays")

    # ── slides ──
    slides_parser = subparsers.add_parser("slides", help="Google Slides operations")
    slides_sub = slides_parser.add_subparsers(dest="action", required=True)

    # slides create
    p = slides_sub.add_parser("create", help="Create a new presentation")
    p.add_argument("--title", required=True, help="Presentation title")

    # slides add-slide
    p = slides_sub.add_parser("add-slide", help="Add a slide")
    p.add_argument("presentation_id", help="Presentation ID")
    p.add_argument("--title", help="Slide title")
    p.add_argument("--body", help="Slide body text")

    args = parser.parse_args()

    # Route to command handler
    if args.command == "auth":
        cmd_auth(args)
    elif args.command == "calendar":
        handlers = {
            "list": cmd_calendar_list,
            "create": cmd_calendar_create,
            "update": cmd_calendar_update,
            "delete": cmd_calendar_delete,
            "conflicts": cmd_calendar_conflicts,
        }
        handlers[args.action](args)
    elif args.command == "docs":
        handlers = {
            "create": cmd_docs_create,
            "read": cmd_docs_read,
            "update": cmd_docs_update,
            "append": cmd_docs_append,
        }
        handlers[args.action](args)
    elif args.command == "sheets":
        handlers = {
            "create": cmd_sheets_create,
            "read": cmd_sheets_read,
            "write": cmd_sheets_write,
            "append": cmd_sheets_append,
        }
        handlers[args.action](args)
    elif args.command == "slides":
        handlers = {
            "create": cmd_slides_create,
            "add-slide": cmd_slides_add_slide,
        }
        handlers[args.action](args)


if __name__ == "__main__":
    main()
