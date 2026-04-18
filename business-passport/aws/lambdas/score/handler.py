import re
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


def _parse_months(date_range: str) -> int:
    """Estimate months of operation from a date range string."""
    years = re.findall(r"\b(20\d{2})\b", date_range)
    if len(years) >= 2:
        return max(1, (int(years[-1]) - int(years[0])) * 12)
    months = re.findall(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", date_range, re.I)
    return max(1, len(set(months)))


def _frequency_multiplier(date_range: str) -> float:
    lower = date_range.lower()
    if "week" in lower:
        return 4.0
    if "biweek" in lower or "bi-week" in lower or "fortnight" in lower:
        return 2.0
    return 1.0


def _score_transactions(count: int) -> float:
    if count >= 51:
        return 100.0
    if count >= 11:
        return 60.0
    return 20.0


def _score_longevity(months: int) -> float:
    if months >= 24:
        return 100.0
    if months >= 12:
        return 70.0
    if months >= 6:
        return 40.0
    return 15.0


def _score_evidence(event: dict) -> float:
    score = 0.0
    if event.get("vision_result", {}).get("transactions", 0) > 0:
        score += 40.0  # has payment screenshots
    if event.get("transcript_result", {}).get("transcript"):
        score += 30.0  # has voice note
    if event.get("scrape_result", {}).get("reviews"):
        score += 30.0  # has social reviews
    return score


def _badge(score: int) -> str:
    if score >= 85:
        return "Platinum"
    if score >= 70:
        return "Gold"
    if score >= 50:
        return "Silver"
    return "Bronze"


def handler(event, context):
    vision = event.get("vision_result", {})
    synthesis = event.get("synthesized", {}).get("synthesis_result", {})

    transactions = vision.get("transactions", 0)
    avg_amount = vision.get("avg_amount", 0.0)
    date_range = vision.get("date_range", "")
    sentiment_score = synthesis.get("sentiment_score", 0.0)

    # Revenue
    multiplier = _frequency_multiplier(date_range)
    monthly_revenue = round(transactions * avg_amount * multiplier, 2)

    # Trust score (weighted)
    months = _parse_months(date_range)
    raw = (
        _score_transactions(transactions) * 0.35
        + (sentiment_score * 100) * 0.25
        + _score_longevity(months) * 0.20
        + _score_evidence(event) * 0.20
    )
    trust_score = min(100, max(0, round(raw)))

    return {
        "trust_score": trust_score,
        "badge": _badge(trust_score),
        "monthly_revenue_estimate": monthly_revenue,
    }
