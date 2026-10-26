# InboxPilot — Google Workspace Deliverability MVP

InboxPilot is a local-first starter app for legitimate email deliverability checks and dispatch outreach.

## What works
- FastAPI backend and browser dashboard
- DNS TXT lookup for SPF, DMARC, and a best-effort DKIM selector check
- Warm-up planning (planning only; no fake engagement)
- Basic draft-risk review
- Gmail sending intentionally disabled in hosted preview until secure web OAuth is implemented
- Send a test email to an inbox you control; manually inspect the receiving inbox/folder

## Important limitations
- No software can guarantee inbox placement.
- The DKIM selector is provider-specific; configure it in Google Admin and pass the selector to the API.
- The app does not generate artificial opens, replies, or fake engagement.
- Postmaster Tools data is not included in this MVP. Add the API integration after domain verification and OAuth scopes are configured.
- Use only recipients you have a legitimate reason to contact. Respect opt-outs and applicable law.
- This hosted preview provides DNS, warm-up planning, and draft-review features only. Gmail sending is disabled. Before using with real accounts or exposing sensitive data, add authentication, rate limits, audit logs, and secure deployment practices.

## Requirements
- Python 3.11+
- A Google Workspace mailbox
- Optional: a domain you control
- Google Cloud project if you want Gmail sending

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```
Open http://127.0.0.1:8000

## Gmail sending
Gmail sending is disabled in this hosted preview. Do not upload Google OAuth client files, access tokens, or passwords to GitHub. A secure web-based OAuth flow and protected token storage must be implemented before enabling sending.

## Domain checks
- SPF: looks for a TXT record starting with `v=spf1`; checks presence only, not full SPF syntax or DNS lookup limits.
- DMARC: checks `_dmarc.<domain>` for a TXT record starting with `v=DMARC1`.
- DKIM: checks `<selector>._domainkey.<domain>`; enter the selector configured in Google Admin (often a value such as `google`, but do not assume).
- DNS results are informational and should be reviewed with your DNS provider.

## Inbox placement test
Enter a Gmail/Outlook test inbox that you own or are authorized to test. InboxPilot sends a message through your connected Workspace mailbox. Open the recipient mailbox and record whether it landed in Inbox, Spam, or another folder. This app does not claim to automatically detect placement in third-party mailboxes.

## Production integrations to add
- PostgreSQL for users, check history, suppression list, and encrypted OAuth tokens
- Background worker/scheduler for periodic DNS checks and reminders
- Gmail API watch/history or bounce processing for delivery events
- Google Postmaster Tools API for aggregate Gmail spam-rate, reputation, and delivery metrics, where available
- Optional third-party inbox placement provider if automated seed testing is required

## Security
- This preview does not store Gmail tokens or credentials.
- Do not enable Gmail sending until secure web OAuth and token storage are implemented.
- Inbox placement is not guaranteed; use relevant recipients and honor opt-outs.
