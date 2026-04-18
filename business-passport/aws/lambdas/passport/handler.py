import io
import os
import sys
from datetime import datetime, timezone

import boto3
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from shared.config import S3_BUCKET, DYNAMODB_TABLE

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")

PRESIGN_EXPIRY = 7 * 24 * 3600  # 7 days


def _build_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    def add(text, style="Normal"):
        story.append(Paragraph(text, styles[style]))
        story.append(Spacer(1, 8))

    profile = data.get("business_profile", {})
    score_data = data.get("scored", {}).get("score_result", {})

    add("Business Passport", "Title")
    add(f"<b>Sector:</b> {profile.get('sector', 'N/A')}")
    add(f"<b>Location:</b> {profile.get('location', 'N/A')}")
    add(f"<b>Operating Since:</b> {profile.get('duration', 'N/A')}")
    add(f"<b>Trust Score:</b> {score_data.get('trust_score', 0)} / 100")
    add(f"<b>Badge:</b> {score_data.get('badge', 'Bronze')}")
    add(f"<b>Est. Monthly Revenue:</b> R{score_data.get('monthly_revenue_estimate', 0):,.2f}")
    add("<b>Summary</b>", "Heading2")
    add(data.get("synthesized", {}).get("synthesis_result", {}).get("summary", ""))
    add("<b>Recommendations</b>", "Heading2")
    for rec in data.get("synthesized", {}).get("synthesis_result", {}).get("recommendations", []):
        add(f"• {rec}")

    doc.build(story)
    return buf.getvalue()


def handler(event, context):
    job_id = event["job_id"]
    pdf_bytes = _build_pdf(event)

    key = f"passports/{job_id}.pdf"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=pdf_bytes, ContentType="application/pdf")

    passport_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=PRESIGN_EXPIRY,
    )

    score_data = event.get("scored", {}).get("score_result", {})
    table = ddb.Table(DYNAMODB_TABLE)
    table.update_item(
        Key={"job_id": job_id},
        UpdateExpression=(
            "SET #s = :s, passport_url = :u, trust_score = :ts, badge = :b, completed_at = :ca"
        ),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "COMPLETE",
            ":u": passport_url,
            ":ts": score_data.get("trust_score", 0),
            ":b": score_data.get("badge", "Bronze"),
            ":ca": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {"job_id": job_id, "passport_url": passport_url}
