# pyrefly: ignore [missing-import]
from _typeshed import importlib
import fitz

def pdf_to_images(pdf_path:str, dpi: int ):
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]

        pix = page.get_pixmap(dpi)


        output = f'output_{1}.png'
        pix.save(output)
        print(f"Saved: {output} at {dpi} DPI ({pix.width}x{pix.height} px)")
    doc.close()

    print("conversion complete")