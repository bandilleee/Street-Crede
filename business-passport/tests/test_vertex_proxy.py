import json
import sys, os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.update({
    "GCP_SA_SECRET_NAME": "gcp-sa-test",
    "VERTEX_PROJECT": "my-project",
    "VERTEX_REGION": "us-central1",
    "VERTEX_ENDPOINT_ID": "1234567890",
})

MOCK_SYNTHESIS = {
    "sentiment_score": 0.82,
    "business_profile": {"sector": "Retail", "location": "Lagos", "duration": "2 years"},
    "summary": "A thriving retail business. Strong customer base. Growing revenue.",
    "recommendations": ["Add more payment screenshots", "Respond to reviews", "Expand online presence"],
}

MOCK_VERTEX_RESPONSE = {
    "choices": [{"message": {"content": json.dumps(MOCK_SYNTHESIS)}}]
}


def _make_mocks():
    sm_mock = MagicMock()
    sm_mock.get_secret_value.return_value = {"SecretString": json.dumps({"type": "service_account"})}
    http_mock = MagicMock()
    http_mock.json.return_value = MOCK_VERTEX_RESPONSE
    http_mock.raise_for_status = MagicMock()
    return sm_mock, http_mock


def test_vertex_proxy_returns_synthesis_result():
    sm_mock, http_mock = _make_mocks()

    with patch("boto3.client", return_value=sm_mock), \
         patch("google.oauth2.service_account.Credentials.from_service_account_info") as mock_creds, \
         patch("google.auth.transport.requests.Request"), \
         patch("httpx.post", return_value=http_mock):

        mock_creds.return_value.token = "fake-token"
        mock_creds.return_value.refresh = MagicMock()

        from aws.lambdas.vertex_proxy.handler import handler
        result = handler({
            "transcript_result": {"transcript": "We sell clothes", "language": "en"},
            "vision_result": {"transactions": 30, "date_range": "Jan-Mar 2024", "avg_amount": 200.0},
            "scrape_result": {"reviews": ["Great shop!"], "follower_count": 500, "platform": "facebook"},
        }, {})

    assert result["sentiment_score"] == 0.82
    assert result["business_profile"]["sector"] == "Retail"
    assert len(result["recommendations"]) == 3
    assert "summary" in result


def test_vertex_proxy_prompt_contains_transcript():
    sm_mock, http_mock = _make_mocks()

    with patch("boto3.client", return_value=sm_mock), \
         patch("google.oauth2.service_account.Credentials.from_service_account_info") as mock_creds, \
         patch("google.auth.transport.requests.Request"), \
         patch("httpx.post", return_value=http_mock) as mock_post:

        mock_creds.return_value.token = "fake-token"
        mock_creds.return_value.refresh = MagicMock()

        from aws.lambdas.vertex_proxy.handler import handler
        handler({
            "transcript_result": {"transcript": "unique-transcript-text-xyz"},
            "vision_result": {},
            "scrape_result": {},
        }, {})

    call_body = mock_post.call_args[1]["json"]
    assert "unique-transcript-text-xyz" in call_body["messages"][0]["content"]
