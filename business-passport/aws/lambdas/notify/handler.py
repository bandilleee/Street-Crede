import os
import sys

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from shared.config import SNS_TOPIC_ARN

sns = boto3.client("sns")


def handler(event, context):
    passport_url = event.get("passport", {}).get("passport_result", {}).get("passport_url", "")
    user_contact = event.get("user_contact", "")
    job_id = event.get("job_id", "")
    score_data = event.get("scored", {}).get("score_result", {})

    message = (
        f"Your Business Passport is ready!\n\n"
        f"Trust Score: {score_data.get('trust_score', 0)}/100 ({score_data.get('badge', 'Bronze')})\n"
        f"Download: {passport_url}\n\n"
        f"Reference: {job_id}"
    )

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=message,
        Subject="Your Business Passport is Ready",
        MessageAttributes={
            "contact": {"DataType": "String", "StringValue": user_contact}
        },
    )

    return {"job_id": job_id, "notified": True}
