import pytest
import io
from PIL import Image
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

# Dummy images
def make_dummy_image_bytes(format: str = "JPEG", size=(10, 10)) -> bytes:
    img = Image.new("RGB", size, color=(255, 0, 0))
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return buffer.getvalue()

# Dummy response from Bedrock for testing
MOCK_BEDROCK_RESPONSE = {
    "success": True,
    "analysis": {
        "name_of_item": "Laptop",
        "brand": "Apple",
        "color": "Silver",
        "serial_number": "NA",
        "detail": "Dog stecker with a silver body"
    },
    "model_used": "jp.anthropic.claude-haiku-4-5-20251001-v1:0"
}

def test_analyze_invalid_file_type():
    response = client.post(
        "/analyze",
        files={"file": ("test.pdf", make_dummy_image_bytes("JPEG"), "application/pdf")}
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_FILE_TYPE"
    assert response.json()["success"] is False

def test_analyze_valid_jpeg(tmp_path):
    with patch("app.main.analyze_image", return_value=MOCK_BEDROCK_RESPONSE):
       dummy_image = make_dummy_image_bytes(format="JPEG")
       respnse = client.post(
            "/analyze",
            files={"file": ("test.jpg", dummy_image, "image/jpeg")}
        )
       assert respnse.status_code == 200
       assert respnse.json()["success"] is True

def test_analyze_valid_png(tmp_path):
    with patch("app.main.analyze_image", return_value=MOCK_BEDROCK_RESPONSE):
       dummy_image = make_dummy_image_bytes(format="PNG")
       respnse = client.post(
            "/analyze",
            files={"file": ("test.png", dummy_image, "image/png")}
        )
       assert respnse.status_code == 200
       assert respnse.json()["success"] is True

def test_analyze_valid_webp(tmp_path):
    with patch("app.main.analyze_image", return_value=MOCK_BEDROCK_RESPONSE):
       dummy_image = make_dummy_image_bytes(format="WEBP")
       respnse = client.post(
            "/analyze",
            files={"file": ("test.webp", dummy_image, "image/webp")}
        )
       assert respnse.status_code == 200
       assert respnse.json()["success"] is True

def test_analyze_file_too_large():
    large_file = b"0" * (5 * 1024 * 1024 + 1)
    response = client.post(
        "/analyze",
        files={"file": ("large.jpg", large_file, "image/jpeg")}
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "FILE_TOO_LARGE"

def test_analyze_file_exact_limit():
    with patch("app.main.analyze_image", return_value=MOCK_BEDROCK_RESPONSE):
        exact_file = b"0" * (5 * 1024 * 1024)
        response = client.post(
            "/analyze",
            files={"file": ("exact.jpg", exact_file, "image/jpeg")}
        )
        assert response.status_code == 200

def test_analyze_bedrock_invalid_json():
    with patch("app.bedrock.boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client
        mock_client.converse.side_effect = ValueError("Bedrock returned invalid JSON")
        response = client.post(
            "/analyze",
            files={"file": ("test.jpg", make_dummy_image_bytes("JPEG"), "image/jpeg")}
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_JSON"

def test_analyze_internal_error():
    with patch("app.bedrock.boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client
        mock_client.converse.side_effect = Exception("Unexpected error")
        response = client.post(
            "/analyze",
            files={"file": ("test.jpg", make_dummy_image_bytes("JPEG"), "image/jpeg")}
        )
        assert response.status_code == 500
        assert response.json()["error_code"] == "INTERNAL_ERROR"

from app.main import detect_image_format

def test_detect_jpeg():
    assert detect_image_format("image/jpeg") == "jpeg"

def test_detect_jpg():
    assert detect_image_format("image/jpg") == "jpeg"

def test_detect_png():
    assert detect_image_format("image/png") == "png"

def test_detect_webp():
    assert detect_image_format("image/webp") == "webp"

from app.bedrock import parse_and_validate_response

def test_parse_valid_json():
    valid_json = '''{
        "name_of_item": "Laptop",
        "brand": "Apple",
        "color": "Silver",
        "serial_number": "",
        "detail": "Dog stecker with a silver body"
    }'''
    result = parse_and_validate_response(valid_json)
    assert result.name_of_item == "Laptop"
    assert result.brand == "Apple"
    assert result.color == "Silver"
    assert result.serial_number == "NA"
    assert result.detail == "Dog stecker with a silver body"

def test_parse_detail_max_length():
    valid_json = '''{
        "name_of_item": "Laptop",
        "brand": "Apple",
        "color": "Silver",
        "serial_number": "",
        "detail": "''' + "A" * 50 + '''"
    }'''
    result = parse_and_validate_response(valid_json)
    assert len(result.detail) == 50

def test_parse_invalid_json():
    with pytest.raises(ValueError, match="Bedrock returned invalid JSON"):
        parse_and_validate_response("invalid json")

def test_parse_missing_field():
    invalid_json = '''{
        "name_of_item": "Laptop",
        "brand": "Apple"
    }'''
    with pytest.raises(ValueError, match="Response validation failed"):
        parse_and_validate_response(invalid_json)

def test_parse_detail_too_long():
    invalid_json = '''{
        "name_of_item": "Laptop",
        "brand": "Apple",
        "color": "Silver",
        "serial_number": "",
        "detail": "''' + "A" * 51 + '''"
    }'''
    with pytest.raises(ValueError, match="detail must be 50 characters or fewer"):
        parse_and_validate_response(invalid_json)