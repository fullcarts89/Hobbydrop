"""Twilio SMS notifications.

Builds the two-part alert from the spec. Message 1 (always) is kept short;
message 2 with entry/exit detail is sent only when the score clears the alert
threshold. The ``window_label`` helper here is the corrected version — the
draft in the spec mislabelled underwater (negative) deltas.
"""
from __future__ import annotations

import logging
from typing import Optional

import config
from models import Filing

log = logging.getLogger("edgar.notifier")

_client = None


def window_label(delta_pct: Optional[float]) -> str:
    if delta_pct is None:
        return "⚪ UNKNOWN"
    if abs(delta_pct) < 5:
        return "🟢 OPEN"
    if delta_pct <= -5:
        return "🔵 INVERTED"
    if delta_pct < 20:
        return "🟡 DEVELOPING"
    return "🔴 CLOSED"


def _money(value: Optional[float]) -> str:
    if not value:
        return "$?"
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(value) >= div:
            return f"${value / div:.1f}{unit}"
    return f"${value:.0f}"


def build_messages(filing: Filing) -> list[str]:
    """Return 1 or 2 SMS bodies for a filing."""
    rel = filing.rel_pct
    rel_str = f"{rel:.2f}% of mkt cap" if rel is not None else "rel size n/a"
    role = filing.role_label or filing.filing_type
    form = filing.form_raw or filing.filing_type

    msg1 = (
        f"🚨 {filing.ticker or filing.issuer_name[:12]} | Score: {filing.score}/100\n"
        f"{(filing.filer_name or 'Insider')[:24]} ({role}) | {form}\n"
        f"+{_money(filing.trade_value)} = {rel_str}\n"
        f"{window_label(filing.price_delta_pct)}"
    )
    messages = [msg1]

    if filing.score >= config.ALERT_THRESHOLD:
        entry = f"${filing.trade_price:.2f}" if filing.trade_price else "n/a"
        now = f"${filing.current_price:.2f}" if filing.current_price else "n/a"
        delta = f"({filing.price_delta_pct:+.1f}%)" if filing.price_delta_pct is not None else ""
        ago = f"{filing.days_since_trade}d ago" if filing.days_since_trade is not None else ""
        silence = (
            f"{filing.days_since_last_8k}d news silence"
            if filing.days_since_last_8k < 9999
            else "no recent 8-K"
        )
        msg2 = (
            f"Entry: {entry} | Now: {now} {delta}\n"
            f"{ago} | {silence}\n"
            f"{filing.filing_url}"
        ).strip()
        messages.append(msg2)
    return messages


def _get_client():
    global _client
    if _client is None:
        from twilio.rest import Client
        _client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    return _client


def send_alert(filing: Filing, dry_run: bool = False) -> bool:
    """Send the alert SMS(es). Returns True if delivered (or dry-run logged)."""
    messages = build_messages(filing)
    if dry_run:
        log.info(
            "[DRY-RUN] would alert %s score=%d:\n%s",
            filing.ticker, filing.score, "\n--\n".join(messages),
        )
        return True
    try:
        client = _get_client()
        for body in messages:
            client.messages.create(
                body=body,
                from_=config.TWILIO_FROM_NUMBER,
                to=config.TWILIO_TO_NUMBER,
            )
        log.info("Sent %d SMS for %s (score %d)", len(messages), filing.ticker, filing.score)
        return True
    except Exception as exc:
        log.error("Twilio send failed for %s: %s", filing.ticker, exc)
        return False
