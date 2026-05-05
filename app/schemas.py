from pydantic import BaseModel

class AnalysisResponse(BaseModel):
    success: bool
    analysis: str
    model_used: str