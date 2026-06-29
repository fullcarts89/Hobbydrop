"""Rate-limited HTTP client for EDGAR.

EDGAR enforces a 10 req/s ceiling and a mandatory descriptive User-Agent.
This module provides a single shared ``requests.Session`` fronted by a simple
token-bucket limiter plus retry-with-backoff on 429/5xx responses.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import requests

import config

log = logging.getLogger("edgar.http")


class _RateLimiter:
    """Minimal thread-safe token bucket: at most ``rate`` requests per second."""

    def __init__(self, rate: float) -> None:
        self._min_interval = 1.0 / rate if rate > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                time.sleep(self._next_allowed - now)
                now = time.monotonic()
            self._next_allowed = now + self._min_interval


_session: Optional[requests.Session] = None
_limiter = _RateLimiter(config.EDGAR_RATE_LIMIT)


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": config.EDGAR_USER_AGENT,
                "Accept-Encoding": "gzip, deflate",
            }
        )
        _session = s
    return _session


def get(
    url: str,
    *,
    params: Optional[dict] = None,
    max_retries: int = 3,
    timeout: int = 30,
) -> Optional[requests.Response]:
    """Rate-limited GET with retry/backoff.

    Returns the ``Response`` on success (2xx) or ``None`` if all retries are
    exhausted, so callers can skip gracefully rather than crash a scan.
    """
    session = _get_session()
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        _limiter.wait()
        try:
            resp = session.get(url, params=params, timeout=timeout)
        except requests.RequestException as exc:
            log.warning("GET %s failed (%s), attempt %d/%d", url, exc, attempt, max_retries)
            time.sleep(backoff)
            backoff *= 2
            continue

        if resp.status_code == 200:
            return resp
        if resp.status_code == 404:
            return None  # genuinely missing; no point retrying
        if resp.status_code in (429, 500, 502, 503, 504):
            retry_after = resp.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else backoff
            log.warning(
                "GET %s -> %d, backing off %.1fs (attempt %d/%d)",
                url, resp.status_code, delay, attempt, max_retries,
            )
            time.sleep(delay)
            backoff *= 2
            continue
        log.warning("GET %s -> %d (giving up)", url, resp.status_code)
        return None
    log.error("GET %s exhausted %d retries", url, max_retries)
    return None


def get_json(url: str, *, params: Optional[dict] = None) -> Optional[dict]:
    resp = get(url, params=params)
    if resp is None:
        return None
    try:
        return resp.json()
    except ValueError:
        log.warning("Non-JSON response from %s", url)
        return None
