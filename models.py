from fields import MetersInfo
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
from typing import Literal
from fields import BuildingOverviewType


# ── API / session models ──────────────────────────────────────────────────────
# project_id here is a backend-generated int; never populated by Claude.

class ProjectCreate(BaseModel):
    name: str

class ProjectResponse(BaseModel):
    project_id: int
    name: str
    workspace_path: str

class UserData(BaseModel):
    pass

class SessionData(BaseModel):
    project_id: int
    project_name: str
    project_description: str | None = None


# ── Shared sub-models (nested inside extraction schemas) ──────────────────────
# No project_id here — inherited from the parent extraction model.

class Meters(BaseModel):
    cubicle_name: str
    context: Literal["HV_cubicle", "LV_breaker"]
    meters_info: MetersInfo = None


class TransformerSpec(BaseModel):
    power_rating_kva:    float | None = None
    primary_voltage_kv:  float | None = None
    secondary_voltage_v: float | None = None
    specifications:      str   | None = None
    meters:              list[Meters] | None = None


class CubicleInfo(BaseModel):
    cubicle_id:          int           # read from drawing: circled number ①=1 ②=2 …
    cubicle_name:        str
    power_specification: str
    cubicle_type:        str
    meters:              list[Meters] | None = None
    ct_scanners:         list[dict[str, str]] | None = None
    lbs:                 dict[str, str] | None = None


class BreakerList(BaseModel):
    cubicle_id:       int           # read from drawing: matches parent cubicle's circled number
    cubicle_name:     str
    cubicle_type:     str
    transformer:      str
    meters:           Meters | None = None
    type:             str
    poles:            int
    af:               str | None = None
    at:               str | None = None
    main_line_number: str
    load_name:        str | None = None
    capacity:         str
    switch_capacity:  str
    main_line_size:   str | None = None
    remarks:          str | None = None


# ── Extraction schemas (Claude output — no project_id, backend stamps it) ─────

# task: project_exploration
class ProjectBase(BaseModel):
    project_title:                str
    number_of_pages:              int
    number_of_projects:           int
    project_boundaries:           dict[str, int]   # key = sub-project label, value = page number
    project_titles:               dict[str, str]
    project_descriptions:         dict[str, str]
    cubicle_count_in_each_project: dict[str, int]
    unique_info:                  str
    design_firm:                  str
    confidence:        Literal["high", "medium", "low"]


# task: equipment_extraction
class ProjectInfo(BaseModel):
    project_title:     str
    design_firm:       str
    date:              str | None = None
    project_location:  str
    cubicle_count:     int
    cubicle_info:      list[CubicleInfo]
    transformer_count: int
    transformers:      list[TransformerSpec]
    confidence:        Literal["high", "medium", "low"]


# task: breaker_extraction
class BreakerExtraction(BaseModel):
    breakerlist: list[BreakerList]


# task: project_overview
class ProjectOverview(BaseModel):
    building_overview:            BuildingOverviewType | None = None
    standards:                    Standards | None = None
    paint_specifications:         PaintingSpec | None = None
    equipment_specs:              EquipmentSpecs | None = None
    legend_info:                  LegendInfo | None = None
    safety_measures:              SafetyMeasures | None = None
    manufacturing_specifications: Manufacturing_Spec | None = None
    additional_systems:           AdditionalSystem | None = None
    functional_explantion:        FunctionalExplanation | None = None
    materials_information:        MaterialsInfo | None = None


# task: equipment_listing
class EquipmentRows(BaseModel):
    cubicle_id:     int           # matches CubicleInfo.cubicle_id
    cubicle_name:   str
    equipment_name: str
    specification:  str | None = None
    quantity:       int
    remarks:        str | None = None


class EquipmentList(BaseModel):
    results: list[EquipmentRows]


# ── Utility models ────────────────────────────────────────────────────────────

class CubicleDimensions(BaseModel):
    cubicle_id:   int
    cubicle_name: str
