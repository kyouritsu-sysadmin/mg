from pydantic import Field
from pydantic import BaseModel

class Confidence(BaseModel):
    low : str =  Field(description='Low confidence')
    high  : str =  Field(description='High confidence')


class TurnResponse(BaseModel):
    title: str = Field(description='Title of the project')
    confidence : str = Confidence