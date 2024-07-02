from pydantic import BaseModel

class ErrorResponseModel(BaseModel):
    status: str
    message: str
    body: dict