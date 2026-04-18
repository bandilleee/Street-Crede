import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aws.lambdas.score.handler import handler, _badge, _parse_months


def _event(transactions=30, avg_amount=200.0, date_range="Jan 2023 - Jan 2025",
           sentiment=0.8, has_audio=True, has_reviews=True):
    return {
        "vision_result": {"transactions": transactions, "avg_amount": avg_amount, "date_range": date_range},
        "synthesized": {"synthesis_result": {"sentiment_score": sentiment}},
        "transcript_result": {"transcript": "hello" if has_audio else ""},
        "scrape_result": {"reviews": ["good"] if has_reviews else [], "follower_count": 100},
    }


# Badge boundary tests
def test_badge_bronze():   assert _badge(49) == "Bronze"
def test_badge_silver():   assert _badge(50) == "Silver"
def test_badge_gold():     assert _badge(70) == "Gold"
def test_badge_platinum(): assert _badge(85) == "Platinum"


def test_parse_months_year_range():
    assert _parse_months("Jan 2022 - Jan 2024") == 24


def test_score_high_activity_returns_gold_or_platinum():
    result = handler(_event(transactions=60, avg_amount=500.0, sentiment=0.9), {})
    assert result["trust_score"] >= 70
    assert result["badge"] in ("Gold", "Platinum")


def test_score_low_activity_returns_bronze():
    result = handler(_event(transactions=5, avg_amount=50.0, date_range="Mar 2025",
                            sentiment=0.2, has_audio=False, has_reviews=False), {})
    assert result["badge"] == "Bronze"


def test_revenue_calculation():
    # 30 transactions × R200 × 4 (weekly) = R24,000
    result = handler(_event(transactions=30, avg_amount=200.0, date_range="weekly Jan-Mar 2024"), {})
    assert result["monthly_revenue_estimate"] == 24000.0


def test_score_capped_at_100():
    result = handler(_event(transactions=200, avg_amount=1000.0, sentiment=1.0), {})
    assert result["trust_score"] <= 100
