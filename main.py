import os
import shutil
import uuid
import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request, status
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from utils import pdf_to_images
from orchestrator import run_agents

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.add_middleware(SessionMiddleware, secret_key='mynkey')

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

WORKSPACE     = Path(__file__).parent / "workspace"
ORIGINALS_DIR = WORKSPACE / "__originals"
IMAGES_DIR    = WORKSPACE / "__images"

WORKSPACE.mkdir(exist_ok=True)
ORIGINALS_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# In-memory job store — keyed by job_id.
job_store: dict[str, dict] = {}


async def _run_analysis(job_id: str, image_dir: Path, project_name: str) -> None:
    try:
        def on_event(event: dict):
            if job_id not in job_store:
                return
            job = job_store[job_id]
            
            # Update active task
            if event.get('type') == 'task_start':
                job['active_task'] = event.get('task_id')
                
            # If a task finishes successfully, load its result
            elif event.get('type') == 'task_end':
                task_id = event.get('task_id')
                status = event.get('status')
                if status == 'success':
                    output_path_str = event.get('output_path')
                    if output_path_str:
                        output_path = Path(output_path_str)
                        if output_path.exists():
                            try:
                                result_data = json.loads(output_path.read_text(encoding='utf-8'))
                                task_result = {
                                    'status': 'success',
                                    'task_id': task_id,
                                    'result': result_data,
                                    'output_path': output_path_str
                                }
                                # Ensure results structure matches
                                if 'results' not in job or not isinstance(job['results'], dict):
                                    job['results'] = {'results': [], 'total_tasks': 4}
                                
                                # Update or append
                                existing = [r for r in job['results']['results'] if r.get('task_id') == task_id]
                                if not existing:
                                    job['results']['results'].append(task_result)
                                else:
                                    idx = job['results']['results'].index(existing[0])
                                    job['results']['results'][idx] = task_result
                            except Exception as e:
                                print(f"Error loading progressive results: {e}")
                elif status == 'failed':
                    task_result = {
                        'status': 'failed',
                        'task_id': task_id,
                        'error': event.get('error', 'Unknown error')
                    }
                    if 'results' not in job or not isinstance(job['results'], dict):
                        job['results'] = {'results': [], 'total_tasks': 4}
                    existing = [r for r in job['results']['results'] if r.get('task_id') == task_id]
                    if not existing:
                        job['results']['results'].append(task_result)
                    else:
                        idx = job['results']['results'].index(existing[0])
                        job['results']['results'][idx] = task_result

        results = await run_agents(ImageListPath=image_dir, Project_name=project_name, on_event=on_event)
        job_store[job_id] = {'status': 'done', 'results': results}
    except Exception as e:
        job_store[job_id] = {'status': 'error', 'message': str(e)}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def main_page(request: Request):
    file_path    = request.session.get('file_path')
    image_files  = request.session.get('image_files', [])
    project_name = request.session.get('project_name', '')

    page_labels: dict[str, str] = {}
    if image_files and project_name:
        labels_file = IMAGES_DIR / project_name / "page_labels.json"
        if labels_file.exists():
            for entry in json.loads(labels_file.read_text(encoding="utf-8")):
                page_labels[Path(entry["path"]).name] = entry["label"]

    return templates.TemplateResponse(request, "index.html", {
        "has_file":     bool(file_path),
        "has_images":   bool(image_files),
        "filename":     Path(file_path).name if file_path else "",
        "project_name": project_name,
        "image_files":  image_files,
        "page_labels":  page_labels,
    })


@app.post('/upload')
async def upload_file(request: Request, file: UploadFile = File(...)):
    if not file or not file.filename:
        return JSONResponse({'error': 'No file uploaded'}, status_code=400)

    project_name = Path(file.filename).stem
    dest = ORIGINALS_DIR / file.filename

    with dest.open("wb") as buf:
        shutil.copyfileobj(file.file, buf)

    request.session['file_path']    = str(dest)
    request.session['project_name'] = project_name
    request.session.pop('image_files', None)
    request.session.pop('base64_img', None)

    return RedirectResponse(url='/', status_code=status.HTTP_303_SEE_OTHER)


@app.post('/image')
async def process_images(request: Request):
    saved_path = request.session.get('file_path')
    if not saved_path or not os.path.exists(saved_path):
        return JSONResponse({'error': 'No valid file in session'}, status_code=400)

    project_name      = request.session.get('project_name', 'unknown')
    project_images_dir = IMAGES_DIR / project_name
    project_images_dir.mkdir(exist_ok=True)

    image_paths, _, _page_info = pdf_to_images(saved_path, project_images_dir, dpi=300)
    request.session['image_files'] = [Path(p).name for p in image_paths]

    return RedirectResponse(url='/', status_code=status.HTTP_303_SEE_OTHER)


@app.get('/preview/{project_name}/{filename}')
async def preview_image(project_name: str, filename: str):
    file_path = IMAGES_DIR / project_name / filename
    if not file_path.exists():
        return JSONResponse({'error': 'Image not found'}, status_code=404)
    return FileResponse(file_path, media_type='image/png')


@app.post('/process/task1')
async def explore_project(request: Request):
    project_name = request.session.get('project_name')
    if not project_name:
        return JSONResponse({'error': 'No project in session'}, status_code=400)

    image_dir = IMAGES_DIR / project_name

    if not any(image_dir.glob("page_*.png")):
        return JSONResponse({'error': 'No images found. Convert the PDF first.'}, status_code=400)
    job_id = uuid.uuid4().hex
    job_store[job_id] = {
        'status': 'running',
        'active_task': None,
        'results': {'results': [], 'total_tasks': 4}
    }
    asyncio.create_task(_run_analysis(job_id, image_dir, project_name))

    return JSONResponse({'job_id': job_id, 'status': 'started'})


@app.get('/status/{job_id}')
async def job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        return JSONResponse({'error': 'Job not found'}, status_code=404)
    return JSONResponse(job)
