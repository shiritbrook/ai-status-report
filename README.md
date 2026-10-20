# AI Status Report Generator

A Python tool that turns a JIRA CSV export and meeting notes into a draft program status report: an executive summary, a color-coded status for each workstream (High risk / Medium risk / On track), and the decisions leadership needs to make.

> **AI-assisted project.** I built this with Claude to explore how a Technical Program Manager can use the Anthropic API in day-to-day program work. I designed the report format, the status rules and the "facts only" guardrails, and tested the output; Claude helped write the code.

## How it works
1. Reads a JIRA export (`.csv`) and meeting notes (`.txt`)
2. Sends both to Claude through the Anthropic API with strict instructions: use only facts from the sources, never invent owners or dates (write "TBD" instead), and cite JIRA keys
3. Gets back structured JSON and produces:
   - a color-coded table in the terminal
   - an HTML report that opens in the browser

## Guardrails
- The model is told to use only the provided sources and mark missing owners or dates as **TBD**
- Every row cites its JIRA keys so it can be traced back to the source
- The report is labeled a **draft**: the TPM checks every owner, date and status before anything is sent

## Run it
```powershell
pip install -r requirements.txt
# put your key in a .env file:  ANTHROPIC_API_KEY=your-key
python status_report.py jira_export.csv meeting_notes.txt
```

Optional: set `ANTHROPIC_MODEL` to choose a different Claude model.

**Tech:** Python · Anthropic API (Claude) · JSON · HTML
