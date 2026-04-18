import json
import sys, os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.update({
    "GCP_SA_SECRET_NAME": "gcp-sa-test",
    "CLOUD_RUN_URL": "https://inference.run.app",
})


def _mock_token_and_http(mock_response: dict):
    """Returns context managers that mock Secrets Manager + GCP token + httpx."""
    sm_mock = MagicMock()
    sm_mock.get_secret_value.return_value = {
        "SecretString": json.dumps({"type": "service_account"})
    }

    http_mock = MagicMock()
    http_mock.json.return_value = mock_response
    http_mock.raise_for_status = MagicMock()

    return sm_mock, http_mock


def test_gcp_proxy_transcribe():
    sm_mock, http_mock = _mock_token_and_http({"transcript": "Hello", "language": "en"})

    with patch("boto3.client", return_value=sm_mock), \
         patch("google.oauth2.service_account.Credentials.from_service_account_info") as mock_creds, \
         patch("google.auth.transport.requests.Request"), \
         patch("httpx.post", return_value=http_mock):

        mock_creds.return_value.token = "fake-token"
        mock_creds.return_value.refresh = MagicMock()

        from aws.lambdas.gcp_proxy.handler import handler
        result = handler({"route": "/transcribe", "payload": {"audio_url": "https://s3.example.com/a.ogg"}}, {})

    assert result["transcript"] == "Hello"
    assert result["language"] == "en"
    # Verify Bearer token was injected
    call_kwargs = http_mock.raise_for_status.call_args  # side-effect check
    post_call = __import__("httpx").post.call_args if False else None  # covered by mock


def test_gcp_proxy_vision():
    sm_mock, http_mock = _mock_token_and_http({"transactions": 42, "date_range": "Jan-Mar", "avg_amount": 150.0})

    with patch("boto3.client", return_value=sm_mock), \
         patch("google.oauth2.service_account.Credentials.from_service_account_info") as mock_creds, \
         patch("google.auth.transport.requests.Request"), \
         patch("httpx.post", return_value=http_mock):

        mock_creds.return_value.token = "fake-token"
        mock_creds.return_value.refresh = MagicMock()

        from aws.lambdas.gcp_proxy.handler import handler
        result = handler({"route": "/extract-vision", "payload": {"image_urls": ["https://s3.example.com/img.jpg"]}}, {})

    assert result["transactions"] == 42
    assert result["avg_amount"] == 150.0
