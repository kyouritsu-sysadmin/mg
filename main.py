import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from models import SessionData
from utils import pdf_to_images

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key='mynkey')

WORKSPACE     = Path(__file__).parent / "data"
ORIGINALS_DIR = WORKSPACE / "__originals"
IMAGES_DIR    = WORKSPACE / "__images"

WORKSPACE.mkdir(exist_ok=True)
ORIGINALS_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    last_saved_path = request.session.get('file_path', "Not uploaded yet")
    image_files: list = request.session.get('image_files', [])

    project_name = request.session.get('project_name', 'unknown')
    preview_html = ""
    if image_files:
        images_html = "".join(
            f'<img src="/preview/{project_name}/{fname}" alt="Page {i+1}" style="max-width: 100%; height: auto; border: 1px solid #ddd; margin-bottom: 10px;"/>'
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
    project_name = Path(file.filename).stem
    des = ORIGINALS_DIR / file.filename
    file_path = str(des)

    with des.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        print(f'{file.filename} saved successfully to {des}')

    request.session['file_path'] = file_path
    request.session['project_name'] = project_name
    request.session.pop('image_files', None)

    return RedirectResponse(url='/', status_code=status.HTTP_303_SEE_OTHER)

    saved_path = request.session.get('file_path')
    
    if not saved_path or not os.path.exists(saved_path):
        return {'error': 'No valid path found in session'}

    project_name = request.session.get('project_name', 'unknown')
    project_images_dir = IMAGES_DIR / project_name
    project_images_dir.mkdir(exist_ok=True)

    image_paths, _ = pdf_to_images(saved_path, project_images_dir, dpi=300)

    request.session['image_files'] = [Path(p).name for p in image_paths]

    return RedirectResponse(url='/', status_code=status.HTTP_303_SEE_OTHER)


@app.get('/preview/{project_name}/{filename}')
async def preview_image(project_name: str, filename: str):
    file_path = IMAGES_DIR / project_name / filename
    if not file_path.exists():
        return {'error': 'Image not found'}
    return FileResponse(file_path, media_type='image/png')

@app.post('/app/v1/users/new')
async def new_project(data: SessionData):

    project_name = data.project_name
    
    if project_name:
        



@app.post('/process/task1')
async def explore_project():
    pass