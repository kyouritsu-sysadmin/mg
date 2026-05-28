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



# step1_smoke.py
import asyncio
import base64
import uuid
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk import query, ClaudeAgentOptions

IMAGE_PATH = "/run/media/bhat/workspace/projects/test_claiudesdk/output_1.png"
WORKSPACE = Path(__file__).parent / "data"
WORKSPACE.mkdir(exist_ok=True)


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
    out_path = WORKSPACE / f"crop_{uuid.uuid4().hex[:8]}.png"
    cropped = img.crop(box)
    cropped.save(out_path)

    buf = base64.b64encode(out_path.read_bytes()).decode()
    return {
        "content": [{
            "type": "image",
            "data": buf,
            "mimeType": "image/png",
        }]
    }


# Register crop_region as an in-process MCP server so Claude can call it.
# can_use_tool is for permission callbacks only — not needed here.
image_tools_server = create_sdk_mcp_server("image_tools", tools=[crop_region])


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={"image_tools": image_tools_server},
        allowed_tools=["Read", "crop_region", "Bash"],  # auto-allow; no permission prompt
        permission_mode="acceptEdits",
        max_turns=10,
        thinking={'type': 'adaptive'},
        cwd=WORKSPACE,  # CLI subprocess resolves relative paths from here
    )
    prompt = (
        f"Read the image at {IMAGE_PATH}. "
        "This is an electrical cubicle panel drawing. "
        "Tell me at what resolution and aspect ratio you received this image "
        "and at what resolution and aspect ratio you process it."
        "Perform an extraction on this image and retrieve me the following"
        "1. Project title"
        "2. How many cubicle or electrical boards are planned in this project"
        "3. Number of Transfomers used in this project along with their power rating and specifications."
    )

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            print(f'Model usage: {message.model_usage}')
            print(f'Total cost: {message.total_cost_usd}')
            print(f'Usage: {message.usage}')
        if isinstance(message, AssistantMessage):
            if message.usage:
                print(f'Usage keys: {list(message.usage.keys())}')
            print(f'Content blocks: {len(message.content)}')
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"From Claude: {block.text}")

asyncio.run(main())