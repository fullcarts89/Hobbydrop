"""Unit tests for the conviction scorer and corrected window labelling."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import Filing  # noqa: E402
import scorer  # noqa: E402
import notifier  # noqa: E402


def _form4(**kw) -> Filing:
    base = dict(
        accession="0000000000-26-000001", filing_type="4", form_raw="4",
        filing_url="http://x", filed_date="2026-06-26", issuer_cik="1",
        issuer_name="Acme", ticker="ACME", owner_cik="2", filer_name="Jane Doe",
        insider_title="CEO", role_label="CEO", transaction_code="P",
        trade_price=10.0, shares=20000, trade_value=200000, trade_date="2026-06-25",
        market_cap=1_000_000, days_since_last_8k=70, cluster_count=0,
        price_delta_pct=2.0,
    )
    base.update(kw)
    return Filing(**base)


def test_relative_size_bands():
    # 200k / 1,000,000 mkt cap = 20% -> top band
    f = _form4(trade_value=200_000, market_cap=1_000_000)
    _, bd = scorer.score_filing(f)
    assert bd["relative_size"] == 25


def test_news_vacuum_bands():
    assert scorer._news_vacuum_points(70) == 20
    assert scorer._news_vacuum_points(30) == 14
    assert scorer._news_vacuum_points(14) == 8
    assert scorer._news_vacuum_points(7) == 4
    assert scorer._news_vacuum_points(3) == 0


def test_role_points():
    assert scorer._match_role("Chief Executive Officer") == 18
    assert scorer._match_role("CFO") == 16
    assert scorer._match_role("Director") == 10
    assert scorer._match_role("Random Title") == 4


def test_window_points_signing():
    assert scorer._window_points(2) == 10       # near entry
    assert scorer._window_points(10) == 6        # up 10%
    assert scorer._window_points(-10) == 4       # underwater
    assert scorer._window_points(40) == 0        # ran away
    assert scorer._window_points(None) == 0


def test_window_label_fixes_negative_bug():
    # The spec draft mislabelled -10% as DEVELOPING; it must be INVERTED.
    assert notifier.window_label(-10) == "🔵 INVERTED"
    assert notifier.window_label(2) == "🟢 OPEN"
    assert notifier.window_label(10) == "🟡 DEVELOPING"
    assert notifier.window_label(40) == "🔴 CLOSED"
    assert notifier.window_label(None) == "⚪ UNKNOWN"


def test_high_conviction_total_clears_threshold():
    f = _form4(
        trade_value=200_000, market_cap=1_000_000,  # 20% -> 25
        days_since_last_8k=70,                        # -> 20
        insider_title="CEO",                          # -> 18
        cluster_count=3,                              # -> 14
        is_first_open_market_purchase=True,           # -> 13
        price_delta_pct=1.0,                          # -> 10
    )
    total, _ = scorer.score_filing(f)
    assert total == 100


def test_13g_passive_scores_low_intent():
    f = Filing(
        accession="0000000000-26-000009", filing_type="13G", form_raw="SCHEDULE 13G",
        filing_url="http://x", filed_date="2026-06-26", issuer_cik="1",
        issuer_name="Acme", ticker="ACME", filer_kind="fund",
        percent_of_class=6.0, market_cap=1_000_000, trade_value=60_000,
        days_since_last_8k=5,
    )
    _, bd = scorer.score_filing(f)
    assert bd["intent"] == 4
    assert bd["filer_quality"] == 8
