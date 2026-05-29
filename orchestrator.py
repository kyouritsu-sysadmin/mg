import asyncio
from tasks import Task
from models import ProjectBase
from pathlib import Path
from runner import run_task 



BASE_TASKS = [
    
  # Task 1: explore the project and get valid info
   Task (
    id='project exploration',
    prompt= "You are work is to read all files in the given folder and get the project information stricly dependent on the schema provided ",
    target_pages="ALL IMAGES",
    schema= ProjectBase,
    max_turns=20,
    max_attempts=2
   )
]

async def run_agents(ImageListPath : Path, output_dir : Path, Project_name: str):

    project_file_name = Project_name

    results_dir = output_dir / project_file_name

    results_dir.mkdir(parents=True, exist_ok=True)
    
    
    project_base = await run_task(task=[t for t in BASE_TASKS], ImageList=ImageListPath,result_dir=results_dir)

    merged , errors = {}, {}

    for task, result in zip(BASE_TASKS, project_base):
        if isinstance(result, Exception):
            errors[task.id] = str(result)
        else:
            merged[task.id] = result
    
    return {"results" : merged, "errors": errors, "total_tasks": len(BASE_TASKS)}