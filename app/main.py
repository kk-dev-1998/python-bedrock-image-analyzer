from fastapi import FastAPI, UploadFile, File, HTTPException
from app.bedrock import analyze_image
from app.schemas import AnalysisResponse
from mangum import Mangum
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.constants import ErrorCode
from app.schemas import ErrorResponse

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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error_code=ErrorCode.VALIDATION_FAILED,
            error_message="Invalid request format: " + str(exc)
        ).model_dump()
    )

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    file: UploadFile = File(...),
):
    #check file type
    supported_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in supported_types:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=ErrorCode.INVALID_FILE_TYPE,
                error_message=f"Unsupported file type: {file.content_type}. Supported types are: {', '.join(supported_types)}"
            ).model_dump()
        )
    
    #check file size
    image_bytes = await file.read()
    if len(image_bytes) > 5 * 1024 * 1024:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=ErrorCode.FILE_TOO_LARGE,
                error_message="File size exceeds the 5MB limit."
            ).model_dump()
        )
    
    image_format = detect_image_format(file.content_type)
    
    try:
        result = analyze_image(image_bytes, image_format)
        return AnalysisResponse(**result)
    except ValueError as value_error:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error_code=ErrorCode.INVALID_JSON,
                error_message=str(value_error)
            ).model_dump()
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                error_message=f"An unexpected error occurred: {str(e)}"
            ).model_dump()
        )

handler = Mangum(app)