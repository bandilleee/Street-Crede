import sys, os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.update({"S3_BUCKET": "test-bucket", "DYNAMODB_TABLE": "test-table"})

SAMPLE_EVENT = {
    "job_id": "test-job-123",
    "user_contact": "+27821234567",
    "synthesized": {
        "synthesis_result": {
            "sentiment_score": 0.8,
            "business_profile": {"sector": "Retail", "location": "Lagos", "duration": "2 years"},
            "summary": "A great business. Very reliable. Highly recommended.",
            "recommendations": ["Add more screenshots", "Respond to reviews"],
        }
    },
    "scored": {
        "score_result": {"trust_score": 75, "badge": "Gold", "monthly_revenue_estimate": 15000.0}
    },
}


def test_passport_writes_pdf_to_s3_and_updates_dynamodb():
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://s3.example.com/passports/test-job-123.pdf"
    mock_table = MagicMock()
    mock_ddb = MagicMock()
    mock_ddb.Table.return_value = mock_table

    with patch("boto3.client", return_value=mock_s3), \
         patch("boto3.resource", return_value=mock_ddb):
        from aws.lambdas.passport.handler import handler
        result = handler(SAMPLE_EVENT, {})

    # S3 put_object called with correct key
    put_call = mock_s3.put_object.call_args[1]
    assert put_call["Key"] == "passports/test-job-123.pdf"
    assert put_call["ContentType"] == "application/pdf"
    assert len(put_call["Body"]) > 0  # PDF bytes non-empty

    # DynamoDB updated with COMPLETE status
    update_call = mock_table.update_item.call_args[1]
    assert update_call["ExpressionAttributeValues"][":s"] == "COMPLETE"
    assert update_call["ExpressionAttributeValues"][":ts"] == 75
    assert update_call["ExpressionAttributeValues"][":b"] == "Gold"

    # Returns job_id and passport_url
    assert result["job_id"] == "test-job-123"
    assert "passport_url" in result


def test_passport_pdf_bytes_non_empty():
    """PDF generation produces non-trivial output."""
    from aws.lambdas.passport.handler import _build_pdf
    pdf = _build_pdf(SAMPLE_EVENT)
    assert len(pdf) > 1000  # a real PDF is at least a few KB
    assert pdf[:4] == b"%PDF"
