'''

The main job of run_task is to safely execute an AI agent job from start to finish.
It takes a raw task instruction, creates a secure physical workspace for it,
lets the AI agent do its work, double-checks that the AI's output isn't broken, saves the valid results,
and cleanly destroys the temporary workspace afterward.

It uses:
1. directory: data/__scratch
2. working on the pages fed via image list
3. Gatekeep for the agents — permissions, tools, rules, hooks
4. Self-correction feedback loop
5. Result validation and clean up temps

'''

from directories import WORKSPACE
import json
from pydantic import ValidationError
from claude_agent_sdk import PermissionResultDeny
from claude_agent_sdk.types import PermissionResultAllow
from tools import ALLOWED_TOOLS
from pathlib import Path
from typing import Optional
from tasks import Task
from agent import main, run_pipeline_session


async def gatekeep(tool_name: str | Optional, path: Path | Optional, _context: str | Optional = None):
    if tool_name in ALLOWED_TOOLS:
        return PermissionResultAllow()
    if path and path.resolve().is_relative_to(WORKSPACE):
        return PermissionResultAllow()
    return PermissionResultDeny(message='write command denied')


async def run_task(task: Task, ImageList: list[str], project_name: str,
                   system_prompt: str | None = None) -> dict:
    """Single-task runner — creates a fresh agent session per task."""
    try:
        prompt = task.base_prompt(Imagelist=ImageList)
        return await main(project_name=project_name, Task=task, gate=gatekeep,
                          cwd=WORKSPACE, prompt=prompt, system_prompt=system_prompt)
    except (json.JSONDecodeError, ValidationError) as e:
        raise Exception(f'Task "{task.id}" failed after all retries') from e


async def run_pipeline(tasks: list[Task], ImageList: list[str], project_name: str,
                       system_prompt: str | None = None) -> list[dict]:
    """Multi-task pipeline — all tasks share one session so each task has full
    context from every previous task's conversation turns and results."""
    try:
        return await run_pipeline_session(
            project_name=project_name,
            gate=gatekeep,
            cwd=WORKSPACE,
            tasks=tasks,
            image_list=ImageList,
            system_prompt=system_prompt,
        )
    except (json.JSONDecodeError, ValidationError) as e:
        raise Exception(f'Pipeline failed: {e}') from e