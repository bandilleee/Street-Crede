import json
import uuid
from datetime import datetime, timezone

import boto3

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from shared.schemas import SubmitPayload
from shared.config import S3_BUCKET, DYNAMODB_TABLE

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")


def handler(event, context):
    try:
        body = json.loads(event.get("body") or event)
        payload = SubmitPayload(**body)
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Store metadata in DynamoDB first (EventBridge trigger reads this)
    table = ddb.Table(DYNAMODB_TABLE)
    table.put_item(Item={
        "job_id": job_id,
        "status": "PENDING",
        "created_at": now,
        "audio_s3_key": f"jobs/{job_id}/audio/{payload.audio_s3_key.split('/')[-1]}",
        "image_s3_keys": [f"jobs/{job_id}/images/{k.split('/')[-1]}" for k in payload.image_s3_keys],
        "social_url": payload.social_url or "",
        "user_contact": payload.user_contact,
    })

    return {
        "statusCode": 202,
        "body": json.dumps({"job_id": job_id, "status": "processing"}),
    }
