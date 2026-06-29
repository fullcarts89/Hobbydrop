-- edgar-alerts state schema.
-- Applied automatically by store.init_schema() at startup; included here so it
-- can also be run manually via the Supabase SQL editor or MCP apply_migration.

CREATE SCHEMA IF NOT EXISTS edgar_alerts;

-- Every accession we've fully evaluated, so steady-state scans skip re-parsing.
CREATE TABLE IF NOT EXISTS edgar_alerts.processed_accessions (
    accession   TEXT PRIMARY KEY,
    form        TEXT,
    filed_date  DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per SMS actually sent. Doubles as dedup and as history for backtest
-- / threshold calibration.
CREATE TABLE IF NOT EXISTS edgar_alerts.alerts (
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
);

CREATE INDEX IF NOT EXISTS alerts_sent_at_idx ON edgar_alerts.alerts (sent_at DESC);
CREATE INDEX IF NOT EXISTS processed_filed_idx ON edgar_alerts.processed_accessions (filed_date);
