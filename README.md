# python-bedrock-image-analyzer
AWS Bedrockを利用した画像解析API
FAST APIを使ったAPIで、画像に写っている物体が何でどこの物かを解析する

The API analyzes uploaded images using AWS Bedrock.
It analyzes the object in the image and return what is this and which company provide the object.
Fast API is used for this system.

## Architecture

[Client] -> POST /analyze (image) -> [FastAPI] -> [AWS Bedrock] -> JSON Response

##Tech Stach
- Python 3.14
- Fast API
- AWS Bedrock
- Docker

## Getting Started

### Prerequisites
- AWS Account
- Docker (Optional)

### Setup

1. Clone repository
git clone https://github.com/kk-dev-1998/python-bedrock-image-analyzer.git

2. Set environment variables
cp .env.example .env
# Update your AWS credentials

3. Enable venv

4. Install dependencies
pip install -r requirements.txt

5. Launch
uvicorn app.main:app --reload

5. Check
https://localhost:8000/docs

### Docker
docker build -t bedrock-image-analyzer
docker run --env-file .env -p 8000:8000 bedrock-image-analyzer

## API Endpoints

Post /analyze : 画像解析(Image analysis)

## AWS Lambda
AWS Lambdaを利用する場合は、以下の手順を行う。
If you want to use AWS Lambda, execute the below steps.

### Windows Powershell
1. mkdir lambda-package

2. makdir package

3. xcopy /E /I app lambda-package\package\app

4. docker run --rm --entrypoint pip -v "C:{your-path}\python-bedrock-image-analyzer:/var/task" public.ecr.aws/lambda/python:3.14 ` install -r /var/task/requirements.txt -t /var/task/lambda-package/package

5. Compress the lambda-package as zip
zip -r lambda-package C:{your-path}\python-bedrock-image-analyzer\lambda-package

6. Upload the zip in AWS Lambda

7. Set environment variables
AWS_USER_DEFAULT_REGION: {your prefer region}
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0

8. Update runtime setting
memory: 512MB
timeout: 30 sec

