# def main():
#     print("Hello from test-claiudesdk!")


# if __name__ == "__main__":
#     main()


from utils import pdf_to_images
from httpx._types import RequestFiles
from fastapi import status
import shutil
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from pathlib import Path
import shutil, os


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key = 'mynkey' )

DIR = Path('/run/media/bhat/workspace/projects/test_claiudesdk')
DIR.mkdir(exist_ok=True)
# ALLOWED_MIMETYPES = mimetypes.common_types('.pdf')

@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):

    last_saved_path = request.session.get('file_path', "Not uploaded yet")
    image_preview = request.session.get('image_preview', "")

    preview_html = ""
    if image_preview:
        preview_html = f'''
        <div class="box">
            <h2>3. Document Preview</h2>
            <img src="data:image/png;base64,{image_preview}" alt="PDF Preview" style="max-width: 100%; height: auto; border: 1px solid #ddd;"/>
        </div>
        '''

    content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Upload</title>
        <style>
            body { font-family: sans-serif; margin: 50px; }
            .container { max-width: 400px; padding: 20px; border: 1px solid #ccc; }
            button { margin-top: 10px; padding: 5px 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Upload Your File</h2>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <br>
                <button type="submit">Upload</button>
            </form>
            <form action="/image" method="post">
                <button type="submit">Process Saved File Path</button>
            </form>
        </div>
        
    {preview_html}
    </body>
    </html>
    """
    return HTMLResponse(content=content)


@app.post('/upload')
async def upload_file(request: Request, file: UploadFile = File(...)):
    file_path = os.path.abspath(os.path.join(DIR, file.filename))

    if not file:
        return ("No file uploaded")

    des = DIR / file.filename

    with des.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        print(f'{file.filename} saved sucessfully {des}')

    request.session['file_path'] = file_path

    return RedirectResponse(url='/', status_code=status.HTTP_303_SEE_OTHER)



@app.post('/image')
async def convert_to_img(request: Request):

    saved_path = request.session.get('file_path')
    
    if not saved_path or not os.path.exists(saved_path):
        return {'error': 'No valid path'}

    image_path ,base_image= pdf_to_images(saved_path,dpi=300)

    request.session['image_preview'] = base_image

    return {
        'path' : saved_path
    }
