"""
ByteFlow App Integrations
==========================
Connect ByteFlow to external messaging apps.

Supported:
  - Email (SMTP send / IMAP read)
  - Telegram Bot (send/receive messages)
  - Slack (send messages to channels)
  - WhatsApp (via Twilio API)

Each integration is optional — only active if credentials are configured
in settings or environment variables.
"""

from __future__ import annotations
import os
import smtplib
import imaplib
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# EMAIL
# ══════════════════════════════════════════════════════════════

class EmailIntegration:
    """Send and read emails via SMTP/IMAP."""

    def __init__(self, smtp_host: str = None, smtp_port: int = 587,
                 imap_host: str = None, imap_port: int = 993,
                 username: str = None, password: str = None):
        self.smtp_host = smtp_host or os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port
        self.imap_host = imap_host or os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
        self.imap_port = imap_port
        self.username = username or os.getenv("EMAIL_USERNAME", "")
        self.password = password or os.getenv("EMAIL_PASSWORD", "")

    def is_configured(self) -> bool:
        return bool(self.username and self.password)

    def send(self, to: str, subject: str, body: str, html: bool = False) -> dict:
        if not self.is_configured():
            return {"ok": False, "error": "Email not configured. Set EMAIL_USERNAME and EMAIL_PASSWORD env vars."}
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.username
            msg["To"] = to
            msg["Subject"] = subject
            part = MIMEText(body, "html" if html else "plain")
            msg.attach(part)
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.username, to, msg.as_string())
            return {"ok": True, "message": f"Email sent to {to}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def read_inbox(self, n: int = 10, folder: str = "INBOX") -> dict:
        if not self.is_configured():
            return {"ok": False, "error": "Email not configured."}
        try:
            with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as mail:
                mail.login(self.username, self.password)
                mail.select(folder)
                _, data = mail.search(None, "ALL")
                ids = data[0].split()
                ids = ids[-n:]  # last N
                messages = []
                for uid in reversed(ids):
                    _, msg_data = mail.fetch(uid, "(RFC822)")
                    msg = email_lib.message_from_bytes(msg_data[0][1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
                    messages.append({
                        "from": msg.get("From", ""),
                        "subject": msg.get("Subject", ""),
                        "date": msg.get("Date", ""),
                        "body": body[:500],
                    })
            return {"ok": True, "messages": messages, "count": len(messages)}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════

class TelegramIntegration:
    """
    Send messages via Telegram Bot API.
    Get token from @BotFather on Telegram.
    Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID env vars.
    """

    BASE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.getenv("TELEGRAM_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def _url(self, method: str) -> str:
        return self.BASE.format(token=self.token, method=method)

    def send(self, text: str, chat_id: str = None, parse_mode: str = "Markdown") -> dict:
        if not self.is_configured():
            return {"ok": False, "error": "Telegram not configured. Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID."}
        try:
            import urllib.request, json
            payload = json.dumps({
                "chat_id": chat_id or self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }).encode()
            req = urllib.request.Request(
                self._url("sendMessage"),
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
            return {"ok": result.get("ok", False), "message_id": result.get("result", {}).get("message_id")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_updates(self, limit: int = 10) -> dict:
        if not self.is_configured():
            return {"ok": False, "error": "Telegram not configured."}
        try:
            import urllib.request, json
            url = self._url("getUpdates") + f"?limit={limit}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                result = json.loads(resp.read())
            messages = []
            for update in result.get("result", []):
                msg = update.get("message", {})
                if msg:
                    messages.append({
                        "from": msg.get("from", {}).get("username", ""),
                        "text": msg.get("text", ""),
                        "date": datetime.fromtimestamp(msg.get("date", 0)).isoformat(),
                    })
            return {"ok": True, "messages": messages}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def send_byteflow_alert(self, title: str, body: str) -> dict:
        text = f"*{title}*\n{body}"
        return self.send(text)


# ══════════════════════════════════════════════════════════════
# SLACK
# ══════════════════════════════════════════════════════════════

class SlackIntegration:
    """
    Post messages to Slack via Incoming Webhook or Bot Token.
    Set SLACK_WEBHOOK_URL or SLACK_TOKEN + SLACK_CHANNEL env vars.
    """

    def __init__(self, webhook_url: str = None, token: str = None, channel: str = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL", "")
        self.token = token or os.getenv("SLACK_TOKEN", "")
        self.channel = channel or os.getenv("SLACK_CHANNEL", "#general")

    def is_configured(self) -> bool:
        return bool(self.webhook_url or self.token)

    def send(self, text: str, channel: str = None) -> dict:
        if not self.is_configured():
            return {"ok": False, "error": "Slack not configured. Set SLACK_WEBHOOK_URL env var."}
        try:
            import urllib.request, json
            if self.webhook_url:
                payload = json.dumps({"text": text}).encode()
                req = urllib.request.Request(
                    self.webhook_url, data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = resp.read().decode()
                return {"ok": body == "ok", "response": body}
            else:
                payload = json.dumps({
                    "channel": channel or self.channel,
                    "text": text,
                }).encode()
                req = urllib.request.Request(
                    "https://slack.com/api/chat.postMessage",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.token}",
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read())
                return {"ok": result.get("ok", False)}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# WHATSAPP (via Twilio)
# ══════════════════════════════════════════════════════════════

class WhatsAppIntegration:
    """
    Send WhatsApp messages via Twilio API.
    Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM env vars.
    """

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.getenv("TWILIO_WHATSAPP_FROM", "")

    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)

    def send(self, to: str, message: str) -> dict:
        if not self.is_configured():
            return {"ok": False, "error": "WhatsApp not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM."}
        try:
            import urllib.request, urllib.parse, json, base64
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            data = urllib.parse.urlencode({
                "From": f"whatsapp:{self.from_number}",
                "To": f"whatsapp:{to}",
                "Body": message,
            }).encode()
            credentials = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
            req = urllib.request.Request(url, data=data, headers={"Authorization": f"Basic {credentials}"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
            return {"ok": result.get("status") not in ("failed", "undelivered"), "sid": result.get("sid")}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# Integration Manager
# ══════════════════════════════════════════════════════════════

class IntegrationManager:
    """Central access point for all integrations."""

    def __init__(self):
        self.email = EmailIntegration()
        self.telegram = TelegramIntegration()
        self.slack = SlackIntegration()
        self.whatsapp = WhatsAppIntegration()

    def status(self) -> dict:
        return {
            "email": {"configured": self.email.is_configured(), "provider": self.email.smtp_host},
            "telegram": {"configured": self.telegram.is_configured()},
            "slack": {"configured": self.slack.is_configured()},
            "whatsapp": {"configured": self.whatsapp.is_configured()},
        }

    def send_to_all(self, title: str, body: str) -> dict:
        """Broadcast a message to all configured integrations."""
        results = {}
        if self.telegram.is_configured():
            results["telegram"] = self.telegram.send_byteflow_alert(title, body)
        if self.slack.is_configured():
            results["slack"] = self.slack.send(f"*{title}*\n{body}")
        return results


_manager: IntegrationManager = None

def get_integrations() -> IntegrationManager:
    global _manager
    if _manager is None:
        _manager = IntegrationManager()
    return _manager
