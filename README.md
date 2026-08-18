# Insider-Screener — swing trade signals

A single-position, cash-only swing trading system: research harness, honest
backtest, and real-ish time alerts, all driven by the same code so that what
alerts you is what was tested.

The premise being tested is the one in the brief: **put the whole account into
one stock at a time, no margin, no options, follow the rules consistently, and
see whether that beats just owning the index.**

The machinery works. The answer, on liquid US large caps, is **no** — and the
most useful thing in this repo is the evidence for that, plus the tooling to
test a better signal when you have one. Numbers below are reproducible with the
commands next to them.

---

## The headline result

Walk-forward validation over 2012–2026: parameters are chosen on the six years
*before* each two-year test window and never revised inside it, so every trade
below was taken with settings picked in advance.

```
python3 -m swing walkforward --start 2005-01-01 --out runs/walkforward
```

| | this strategy (out of sample) | SPY buy & hold |
|---|---|---|
| total return | **+129.2%** | +683.7% |
| CAGR | **+5.84%** | +15.13% |
| max drawdown | **−36.2%** | −33.7% |
| Sharpe | **0.37** | 0.94 |
| trades | 421 (28.8/yr) | 1 |
| win rate | 61.3% | — |
| avg win / avg loss | +2.34% / −3.03% | — |
| profit factor | 1.18 | — |
| expectancy | +0.030 R | — |
| time in market | 54% | 100% |

It makes money. It loses to the index on return, on drawdown, and on
risk-adjusted return simultaneously — while requiring ~29 decisions a year and
leaving you exposed to one company at a time.

The trade-order bootstrap says the single historical path was also a fairly
kind one:

```
median outcome        $54,922   (from $25,000)
5th / 95th percentile $16,424 / $187,651
chance of losing money            15.0%
chance of a >30% drawdown         89.6%
chance of a >50% drawdown         31.1%
```

That last line is the real cost of the all-in constraint. Same edge, same
trades, different order: a coin-flip's chance of watching a third of the
account evaporate, and a one-in-three chance of a halving.

## Why — the entry has an edge, and costs eat it

The interesting question is not "did it make money" (in a rising market, beta
does that) but "did the signal beat what you'd have got anyway". So each signal
is compared against a **control**: every liquid name in the universe that was
above its 200-day average on a risk-on day — the pool the strategy draws from.

```
python3 -m swing edge --start 2005-01-01
```

Default `oversold` entry — a 2-period RSI washout inside a strong uptrend:

| horizon | mean return | control | **edge vs control** | t |
|---|---|---|---|---|
| 3 sessions | +0.398% | +0.141% | **+0.257%** | 2.95 |
| 5 sessions | +0.506% | +0.239% | **+0.267%** | 2.17 |
| 10 sessions | +0.733% | +0.484% | **+0.249%** | 3.27 |
| 20 sessions | +1.222% | +0.970% | **+0.251%** | 4.21 |

There is a real edge, it is about **+0.26% per trade**, and it is entirely
earned in the first three sessions. Now price it: a round trip at 10 bps of
slippage each way costs **0.20%**. Costs consume roughly three quarters of the
edge before commission. That is the whole story, and the sweep confirms it —
same strategy, only the cost assumption changed:

| slippage | CAGR | Sharpe |
|---|---|---|
| 0 bps | +14.96% | 0.81 |
| 5 bps | +11.42% | 0.65 |
| 10 bps (default) | +7.98% | 0.49 |

(Single-pass 2005–2026, in-sample — the walk-forward figures above are the ones
to believe. The point here is the slope, not the level.)

The system is not really trading a stock edge. It is trading a thin edge
against its own transaction costs.

## The textbook entry is worse than random

The classic swing setup — wait for a pullback, buy the first close above the
prior day's high — is included as `--entry-mode reclaim`. Measured the same way:

| horizon | mean return | control | **edge vs control** | t |
|---|---|---|---|---|
| 3 sessions | −0.006% | +0.141% | **−0.147%** | −3.73 |
| 5 sessions | +0.048% | +0.239% | **−0.191%** | −3.63 |
| 10 sessions | +0.197% | +0.484% | **−0.287%** | −1.73 |
| 20 sessions | +0.492% | +0.970% | **−0.478%** | −0.84 |

Negative at every horizon. Run all-in through the engine
(`--entry-mode reclaim backtest --start 2005-01-01`) it turns $25,000 into
$15,992: **−2.05% CAGR with a −67.3% drawdown**, against SPY's +11.02% and
−55.2% over the same window. It looks like it works because it buys stocks in
uptrends and stocks in uptrends go up; against the honest baseline it is worse
than picking from the same pool at random. It is kept in the repo so you can
re-run that comparison rather than take it on faith.

## Which name to pick barely matters

With one slot and several triggers on the same day, the pick rule feels
important. It isn't. Mean return of the chosen trade, 2005–2026:

| rule | mean | std | worst |
|---|---|---|---|
| pick at random | +0.51% | 3.60% | −32.7% |
| highest 6-month momentum | +0.51% | 3.98% | −31.3% |
| highest ADX | +0.52% | 3.36% | −26.7% |
| lowest RSI(2) | +0.42% | 3.63% | −31.3% |
| lowest ATR% | +0.33% | 2.80% | −13.5% |

Every rule lands inside the noise of picking at random. One finding did stick
and is now the default: ranking on a *tight stop* actively hurts, because it
selects the lowest-volatility candidate, which had the lowest forward return.

## What the strategy actually does

Four gates, in order. A bar passing all four is a signal, and it is filled at
the **next** session's open — never at the close that produced it.

1. **Regime** — SPY above its 200-day average, otherwise sit in cash.
2. **Trend** — the name above its own 200-day, 50-day above 200-day and rising,
   6-month return above a floor, and stronger than SPY's over the same window.
3. **Weakness** — RSI(2) below the threshold: a washout inside that uptrend.
4. **Risk** — a stop below the pullback low or 2.5 ATR back, whichever is
   lower, rejected if it sits further than 12% away. All-in means stop distance
   *is* position size; there is no other dial.

Exits: RSI(2) recovering above the exit threshold (the usual case, 326 of 421
trades), the hard stop intraday, a 10-session time stop, or the market regime
flipping risk-off.

## Using it

```bash
pip install -r requirements.txt
python3 -m swing fetch                       # warm the bar cache (~3 min, 240 symbols)

python3 -m swing backtest --start 2005-01-01 --out runs/base
python3 -m swing walkforward --out runs/walkforward     # the honest one
python3 -m swing edge                                    # is there an edge at all?

python3 -m swing scan --paper-start 2025-01-01           # today's signal + paper account
python3 -m swing watch --interval 300                    # intraday stop/target monitor
```

`scan` replays the paper account from `--paper-start` with the same engine the
backtest uses, so paper results and backtest results cannot drift apart. It
prints the open position, its current stop, and any order to place at the next
open. The first run seeds the replayed history silently; after that it only
reports what is new.

Alerts go to console plus any of: a JSONL file (`--alert-log`), a Slack or
Discord webhook (`--webhook` or `SWING_WEBHOOK_URL`), or email
(`--email` / `SWING_EMAIL_TO` with `SWING_SMTP_HOST`, `SWING_SMTP_PORT`,
`SWING_SMTP_USER`, `SWING_SMTP_PASSWORD`).

For real-ish time, run `scan` once after the close and `watch` during the
session:

```cron
10 16 * * 1-5  cd /path/to/Insider-Screener && python3 -m swing scan --webhook "$SWING_WEBHOOK_URL"
*/5 10-16 * * 1-5  cd /path/to/Insider-Screener && python3 -m swing watch --once --webhook "$SWING_WEBHOOK_URL"
```

Times are US/Eastern; the daily bar for a session is only final after the close,
so the entry decision is genuinely an after-close decision with a next-open fill.

## How the simulation avoids flattering itself

* Signals come from bar *t*'s close and fill at bar *t+1*'s open.
* Causality is enforced by test: appending future bars must not change any
  already-computed indicator or signal (`tests/test_strategy.py`).
* A gap through the stop fills at the open, not at the stop price.
* A bar touching both stop and target is assumed to have hit the stop first.
* Slippage is charged both ways; whole shares only; idle cash earns nothing.
* Walk-forward parameters are chosen only on data preceding each test window.

```
python3 -m pytest tests/ -q      # 28 tests
```

## What this does not account for

* **Survivorship.** The default universe is names that were already liquid in
  2004, which keeps the *selection* honest — the backtest is not picking stocks
  because of what happened after 2005. But every name in it still trades in
  2026, so the era's outright failures are missing, and eight symbols
  (acquisitions and de-listings) dropped out of the fetch entirely. Real
  results would be somewhat worse than shown.
* **Taxes.** 421 trades held ~5 sessions each are short-term gains, taxed as
  income. The comparison against buy-and-hold gets worse after tax, not better.
* **Multiple testing.** Nine setups and sixteen variants were tried before
  settling on this one. The walk-forward controls for tuning *within* the
  chosen strategy, not for the strategy having been chosen after looking.
* **Data.** One free source (Yahoo), adjusted by scaling OHLC by the
  adjusted-close ratio. No fundamentals, no earnings dates, no corporate
  actions beyond splits and dividends.

## Where an edge might actually come from

The signal here is a transform of price, competing against everyone else's
transform of price, and it clears costs by a hair. The repo's original premise —
Form 4 and 13 filings — is a *different information source* rather than another
rearrangement of the same one, which is the more promising direction: cluster
insider buying has documented abnormal returns, and the filing timestamp gives a
defensible reason the information is not yet in the price.

The harness is built for that. `python3 -m swing edge` will measure any signal
against the same control on the same terms, and if an insider-derived signal
shows an edge materially larger than +0.26% per trade, it becomes worth trading
all-in — because at that point the edge, not the spread, is what you are
collecting.
