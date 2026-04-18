import sys, os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["SNS_TOPIC_ARN"] = "arn:aws:sns:us-east-1:123456789012:passport-notifications"

SAMPLE_EVENT = {
    "job_id": "test-job-123",
    "user_contact": "+27821234567",
    "passport": {"passport_result": {"passport_url": "https://s3.example.com/passports/test-job-123.pdf"}},
    "scored": {"score_result": {"trust_score": 75, "badge": "Gold"}},
}


def test_notify_publishes_to_sns():
    mock_sns = MagicMock()

    with patch("boto3.client", return_value=mock_sns):
        from aws.lambdas.notify.handler import handler
        result = handler(SAMPLE_EVENT, {})

    mock_sns.publish.assert_called_once()
    call_kwargs = mock_sns.publish.call_args[1]
    assert call_kwargs["TopicArn"] == os.environ["SNS_TOPIC_ARN"]
    assert "test-job-123" in call_kwargs["Message"]
    assert "75" in call_kwargs["Message"]
    assert "Gold" in call_kwargs["Message"]
    assert result["notified"] is True
    assert result["job_id"] == "test-job-123"
