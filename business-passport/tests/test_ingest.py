import json
import sys, os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.update({"S3_BUCKET": "test-bucket", "DYNAMODB_TABLE": "test-table"})


def test_ingest_returns_job_id():
    mock_table = MagicMock()
    mock_ddb = MagicMock()
    mock_ddb.Table.return_value = mock_table

    with patch("boto3.client"), patch("boto3.resource", return_value=mock_ddb):
        from aws.lambdas.ingest.handler import handler

        event = {
            "body": json.dumps({
                "audio_s3_key": "uploads/voice.ogg",
                "image_s3_keys": ["uploads/img1.jpg", "uploads/img2.jpg"],
                "social_url": "https://facebook.com/mybiz",
                "user_contact": "+27821234567",
            })
        }
        resp = handler(event, {})

    assert resp["statusCode"] == 202
    body = json.loads(resp["body"])
    assert "job_id" in body
    assert body["status"] == "processing"

    # DynamoDB put_item called with correct structure
    call_kwargs = mock_table.put_item.call_args[1]["Item"]
    assert call_kwargs["status"] == "PENDING"
    assert call_kwargs["job_id"] == body["job_id"]
    assert "jobs/" in call_kwargs["audio_s3_key"]
    assert len(call_kwargs["image_s3_keys"]) == 2


def test_ingest_bad_payload_returns_400():
    with patch("boto3.client"), patch("boto3.resource"):
        from aws.lambdas.ingest.handler import handler
        resp = handler({"body": json.dumps({"bad": "data"})}, {})
    assert resp["statusCode"] == 400
