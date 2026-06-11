import base64
import io
import uuid
import datetime
import json
import asyncio
from pathlib import Path
from typing import Callable
from PIL import Image

from singleton import first_turn, run_phase2
from models import EquipmentList, ProjectOverview, ProjectInfo, BreakerExtraction, ProjectBase
from tasks import Task
from utils import LABEL_SPEC_OVERVIEW, LABEL_SLD, LABEL_BREAKER_LIST
from directories import _log_writer, make_log_writer, SCRATCH_DIR

_RULES_PATH = Path(__file__).parent / "rules.md"
ESTIMATION_RULES = (
    _RULES_PATH.read_text(encoding="utf-8").strip() if _RULES_PATH.exists() else ""
)


SYSTEM_PROMPT = """
You are a specialized engineering data extraction processor. Your sole task is to analyze technical document images and compile their contents into the requested structural schema.

CRITICAL WORKFLOW INSTRUCTIONS:
1. Target Scope: You will be provided a distinct batch of images from an electrical cubicle board engineering file (including project overviews, compliance standards, single-line diagrams, and breaker component lists).
2. Processing Domain: Analyze the immediate visual inputs on a one-shot basis. Do not reference historical session data, external context, or past extraction turns.
3. Output Enforcement: Extract all discovered fields and map them directly into the target schema structure.
4. Quality Assurance: Evaluate the readability and clarity of the raw visual data. Populate the 'confidence_score' field using exactly one of these string tokens: "high", "medium", or "low".

OUTPUT CONSTRAINT:
Speak ONLY in raw, structurally valid JSON matching the schema requirements. Do not include markdown code wrappers (e.g., ```json), preambles, or post-extraction summaries.
"""


def _with_rules(body: str, include_estimation: bool = False) -> str:
    parts = [body.strip()]
    if include_estimation and ESTIMATION_RULES:
        parts.append(f"Estimation rules (apply strictly):\n{ESTIMATION_RULES}")
    return "\n\n".join(parts)


PHASE1_TASK = Task(
    id="project_exploration",
    group=1,
    prompt=_with_rules("""
    ROLE: Survey ALL supplied images to map the document's top-level structure.
    Determine how many distinct projects are bundled, where each one starts and ends
    (by reading the title block on every sheet), each project's title and design firm,
    and an approximate cubicle count per project. Populate ProjectBase.
    Output ONLY the JSON object. Keep values concise — no prose, no explanations.

    FIELD FORMAT RULES (follow exactly):
    - project_boundaries: {"ProjectLabel": <start_page_number_int>} — one integer per project, the first page number where that project begins. NOT a nested object.
    - project_titles:     {"ProjectLabel": "title string"}
    - project_descriptions: {"ProjectLabel": "description string"}
    - cubicle_count_in_each_project: {"ProjectLabel": <int>}
    """),
    target_pages="ALL IMAGES",
    page_types=[],
    schema=ProjectBase,
    max_turns=10,
    max_attempts=3,
)

PHASE2_TASKS = [
    Task(
        id="project_overview",
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
        max_turns=10,
        max_attempts=3,
    ),
    Task(
        id="equipment_extraction",
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
        max_turns=15,
        max_attempts=3,
    ),
    Task(
        id="breaker_extraction",
        group=2,
        prompt=_with_rules("""
        ROLE: Extract the complete low-voltage breaker / MCCB list from the 低圧配電盤リスト
        (breaker list) pages strictly per the BreakerExtraction schema. Each row in the table
        is one BreakerList entry. Read every row — do not skip or summarise.
        """, include_estimation=True),
        target_pages="Breaker list pages only",
        page_types=[LABEL_BREAKER_LIST],
        schema=BreakerExtraction,
        max_turns=15,
        max_attempts=3,
    ),
    Task(
        id="equipment_listing",
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
        max_turns=15,
        max_attempts=3,
    ),
]

# Keep BASE_TASKS for any code that still references it
BASE_TASKS = [PHASE1_TASK] + PHASE2_TASKS


async def build_content(image_list: list[dict], task: Task) -> list[dict]:
    content: list[dict] = []
    for item in image_list:
        raw = await asyncio.to_thread(Path(item["path"]).read_bytes)
        img = Image.open(io.BytesIO(raw))
        if max(img.size) > 2000:
            img.thumbnail((2000, 2000), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            raw = buf.getvalue()
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64.standard_b64encode(raw).decode(),
            },
        })
    content.append({"type": "text", "text": task.base_prompt_text(image_list)})
    return content


def _save_result(result_data: dict, project_scratch: Path, project_name: str, task_id: str) -> str:
    run_id = uuid.uuid4().hex[:8]
    result_path = project_scratch / f"result_{project_name}_{task_id}_{run_id}.json"
    result_path.write_text(json.dumps(result_data, indent=2, ensure_ascii=False))
    return str(result_path)


async def run_agents(
    ImageListPath: Path,
    Project_name: str | None,
    on_event: Callable[[dict], None] | None = None,
):
    project_name = Project_name or "New project"

    image_paths = sorted(ImageListPath.glob("page_*.png"))
    if not image_paths:
        raise ValueError(f"No page_*.png images found in {ImageListPath}")

    labels_file = ImageListPath / "page_labels.json"
    label_map: dict[str, str] = {}
    if labels_file.exists():
        for entry in json.loads(labels_file.read_text()):
            label_map[Path(entry["path"]).name] = entry["label"]

    image_list: list[dict] = [
        {"path": str(p), "page_number": i + 1, "label": label_map.get(p.name, "unknown")}
        for i, p in enumerate(image_paths)
    ]

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
                print(f"[on_event error] {cb_err}")

    log_token = _log_writer.set(log_and_callback)
    log = _log_writer.get()
    log({"type": "run_start", "project": project_name,
         "total_tasks": 1 + len(PHASE2_TASKS), "pages": len(image_list),
         "log_file": str(log_path)})

    try:
        # ── Phase 1 ──────────────────────────────────────────────────────────
        log({"type": "task_start", "task_id": PHASE1_TASK.id})
        phase1_content = await build_content(image_list, PHASE1_TASK)
        phase1_response = await first_turn(
            system_prompt=SYSTEM_PROMPT,
            content=phase1_content,
            schema=ProjectBase,
        )

        if phase1_response["status"] != "success":
            raise RuntimeError(
                f"Phase 1 failed after {phase1_response.get('attempts')} attempts: "
                f"{phase1_response.get('error')}"
            )

        project_base: ProjectBase = phase1_response["result"]
        phase1_data = project_base.model_dump()
        phase1_path = _save_result(phase1_data, project_scratch, project_name, PHASE1_TASK.id)
        log({"type": "task_end", "task_id": PHASE1_TASK.id, "status": "success",
             "attempt": phase1_response["attempt"], "output_path": phase1_path})

        # ── Phase 2 ──────────────────────────────────────────────────────────
        phase2_results = await run_phase2(
            project_base=project_base,
            image_list=image_list,
            content_builder=build_content,
            system_prompt=SYSTEM_PROMPT,
            phase2_tasks=PHASE2_TASKS,
        )

        # save + log each Phase 2 task result
        all_results: dict = {"phase1": phase1_data, "phase2": {}}
        for proj_label, tasks in phase2_results.items():
            all_results["phase2"][proj_label] = {}
            for task_id, response in tasks.items():
                status = response.get("status")
                if status == "skipped":
                    log({"type": "task_end", "task_id": task_id,
                         "project_label": proj_label, "status": "skipped"})
                    continue
                if status == "success":
                    result_data = response["result"].model_dump()
                    out_path = _save_result(result_data, project_scratch, project_name, f"{proj_label}_{task_id}")
                    log({"type": "task_end", "task_id": task_id,
                         "project_label": proj_label, "status": "success",
                         "attempt": response.get("attempt"), "output_path": out_path})
                    all_results["phase2"][proj_label][task_id] = result_data
                else:
                    log({"type": "task_end", "task_id": task_id,
                         "project_label": proj_label, "status": status,
                         "error": response.get("error")})

        log({"type": "run_end", "project": project_name, "status": "success"})
        return {"results": all_results}

    except Exception as e:
        log({"type": "run_end", "project": project_name, "status": "error", "error": str(e)})
        raise
    finally:
        _log_writer.reset(log_token)
