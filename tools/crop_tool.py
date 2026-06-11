CROP_REGION_TOOL_DEFINITION = {
    "name": "crop_region",
    "description": (
        "Crop a region of a page image at higher effective resolution when text or "
        "symbols are too small to read clearly. Coordinates are normalized "
        "fractions of page dimensions (0.0–1.0); (0,0) is the top-left corner. "
        "If the first crop misses the region, call again with adjusted coordinates."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_image": {
                "type": "string",
                "description": "The local filesystem path to the page image file."
            },
            "x": {
                "type": "number",
                "description": "Normalized top-left X coordinate fraction (0.0 - 1.0)."
            },
            "y": {
                "type": "number",
                "description": "Normalized top-left Y coordinate fraction (0.0 - 1.0)."
            },
            "width": {
                "type": "number",
                "description": "Normalized width fraction (0.0 - 1.0)."
            },
            "height": {
                "type": "number",
                "description": "Normalized height fraction (0.0 - 1.0)."
            }
        },
        "required": ["page_image", "x", "y", "width", "height"]
    }
}

import uuid
import base64
from pathlib import Path
from PIL import Image

def handle_crop_region_execution(arguments: dict, output_dir: Path) -> dict:
    """
    Executes the physical image processing on your local server.
    Accepts the raw arguments dictionary extracted from Claude's ToolUseBlock.
    """
    # 1. Extract arguments safely from the stateless dictionary
    page_image_path = arguments["page_image"]
    x = float(arguments["x"])
    y = float(arguments["y"])
    width = float(arguments["width"])
    height = float(arguments["height"])
    
    # 2. Open and process the image via Pillow
    img = Image.open(page_image_path)
    W, H = img.size
    
    box = (
        int(x * W),
        int(y * H),
        int((x + width) * W),
        int((y + height) * H),
    )
    
    # Ensure the target directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"crop_{uuid.uuid4().hex[:8]}.png"
    
    cropped = img.crop(box)

    # 3. Apply the same elite downscaling to guard bandwidth
    MAX_DIM = 1600
    if cropped.width > MAX_DIM or cropped.height > MAX_DIM:
        cropped.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)

    cropped.save(out_path, format="PNG", optimize=True)

    # 4. Convert to Base64 to return to the pipeline
    buf = base64.b64encode(out_path.read_bytes()).decode("utf-8")
    
    # Structure the return value using standard Messages API tool result formats
    return {
        "status": "success",
        "crop_path": str(out_path),
        "image_data_b64": buf
    }
