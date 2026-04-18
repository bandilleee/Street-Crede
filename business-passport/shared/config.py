import os


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# AWS
S3_BUCKET = get("S3_BUCKET")
DYNAMODB_TABLE = get("DYNAMODB_TABLE", "business-passport-jobs")
SNS_TOPIC_ARN = get("SNS_TOPIC_ARN")

# GCP
GCP_SA_SECRET_NAME = get("GCP_SA_SECRET_NAME", "gcp-service-account")
CLOUD_RUN_URL = get("CLOUD_RUN_URL")
VERTEX_PROJECT = get("VERTEX_PROJECT")
VERTEX_REGION = get("VERTEX_REGION", "us-central1")
VERTEX_ENDPOINT_ID = get("VERTEX_ENDPOINT_ID")
