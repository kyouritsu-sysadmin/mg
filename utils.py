# pyrefly: ignore [missing-import]
import fitz
import base64

def pdf_to_images(pdf_path:str, dpi: int ):
    doc = fitz.open(pdf_path)
    output = ""
    base64_image = ""

    for page_num in range(len(doc)):
        page = doc[page_num]

        pix = page.get_pixmap(dpi=dpi)

        image_bytes = pix.tobytes("png")
        
        # Encode the bytes into a base64 string
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        output = f'output_{page_num + 1}.png'
        pix.save(output)
        print(f"Saved: {output} at {dpi} DPI ({pix.width}x{pix.height} px)")
    doc.close()

    print("conversion complete")
    return output, base64_image