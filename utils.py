# pyrefly: ignore [missing-import]
import fitz
import base64
import PIL
from pathlib import Path

def pdf_to_images(pdf_path: str, output_dir: Path, dpi: int):
    doc = fitz.open(pdf_path)
    outputs = []
    base64_images = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        image_bytes = pix.tobytes("png")
        base64_images.append(base64.b64encode(image_bytes).decode("utf-8"))

        output = output_dir / f'page_{page_num + 1}.png'
        pix.save(str(output))
        outputs.append(output)
        print(f"Saved: {output} at {dpi} DPI ({pix.width}x{pix.height} px)")

    doc.close()
    print("conversion complete")
    return outputs, base64_images