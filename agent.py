import asyncio
import base64
from collections.abc import AsyncGenerator
from typing import Any
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
    _log_writer,
    CROPS_DIR,
    SCRATCH_DIR,
)
from tasks import Task


async def _image_message(
    image_list: list[dict], text: str
) -> AsyncGenerator[dict[str, Any], None]:
    """Yield one user-message dict with images embedded as base64 content blocks.

    image_list is a list[dict] with keys: path, page_number, label.
    Each image gets an alt-text annotation (page number + label) so the model
    can correlate its analysis with the page manifest in the text block.

    The last image block carries cache_control so image tokens are cached across
    all continuation tasks in the same shared session (Anthropic 5-min TTL).
    """
    content: list[dict] = []
    for i, img in enumerate(image_list):
        raw = await asyncio.to_thread(Path(img["path"]).read_bytes)
        block: dict = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64.standard_b64encode(raw).decode(),
            },
        }
        if i == len(image_list) - 1:
            block["cache_control"] = {"type": "ephemeral"}
        content.append(block)

    content.append({"type": "text", "text": text})

    yield {
        "type": "user",
        "message": {"role": "user", "content": content},
        "parent_tool_use_id": None,
    }


def _options(gate, cwd: Path, max_turns: int, system_prompt: str | None = None) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        mcp_servers={"image_tools": image_tools_server},
        allowed_tools=["mcp__image_tools__crop_region"],
        permission_mode="acceptEdits",
        max_turns=max_turns,
        max_buffer_size=10 * 1024 * 1024,
        thinking={'type': 'thinking', 'budget_tokens': 2048},
        cwd=cwd,
        can_use_tool=gate,
        system_prompt=system_prompt,
        effort='max',
    )


async def run_turns(
    client: ClaudeSDKClient,
    task: Task,
    prompt: str | AsyncGenerator[dict[str, Any], None],
    project_scratch_dir: Path,
    project_name: str,
) -> dict:
    """Run one task's query/retry loop inside an existing client session.

    `prompt` is an AsyncGenerator (image content blocks) for the first task,
    or a plain string for continuation tasks and all retries.
    """
    log = _log_writer.get()
    log({"type": "task_start", "task_id": task.id, "group": task.group,
         "max_turns": task.max_turns, "max_attempts": task.max_attempts})

    current_prompt: str | AsyncGenerator = prompt

    for attempt in range(1, task.max_attempts + 1):
        result = ""
        turn = 0
        await client.query(current_prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                turn += 1
                thinking_text = ""
                text_content = ""
                print(f"\n--- Turn {turn} ---")
                for block in message.content:
                    if isinstance(block, ThinkingBlock):
                        print(f"[Thinking]: {block.thinking}")
                        thinking_text = block.thinking
                    elif isinstance(block, TextBlock):
                        print(f"[Text]: {block.text}")
                        text_content = block.text
                log({"type": "turn", "task_id": task.id, "attempt": attempt,
                     "turn": turn, "thinking": thinking_text, "text": text_content})
            if isinstance(message, ResultMessage):
                result = message.result or ""
                tokens = message.usage or {}
                print(f"\n--- Result ---")
                print(f"Turns: {message.num_turns}")
                print(f"Total cost: ${message.total_cost_usd:.4f}")
                print(f"Input tokens: {tokens.get('input_tokens')}  Output tokens: {tokens.get('output_tokens')}")
                log({"type": "result", "task_id": task.id, "attempt": attempt,
                     "num_turns": message.num_turns, "cost_usd": message.total_cost_usd,
                     "input_tokens": tokens.get("input_tokens"),
                     "output_tokens": tokens.get("output_tokens")})
 
        if not result.strip():
            print(f"[Attempt {attempt}] Empty result — Claude produced no output.")
            log({"type": "retry", "task_id": task.id, "attempt": attempt,
                 "reason": "empty_result"})
            current_prompt = "Your previous response was empty. Return ONLY a raw JSON object matching the schema."
            continue

        clean = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = task.schema.model_validate(json.loads(clean))
            safe_id = task.id.replace(' ', '_')
            result_path = project_scratch_dir / f"result_{project_name}_{safe_id}.json"
            result_path.write_text(json.dumps(data.model_dump(), indent=2))
            log({"type": "task_end", "task_id": task.id, "status": "success",
                 "attempt": attempt, "output_path": str(result_path)})
            confidence = getattr(data, 'confidence', None)
            if confidence is not None and confidence != 'high':
                log({"type": "confidence_low", "task_id": task.id,
                     "attempt": attempt, "confidence": confidence})

            return {
                'status': 'success',
                'task_id': task.id,
                'result': data.model_dump(),
                'output_path': str(result_path)
            }

            

        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == task.max_attempts:
                log({"type": "task_end", "task_id": task.id, "status": "failed",
                    "attempt": attempt, "error": str(e)})
                raise
            log({"type": "retry", "task_id": task.id, "attempt": attempt,
                "reason": "validation_error", "error": str(e)})
            current_prompt = (
                f"Your previous output failed validation: {e}\n"
                "Fix it and return only valid JSON matching the schema."
            )

    log({"type": "task_end", "task_id": task.id, "status": "failed",
         "attempt": task.max_attempts, "error": "no_valid_output"})
    raise RuntimeError(f'Task "{task.id}" produced no valid output after {task.max_attempts} attempts.')


async def main(project_name: str, gate, cwd: Path, Task: Task,
               image_list: list[dict], system_prompt: str | None = None) -> dict:
    """Single-task entry point — creates a fresh session and supplies images directly."""
    project_crops_dir   = CROPS_DIR   / project_name
    project_scratch_dir = SCRATCH_DIR / project_name
    project_crops_dir.mkdir(exist_ok=True)
    project_scratch_dir.mkdir(exist_ok=True)

    token = _project_crops_dir.set(project_crops_dir)
    try:
        async with ClaudeSDKClient(options=_options(gate, cwd, Task.max_turns, system_prompt)) as client:
            prompt = _image_message(Task.filter_pages(image_list), Task.base_prompt_text(image_list))
            return await run_turns(client, Task, prompt, project_scratch_dir, project_name)
    finally:
        _project_crops_dir.reset(token)


async def run_pipeline_session(
    project_name: str,
    gate,
    cwd: Path,
    tasks: list[Task],
    image_list: list[dict],
    system_prompt: str | None = None,
) -> list[dict]:
    """Multi-task entry point — one session shared across all tasks in sequence.

    Task 0: ALL images embedded as base64 content blocks with page labels.
            Cache-control on the last image means image tokens are reused across
            all continuation turns in the shared session (Anthropic 5-min TTL).
    Tasks 1+: plain-string continuation; images + labels already in context.
    """
    project_crops_dir   = CROPS_DIR   / project_name
    project_scratch_dir = SCRATCH_DIR / project_name
    project_crops_dir.mkdir(exist_ok=True)
    project_scratch_dir.mkdir(exist_ok=True)

    token = _project_crops_dir.set(project_crops_dir)
    try:
        total_turns = sum(t.max_turns for t in tasks)
        async with ClaudeSDKClient(options=_options(gate, cwd, total_turns, system_prompt)) as client:
            results = []
            prev_result = None
            for i, task in enumerate(tasks):
                if i == 0:
                    prompt = _image_message(task.filter_pages(image_list), task.base_prompt_text(image_list))
                else:
                    prompt = task.continuation(prev_result)
                result = await run_turns(client, task, prompt, project_scratch_dir, project_name)
                prev_result = result['result']
                results.append(result)
            return results
    finally:
        _project_crops_dir.reset(token)
