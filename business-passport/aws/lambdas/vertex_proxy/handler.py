import json
import os
import sys

import boto3
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from shared.config import GCP_SA_SECRET_NAME, VERTEX_PROJECT, VERTEX_REGION, VERTEX_ENDPOINT_ID
from shared.schemas import SynthesisResult

_sm = boto3.client("secretsmanager")


def _get_gcp_token() -> str:
    secret = _sm.get_secret_value(SecretId=GCP_SA_SECRET_NAME)
    sa_info = json.loads(secret["SecretString"])

    from google.oauth2 import service_account
    import google.auth.transport.requests

    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _build_prompt(event: dict) -> str:
    transcript = event.get("transcript_result", {}).get("transcript", "")
    vision = event.get("vision_result", {})
    scrape = event.get("scrape_result", {})

    return (
        "You are a business analyst. Analyze the following data and return ONLY valid JSON.\n\n"
        f"Voice transcript: {transcript}\n"
        f"Financial data: {json.dumps(vision)}\n"
        f"Social reviews: {json.dumps(scrape.get('reviews', []))}\n"
        f"Follower count: {scrape.get('follower_count', 0)}\n\n"
        'Return JSON: {"sentiment_score": <float 0-1>, "business_profile": {"sector": "<str>", '
        '"location": "<str>", "duration": "<str>"}, "summary": "<3 sentence summary>", '
        '"recommendations": ["<rec1>", "<rec2>", "<rec3>"]}'
    )


def handler(event, context):
    token = _get_gcp_token()

    url = (
        f"https://{VERTEX_REGION}-aiplatform.googleapis.com/v1/projects/{VERTEX_PROJECT}"
        f"/locations/{VERTEX_REGION}/endpoints/{VERTEX_ENDPOINT_ID}/chat/completions"
    )

    body = {
        "model": "google/gemma-2-9b-it",
        "messages": [{"role": "user", "content": _build_prompt(event)}],
        "max_tokens": 512,
        "temperature": 0.2,
    }

    r = httpx.post(url, json=body, headers={"Authorization": f"Bearer {token}"}, timeout=120)
    r.raise_for_status()

    content = r.json()["choices"][0]["message"]["content"]
    start, end = content.find("{"), content.rfind("}") + 1
    parsed = json.loads(content[start:end])

    result = SynthesisResult(**parsed)
    return result.model_dump()
