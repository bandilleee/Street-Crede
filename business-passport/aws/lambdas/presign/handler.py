import os
import sys

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from shared.config import S3_BUCKET, DYNAMODB_TABLE

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")

EXPIRY = 3600  # 1 hour


def handler(event, context):
    """
    Input:  {"job_id": "..."}
    Output: event enriched with presigned audio_url + image_urls + social_url + user_contact
    """
    job_id = event["job_id"]

    table = ddb.Table(DYNAMODB_TABLE)
    item = table.get_item(Key={"job_id": job_id})["Item"]

    audio_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": item["audio_s3_key"]},
        ExpiresIn=EXPIRY,
    )

    image_urls = [
        s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=EXPIRY,
        )
        for key in item["image_s3_keys"]
    ]

    return {
        "job_id": job_id,
        "audio_url": audio_url,
        "image_urls": image_urls,
        "social_url": item.get("social_url", ""),
        "user_contact": item["user_contact"],
        # pass raw keys for downstream DynamoDB updates
        "audio_s3_key": item["audio_s3_key"],
        "image_s3_keys": item["image_s3_keys"],
    }
