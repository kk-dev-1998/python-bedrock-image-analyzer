import boto3
import os
import logging
import json
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def analyze_image(image_data: bytes, prompt: str, image_format: str) -> dict:

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
                    "text": prompt
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

    return {
        "success": True,
        "analysis": clean_text,
        "model_used": model_id
    }