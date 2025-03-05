from pydantic import BaseModel, HttpUrl

class SummarizeRequest(BaseModel):
    link: HttpUrl