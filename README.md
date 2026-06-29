# edgar-alerts

Monitors SEC EDGAR for high-conviction insider activity — Form 4 open-market
purchases and Schedule 13D/13G accumulations in companies under a $2B market cap
— scores each filing on a 100-point conviction model, and sends an SMS via
Twilio when a filing scores **≥ 75**.

It runs as an always-on worker: an immediate scan on startup, then every 15
minutes. State (which filings have been seen/alerted) lives in Postgres
(Supabase) so it survives redeploys.

---

## How it works

```
EDGAR (EFTS + getcurrent)  ->  parse Form 4 / 13D-G XML  ->  hard filters
   ->  enrich (8-K gap, cluster, insider history, price/market cap)
   ->  conviction score (0-100)  ->  score >= 75  ->  Twilio SMS  ->  record in Postgres
```

| Module | Responsibility |
|--------|----------------|
| `config.py` | Env loading + fail-fast validation |
| `http_client.py` | Rate-limited (8 req/s) EDGAR HTTP with retry/backoff |
| `edgar.py` | Hybrid discovery + Form 4 / 13D-13G XML parsing + enrichment |
| `scorer.py` | 100-point conviction model |
| `pricer.py` | yfinance price/market cap (+ XBRL shares fallback) |
| `filters.py` | Hard filters (P-code, $100k, 10b5-1, market-cap ceiling) |
| `notifier.py` | Twilio SMS (2-part message) |
| `store.py` | Postgres dedup cache + alert history |
| `main.py` | Scheduler + `--dry-run` / `--once` / `--backtest` |

### Conviction model (max 100)

| Axis | Max | Signal |
|------|-----|--------|
| Relative size | 25 | trade value as % of market cap |
| News vacuum | 20 | days since the issuer's last 8-K |
| Filer quality | 18 | insider seniority (CEO/CFO/…) or 13D filer type |
| Cluster / new position | 14 | other insider buys ±5d, or a new 13D position |
| Intent | 13 | first open-market buy in 12m, or 13D active intent |
| Price window | 10 | how far price has moved from the insider's entry |

### Hard filters (applied before scoring)

- Form 4 transaction code must be **`P`** (open-market purchase only)
- Trade value **≥ $100,000**
- Issuer market cap **≤ $2B** (yfinance, with XBRL shares × price fallback)
- Form 4 10b5-1 pre-scheduled trades are excluded
- Accession not already processed (Postgres dedup)

---

## Local setup

```bash
pip install -r requirements.txt
cp .env.example .env       # then fill in the values below
python main.py --dry-run   # scores live filings, sends NO SMS
```

Run for real (sends SMS):

```bash
python main.py
```

Useful modes:

```bash
python main.py --once                       # one scan then exit
python main.py --backtest 2026-06-01 2026-06-15   # score a historical range, no SMS/state
```

---

## Configuration

All settings are environment variables (see `.env.example`). Thresholds can be
changed without touching code:

| Var | Default | Meaning |
|-----|---------|---------|
| `ALERT_THRESHOLD` | 75 | Minimum score to send an SMS |
| `MIN_TRADE_VALUE` | 100000 | Minimum Form 4 purchase value |
| `MAX_MARKET_CAP` | 2000000000 | Market-cap ceiling |
| `CHECK_INTERVAL_MIN` | 15 | Minutes between scans |
| `LOOKBACK_DAYS` | 1 | How far back each scan looks (overlap absorbs indexing lag) |
| `EDGAR_RATE_LIMIT` | 8 | Max EDGAR requests/sec |
| `DRY_RUN` | false | Score + log but never send SMS |
| `EDGAR_USER_AGENT` | — | **Required**, must contain a contact email |

---

## Supabase (state store)

State lives in Postgres so the dedup cache survives Railway redeploys. The app
**creates its own schema and tables on first startup** (`edgar_alerts.*`), so all
you need to provide is the connection string.

1. In your Supabase project → **Settings → Database → Connection string → URI**.
   Use the **Connection pooling** URI for Railway (port `6543`).
2. Set it as `DATABASE_URL` in `.env` (local) and in the Railway dashboard (prod):
   ```
   DATABASE_URL=postgresql://postgres.<ref>:<password>@<host>:6543/postgres
   ```
3. (Optional) To create the tables ahead of time, run
   [`migrations/001_init.sql`](migrations/001_init.sql) in the Supabase SQL editor.

Tables created:
- `edgar_alerts.processed_accessions` — every evaluated filing (dedup)
- `edgar_alerts.alerts` — every SMS sent (history / backtest calibration)

---

## Twilio (SMS)

1. Sign up / log in at <https://console.twilio.com>.
2. From the console dashboard copy your **Account SID** and **Auth Token**.
3. Buy an SMS-capable phone number (Phone Numbers → Buy a number) → this is
   `TWILIO_FROM_NUMBER`. `TWILIO_TO_NUMBER` is your own mobile.
4. Put all four into `.env` / Railway env vars.

---

## Railway deployment

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

Then in the Railway dashboard, set **all** of these env vars (Service → Variables):

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`
- `TWILIO_TO_NUMBER`
- `DATABASE_URL`
- `EDGAR_USER_AGENT`
- (optional overrides) `ALERT_THRESHOLD`, `MIN_TRADE_VALUE`, `MAX_MARKET_CAP`,
  `CHECK_INTERVAL_MIN`, `LOOKBACK_DAYS`, `EDGAR_RATE_LIMIT`, `DRY_RUN`

The `Procfile` runs `python main.py` as a worker. Confirm it's live:

```bash
railway logs
```

You should see `Scan start …` / `Scan done: N checked, …` lines every 15 minutes.

> Tip: deploy first with `DRY_RUN=true` for a day to watch what *would* alert and
> calibrate `ALERT_THRESHOLD` before enabling SMS.

---

## Testing

```bash
python -m pytest tests/ -q
```

Covers the scorer bands, the corrected window labelling, and Form 4 / 13D XML
parsing against fixtures.

---

## Notes & limitations

- EDGAR requires a descriptive `User-Agent` with contact info — requests without
  it are blocked. Stay under 10 req/s (this app uses 8).
- `yfinance` is best-effort; tickers it can't price are skipped (logged), since
  the market-cap filter can't be evaluated without it.
- 13D/13G "trade value" is approximated from reported ownership % × market cap
  (these filings report a position, not a single priced transaction).
- All filings on EDGAR are public the instant they're filed; this tool surfaces
  them faster than manual watching, not before publication.
