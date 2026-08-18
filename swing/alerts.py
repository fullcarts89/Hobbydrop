"""Alert delivery.

Channels are intentionally dumb: format a message, hand it off, never let
a delivery failure take down the scan that produced it.
"""

from __future__ import annotations

import json
import os
import smtplib
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

USER_AGENT = "swing-alerts/1.0"


@dataclass
class Alert:
    key: str            # stable id, used to avoid sending the same thing twice
    kind: str           # entry | exit | stop_moved | watch | info
    title: str
    body: str
    urgency: str = "normal"      # normal | high
    data: dict = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict:
        return asdict(self)

    def as_text(self) -> str:
        marker = "!!" if self.urgency == "high" else "--"
        return f"{marker} {self.title}\n{self.body}"


class Channel:
    name = "channel"

    def send(self, alert: Alert) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class ConsoleChannel(Channel):
    name = "console"

    def send(self, alert: Alert) -> None:
        print(alert.as_text())


class JsonlChannel(Channel):
    name = "jsonl"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def send(self, alert: Alert) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as handle:
            handle.write(json.dumps(alert.to_dict()) + "\n")


class WebhookChannel(Channel):
    """Posts `{"text": ...}` -- the shape Slack and Discord both accept."""

    name = "webhook"

    def __init__(self, url: str, timeout: float = 10.0):
        self.url = url
        self.timeout = timeout

    def send(self, alert: Alert) -> None:
        payload = json.dumps({"text": alert.as_text(), "alert": alert.to_dict()}).encode()
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            response.read()


class EmailChannel(Channel):
    """SMTP via environment: SWING_SMTP_HOST/PORT/USER/PASSWORD, SWING_EMAIL_TO."""

    name = "email"

    def __init__(self, to: str, sender: str | None = None):
        self.to = to
        self.sender = sender or os.environ.get("SWING_EMAIL_FROM", to)

    def send(self, alert: Alert) -> None:
        host = os.environ.get("SWING_SMTP_HOST")
        if not host:
            raise RuntimeError("SWING_SMTP_HOST is not set")
        port = int(os.environ.get("SWING_SMTP_PORT", "587"))
        message = EmailMessage()
        message["Subject"] = alert.title
        message["From"] = self.sender
        message["To"] = self.to
        message.set_content(alert.body)

        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            user = os.environ.get("SWING_SMTP_USER")
            password = os.environ.get("SWING_SMTP_PASSWORD")
            if user and password:
                server.login(user, password)
            server.send_message(message)


class Notifier:
    def __init__(self, channels: list[Channel] | None = None):
        self.channels = channels or [ConsoleChannel()]
        self.errors: list[str] = []

    def send(self, alert: Alert) -> None:
        for channel in self.channels:
            try:
                channel.send(alert)
            except (OSError, RuntimeError, urllib.error.URLError, smtplib.SMTPException) as exc:
                self.errors.append(f"{channel.name}: {exc}")

    def send_all(self, alerts: list[Alert]) -> None:
        for alert in alerts:
            self.send(alert)


def build_notifier(
    *,
    console: bool = True,
    jsonl_path: str | Path | None = None,
    webhook_url: str | None = None,
    email_to: str | None = None,
) -> Notifier:
    channels: list[Channel] = []
    if console:
        channels.append(ConsoleChannel())
    if jsonl_path:
        channels.append(JsonlChannel(jsonl_path))
    webhook_url = webhook_url or os.environ.get("SWING_WEBHOOK_URL")
    if webhook_url:
        channels.append(WebhookChannel(webhook_url))
    email_to = email_to or os.environ.get("SWING_EMAIL_TO")
    if email_to:
        channels.append(EmailChannel(email_to))
    return Notifier(channels)
