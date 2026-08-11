# python-bedrock-image-analyzer
AWS Bedrockを利用した画像解析API。  
FAST APIを使ったAPIで、アップロードされた画像に写っている物体が何か・どこのメーカの製品かを解析する。  

The API analyzes uploaded images using AWS Bedrock.  
Built with FASTAPI, It analyzes the object in the image and return what is this and which company provide the object.  

---

## Architecture

```
[Client] -> POST /analyze (image) -> [FastAPI] -> [AWS Bedrock] -> JSON Response
```

インフラ（AWS Lambda / API Gateway / S3 / IAM）はTerraformで別リポジトリ管理しています。
→ [python-bedrock-image-analyzer-infra](https://github.com/kk-dev-1998/python-bedrock-image-analyzer-infra)
---

## Tech Stach
- Python 3.14
- Fast API
- Amazon Bedrock
- Docker

## Getting Started

### Prerequisites
- AWS Account
- Docker (Optional)

### Setup

1. Clone repository

```bash
git clone https://github.com/kk-dev-1998/python-bedrock-image-analyzer.git
cd python-bedrock-image-analyzer
```

2. Set environment variables

```bash
cp .env.example .env
# Update your AWS credentials
```

3. Create and enable virtual environment

```bash
python -m venv .venv

# Mac/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

4. Install dependencies

```bash
pip install -r requirements.txt
```

5. Launch

```
uvicorn app.main:app --reload
```

5. Open API docs in browser

```
https://localhost:8000/docs
```

### Docker

```bash
# Build
docker build -t bedrock-image-analyzer
# Run
docker run --env-file .env -p 8000:8000 bedrock-image-analyzer
```

## API Endpoints

Post /analyze : 画像解析(Image analysis)

---

## AWS Lambda Deployment
AWS Lambdaを利用する場合は、以下の手順を行う。
If you want to use AWS Lambda, execute the below steps.

### Overview

1. Build the container image for Lambda
```bash
   docker build -t python-bedrock-image-analyzer .
```
2. Push the image to ECR
3. Run `terraform apply` in the infra repository (provisions Lambda / API Gateway / S3 / IAM)

Environment variables (region, Bedrock inference profile ID, etc.) are configured automatically
by Terraform, so no manual setup in the Lambda console is required.

> Note: Since a container started with Docker uses the Lambda runtime format,
> it cannot be accessed directly as an HTTP server via `docker run`.
> For local testing, use the uvicorn startup described in "Getting Started" above.