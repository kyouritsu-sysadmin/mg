# pyrefly: ignore [missing-import]
from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server
)
import uuid
import base64
from directories import _project_crops_dir


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
    out_path = _project_crops_dir.get() / f"crop_{uuid.uuid4().hex[:8]}.png"
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

ALLOWED_TOOLS = ['Read', 'mcp__image_tools__crop_region', 'crop_region']
