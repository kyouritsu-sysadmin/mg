from models import EquipmentList
from models import ProjectOverview
from models import ProjectInfo
import asyncio
import datetime
import json
from typing import Callable
from tasks import Task
from models import ProjectBase
from pathlib import Path
from runner import run_pipeline
from utils import LABEL_SPEC_OVERVIEW, LABEL_SLD, LABEL_BREAKER_LIST
from directories import _log_writer, make_log_writer, SCRATCH_DIR

_RULES_PATH = Path(__file__).parent / "rules.md"
ESTIMATION_RULES = (
    _RULES_PATH.read_text(encoding="utf-8").strip() if _RULES_PATH.exists() else ""
)


COMMON_RULES = """\
Domain: Japanese high-voltage power receiving / transformation (受変電) cubicle
construction drawings. A single document may bundle SEVERAL projects; each sheet's
title block (usually bottom-right) names its project and design firm — use it to
tell projects apart and to find project boundaries.

There will be scenarios that a project have only A SINGLE PAGE or even 50 pages. 
You need to handle them accordingly. 

Strictly restrict on creating more than 5 crops. No more than 5 crops per tasks. 

"Do not write long prose, summaries, or transcribe drawings inside your thinking block. 
Keep your thinking extremely brief, focus only on locating the fields, and directly output the JSON."

Rules:
- Extract ONLY what is visibly present. If a field is absent, return null — never guess or invent.
- Keep Japanese technical terms verbatim (e.g. 真空遮断器, マンセル 5Y7/1); do not translate values.
- Your output MUST validate against the schema provided below the prompt. Read each
  field's description in the schema — it tells you exactly where to look.
- When the schema has a `confidence` field, set it to: "high" when read directly off
  the sheet, "medium" when inferred from context, "low" when partially legible or ambiguous.
"""



def _with_rules(body: str, include_estimation: bool = False) -> str:
    """Compose a task prompt: the per-task ROLE body (+ task-scoped estimation rules).

    COMMON_RULES is NOT included here — it is supplied once as the session
    system prompt (see run_agents), so it is not duplicated across tasks.
    """
    parts = [body.strip()]
    if include_estimation and ESTIMATION_RULES:
        parts.append(f"Estimation rules (apply strictly):\n{ESTIMATION_RULES}")
    return "\n\n".join(parts)


BASE_TASKS = [

    Task(
        id='project_exploration',
        group=1,
        prompt=_with_rules("""
        ROLE: Survey ALL supplied images to map the document's top-level structure.
        Determine how many distinct projects are bundled, where each one starts and ends
        (by reading the title block on every sheet), each project's title and design firm,
        and an approximate cubicle count per project. Populate ProjectBase.
        """),
        target_pages="ALL IMAGES",
        page_types=[],                
        schema=ProjectBase,
        max_turns=5,
        max_attempts=2
    ),

    Task(
        id='project_overview',
        group=1,
        prompt=_with_rules("""
        ROLE: Extract the detailed specification overview — standards, painting, equipment,
        legend, safety, manufacturing, additional systems, functional explanation and
        materials, per the ProjectOverview schema. This data lives on the specification
        sheets (特記仕様書 / 仕様表) that come BEFORE the single-line diagrams (SLD). Fill each
        field using its schema description as the locator.
        """),
        target_pages="Pages Before the SLDs and breaker list",
        page_types=[LABEL_SPEC_OVERVIEW],
        schema=ProjectOverview,
        max_turns=5,
        max_attempts=2
    ),

    Task(
        id='equipment_extraction',
        group=2,
        prompt=_with_rules("""
        ROLE: Extract each electrical device and its rating (真空遮断器/VCB, 高圧交流負荷開閉器/LBS,
        変圧器/Tr, 進相コンデンサ/SC, 直列リアクトル/SR, VT, CT, etc.) plus transformer specs and
        counts, strictly per the ProjectInfo schema. This data is densest on the single-line
        diagram (単線結線図) and the 機器仕様 tables.
        """, include_estimation=True),
        target_pages="Pages with SLDs and Breaker(MCCB) list",
        page_types=[LABEL_SLD, LABEL_BREAKER_LIST],
        schema=ProjectInfo,
        max_turns=5,
        max_attempts=2
    ),

    Task(
        id='equipment_listing',
        group=2,
        prompt=_with_rules("""
        ROLE: Gather the information about the total cubicle in the project and the
        equipment in each cubicle and create a flat list keyed by cubicle name.
        Example:
          "Cubicle 1": Equipment 1
          "Cubicle 1": Equipment 2
          "Cubicle 2": Equipment 1
        """, include_estimation=True),
        target_pages="Pages with SLD and Breaker list",
        page_types=[LABEL_SLD, LABEL_BREAKER_LIST],
        schema=EquipmentList,
        max_turns=5,
        max_attempts=2
    ),

]

async def run_agents(ImageListPath: Path, Project_name: str | None, tasks: list[Task] = BASE_TASKS,
                     on_event: Callable[[dict], None] | None = None):
    project_name = Project_name or "New project"

    image_paths = sorted(ImageListPath.glob("page_*.png"))
    if not image_paths:
        raise ValueError(f"No page_*.png images found in {ImageListPath}")

    # Load pre-computed page labels written by pdf_to_images() during conversion.
    # Falls back to 'unknown' for any page that wasn't classified (e.g. old runs).
    labels_file = ImageListPath / "page_labels.json"
    label_map: dict[str, str] = {}
    if labels_file.exists():
        for entry in json.loads(labels_file.read_text()):
            label_map[Path(entry["path"]).name] = entry["label"]

    image_list: list[dict] = [
        {"path": str(p), "page_number": i + 1, "label": label_map.get(p.name, "unknown")}
        for i, p in enumerate(image_paths)
    ]

    # One shared log file for the entire run — both pipeline groups write to it.
    # Set before asyncio.gather so both tasks inherit the ContextVar via context copy.
    
    project_scratch = SCRATCH_DIR / project_name
    project_scratch.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = project_scratch / f"{project_name}_{ts}.jsonl"

    base_writer = make_log_writer(log_path)
    def log_and_callback(event: dict) -> None:
        base_writer(event)
        if on_event:
            try:
                on_event(event)
            except Exception as cb_err:
                print(f"Error in run_agents on_event callback: {cb_err}")

    log_token = _log_writer.set(log_and_callback)
    log = _log_writer.get()
    log({"type": "run_start", "project": project_name,
         "total_tasks": len(tasks), "pages": len(image_list),
         "log_file": str(log_path)})

    # grp_01 = [t for t in tasks if t.group == 1]
    # grp_02 = [t for t in tasks if t.group == 2]

    try:
        
        # result_01 = await asyncio.gather(
        #     run_pipeline(tasks=grp_01, ImageList=image_list,
        #                  project_name=project_name, system_prompt=COMMON_RULES),
            
        # )
        # result_02 = await asyncio.gather(
        #     run_pipeline(tasks=grp_02, ImageList=image_list,
        #                  project_name=project_name, system_prompt=COMMON_RULES),
        # )
        
        
        results = await asyncio.gather(
            run_pipeline(tasks=BASE_TASKS, ImageList=image_list,
                         project_name=project_name, system_prompt=COMMON_RULES),
        )
    
        log({"type": "run_end", "project": project_name, "status": "success"})
        
        # flat_results = []
        # if result_01 and isinstance(result_01, list) and len(result_01) > 0:
        #     flat_results.extend(result_01[0])
        # if result_02 and isinstance(result_02, list) and len(result_02) > 0:
        #     flat_results.extend(result_02[0])

        return {"results": results, "total_tasks": len(tasks)}
    except Exception as e:
        log({"type": "run_end", "project": project_name, "status": "error", "error": str(e)})
        raise
    finally:
        _log_writer.reset(log_token)