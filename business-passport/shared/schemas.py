from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class SubmitPayload(BaseModel):
    audio_s3_key: str
    image_s3_keys: list[str]
    social_url: Optional[str] = None
    user_contact: str  # phone or email


class TranscriptResult(BaseModel):
    transcript: str
    language: str


class VisionResult(BaseModel):
    transactions: int
    date_range: str
    avg_amount: float


class ScrapeResult(BaseModel):
    reviews: list[str] = []
    follower_count: int = 0
    platform: str = "unknown"


class SynthesisResult(BaseModel):
    sentiment_score: float = Field(ge=0.0, le=1.0)
    business_profile: dict  # {sector, location, duration}
    summary: str
    recommendations: list[str]


class PassportRecord(BaseModel):
    job_id: str
    status: str
    trust_score: Optional[int] = None
    badge: Optional[str] = None
    passport_url: Optional[str] = None
    created_at: str
