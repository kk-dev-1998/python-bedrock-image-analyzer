import boto3
import os
import logging
import json
from dotenv import load_dotenv
from pathlib import Path

from app.schemas import ImageAnalysisResult

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def load_prompt() -> str:
    prompt_path = Path(__file__).parent / "prompts" / "analyze_image.txt"
    if not prompt_path.exists():
        logger.warning(f"Prompt file not found at {prompt_path}. Using default prompt.")
        return "Analyze the following image and provide insights."
    
    return prompt_path.read_text(encoding="utf-8")

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

    bedrock_client = boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_USER_DEFAULT_REGION", "us-east-1")
    )

    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

    #generate request
    message ={
        {
            "role": "user",
            "content": [
                {
                    "text": load_prompt()
                },
                {
                    "type": "image",
                    "image": {
                        "source": {
                            bytes: image_data                        },
                        "format": image_format
                    }
                }
            ]
        }
    }

    messages = [message]

    inference_config = {
        "topP": 0.8,
        "topK": 20
    }

    response = bedrock_client.converse(
        modelId = model_id,
        messages = messages,
        inferenceConfig = inference_config
    )

    response_body = json.loads(response["body"].read())
    response_text = response_body["output"]["message"]["content"][0]["text"]

    clean_text = response_text.strip()
    if clean_text.startswith("```"):
        clean_text = clean_text.split("\n", 1)[1]
    if clean_text.endswith("```"):
        clean_text = clean_text.rsplit("```", 1)[0]
    clean_text = clean_text.strip()

    validated_result = parse_and_validate_response(clean_text)

    return {
        "success": True,
        "analysis": validated_result,
        "model_used": model_id
    }