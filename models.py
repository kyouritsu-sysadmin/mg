from fields import MaterialsInfo
from fields import FunctionalExplanation
from fields import AdditionalSystem
from fields import Manufacturing_Spec
from fields import SafetyMeasures
from fields import LegendInfo
from fields import EquipmentSpecs
from fields import PaintingSpec
from fields import Standards
from pydantic import BaseModel, Field
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




class ProjectOverview(BaseModel):
    
    building_overview : BuildingOverviewType

    standards : Standards

    paint_speciications :PaintingSpec


    equipment_specs :EquipmentSpecs

    legend_info : LegendInfo

    safety_measures : SafetyMeasures

    manufacturing_specifications :Manufacturing_Spec

    additional_systems: AdditionalSystem

    functional_explantion: FunctionalExplanation

    materials_information : MaterialsInfo