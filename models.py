from click.types import DateTime
from pydantic import BaseModel, Field
from typing import Optional, Literal


# class Confidence(BaseModel):
#     low : str =  Field(description='Low confidence')
#     high  : str =  Field(description='High confidence')

# class AgentResponse(BaseModel):
#     title: str = Field(description='Title of the session mapping to the title')
#     confidence : Literal["high", "medium", "low"]

# class CubicleReference(BaseModel):
#     air_vent : Optional[bool] = None
#     bird_net :  Optional[bool] = None
#     bird_net_material :  Optional[bool] = None
#     cubicle_material : str
#     cubicleinfo : List[CubicleInfo]

class UserData(BaseModel):
    pass

class SessionData(BaseModel):
    project_name: str
    project_description : str | Optional[None]
    
class ProjectBase(BaseModel):
    id : str
    project_title : str
    number_of_pages: int
    number_of_projects: int
    project_boundries : dict[str, int]
    project_titles : dict[str, str]
    project_descriptions : dict[str,str]
    cubicle_count_in_each_project : dict[str,int]
    unique_info : str
    design_firm: str



class CubicleInfo(BaseModel):
    cubicle_name: str
    power_specification : str
    cubicle_type : str


# class LegendInfo(BaseModel):
#     symbol : str
#     name : str
class TransformerSpec(BaseModel):
    power_rating_kva:   Optional[float] = None
    primary_voltage_kv: Optional[float] = None
    secondary_voltage_v: Optional[float] = None
    specifications:     Optional[str]   = None

class ProjectInfo(BaseModel):
    project_title : str
    design_firm : str 
    date: int
    cubicle_info : list[CubicleInfo]
    cubicle_count : int
    project_location: str
    transformer_count: int
    transformers:      list[TransformerSpec]
    confidence:        Literal["high", "medium", "low"]



