import asyncio
from claude_agent_sdk import ClaudeSDKClient
from models import ProjectInfo
import asyncio
import base64
import uuid
from pathlib import Path
import json
from pydantic import ValidationError
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    create_sdk_mcp_server,
    tool,
    ClaudeAgentOptions
)
from utils import build_prompt
from tools import image_tools_server
from directories import (
    _project_crops_dir,
    CROPS_DIR,
    SCRATCH_DIR,
    WORKSPACE
)
from tasks import Task


async def main(project_name: str, gate: str , cwd: Path):
    global _project_crops_dir

    project_crops_dir   = CROPS_DIR   / project_name
    project_scratch_dir = SCRATCH_DIR / project_name
    project_crops_dir.mkdir(exist_ok=True)
    project_scratch_dir.mkdir(exist_ok=True)

    _project_crops_dir = project_crops_dir

    # base_prompt = build_prompt(image_path) # this needs to change to the task prompt 
    base_prompt = Task.prompt # this needs to change to the task prompt 

    options = ClaudeAgentOptions(
        mcp_servers={"image_tools": image_tools_server},
        allowed_tools=["Read", "mcp__image_tools__crop_region"],
        permission_mode="acceptEdits",
        max_turns=20,
        max_buffer_size=10*1024*1024,
        thinking={'type': 'adaptive', 'display': 'summarized'},
        cwd=cwd,
        can_use_tool=gate
    )

    async with ClaudeSDKClient(options=options) as client:
        current_prompt = base_prompt

        for attempt in range(1, Task.max_attempts + 1):
            result = ""
            turn = None
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
                    result = message.result or "No Result"
                    tokens = message.usage or {}
                    print(f"\n--- Result ---")
                    print(f"Turns: {message.num_turns}")
                    print(f"Total cost: ${message.total_cost_usd:.4f}")
                    print(f"Input tokens: {tokens.get('input_tokens')}  Output tokens: {tokens.get('output_tokens')}")

            if not result.strip():
                print(f"[Attempt {attempt}] Empty result — Claude produced no JSON output.")
                current_prompt = f"{base_prompt}\n\nYour previous response contained no JSON. Return ONLY a raw JSON object."
                continue

            clean = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                data = ProjectInfo.model_validate(json.loads(clean))
                output_dir = (project_scratch_dir / f"result_{project_name}.json").write_text(
                    json.dumps(data.model_dump(), indent=2)
                )
                if data :
                    return {
                        'status': 'sucess',
                        'result' : data,
                        "output_dir" : output_dir 
                    }
                    continue

            except (json.JSONDecodeError, ValidationError) as e:
                if attempt == Task.max_attempts:
                    raise
                current_prompt = (
                    f"Your previous output failed validation: {e}\n"
                    "Fix it and return only valid JSON matching the schema."
                )

# Test invocation — orchestrator will call main(project_name, image_path) directly.
# asyncio.run(main("output_1", str(WORKSPACE / "__images" / "output_1" / "page_1.png")))

# if __name__ == '__main__':

#     '''
#     inputs: 
#         1. Imagelist from the fastapi endpoint supplied by the orchestrator to the runner script, 
#         from th runner script it comes to the Agent 
#     '''
#     asyncio.run(main())