import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Stub heavy ML deps before importing the app
for mod in ["faster_whisper", "transformers", "torch", "PIL", "PIL.Image", "accelerate"]:
    sys.modules.setdefault(mod, MagicMock())


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    # Patch httpx.AsyncClient used inside the routes
    with patch("gcp.inference_gateway.main._get_whisper"), \
         patch("gcp.inference_gateway.main._get_qwen"):
        from gcp.inference_gateway.main import app
        return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_transcribe(client):
    mock_segment = MagicMock()
    mock_segment.text = "Hello world"
    mock_info = MagicMock()
    mock_info.language = "en"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], mock_info)

    mock_response = MagicMock()
    mock_response.content = b"fake-audio"
    mock_response.raise_for_status = MagicMock()

    with patch("gcp.inference_gateway.main._get_whisper", return_value=mock_model), \
         patch("httpx.AsyncClient") as mock_client_cls, \
         patch("tempfile.NamedTemporaryFile"), \
         patch("os.unlink"):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        r = client.post("/transcribe", json={"audio_url": "https://s3.example.com/audio.ogg"})

    assert r.status_code == 200
    data = r.json()
    assert "transcript" in data
    assert "language" in data


def test_extract_vision_invalid_model_output(client):
    mock_model = MagicMock()
    mock_processor = MagicMock()
    # processor(...).to("cuda") must return something iterable for **inputs
    mock_inputs = MagicMock()
    mock_inputs.to.return_value = {}
    mock_processor.return_value = mock_inputs
    mock_processor.decode.return_value = "no json here"
    mock_model.generate.return_value = [MagicMock()]

    mock_response = MagicMock()
    mock_response.content = b"fake-image-bytes"
    mock_response.raise_for_status = MagicMock()

    with patch("gcp.inference_gateway.main._get_qwen", return_value=(mock_model, mock_processor)), \
         patch("httpx.AsyncClient") as mock_client_cls, \
         patch("PIL.Image.open", return_value=MagicMock()):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        r = client.post("/extract-vision", json={"image_urls": ["https://s3.example.com/img.jpg"]})

    assert r.status_code == 422
