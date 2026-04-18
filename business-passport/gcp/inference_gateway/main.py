import io
import json
import os
import tempfile

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Lazy-loaded models
_whisper_model = None
_qwen_model = None
_qwen_processor = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    return _whisper_model


def _get_qwen():
    global _qwen_model, _qwen_processor
    if _qwen_model is None:
        from transformers import AutoModelForCausalLM, AutoProcessor
        model_id = "Qwen/Qwen-VL-Chat"
        _qwen_processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        _qwen_model = AutoModelForCausalLM.from_pretrained(
            model_id, device_map="cuda", trust_remote_code=True
        ).eval()
    return _qwen_model, _qwen_processor


class TranscribeRequest(BaseModel):
    audio_url: str


class VisionRequest(BaseModel):
    image_urls: list[str]


@app.post("/transcribe")
async def transcribe(req: TranscribeRequest):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(req.audio_url)
        r.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(r.content)
        tmp_path = f.name

    try:
        model = _get_whisper()
        segments, info = model.transcribe(tmp_path, beam_size=5)
        transcript = " ".join(s.text for s in segments).strip()
    finally:
        os.unlink(tmp_path)

    return {"transcript": transcript, "language": info.language}


@app.post("/extract-vision")
async def extract_vision(req: VisionRequest):
    from PIL import Image

    images = []
    async with httpx.AsyncClient(timeout=60) as client:
        for url in req.image_urls:
            r = await client.get(url)
            r.raise_for_status()
            images.append(Image.open(io.BytesIO(r.content)).convert("RGB"))

    model, processor = _get_qwen()

    # Build multi-image prompt
    image_tags = "".join(f"<img>{i}</img>" for i in range(len(images)))
    prompt = (
        f"{image_tags}\n"
        "Extract financial data from these WhatsApp payment screenshots. "
        "Return ONLY valid JSON: {\"transactions\": <int>, \"date_range\": \"<str>\", \"avg_amount\": <float>}"
    )

    inputs = processor(text=prompt, images=images, return_tensors="pt").to("cuda")
    output_ids = model.generate(**inputs, max_new_tokens=128)
    response = processor.decode(output_ids[0], skip_special_tokens=True)

    # Extract JSON from response
    start = response.find("{")
    end = response.rfind("}") + 1
    if start == -1 or end == 0:
        raise HTTPException(status_code=422, detail="Model did not return valid JSON")

    return json.loads(response[start:end])


@app.get("/health")
def health():
    return {"status": "ok"}
