# import asyncio
# # pyrefly: ignore [missing-import]
# from claude_agent_sdk import  ClaudeSDKClient, ClaudeAgentOptions , AssistantMessage, TextBlock, ResultMessage


# # async with ClaudeSDKClient() as client:
# #     await client.query('')




# options = ClaudeAgentOptions(
#     thinking={'type': 'adaptive', "budget_tokens" : 500000},
#     tools={},
#     allowed_tools=['Read' ,'Write', 'Bash'],
#     permission_mode = "acceptEdits" 
# )

# async def main():
#     async with ClaudeSDKClient() as client:
#         await client.query(input(''))


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

IMAGE_PATH = WORKSPACE / "__images"
WORKSPACE   = Path(__file__).parent / "data"
CROPS_DIR   = WORKSPACE / "__crops"
SCRATCH_DIR = WORKSPACE / "__scratch"

WORKSPACE.mkdir(exist_ok=True)
CROPS_DIR.mkdir(exist_ok=True)
SCRATCH_DIR.mkdir(exist_ok=True)


@tool(
    "crop_region",
    "Crop a region of a page image at higher effective resolution when text or "
    "symbols are too small to read clearly. Coordinates are normalized "
    "fractions of page dimensions (0.0–1.0); (0,0) is the top-left corner. "
    "If the first crop misses the region, call again with adjusted coordinates.",
    {
        "page_image": str,
        "x": float, "y": float,
        "width": float, "height": float,
    },
)
async def crop_region(args):
    from PIL import Image
    img = Image.open(args["page_image"])
    W, H = img.size
    box = (
        int(args["x"] * W),
        int(args["y"] * H),
        int((args["x"] + args["width"]) * W),
        int((args["y"] + args["height"]) * H),
    )
    out_path = CROPS_DIR / f"crop_{uuid.uuid4().hex[:8]}.png"
    cropped = img.crop(box)

   
    MAX_DIM = 1600
    if cropped.width > MAX_DIM or cropped.height > MAX_DIM:
        cropped.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)

    cropped.save(out_path, format="PNG", optimize=True)

    buf = base64.b64encode(out_path.read_bytes()).decode()
    return {
        "content": [{
            "type": "image",
            "data": buf,
            "mimeType": "image/png",
        }]
    }

async def get_images(path: str):
    pass


image_tools_server = create_sdk_mcp_server("image_tools", tools=[crop_region])

MAX_ATTEMPTS = 3
SCHEMA_DESCRIPTION = """
{
  "project_title": "string",
  "design_firm": "string",
  "date": "int",
  "cubicle_info": [
    {
      "cubicle_name": "string",
      "power_specification": "string",
      "cubicle_type": "string"
    }
  ],
  "cubicle_count": integer,
  "project_location": "string",
  "transformer_count": integer,
  "transformers": [
    {
      "power_rating_kva": number or null,
      "primary_voltage_kv": number or null,
      "secondary_voltage_v": number or null,
      "specifications": "string or null"
    }
  ],
  "confidence": "high | medium | low"
}
"""

BASE_PROMPT = (
    f"Read the image at {IMAGE_PATH}. "
    "This is an electrical cubicle panel drawing. "
    "Perform an extraction on this image and retrieve the following:\n"
    "1. Project title\n"
    "2. How many cubicles or electrical boards are planned in this project\n"
    "3. Number of transformers used along with their power rating and specifications.\n"
    f"Schema to follow:\n{SCHEMA_DESCRIPTION}\n"
    "Return ONLY a raw JSON object matching the schema. No markdown fences, no explanation."
)


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={"image_tools": image_tools_server},
        allowed_tools=["Read", "mcp__image_tools__crop_region"],
        permission_mode="acceptEdits",
        max_turns=20,
        max_buffer_size=10*1024*1024,
        thinking={'type': 'adaptive', 'display': 'summarized'},
        cwd=WORKSPACE,
    )

    async with ClaudeSDKClient(options=options) as client:
        current_prompt = BASE_PROMPT

        for attempt in range(1, MAX_ATTEMPTS + 1):
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
                print(f"[Attempt {attempt}] Empty result — Claude produced no JSON output.")
                prompt = f"{BASE_PROMPT}\n\nYour previous response contained no JSON. Return ONLY a raw JSON object."
                continue

            clean = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                data = ProjectInfo.model_validate(json.loads(clean))
                (SCRATCH_DIR / f"{data.project_title}_result_project_info.json{uuid.uuid4.hex[:4]}").write_text(
                    json.dumps(data.model_dump(), indent=2)
                )
                return data
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt == MAX_ATTEMPTS:
                    raise 
                # RuntimeError(f"Failed after {MAX_ATTEMPTS} attempts. Last error: {e}") from e
                current_prompt = (
                f"Your previous output failed validation: {e}\n"
                "Fix it and return only valid JSON matching the schema."
                )

asyncio.run(main())