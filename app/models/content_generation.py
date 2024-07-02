from pydantic import BaseModel, create_model, Field
from typing import List,Optional

class BaseResponse(BaseModel):
    status: str
    message: str

def create_success_response(body_model):
    return create_model(
        f"Success{body_model.__name__}Response",
        body=(body_model, ...),
        __base__=BaseResponse
    )

class CaptionResponse(BaseModel):
    captions: List[str]

    
    
SuccessCaptionsResponse = create_success_response(CaptionResponse)