import io
import json
from unittest.mock import MagicMock

import pytest
from PIL import Image

from app import bedrock

VALID = {
    "name_of_item": "Mug", "brand": "NA", "color": "White",
    "serial_number": "NA", "detail": "NA",
}
TOO_LONG = {**VALID, "detail": "x" * 51}


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


def _converse_response(payload) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return {"output": {"message": {"content": [{"text": text}]}}}


@pytest.fixture
def client(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(bedrock.boto3, "client", lambda *a, **kw: mock_client)
    return mock_client


def test_clean_response_text_strips_code_fence():
    assert bedrock.clean_response_text('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert bedrock.clean_response_text('  {"a": 1}  ') == '{"a": 1}'


def test_valid_output_calls_bedrock_once(client):
    client.converse.return_value = _converse_response(VALID)
    result = bedrock.analyze_image(_png_bytes(), "png")
    assert result["analysis"].name_of_item == "Mug"
    assert client.converse.call_count == 1


def test_detail_too_long_is_retried_once(client):
    client.converse.side_effect = [_converse_response(TOO_LONG), _converse_response(VALID)]
    result = bedrock.analyze_image(_png_bytes(), "png")
    assert result["analysis"].detail == "NA"
    assert client.converse.call_count == 2


def test_invalid_json_is_retried_once(client):
    client.converse.side_effect = [_converse_response("not json"), _converse_response(VALID)]
    result = bedrock.analyze_image(_png_bytes(), "png")
    assert result["success"] is True
    assert client.converse.call_count == 2


def test_gives_up_after_max_attempts(client):
    client.converse.side_effect = [_converse_response(TOO_LONG)] * bedrock.MAX_ATTEMPTS
    with pytest.raises(ValueError, match="50 characters"):
        bedrock.analyze_image(_png_bytes(), "png")
    assert client.converse.call_count == bedrock.MAX_ATTEMPTS


def test_api_errors_are_not_retried_here(client):
    client.converse.side_effect = RuntimeError("ThrottlingException")
    with pytest.raises(RuntimeError):
        bedrock.analyze_image(_png_bytes(), "png")
    assert client.converse.call_count == 1
