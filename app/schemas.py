from pydantic import BaseModel, field_validator

class ImageAnalysisResult(BaseModel):
    name_of_item: str
    brand: str
    color: str
    serial_number: str
    detail: str

    @field_validator("detail")
    @classmethod
    def detail_max_length(cls, value):
        if value != "NA" and len(value) > 50:
            raise ValueError("detail must be 50 characters or fewer")
        return value
    
    @field_validator("*", mode="before")
    @classmethod
    def empty_to_na(cls, value):
        return value if value else "NA"
    
class AnalysisResponse(BaseModel):
    success: bool
    analysis: ImageAnalysisResult
    model_used: str