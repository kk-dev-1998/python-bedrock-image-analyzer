import boto3
import os
import logging
import json
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image
import io

from app.schemas import ImageAnalysisResult

MAX_DIMENSION = 8000  # Bedrock limit
TARGET_MAX_DIMENSION = 1568  # Claude's recommended max (balance of image recognition accuracy and cost)
MAX_ATTEMPTS = 2  # 1 retry when the model output fails JSON parsing / validation

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def resize_image_if_needed(image_data: bytes, image_format: str) -> bytes:
    """Resize the image if it exceeds Bedrock's limit or is otherwise too large"""
    img = Image.open(io.BytesIO(image_data))
    width, height = img.size

    if max(width, height) <= TARGET_MAX_DIMENSION:
        return image_data

    scale = TARGET_MAX_DIMENSION / max(width, height)
    new_size = (int(width * scale), int(height * scale))
    resized_img = img.resize(new_size, Image.LANCZOS)

    buffer = io.BytesIO()
    save_format = "JPEG" if image_format in ("jpeg", "jpg") else image_format.upper()
    resized_img.save(buffer, format=save_format)
    return buffer.getvalue()

def load_prompt() -> str:
    prompt_path = Path(__file__).parent / "prompts" / "analyze_image.txt"
    if not prompt_path.exists():
        logger.warning(f"Prompt file not found at {prompt_path}. Using default prompt.")
        return "Analyze the following image and provide insights."
    
    return prompt_path.read_text(encoding="utf-8")

def clean_response_text(response_text: str) -> str:
    """Strip surrounding whitespace and a Markdown code fence, if present."""
    clean_text = response_text.strip()
    if clean_text.startswith("```"):
        clean_text = clean_text.split("\n", 1)[1]
    if clean_text.endswith("```"):
        clean_text = clean_text.rsplit("```", 1)[0]
    return clean_text.strip()

def parse_and_validate_response(response_text: str) -> ImageAnalysisResult:
    try:
        data = json.loads(response_text.strip())
        return ImageAnalysisResult(**data)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON response: {response_text}")
        raise ValueError("Bedrock returned invalid JSON")
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise ValueError(f"Response validation failed: {str(e)}")
  

def analyze_image(image_data: bytes, image_format: str) -> dict:

    image_data = resize_image_if_needed(image_data, image_format)
    
    bedrock_client = boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
    )

    model_id = os.getenv("BEDROCK_MODEL_ID", "jp.anthropic.claude-haiku-4-5-20251001-v1:0")

    #generate request
    message ={
        "role": "user",
        "content": [
            {
                "text": load_prompt()
            },
            {
                "image": {
                    "source": {
                        "bytes": image_data
                    },
                    "format": image_format
                }
            }
     ]
    }

    messages = [message]

    inference_config = {
        "topP": 0.8
    }

    # The model occasionally breaks the output contract (e.g. "detail" over 50 chars).
    # Retry once so a one-off format slip does not surface as an error to the caller.
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = bedrock_client.converse(
            modelId = model_id,
            messages = messages,
            inferenceConfig = inference_config
        )
        clean_text = clean_response_text(response["output"]["message"]["content"][0]["text"])
        try:
            validated_result = parse_and_validate_response(clean_text)
            break
        except ValueError as e:
            if attempt == MAX_ATTEMPTS:
                raise
            logger.warning(f"Output rejected (attempt {attempt}/{MAX_ATTEMPTS}), retrying: {e}")

    return {
        "success": True,
        "analysis": validated_result,
        "model_used": model_id
    }