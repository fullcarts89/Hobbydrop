"""Postgres-backed persistence (Supabase).

Replaces the spec's local ``seen.json`` because Railway's filesystem is
ephemeral — a local cache would reset on every redeploy and cause duplicate
SMS alerts. Two tables (in a dedicated ``edgar_alerts`` schema so it can live
alongside other apps in a shared Supabase project):

* ``processed_accessions`` — every accession we've fully evaluated, so steady
  state scans skip re-fetching/parsing filings already seen.
* ``alerts`` — one row per SMS actually sent; doubles as dedup and history for
  backtesting/calibration.
"""
from __future__ import annotations

import json
import logging
from typing import Iterable

import psycopg

import config
from models import Filing

log = logging.getLogger("edgar.store")

SCHEMA = "edgar_alerts"


class Store:
    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or config.DATABASE_URL
        if not self._dsn:
            raise config.ConfigError("DATABASE_URL is not set")
        self._conn: psycopg.Connection | None = None

    # -- connection management ------------------------------------------
    def _connection(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._dsn, autocommit=True)
        return self._conn

    def _execute(self, sql: str, params: tuple = ()):  # small reconnect wrapper
        try:
            return self._connection().execute(sql, params)
        except psycopg.OperationalError:
            log.warning("DB connection dropped; reconnecting")
            self._conn = None
            return self._connection().execute(sql, params)

    def init_schema(self) -> None:
        """Create schema + tables if absent (idempotent)."""
        self._execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.processed_accessions (
                accession   TEXT PRIMARY KEY,
                form        TEXT,
                filed_date  DATE,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.alerts (
                dedup_key   TEXT PRIMARY KEY,
                accession   TEXT NOT NULL,
                owner_cik   TEXT,
                ticker      TEXT,
                form        TEXT,
                score       INT,
                breakdown   JSONB,
                filer_name  TEXT,
                trade_value NUMERIC,
                market_cap  NUMERIC,
                sent_at     TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        log.info("Schema ready (%s)", SCHEMA)

    # -- processed accessions -------------------------------------------
    def filter_unprocessed(self, accessions: Iterable[str]) -> set[str]:
        """Return the subset of ``accessions`` not yet processed."""
        accs = list(dict.fromkeys(accessions))
        if not accs:
            return set()
        rows = self._execute(
            f"SELECT accession FROM {SCHEMA}.processed_accessions "
            "WHERE accession = ANY(%s)",
            (accs,),
        ).fetchall()
        seen = {r[0] for r in rows}
        return {a for a in accs if a not in seen}

    def mark_processed(self, accession: str, form: str, filed_date: str | None) -> None:
        self._execute(
            f"INSERT INTO {SCHEMA}.processed_accessions (accession, form, filed_date) "
            "VALUES (%s, %s, %s) ON CONFLICT (accession) DO NOTHING",
            (accession, form, filed_date),
        )

    # -- alerts ----------------------------------------------------------
    def is_alerted(self, dedup_key: str) -> bool:
        row = self._execute(
            f"SELECT 1 FROM {SCHEMA}.alerts WHERE dedup_key = %s", (dedup_key,)
        ).fetchone()
        return row is not None

    def record_alert(self, filing: Filing) -> None:
        self._execute(
            f"""
            INSERT INTO {SCHEMA}.alerts
                (dedup_key, accession, owner_cik, ticker, form, score,
                 breakdown, filer_name, trade_value, market_cap)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (dedup_key) DO NOTHING
            """,
            (
                filing.dedup_key,
                filing.accession,
                filing.owner_cik,
                filing.ticker,
                filing.filing_type,
                filing.score,
                json.dumps(filing.breakdown),
                filing.filer_name,
                filing.trade_value,
                filing.market_cap,
            ),
        )

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
