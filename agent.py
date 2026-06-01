import asyncio
from claude_agent_sdk import ClaudeSDKClient
from pathlib import Path
import json
from pydantic import ValidationError
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ClaudeAgentOptions
)
from tools import image_tools_server
from directories import (
    _project_crops_dir,
    CROPS_DIR,
    SCRATCH_DIR,
    WORKSPACE
)
from tasks import Task


def _options(gate, cwd: Path, max_turns: int) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        mcp_servers={"image_tools": image_tools_server},
        allowed_tools=["Read", "mcp__image_tools__crop_region"],
        permission_mode="acceptEdits",
        max_turns=max_turns,
        max_buffer_size=10 * 1024 * 1024,
        thinking={'type': 'adaptive'},
        cwd=cwd,
        can_use_tool=gate
    )


async def run_turns(
    client: ClaudeSDKClient,
    task: Task,
    prompt: str,
    project_scratch_dir: Path,
    project_name: str,
) -> dict:
    """Run one task's query/retry loop inside an existing client session."""
    current_prompt = prompt

    for attempt in range(1, task.max_attempts + 1):
        result = ""
        turn = 0
        await client.query(current_prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                turn += 1
                print(f"\n--- Turn {turn} ---")
                for block in message.content:
                    if isinstance(block, ThinkingBlock):
                        print(f"[Thinking]: {block.thinking}")
                    elif isinstance(block, TextBlock):
                        print(f"[Text]: {block.text}")
            if isinstance(message, ResultMessage):
                result = message.result or ""
                tokens = message.usage or {}
                print(f"\n--- Result ---")
                print(f"Turns: {message.num_turns}")
                print(f"Total cost: ${message.total_cost_usd:.4f}")
                print(f"Input tokens: {tokens.get('input_tokens')}  Output tokens: {tokens.get('output_tokens')}")

        if not result.strip():
            print(f"[Attempt {attempt}] Empty result — Claude produced no output.")
            current_prompt = "Your previous response was empty. Return ONLY a raw JSON object matching the schema."
            continue

        clean = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = task.schema.model_validate(json.loads(clean))
            safe_id = task.id.replace(' ', '_')
            result_path = project_scratch_dir / f"result_{project_name}_{safe_id}.json"
            result_path.write_text(json.dumps(data.model_dump(), indent=2))
            return {
                'status': 'success',
                'task_id': task.id,
                'result': data.model_dump(),
                'output_path': str(result_path)
            }

        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == task.max_attempts:
                raise
            current_prompt = (
                f"Your previous output failed validation: {e}\n"
                "Fix it and return only valid JSON matching the schema."
            )

    raise RuntimeError(f'Task "{task.id}" produced no valid output after {task.max_attempts} attempts.')


async def main(project_name: str, gate, cwd: Path, Task: Task, prompt: str) -> dict:
    """Single-task entry point — creates a fresh session for one task."""
    project_crops_dir   = CROPS_DIR   / project_name
    project_scratch_dir = SCRATCH_DIR / project_name
    project_crops_dir.mkdir(exist_ok=True)
    project_scratch_dir.mkdir(exist_ok=True)

    token = _project_crops_dir.set(project_crops_dir)
    try:
        async with ClaudeSDKClient(options=_options(gate, cwd, Task.max_turns)) as client:
            return await run_turns(client, Task, prompt, project_scratch_dir, project_name)
    finally:
        _project_crops_dir.reset(token)


async def run_pipeline_session(
    project_name: str,
    gate,
    cwd: Path,
    tasks: list[Task],
    image_list: list[str],
) -> list[dict]:
    """Multi-task entry point — one session shared across all tasks in sequence.

    Task 0 gets base_prompt (image file paths — Claude reads them via Read tool).
    Each subsequent task gets continuation(prev_result) — no image re-listing.
    """
    project_crops_dir   = CROPS_DIR   / project_name
    project_scratch_dir = SCRATCH_DIR / project_name
    project_crops_dir.mkdir(exist_ok=True)
    project_scratch_dir.mkdir(exist_ok=True)

    token = _project_crops_dir.set(project_crops_dir)
    try:
        total_turns = sum(t.max_turns for t in tasks)
        async with ClaudeSDKClient(options=_options(gate, cwd, total_turns)) as client:
            results = []
            prev_result = None
            for i, task in enumerate(tasks):
                prompt = task.base_prompt(image_list) if i == 0 else task.continuation(prev_result)
                result = await run_turns(client, task, prompt, project_scratch_dir, project_name)
                prev_result = result['result']
                results.append(result)
            return results
    finally:
        _project_crops_dir.reset(token)