from fastapi import FastAPI, UploadFile, File, HTTPException
from app.bedrock import analyze_image
from app.schemas import AnalysisResponse
from mangum import Mangum

app = FastAPI(
    title = "Bedrock Image Analyzer",
    description = "Image analysis using AWS Bedrock API",
    version = "1.0.0"
)

def detect_image_format(content_type: str) -> str:
    format_map = {
        "image/jpeg": "jpeg",
        "image/jpg": "jpeg",
        "image/png": "png",
        "image/webp": "webp"
    }
    return format_map.get(content_type)

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    file: UploadFile = File(...),
    prompt: str = "Describe the content of the image."
):
    #ceck file type
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only JPEG, JPG, PNG, and WEBP are supported."
            )
    
    #check file size
    image_bytes = await file.read()
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400, 
            detail="File size exceeds the 5MB limit."
        )
    
    image_format = detect_image_format(file.content_type)
    
    try:
        result = analyze_image(image_bytes, prompt, image_format)
        return AnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

handler = Mangum(app)