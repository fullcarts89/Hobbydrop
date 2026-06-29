"""edgar-alerts entrypoint.

Runs an immediate scan on startup (covering today + the lookback window to
catch overnight filings), then schedules recurring scans every
``CHECK_INTERVAL_MIN`` minutes with APScheduler.

CLI:
    python main.py                # run the scheduler (sends SMS)
    python main.py --dry-run      # run the scheduler but never send SMS
    python main.py --once         # single scan, then exit
    python main.py --backtest 2026-06-01 2026-06-15   # score a historical range
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

import config
import edgar
import filters
import notifier
import pricer
import scorer
from models import Filing
from store import Store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("edgar.main")

# EDGAR operates on US Eastern time; "today/yesterday" must follow it.
ET = ZoneInfo("America/New_York")


def _today_et() -> dt.date:
    return dt.datetime.now(ET).date()


def evaluate(rec: dict, store: Store, dry_run: bool) -> dict:
    """Parse → filter → enrich → price → score → maybe alert one record.

    Returns a small result dict for logging/backtesting.
    """
    filing = edgar.parse_filing(rec)
    if filing is None:
        return {"status": "unparseable", "accession": rec["accession"]}

    reason = filters.prefilter(filing)
    if reason:
        return {"status": "filtered", "reason": reason, "accession": filing.accession}

    edgar.enrich(filing)
    pricer.attach_market_data(filing)

    reason = filters.market_filter(filing)
    if reason:
        return {"status": "filtered", "reason": reason, "accession": filing.accession}

    score, _ = scorer.score_filing(filing)
    result = {
        "status": "scored",
        "accession": filing.accession,
        "ticker": filing.ticker,
        "score": score,
        "filing": filing,
    }

    if score >= config.ALERT_THRESHOLD and not store.is_alerted(filing.dedup_key):
        if notifier.send_alert(filing, dry_run=dry_run):
            if not dry_run:
                store.record_alert(filing)
            result["status"] = "alerted"
    return result


def scan(store: Store, dry_run: bool, *, start: str | None = None, end: str | None = None,
         mark: bool = True) -> None:
    today = _today_et()
    end = end or today.isoformat()
    start = start or (today - dt.timedelta(days=config.LOOKBACK_DAYS)).isoformat()
    t0 = dt.datetime.now(ET)
    log.info("Scan start window=%s..%s dry_run=%s", start, end, dry_run)

    records = edgar.discover(start, end)
    # Skip accessions we've already fully evaluated (steady-state efficiency).
    if mark:
        fresh_accs = store.filter_unprocessed(r["accession"] for r in records)
        records = [r for r in records if r["accession"] in fresh_accs]

    checked = alerts = scored = 0
    for rec in records:
        try:
            res = evaluate(rec, store, dry_run)
        except Exception as exc:  # never let one filing kill the scan
            log.exception("Error evaluating %s: %s", rec.get("accession"), exc)
            res = {"status": "error"}
        checked += 1
        if res.get("status") in ("scored", "alerted"):
            scored += 1
            log.info("Scored %s %s -> %d", res.get("ticker"), res["accession"], res["score"])
        if res.get("status") == "alerted":
            alerts += 1
        if mark:
            store.mark_processed(rec["accession"], rec.get("form_internal", ""), rec.get("filed_date"))

    dur = (dt.datetime.now(ET) - t0).total_seconds()
    log.info(
        "Scan done: %d checked, %d scored, %d alerts in %.1fs", checked, scored, alerts, dur
    )


def backtest(start: str, end: str) -> None:
    """Score a historical range without sending SMS or writing dedup state."""
    config.validate(require_twilio=False)
    store = Store()
    store.init_schema()
    log.info("Backtest %s..%s (dry-run, no state writes)", start, end)
    records = edgar.discover(start, end)
    hits = []
    for rec in records:
        try:
            res = evaluate(rec, store, dry_run=True)
        except Exception:
            continue
        if res.get("status") in ("scored", "alerted") and res.get("score", 0) >= config.ALERT_THRESHOLD:
            f: Filing = res["filing"]
            hits.append((res["score"], f.ticker, f.filer_name, f.breakdown))
    hits.sort(reverse=True)
    print(f"\n=== Backtest results: {len(hits)} filings >= {config.ALERT_THRESHOLD} ===")
    for score, ticker, name, bd in hits:
        print(f"{score:>3}  {ticker or '?':<6} {name[:28]:<28} {bd}")
    store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="EDGAR insider-trading SMS alerts")
    parser.add_argument("--dry-run", action="store_true", help="score but never send SMS")
    parser.add_argument("--once", action="store_true", help="run one scan and exit")
    parser.add_argument("--backtest", nargs=2, metavar=("START", "END"),
                        help="score a historical YYYY-MM-DD range, no SMS/state")
    args = parser.parse_args()

    if args.backtest:
        backtest(args.backtest[0], args.backtest[1])
        return

    dry_run = args.dry_run or config.DRY_RUN
    config.validate(require_twilio=not dry_run)
    store = Store()
    store.init_schema()

    # Immediate startup scan.
    scan(store, dry_run)

    if args.once:
        store.close()
        return

    sched = BlockingScheduler(timezone=ET)
    sched.add_job(
        scan, "interval", minutes=config.CHECK_INTERVAL_MIN,
        args=[store, dry_run], id="scan", max_instances=1, coalesce=True,
    )
    log.info("Scheduler started: every %d min", config.CHECK_INTERVAL_MIN)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down")
    finally:
        store.close()


if __name__ == "__main__":
    main()
