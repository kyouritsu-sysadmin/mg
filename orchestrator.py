from models import EquipmentList
from models import ProjectOverview
from models import ProjectInfo
import asyncio
from tasks import Task
from models import ProjectBase
from pathlib import Path
from runner import run_pipeline



_RULES_PATH = Path(__file__).parent / "rules.md"
ESTIMATION_RULES = (
    _RULES_PATH.read_text(encoding="utf-8").strip() if _RULES_PATH.exists() else ""
)


COMMON_RULES = """\
Domain: Japanese high-voltage power receiving / transformation (受変電) cubicle
construction drawings. A single document may bundle SEVERAL projects; each sheet's
title block (usually bottom-right) names its project and design firm — use it to
tell projects apart and to find project boundaries.

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
        prompt=_with_rules("""
        ROLE: Survey ALL supplied images to map the document's top-level structure.
        Determine how many distinct projects are bundled, where each one starts and ends
        (by reading the title block on every sheet), each project's title and design firm,
        and an approximate cubicle count per project. Populate ProjectBase.
        """),
        target_pages="ALL IMAGES",
        schema=ProjectBase,
        max_turns=10,
        max_attempts=2
    ),

    Task(
        id='project_overview',
        prompt=_with_rules("""
        ROLE: Extract the detailed specification overview — standards, painting, equipment,
        legend, safety, manufacturing, additional systems, functional explanation and
        materials, per the ProjectOverview schema. This data lives on the specification
        sheets (特記仕様書 / 仕様表) that come BEFORE the single-line diagrams (SLD). Fill each
        field using its schema description as the locator.
        """),
        target_pages="ALL IMAGES",
        schema=ProjectOverview,
        max_turns=10,
        max_attempts=2
    ),

    Task(
        id='equipment_extraction',
        prompt=_with_rules("""
        ROLE: Extract each electrical device and its rating (真空遮断器/VCB, 高圧交流負荷開閉器/LBS,
        変圧器/Tr, 進相コンデンサ/SC, 直列リアクトル/SR, VT, CT, etc.) plus transformer specs and
        counts, strictly per the ProjectInfo schema. This data is densest on the single-line
        diagram (単線結線図) and the 機器仕様 tables.
        """, include_estimation=True),
        target_pages="ALL IMAGES",
        schema=ProjectInfo,
        max_turns=10,
        max_attempts=2
    ),
    Task(
        id='equipment_listing',
        prompt=_with_rules("""
        ROLE:Gather the information about the total cubicle in the project and equipments in that cubicle and create a list of the equipment based on the cubicle
            Example: 
             " Cubicle 1" : Equipment 1
             " Cubicle 1" : Equipment 2
             " Cubicle 1" : Equipment 3
             " Cubicle 2" : Equipment 1
             " Cubicle 2" : Equipment 2
             " Cubicle 2" : Equipment 3
             " Cubicle 3" : Equipment 1
        """, include_estimation=True),
        target_pages="ALL IMAGES",
        schema=EquipmentList,
        max_turns=10,
        max_attempts=2
    )
]


async def run_agents(ImageListPath: Path, Project_name: str | None, tasks: list[Task] = BASE_TASKS):
    project_name = Project_name or "New project"

    imagePath = [str(p) for p in sorted(ImageListPath.glob("page_*.png"))]
    if not imagePath:
        raise ValueError(f"No page_*.png images found in {ImageListPath}")

    results = await run_pipeline(
        tasks=tasks,
        ImageList=imagePath,
        project_name=project_name,
        system_prompt=COMMON_RULES,
    )

    return {"results": results, "total_tasks": len(tasks)}