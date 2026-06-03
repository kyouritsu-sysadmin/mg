from fields import MaterialsInfo
from fields import FunctionalExplanation
from fields import AdditionalSystem
from fields import Manufacturing_Spec
from fields import SafetyMeasures
from fields import LegendInfo
from fields import EquipmentSpecs
from fields import PaintingSpec
from fields import Standards
from pydantic import BaseModel
from typing import Optional, Literal
from fields import BuildingOverviewType

class ProjectCreate(BaseModel):
    name: str

class ProjectResponse(BaseModel):
    project_id: str
    name: str
    workspace_path: str

class UserData(BaseModel):
    pass

class SessionData(BaseModel):
    project_name: str
    project_description : str | Optional[None]
    

# task : project_exploration
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


# equipment listing 
class EquipmentList(BaseModel):
    results : list[dict]


class TransformerSpec(BaseModel):
    power_rating_kva:   Optional[float] = None
    primary_voltage_kv: Optional[float] = None
    secondary_voltage_v: Optional[float] = None
    specifications:     Optional[str]   = None
    meters:  list[dict[str, str]] | None = None

class CubicleInfo(BaseModel):
    cubicle_name: str
    power_specification : str
    cubicle_type : str
    meters : list[dict[str, str]] | None = None
    ct_scanners : list[dict[str, str]] | None = None
    lbs : dict[str, str] | None = None 


class BreakerList(BaseModel):
    cubicle_name : str
    cubicle_type: str
    transformer : str
    type : str
    poles : int 
    af : str |None
    at : str | None 
    main_line_number : str 
    load_name : str | None
    capacity: str
    switch_capacity: str 
    main_line_size : str | None
    remarks : str | None


# equipment_extraction
class ProjectInfo(BaseModel):

    project_title : str
    design_firm : str 
    date: int
    cubicle_info : list[CubicleInfo]
    cubicle_count : int
    project_location: str
    transformer_count: int
    transformers: list[TransformerSpec]
    breakerlist : list[BreakerList]
    confidence: Literal["high", "medium", "low"]



# project_overview 
class ProjectOverview(BaseModel):

    building_overview : BuildingOverviewType | None = None
    standards : Standards | None = None
    paint_specifications :PaintingSpec| None = None
    equipment_specs :EquipmentSpecs| None = None
    legend_info : LegendInfo| None = None
    safety_measures : SafetyMeasures | None = None
    manufacturing_specifications :Manufacturing_Spec | None = None
    additional_systems: AdditionalSystem| None = None
    functional_explantion: FunctionalExplanation| None = None
    materials_information : MaterialsInfo| None = None