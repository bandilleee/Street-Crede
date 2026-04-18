import json
import os
import sys

import boto3
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from shared.config import GCP_SA_SECRET_NAME, CLOUD_RUN_URL

_sm = boto3.client("secretsmanager")


def _get_gcp_token() -> str:
    secret = _sm.get_secret_value(SecretId=GCP_SA_SECRET_NAME)
    sa_info = json.loads(secret["SecretString"])

    from google.oauth2 import service_account
    import google.auth.transport.requests

    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def handler(event, context):
    route = event["route"]          # "/transcribe" or "/extract-vision"
    payload = event["payload"]

    token = _get_gcp_token()
    url = CLOUD_RUN_URL.rstrip("/") + route

    r = httpx.post(url, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=120)
    r.raise_for_status()
    return r.json()
