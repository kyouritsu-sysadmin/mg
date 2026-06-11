from __future__ import annotations

from models import ProjectBase
from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from typing import Callable, Any
import asyncio
import json
import os

load_dotenv()

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_RETRIES = 3


async def first_turn(
    system_prompt: str,
    content: list[dict],
    schema: type[BaseModel] = ProjectBase,
    model: str = "claude-sonnet-4-6",
    on_token: Callable[[str], None] | None = None,
) -> dict:
    client = AsyncAnthropic(api_key=ANTHROPIC_KEY)
    messages: list[dict] = [{"role": "user", "content": content}]
    last_error: str = ""
    text: str = ""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[{schema.__name__}] attempt {attempt} streaming...", flush=True)
            async with client.messages.stream(
                messages=messages,
                model=model,
                system=system_prompt,
                max_tokens=120000,
            ) as stream:
                async for chunk in stream.text_stream:
                    print(chunk, end="", flush=True)
                    if on_token:
                        on_token(chunk)
                print()
                msg = await stream.get_final_message()

            text = msg.content[0].text
            result = schema.model_validate_json(text)

            confidence = getattr(result, "confidence", "high")
            if confidence == "high" or attempt == MAX_RETRIES:
                return {"status": "success", "attempt": attempt, "result": result}

            last_error = f"confidence={confidence}"
            messages = messages + [
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": (
                        "Your previous output had low confidence. "
                        "Re-examine the images more carefully and return an updated JSON "
                        "with confidence='high' only if you can read the fields directly off the sheets."
                    ),
                },
            ]

        except (ValidationError, json.JSONDecodeError) as e:
            last_error = str(e)
            if attempt == MAX_RETRIES:
                break
            messages = messages + [
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": (
                        f"Your previous output failed schema validation:\n{last_error}\n\n"
                        f"Return ONLY a raw JSON object matching the {schema.__name__} schema exactly. "
                        "No markdown, no extra nesting."
                    ),
                },
            ]

        except Exception as e:
            return {"status": "error", "attempt": attempt, "error": str(e), "result": None}

    return {"status": "failed", "attempts": MAX_RETRIES, "error": last_error, "result": None}


def derive_project_ranges(project_base: ProjectBase, total_pages: int) -> dict[str, tuple[int, int]]:
    if project_base.number_of_projects <= 1:
        return {"project_1": (1, total_pages)}
    sorted_bounds = sorted(project_base.project_boundaries.items(), key=lambda x: x[1])
    ranges: dict[str, tuple[int, int]] = {}
    for i, (label, start) in enumerate(sorted_bounds):
        end = sorted_bounds[i + 1][1] - 1 if i + 1 < len(sorted_bounds) else total_pages
        ranges[label] = (start, end)
    return ranges


async def run_phase2(
    project_base: ProjectBase,
    image_list: list[dict],
    content_builder: Callable[..., Any],
    system_prompt: str,
    phase2_tasks: list,
    model: str = "claude-sonnet-4-6",
) -> dict[str, dict]:
    ranges = derive_project_ranges(project_base, len(image_list))

    async def run_task_for_project(proj_label: str, start: int, end: int, task) -> tuple[str, str, dict]:
        proj_images = [img for img in image_list if start <= img["page_number"] <= end]
        filtered = task.filter_pages(proj_images)
        if not filtered:
            return proj_label, task.id, {"status": "skipped", "result": None}
        content = await content_builder(filtered, task)
        result = await first_turn(
            system_prompt=system_prompt,
            content=content,
            schema=task.schema,
            model=model,
        )
        return proj_label, task.id, result

    coroutines = [
        run_task_for_project(label, start, end, task)
        for label, (start, end) in ranges.items()
        for task in phase2_tasks
    ]

    raw = await asyncio.gather(*coroutines, return_exceptions=True)

    results: dict[str, dict] = {}
    for item in raw:
        if isinstance(item, Exception):
            continue
        proj_label, task_id, response = item
        results.setdefault(proj_label, {})[task_id] = response

    return results
