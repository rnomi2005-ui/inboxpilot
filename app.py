import base64
import os
import re
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

import dns.resolver
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

ROOT = Path(__file__).parent

app = FastAPI(title="InboxPilot", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class DomainCheckRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253)
    dkim_selector: str = Field(default="google", min_length=1, max_length=63)


class PlanRequest(BaseModel):
    mailbox_status: str = "New"
    current_daily_volume: int = Field(default=5, ge=1, le=500)


class ReviewRequest(BaseModel):
    subject: str = Field(default="", max_length=998)
    body: str = Field(default="", max_length=100000)
    recipients_are_relevant: bool = True
    opt_out_handling: bool = True


class SendRequest(BaseModel):
    to: EmailStr
    subject: str = Field(min_length=1, max_length=250)
    body: str = Field(min_length=1, max_length=50000)
    test_mode: bool = True


def clean_domain(value: str) -> str:
    domain = value.strip().lower().rstrip(".")
    if "://" in domain or "/" in domain or "@" in domain or " " in domain:
        raise HTTPException(400, "Enter a domain only, e.g. example.com")
    if not re.fullmatch(r"(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", domain):
        raise HTTPException(400, "Domain format looks invalid.")
    return domain


def txt_records(name: str):
    try:
        answers = dns.resolver.resolve(name, "TXT", lifetime=4)
        return [b"".join(r.strings).decode("utf-8", errors="replace") for r in answers]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return []
    except Exception:
        return []


@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/api/status")
def status():
    return {"gmail_connected": False, "credentials_file_present": False,
            "token_file_present": False, "mode": "hosted preview; Gmail sending disabled until secure OAuth setup"}


@app.post("/api/domain-check")
def domain_check(req: DomainCheckRequest):
    domain = clean_domain(req.domain)
    selector = req.dkim_selector.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,63}", selector):
        raise HTTPException(400, "DKIM selector contains unsupported characters.")
    spf = [x for x in txt_records(domain) if x.lower().startswith("v=spf1")]
    dmarc = [x for x in txt_records(f"_dmarc.{domain}") if x.lower().startswith("v=dmarc1")]
    dkim = [x for x in txt_records(f"{selector}._domainkey.{domain}") if "v=DKIM1" in x.upper() or "p=" in x]
    return {
        "domain": domain,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "spf": {"status": "found" if spf else "not_found", "records": spf,
                "note": "Presence-only check; verify all legitimate senders are included."},
        "dkim": {"status": "found" if dkim else "not_found", "selector": selector, "records": dkim,
                 "note": "Best-effort check; use the exact selector from Google Admin."},
        "dmarc": {"status": "found" if dmarc else "not_found", "records": dmarc,
                  "note": "Presence-only check; review policy and alignment."},
        "warning": "DNS presence does not prove that a sent message passes SPF, DKIM, or DMARC."
    }


@app.post("/api/warmup-plan")
def warmup_plan(req: PlanRequest):
    if req.mailbox_status == "New":
        base = [3, 4, 5, 6, 8, 10, 12]
    elif req.mailbox_status == "Established but inactive":
        base = [5, 8, 12, 16, 20, 25, 30]
    else:
        base = [10, 15, 20, 25, 30, 35, 40]
    plan = [max(1, min(500, req.current_daily_volume + n - 5)) for n in base]
    return {"days": [{"day": i + 1, "planned_messages": count} for i, count in enumerate(plan)],
            "notice": "Illustrative planning targets only. Send relevant, wanted emails; pause increases if bounces or complaints rise. No fake engagement."}


@app.post("/api/review")
def review(req: ReviewRequest):
    body = req.body
    flags = []
    if not req.subject.strip():
        flags.append({"level": "high", "message": "Add a clear, accurate subject line."})
    if not req.recipients_are_relevant:
        flags.append({"level": "high", "message": "Do not send unless the recipient is relevant and you have a legitimate reason to contact them."})
    if not req.opt_out_handling:
        flags.append({"level": "medium", "message": "For ongoing outreach, document opt-outs and do not contact people who opted out."})
    if re.search(r"https?://|www\.", body, re.I):
        flags.append({"level": "low", "message": "Review links and make sure they lead to trustworthy, relevant pages."})
    if len(re.findall(r"[!$]{2,}", req.subject + " " + body)):
        flags.append({"level": "medium", "message": "Reduce repeated punctuation or excessive symbols."})
    if len(body.strip()) < 30:
        flags.append({"level": "low", "message": "The message is very short; make the purpose clear without adding filler."})
    if re.search(r"\b(guaranteed inbox|100% inbox|act now!!!|make money fast)\b", req.subject + " " + body, re.I):
        flags.append({"level": "medium", "message": "Avoid exaggerated or misleading claims."})
    return {"flags": flags, "word_count": len(body.split()),
            "status": "review" if flags else "no_basic_flags",
            "notice": "Heuristic content review only; it cannot predict a spam filter or guarantee inbox placement."}


@app.post("/api/connect-gmail")
def connect_gmail():
    raise HTTPException(501, "Gmail OAuth is not configured in this hosted preview yet. Do not upload credentials or tokens. Hosted OAuth setup is a separate next step.")


@app.post("/api/send-test")
def send_test(req: SendRequest):
    raise HTTPException(501, "Sending is disabled in this hosted preview until secure Google OAuth is configured.")


@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}
