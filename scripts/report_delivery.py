#!/usr/bin/env python3
"""
Shared report delivery utilities — HTML email + Google Sheets.

Used by both verify_videos.py (daily) and weekly_report.py (weekly).
Graceful failures — prints warnings but never crashes the pipeline.
"""

import json
import os
import re
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from scrapers.utils import load_env_var


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def send_email(subject, html_body, recipient=None, attachments=None):
    """Send an HTML email via Gmail SMTP.

    Args:
        subject: Email subject line.
        html_body: HTML string for the email body.
        recipient: Email address (defaults to GMAIL_SENDER).
        attachments: List of (filename, content_bytes_or_str) tuples.

    Returns True on success, False on failure.
    """
    sender = load_env_var("GMAIL_SENDER")
    password = load_env_var("GMAIL_APP_PASSWORD")
    if not sender or not password:
        print("  Warning: GMAIL_SENDER or GMAIL_APP_PASSWORD not set — skipping email")
        return False

    if not recipient:
        recipient = sender

    msg = MIMEMultipart()
    msg["From"] = f"Local Soundcheck <{sender}>"
    msg["To"] = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    if attachments:
        for filename, content in attachments:
            if isinstance(content, str):
                content = content.encode("utf-8")
            part = MIMEBase("application", "octet-stream")
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        print(f"  Email sent: {subject}")
        return True
    except Exception as e:
        print(f"  Warning: email failed — {e}")
        return False


# ---------------------------------------------------------------------------
# Google Sheets
# ---------------------------------------------------------------------------

def _get_sheets_service():
    """Build an authenticated Google Sheets API service."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("  Warning: google-api-python-client not installed — skipping Sheets")
        return None

    creds_raw = load_env_var("GA4_SERVICE_ACCOUNT")
    if not creds_raw:
        print("  Warning: GA4_SERVICE_ACCOUNT not set — skipping Sheets")
        return None

    if creds_raw.strip().startswith("{"):
        info = json.loads(creds_raw)
    else:
        with open(creds_raw) as f:
            info = json.load(f)

    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=credentials)


def append_to_sheet(rows, tab_name, header=None):
    """Append rows to a named tab in the report spreadsheet.

    Args:
        rows: List of lists (each inner list = one row of cell values).
        tab_name: Sheet tab name (e.g., "Daily Video Reports").
        header: Optional header row (list of strings). Written automatically
                if the tab is empty.

    Returns True on success, False on failure.
    """
    sheet_id = load_env_var("REPORT_SHEETS_ID")
    if not sheet_id:
        print("  Warning: REPORT_SHEETS_ID not set — skipping Sheets")
        return False

    if not rows:
        print("  Warning: no rows to append — skipping Sheets")
        return False

    service = _get_sheets_service()
    if not service:
        return False

    try:
        # Check if the tab is empty and needs a header
        if header:
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f"'{tab_name}'!A1",
            ).execute()
            if not result.get("values"):
                rows = [header] + rows
                print(f"  Sheets: tab '{tab_name}' was empty — adding header row")

        body = {"values": rows}
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        print(f"  Sheets: appended {len(rows)} rows to '{tab_name}'")
        return True
    except Exception as e:
        print(f"  Warning: Sheets append failed — {e}")
        return False


def ensure_definitions_tab():
    """Create and populate a Definitions tab if it doesn't already have content.

    Writes skip reason definitions so the spreadsheet is self-documenting.
    Only writes if the tab is empty (won't overwrite existing content).

    Returns True on success, False on failure.
    """
    sheet_id = load_env_var("REPORT_SHEETS_ID")
    if not sheet_id:
        return False

    service = _get_sheets_service()
    if not service:
        return False

    tab_name = "Definitions"

    definitions = [
        ["Skip Reason", "Definition"],
        ["verified", "Video passed verifier checks (view count, channel analysis, upload date). Assigned to show."],
        ["rejected", "Video failed verifier checks. Removed from show."],
        ["accept", "YouTube search found a video scoring 70+ (gate score). Assigned as candidate."],
        ["flag", "YouTube search found a video scoring 40-69. Assigned but flagged for review."],
        ["reused", "Existing match with high confidence kept from prior run. No new API search needed."],
        ["override", "Manual override from overrides.json — specific video ID or null (no video)."],
        ["skip", "Artist skipped before searching — event name, invalid name, too short, or recently rejected."],
        ["no_results", "YouTube API search ran but returned zero results."],
        ["api_error", "YouTube API or network error — scraper could not reach the API."],
        ["code_error", "Bug in scraper code — unexpected exception during search."],
        ["no_log", "No match log entry found for this artist. Typically a 2nd/3rd opener (only first opener is searched)."],
        [],
        ["Column", "Definition"],
        ["Section", "Report section: Verified (new tonight), Rejected (failed tonight), No Preview (no video assigned). No Preview is split into actionable items (top) and expected items (bottom) separated by a --- row."],
        ["Artist", "Artist or event name as scraped from venue website."],
        ["Role", "headliner or opener."],
        ["Venue", "Venue name."],
        ["Date", "Show date as listed on venue website."],
        ["Video URL", "YouTube video URL (blank for No Preview rows)."],
        ["Detail", "Confidence score (Verified), rejection reasons (Rejected), or status note (No Preview). Items prefixed with NEW appeared for the first time (not in yesterday's report)."],
        ["Skip Reason", "How the scraper/verifier processed this artist. See definitions above."],
        [],
        ["Quality Metric", "Definition"],
        ["Match Confidence", "% of assigned videos scoring 70+ in name matching (audit oEmbed score). Measures name similarity, not true video correctness."],
        ["Coverage", "% of active shows with a video assigned. Excludes expired shows and override-null artists."],
        [],
        ["Report Filters (what is excluded)", ""],
        ["Expired shows", "Shows past their date are excluded from No Preview rows and inventory counts."],
        ["Override-null artists", "Artists with null overrides (events, not bands) are excluded from No Preview rows. Counted separately as Overrides in inventory."],
        [],
        ["No Preview Layout", ""],
        ["Actionable (top)", "Items with skip reasons: flag, no_results, api_error, code_error. These may need review or a manual override."],
        ["--- separator", "Shows count of expected items below. Everything above needs attention, everything below is informational."],
        ["Expected (bottom)", "Items with skip reasons: skip, reused, no_log. Already reviewed or expected to have no video."],
        ["NEW marker", "Appears in Detail column when an artist was NOT in yesterday's No Preview list. Highlights overnight changes for quick triage."],
        [],
        ["Last updated", "2026-03-05"],
    ]

    try:
        # Check if tab exists
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        tab_exists = any(
            s["properties"]["title"] == tab_name
            for s in spreadsheet["sheets"]
        )

        if not tab_exists:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
            ).execute()
            print(f"  Sheets: created '{tab_name}' tab")

        # Check if already populated
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A1",
        ).execute()
        if result.get("values"):
            return True  # Already has content

        # Write definitions
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": definitions},
        ).execute()
        print(f"  Sheets: wrote definitions to '{tab_name}' tab")
        return True
    except Exception as e:
        print(f"  Warning: Definitions tab failed — {e}")
        return False


def sort_sheet(tab_name, sort_specs):
    """Sort all data rows in a sheet tab (preserves header row).

    Args:
        tab_name: Sheet tab name (e.g., "Daily Video Reports").
        sort_specs: List of (column_index, "ASCENDING"|"DESCENDING") tuples.
                    Column indices are 0-based.

    Returns True on success, False on failure.
    """
    sheet_id = load_env_var("REPORT_SHEETS_ID")
    if not sheet_id:
        return False

    service = _get_sheets_service()
    if not service:
        return False

    try:
        # Look up the numeric tab ID
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        tab_id = None
        for sheet in spreadsheet["sheets"]:
            if sheet["properties"]["title"] == tab_name:
                tab_id = sheet["properties"]["sheetId"]
                break
        if tab_id is None:
            print(f"  Warning: tab '{tab_name}' not found — skipping sort")
            return False

        # Get row count to set sort range
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A:A",
        ).execute()
        row_count = len(result.get("values", []))
        if row_count < 3:
            # Need at least header + 2 data rows to sort
            return True

        sort_request = {
            "sortRange": {
                "range": {
                    "sheetId": tab_id,
                    "startRowIndex": 1,  # skip header
                    "endRowIndex": row_count,
                },
                "sortSpecs": [
                    {"dimensionIndex": col, "sortOrder": order}
                    for col, order in sort_specs
                ],
            }
        }
        freeze_request = {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": tab_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [sort_request, freeze_request]},
        ).execute()
        print(f"  Sheets: sorted '{tab_name}' ({row_count - 1} data rows)")
        return True
    except Exception as e:
        print(f"  Warning: Sheets sort failed — {e}")
        return False


# ---------------------------------------------------------------------------
# Markdown → HTML conversion
# ---------------------------------------------------------------------------

# Inline styles (email clients strip <style> blocks)
_STYLE_TABLE = (
    'style="border-collapse:collapse; width:100%; font-family:Arial,sans-serif; font-size:14px;"'
)
_STYLE_TH = (
    'style="background-color:#1a1a2e; color:#ffffff; padding:8px 12px; '
    'text-align:left; border:1px solid #ddd;"'
)
_STYLE_TD = (
    'style="padding:8px 12px; border:1px solid #ddd;"'
)
_STYLE_TD_NUM = (
    'style="padding:8px 12px; border:1px solid #ddd; text-align:right;"'
)
_STYLE_TR_ALT = (
    'style="background-color:#f8f9fa;"'
)
_STYLE_H1 = 'style="color:#1a1a2e; font-family:Arial,sans-serif; margin-bottom:4px;"'
_STYLE_H2 = 'style="color:#1a1a2e; font-family:Arial,sans-serif; margin-top:24px; margin-bottom:8px;"'
_STYLE_BOLD = 'style="font-family:Arial,sans-serif; font-size:14px; margin-bottom:16px;"'
_STYLE_P = 'style="font-family:Arial,sans-serif; font-size:14px;"'


def _is_numeric(text):
    """Check if text looks like a number or percentage."""
    cleaned = text.strip().rstrip("%").replace(",", "").replace("+", "").replace("-", "")
    if not cleaned:
        return False
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def _md_table_to_html(lines):
    """Convert markdown table lines to an HTML table string."""
    if len(lines) < 2:
        return ""

    header_cells = [c.strip() for c in lines[0].strip("|").split("|")]
    # Skip separator line (lines[1])
    data_lines = lines[2:]

    html = [f"<table {_STYLE_TABLE}>", "<thead><tr>"]
    for cell in header_cells:
        html.append(f"  <th {_STYLE_TH}>{cell}</th>")
    html.append("</tr></thead>")
    html.append("<tbody>")

    for i, line in enumerate(data_lines):
        cells = [c.strip() for c in line.strip("|").split("|")]
        row_style = _STYLE_TR_ALT if i % 2 == 1 else ""
        html.append(f"<tr {row_style}>")
        for cell in cells:
            td_style = _STYLE_TD_NUM if _is_numeric(cell) else _STYLE_TD
            # Convert markdown bold
            cell = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", cell)
            html.append(f"  <td {td_style}>{cell}</td>")
        html.append("</tr>")

    html.append("</tbody></table>")
    return "\n".join(html)


def markdown_to_html(markdown_text):
    """Convert a markdown report to styled HTML for email.

    Handles: # headings, ## headings, **bold** lines, tables, plain text.
    """
    lines = markdown_text.split("\n")
    html_parts = []
    table_buffer = []
    in_table = False

    def flush_table():
        nonlocal in_table
        if table_buffer:
            html_parts.append(_md_table_to_html(table_buffer))
            table_buffer.clear()
        in_table = False

    for line in lines:
        stripped = line.strip()

        # Detect table lines (start with |)
        if stripped.startswith("|"):
            # Skip separator-only lines for detection
            is_separator = bool(re.match(r"^\|[-| :]+\|$", stripped))
            if not in_table and is_separator:
                # This is the separator after a header we already buffered
                table_buffer.append(stripped)
                continue
            in_table = True
            table_buffer.append(stripped)
            continue
        else:
            if in_table:
                flush_table()

        # Headings
        if stripped.startswith("# "):
            html_parts.append(f'<h1 {_STYLE_H1}>{stripped[2:]}</h1>')
        elif stripped.startswith("## "):
            html_parts.append(f'<h2 {_STYLE_H2}>{stripped[3:]}</h2>')
        elif stripped.startswith("### "):
            html_parts.append(f'<h3 {_STYLE_H2}>{stripped[4:]}</h3>')
        elif stripped.startswith("**") and stripped.endswith("**"):
            html_parts.append(f'<p {_STYLE_BOLD}><strong>{stripped[2:-2]}</strong></p>')
        elif stripped:
            # Convert inline bold
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
            html_parts.append(f'<p {_STYLE_P}>{text}</p>')
        # Skip blank lines (spacing handled by margins)

    # Flush any trailing table
    if table_buffer:
        flush_table()

    return "\n".join(html_parts)


def monospace_to_html(text):
    """Convert a monospace text report (like weekly analytics) to styled HTML.

    Detects ASCII tables (lines with | delimiters and - separators) and
    converts them. Other lines become styled paragraphs.
    """
    lines = text.split("\n")
    html_parts = []
    table_buffer = []
    in_table = False

    def flush_table():
        nonlocal in_table
        if not table_buffer:
            in_table = False
            return

        # Parse ASCII table: header, separator, data rows
        header_line = table_buffer[0]
        sep_line = table_buffer[1] if len(table_buffer) > 1 else ""
        data_lines = table_buffer[2:] if len(table_buffer) > 2 else []

        # Split on | for columns
        header_cells = [c.strip() for c in header_line.split("|") if c.strip()]

        html = [f"<table {_STYLE_TABLE}>", "<thead><tr>"]
        for cell in header_cells:
            html.append(f"  <th {_STYLE_TH}>{cell}</th>")
        html.append("</tr></thead>")
        html.append("<tbody>")

        for i, dline in enumerate(data_lines):
            # Check if this is another separator (totals separator)
            if set(dline.strip()) <= set("-+| "):
                continue
            cells = [c.strip() for c in dline.split("|") if c.strip()]
            row_style = _STYLE_TR_ALT if i % 2 == 1 else ""
            is_total = any("TOTAL" in c.upper() for c in cells)
            html.append(f"<tr {row_style}>")
            for cell in cells:
                td_style = _STYLE_TD_NUM if _is_numeric(cell) else _STYLE_TD
                if is_total:
                    cell = f"<strong>{cell}</strong>"
                html.append(f"  <td {td_style}>{cell}</td>")
            html.append("</tr>")

        html.append("</tbody></table>")
        html_parts.append("\n".join(html))
        table_buffer.clear()
        in_table = False

    for line in lines:
        stripped = line.strip()

        # Detect ASCII table lines (contain | as column separator)
        has_pipe = "|" in stripped and not stripped.startswith("Generated:")
        is_separator = bool(re.match(r"^[-+|: ]+$", stripped)) and len(stripped) > 5

        if has_pipe and not is_separator:
            if not in_table:
                in_table = True
            table_buffer.append(stripped)
            continue
        elif is_separator and in_table:
            table_buffer.append(stripped)
            continue
        else:
            if in_table:
                flush_table()

        # Section headers (ALL CAPS lines)
        if stripped and stripped == stripped.upper() and len(stripped) > 3 and stripped.isalpha():
            html_parts.append(f'<h2 {_STYLE_H2}>{stripped}</h2>')
        elif stripped.startswith("LOCAL SOUNDCHECK"):
            html_parts.append(f'<h1 {_STYLE_H1}>{stripped}</h1>')
        elif stripped and not is_separator:
            text = stripped
            # Highlight percentages and changes
            text = re.sub(r"\+(\d+%)", r'<span style="color:#28a745;">+\1</span>', text)
            text = re.sub(r"(-\d+%)", r'<span style="color:#dc3545;">\1</span>', text)
            html_parts.append(f'<p {_STYLE_P}>{text}</p>')

    if table_buffer:
        flush_table()

    return "\n".join(html_parts)


def wrap_html_email(body_html, footer_text=None):
    """Wrap HTML content in a full email template."""
    footer = ""
    if footer_text:
        footer = f'<p style="font-family:Arial,sans-serif; font-size:12px; color:#666; margin-top:24px; border-top:1px solid #eee; padding-top:12px;">{footer_text}</p>'

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:20px; background-color:#f5f5f5;">
<div style="max-width:700px; margin:0 auto; background:#ffffff; padding:24px; border-radius:8px;">
{body_html}
{footer}
</div>
</body>
</html>"""
