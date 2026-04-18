import sys, os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SAMPLE_HTML = """
<html><body>
  <div class="review-item">Great service, very fast!</div>
  <div class="review-item">Trusted seller, 5 stars.</div>
  <span>1,234 followers</span>
</body></html>
"""


def test_scrape_returns_structured_data():
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_HTML
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_resp):
        from aws.lambdas.scrape.handler import handler
        result = handler({"url": "https://facebook.com/mybiz"}, {})

    assert isinstance(result["reviews"], list)
    assert result["platform"] == "facebook"
    assert isinstance(result["follower_count"], int)


def test_scrape_fallback_on_error():
    with patch("httpx.get", side_effect=Exception("timeout")):
        from aws.lambdas.scrape.handler import handler
        result = handler({"url": "https://facebook.com/mybiz"}, {})

    assert result == {"reviews": [], "follower_count": 0, "platform": "unknown"}


def test_scrape_empty_url():
    from aws.lambdas.scrape.handler import handler
    result = handler({}, {})
    assert result == {"reviews": [], "follower_count": 0, "platform": "unknown"}
