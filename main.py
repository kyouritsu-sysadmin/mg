import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from utils import pdf_to_images

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key='mynkey')

DIR = Path('data')
DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    last_saved_path = request.session.get('file_path', "Not uploaded yet")
    image_files: list = request.session.get('image_files', [])

    preview_html = ""
    if image_files:
        images_html = "".join(
            f'<img src="/preview/{fname}" alt="Page {i+1}" style="max-width: 100%; height: auto; border: 1px solid #ddd; margin-bottom: 10px;"/>'
            for i, fname in enumerate(image_files)
        )
        preview_html = f'''
        <div class="box" style="margin-top: 20px;">
            <h2>3. Document Preview</h2>
            {images_html}
        </div>
        '''
        
    content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Upload</title>
        <style>
            body {{ font-family: sans-serif; margin: 50px; }}
            .container {{ max-width: 400px; padding: 20px; border: 1px solid #ccc; }}
            button {{ margin-top: 10px; padding: 5px 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Upload Your File</h2>
            <p><strong>Last Saved:</strong> {last_saved_path}</p>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <br>
                <button type="submit">Upload</button>
            </form>
            
            <form action="/image" method="post">
                <button type="submit" {"disabled" if last_saved_path == "Not uploaded yet" else ""}>
                    Process Saved File Path
                </button>
            </form>
        </div>
        
    {preview_html}
    </body>
    </html>
    """
    return HTMLResponse(content=content)


@app.post('/upload')
async def upload_file(request: Request, file: UploadFile = File(...)):
    if not file or not file.filename:
        return {"error": "No file uploaded"}

    # Use Path library consistently
    des = DIR / file.filename
    file_path = os.path.abspath(des)

    with des.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        print(f'{file.filename} saved successfully to {des}')

    request.session['file_path'] = file_path
    
    request.session.pop('image_files', None)

    return RedirectResponse(url='/', status_code=status.HTTP_303_SEE_OTHER)



@app.post('/image')
async def convert_to_img(request: Request):
    saved_path = request.session.get('file_path')
    
    if not saved_path or not os.path.exists(saved_path):
        return {'error': 'No valid path found in session'}


    image_paths, _ = pdf_to_images(saved_path, dpi=300)

  
    request.session['image_files'] = [os.path.basename(p) for p in image_paths]

    return RedirectResponse(url='/', status_code=status.HTTP_303_SEE_OTHER)


@app.get('/preview/{filename}')
async def preview_image(filename: str):
    file_path = os.path.abspath(filename)
    if not os.path.exists(file_path):
        return {'error': 'Image not found'}
    return FileResponse(file_path, media_type='image/png')