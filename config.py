"""Central configuration for edgar-alerts.

All tunables are loaded from environment variables (with sane defaults) so the
service can be reconfigured on Railway without code changes. Call
``validate()`` once at startup to fail fast on missing credentials.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


# --- Twilio (SMS) ---------------------------------------------------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
TWILIO_TO_NUMBER = os.getenv("TWILIO_TO_NUMBER")

# --- Persistence ----------------------------------------------------------
# Postgres connection string (Supabase). Used for the dedup cache + alert
# history so state survives Railway redeploys (a local file would not).
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Scoring / filter thresholds -----------------------------------------
ALERT_THRESHOLD = _int("ALERT_THRESHOLD", 75)
MIN_TRADE_VALUE = _int("MIN_TRADE_VALUE", 100_000)
MAX_MARKET_CAP = _int("MAX_MARKET_CAP", 2_000_000_000)
MIN_REL_PCT = _float("MIN_REL_PCT", 0.25)

# --- Scheduling -----------------------------------------------------------
CHECK_INTERVAL_MIN = _int("CHECK_INTERVAL_MIN", 15)
# How many days back each scan looks. The window overlaps previous scans on
# purpose (to absorb EDGAR full-text indexing lag); the store dedups.
LOOKBACK_DAYS = _int("LOOKBACK_DAYS", 1)

# --- EDGAR ----------------------------------------------------------------
# EDGAR REQUIRES a descriptive User-Agent with contact info or it returns 403.
EDGAR_USER_AGENT = os.getenv("EDGAR_USER_AGENT", "edgar-alerts liuxnard@gmail.com")
# Max sustained requests/sec to EDGAR. Their published ceiling is 10; we stay
# under it to leave headroom and avoid throttling.
EDGAR_RATE_LIMIT = _float("EDGAR_RATE_LIMIT", 8.0)

# Which forms to monitor. EFTS form tokens (verified live):
#   "4" -> Form 4, "SCHEDULE 13D" -> SC 13D, "SCHEDULE 13G" -> SC 13G
EDGAR_FORMS = {
    "4": "4",
    "SCHEDULE 13D": "13D",
    "SCHEDULE 13G": "13G",
}

# --- Behaviour flags ------------------------------------------------------
# When true, score and log would-be alerts but never send SMS. Useful for
# calibrating the threshold. Overridden by the --dry-run CLI flag.
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


def validate(require_twilio: bool = True) -> None:
    """Fail fast on missing required configuration.

    ``require_twilio`` is False in dry-run/backtest modes where no SMS is sent.
    """
    missing = []
    if not DATABASE_URL:
        missing.append("DATABASE_URL")
    if require_twilio:
        for name in (
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_FROM_NUMBER",
            "TWILIO_TO_NUMBER",
        ):
            if not globals().get(name):
                missing.append(name)
    if "@" not in (EDGAR_USER_AGENT or ""):
        raise ConfigError(
            "EDGAR_USER_AGENT must include a contact email, e.g. "
            "'edgar-alerts you@example.com' — EDGAR blocks requests without it."
        )
    if missing:
        raise ConfigError(
            "Missing required environment variables: " + ", ".join(missing)
        )
