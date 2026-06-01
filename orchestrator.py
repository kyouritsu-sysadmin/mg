from models import ProjectInfo
import asyncio
from tasks import Task
from models import ProjectBase
from pathlib import Path
from runner import run_pipeline


BASE_TASKS = [
    Task(
        id='project exploration',
        prompt="You are work is to read all files in the given folder and get the project information strictly dependent on the schema provided ",
        target_pages="ALL IMAGES",
        schema=ProjectBase,
        max_turns=10,
        max_attempts=2
    ),
    Task(
        id='Extraction Phase',
        prompt="You are job is the extract the electricle equipement and their rating strictly based on the schema provided",
        schema=ProjectInfo,
        max_turns=10,
        max_attempts=2
    )
]


async def run_agents(ImageListPath: Path, Project_name: str | None, tasks: list[Task] = BASE_TASKS):
    project_name = Project_name or "New project"

    imagePath = [str(p) for p in sorted(ImageListPath.glob("page_*.png"))]
    if not imagePath:
        raise ValueError(f"No page_*.png images found in {ImageListPath}")

    results = await run_pipeline(tasks=tasks, ImageList=imagePath, project_name=project_name)

    return {"results": results, "total_tasks": len(tasks)}