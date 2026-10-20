"""
EVA v2 status report generator (demo).

Reads a JIRA CSV export and meeting notes, asks Claude (Anthropic API) for an
executive summary plus a per-workstream status, then:
  - prints a color-coded table in the terminal
  - saves a color-coded HTML report and opens it in the browser

Status colors:  High risk = Red | Medium risk = Yellow | On track = Green

Usage (PowerShell, from this folder):
    python status_report.py jira_export_EVA_v2.csv meeting_notes_EVA_v2.txt

The output is a DRAFT. A person checks every owner, date and status
against the source before anything is sent.
"""

import html
import json
import os
import sys
import webbrowser
from datetime import date
from pathlib import Path

import anthropic

try:  # load ANTHROPIC_API_KEY from a .env file if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Use the same model you use in your other scripts; override with ANTHROPIC_MODEL.
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

SYSTEM_PROMPT = (
    "You are an assistant to a Technical Program Manager. "
    "Use ONLY the facts in the JIRA export and the meeting notes. "
    "Never invent owners, dates or numbers. If an owner or date is missing, write 'TBD'. "
    "Always cite JIRA keys. Respond with valid JSON only - no markdown, no code fences."
)

TASK_PROMPT = """Create a status report for the Edge Video Analytics v2 release (GA target Nov 20, 2026).

Return JSON in exactly this shape:
{{
  "executive_summary": "3-4 sentences for the VP: overall health, the biggest risk, and the decision needed",
  "workstreams": [
    {{
      "workstream": "team or area name",
      "status": "High risk" | "Medium risk" | "On track",
      "summary": "one short sentence on where it stands",
      "owner": "name or TBD",
      "due": "date from the source or TBD",
      "jira": "JIRA keys, comma separated",
      "next_step": "one short action"
    }}
  ],
  "decisions_needed": ["short decision 1", "short decision 2"]
}}

Status rules:
- "High risk": blocked, or likely to miss its date without a decision or escalation
- "Medium risk": open issue or dependency, with a plan, date still achievable
- "On track": progressing as planned

Include one row per workstream (AI Models, MLOps, Edge Platform, Cloud Video Platform, Security, QA, Program/Pilot).
Sort rows: High risk first, then Medium risk, then On track.

=== JIRA EXPORT (CSV) ===
{jira}

=== MEETING NOTES ===
{notes}
"""

COLORS = {  # status -> (HTML background, HTML text, ANSI terminal color)
    "High risk": ("#f8d7da", "#842029", "\033[41;97m"),
    "Medium risk": ("#fff3cd", "#664d03", "\033[43;30m"),
    "On track": ("#d1e7dd", "#0f5132", "\033[42;30m"),
}
RESET = "\033[0m"


def ask_claude(jira: str, notes: str) -> dict:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": TASK_PROMPT.format(jira=jira, notes=notes)}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):  # strip code fences if the model adds them anyway
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


def print_terminal(report: dict) -> None:
    print("\nEXECUTIVE SUMMARY")
    print(report["executive_summary"])
    print("\nWORKSTREAM STATUS")
    for row in report["workstreams"]:
        color = COLORS.get(row["status"], ("", "", ""))[2]
        print(f"{color} {row['status']:<11} {RESET}  {row['workstream']:<22} "
              f"{row['owner']:<14} {row['due']:<12} {row['jira']}")
        print(f"{'':15}{row['summary']}  ->  {row['next_step']}")
    print("\nDECISIONS NEEDED")
    for d in report.get("decisions_needed", []):
        print(f" - {d}")


def write_html(report: dict, out_path: Path) -> None:
    e = html.escape
    rows = ""
    for r in report["workstreams"]:
        bg, fg, _ = COLORS.get(r["status"], ("#eeeeee", "#000000", ""))
        rows += (
            f"<tr><td style='background:{bg};color:{fg};font-weight:600'>{e(r['status'])}</td>"
            f"<td>{e(r['workstream'])}</td><td>{e(r['summary'])}</td><td>{e(r['owner'])}</td>"
            f"<td>{e(r['due'])}</td><td>{e(r['jira'])}</td><td>{e(r['next_step'])}</td></tr>\n"
        )
    decisions = "".join(f"<li>{e(d)}</li>" for d in report.get("decisions_needed", []))
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<title>EVA v2 Status - {date.today().isoformat()}</title>
<style>
 body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; color: #222; max-width: 1200px; }}
 h1 {{ font-size: 22px; margin-bottom: 4px; }} .sub {{ color: #666; margin-top: 0; }}
 .summary {{ background: #f5f7fa; border-left: 4px solid #3b6fd8; padding: 12px 16px; line-height: 1.5; }}
 table {{ border-collapse: collapse; width: 100%; margin-top: 12px; font-size: 14px; }}
 th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
 th {{ background: #f0f0f0; }}
 .legend span {{ display: inline-block; padding: 2px 8px; margin-right: 8px; border-radius: 4px; font-size: 13px; }}
 .draft {{ color: #a00; font-size: 13px; margin-top: 24px; }}
</style></head><body>
<h1>Edge Video Analytics v2 - Status Report</h1>
<p class="sub">GA target Nov 20, 2026 &middot; generated {date.today().isoformat()}</p>
<h2>Executive summary</h2>
<div class="summary">{e(report['executive_summary'])}</div>
<h2>Workstream status</h2>
<div class="legend">
 <span style="background:#f8d7da;color:#842029">High risk</span>
 <span style="background:#fff3cd;color:#664d03">Medium risk</span>
 <span style="background:#d1e7dd;color:#0f5132">On track</span>
</div>
<table>
<tr><th>Status</th><th>Workstream</th><th>Where it stands</th><th>Owner</th><th>Due</th><th>JIRA</th><th>Next step</th></tr>
{rows}</table>
<h2>Decisions needed</h2>
<ul>{decisions}</ul>
<p class="draft">AI-generated draft - owners, dates and status verified by the TPM before sending.</p>
</body></html>"""
    out_path.write_text(page, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python status_report.py <jira_export.csv> <meeting_notes.txt>")
        sys.exit(1)

    jira = Path(sys.argv[1]).read_text(encoding="utf-8")
    notes = Path(sys.argv[2]).read_text(encoding="utf-8")

    print("Asking Claude for the status report...")
    report = ask_claude(jira, notes)

    print_terminal(report)

    out_path = Path(f"EVA_v2_status_{date.today().isoformat()}.html").resolve()
    write_html(report, out_path)
    print(f"\nDraft saved to {out_path} - review owners and dates before sending.")
    webbrowser.open(out_path.as_uri())


if __name__ == "__main__":
    main()
