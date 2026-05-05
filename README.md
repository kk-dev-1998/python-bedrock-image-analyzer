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

---

## Tech Stach
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
source venv/bin/activate

# Windows
venv\Scripts\activate
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

### Windows Powershell
1. Create build directory

```powershell
mkdir lambda-package
makdir package
```

2. Install dependencies for Linux environment

```powershell
docker run --rm `
  --entrypoint pip `
  -v "C:\{your-path}\python-bedrock-image-analyzer:/var/task" `
  public.ecr.aws/lambda/python:3.11 `
  install -r /var/task/requirements.txt -t /var/task/lambda-package/package
```

3. Copy app directory

```powershell
xcopy /E /I app lambda-package\package\app
```

4. Create zip file
```
Open lambda-package\package in Explorer
→ Select all（Ctrl+A）
→ Right click → Compress to ZIP
```

5. Upload zip to AWS Lambda

6. Set environment variables in Lambda console

```
AWS_USER_DEFAULT_REGION = us-east-1
BEDROCK_MODEL_ID = us.anthropic.claude-haiku-4-5-20251001-v1:0
```

7. Update runtime setting

```
Handler : app.main.handler
Memory  : 512MB
Timeout : 30 sec
```
