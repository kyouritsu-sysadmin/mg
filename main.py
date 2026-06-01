import os
import shutil
import uuid
import asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from utils import pdf_to_images
from orchestrator import run_agents

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.add_middleware(SessionMiddleware, secret_key='mynkey')

WORKSPACE     = Path(__file__).parent / "data"
ORIGINALS_DIR = WORKSPACE / "__originals"
IMAGES_DIR    = WORKSPACE / "__images"

WORKSPACE.mkdir(exist_ok=True)
ORIGINALS_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# In-memory job store — keyed by job_id.
job_store: dict[str, dict] = {}


async def _run_analysis(job_id: str, image_dir: Path, project_name: str) -> None:
    try:
        results = await run_agents(ImageListPath=image_dir, Project_name=project_name)
        job_store[job_id] = {'status': 'done', 'results': results}
    except Exception as e:
        job_store[job_id] = {'status': 'error', 'message': str(e)}


def _render_page(file_path: str | None, project_name: str, image_files: list) -> str:
    has_file   = bool(file_path)
    has_images = bool(image_files)
    filename   = Path(file_path).name if has_file else ""

    badge1 = f'<span class="badge {"done" if has_file else ""}">{"✓" if has_file else "1"}</span>'
    badge2 = f'<span class="badge {"done" if has_images else ""}">{"✓" if has_images else "2"}</span>'
    badge3 = '<span class="badge">3</span>'

    file_chip    = f'<div class="chip">✓ {filename}</div>' if has_file else ''
    step2_muted  = '' if has_file   else 'muted'
    step3_muted  = '' if has_images else 'muted'
    step2_dis    = '' if has_file   else 'disabled'
    step3_dis    = '' if has_images else 'disabled'

    if has_images:
        imgs = ''.join(
            f'<img src="/preview/{project_name}/{f}" title="Page {i+1}" loading="lazy" />'
            for i, f in enumerate(image_files)
        )
        thumbs_html = (
            f'<div class="thumbs">{imgs}</div>'
            f'<p class="page-count">{len(image_files)} page(s)</p>'
        )
    else:
        thumbs_html = ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Document Analyzer</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f1f5f9;color:#1e293b;min-height:100vh}}
header{{background:#0f172a;color:#f8fafc;padding:1rem 2rem;display:flex;align-items:center;gap:.6rem;box-shadow:0 1px 3px rgba(0,0,0,.3)}}
header h1{{font-size:1.05rem;font-weight:600;letter-spacing:-.01em}}
main{{max-width:700px;margin:1.75rem auto;padding:0 1rem;display:flex;flex-direction:column;gap:1rem}}
.card{{background:#fff;border-radius:10px;border:1px solid #e2e8f0;overflow:hidden;transition:opacity .2s}}
.card.muted{{opacity:.4;pointer-events:none}}
.card-head{{display:flex;align-items:center;gap:.6rem;padding:.85rem 1.25rem;border-bottom:1px solid #f1f5f9;background:#f8fafc}}
.card-head h2{{font-size:.9rem;font-weight:600;color:#334155}}
.card-body{{padding:1rem 1.25rem}}
.badge{{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:#3b82f6;color:#fff;font-size:.7rem;font-weight:700;flex-shrink:0}}
.badge.done{{background:#22c55e}}
.upload-zone{{position:relative;border:2px dashed #cbd5e1;border-radius:8px;padding:1.75rem 1.25rem;text-align:center;cursor:pointer;transition:border-color .15s,background .15s}}
.upload-zone.drag{{border-color:#3b82f6;background:#eff6ff}}
.upload-zone input[type=file]{{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}}
.upload-zone .uz-icon{{font-size:1.9rem;line-height:1;margin-bottom:.4rem}}
.upload-zone p{{color:#64748b;font-size:.85rem;margin-top:.2rem}}
.upload-zone .hl{{color:#3b82f6}}
.chip{{display:inline-flex;align-items:center;gap:.3rem;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:999px;padding:.2rem .65rem;font-size:.78rem;color:#15803d;margin-top:.7rem;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.btn{{display:inline-flex;align-items:center;gap:.35rem;padding:.45rem 1.1rem;border-radius:6px;border:none;font-size:.85rem;font-weight:500;cursor:pointer;transition:background .15s}}
.btn-blue{{background:#3b82f6;color:#fff}}
.btn-blue:hover{{background:#2563eb}}
.btn-green{{background:#22c55e;color:#fff}}
.btn-green:hover{{background:#16a34a}}
.btn:disabled{{opacity:.4;cursor:not-allowed}}
.mt{{margin-top:.8rem}}
.thumbs{{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.85rem}}
.thumbs img{{height:96px;width:auto;border-radius:5px;border:1px solid #e2e8f0;object-fit:cover;transition:transform .15s,box-shadow .15s;cursor:zoom-in}}
.thumbs img:hover{{transform:scale(1.07);box-shadow:0 4px 14px rgba(0,0,0,.14)}}
.page-count{{font-size:.78rem;color:#94a3b8;margin-top:.4rem}}
#status-area{{display:none;align-items:center;gap:.6rem;margin-top:.85rem;color:#475569;font-size:.85rem}}
.spin{{width:17px;height:17px;border:2.5px solid #e2e8f0;border-top-color:#3b82f6;border-radius:50%;animation:spin .6s linear infinite;flex-shrink:0}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
#results-area{{display:none;margin-top:1rem}}
.result-block h4{{font-size:.78rem;font-weight:700;color:#64748b;margin-bottom:.5rem;text-transform:uppercase;letter-spacing:.05em}}
table.rtable{{width:100%;border-collapse:collapse;font-size:.83rem;border:1px solid #e2e8f0;border-radius:7px;overflow:hidden}}
table.rtable tr:nth-child(even) td{{background:#f8fafc}}
table.rtable td{{padding:.5rem .7rem;border-bottom:1px solid #e2e8f0;vertical-align:top}}
table.rtable td:first-child{{font-weight:600;color:#64748b;white-space:nowrap;width:36%}}
pre.jval{{background:#f1f5f9;border-radius:4px;padding:.3rem .5rem;font-size:.75rem;overflow-x:auto;white-space:pre-wrap;word-break:break-word;margin:0}}
.err{{background:#fef2f2;border:1px solid #fecaca;border-radius:7px;padding:.8rem 1rem;color:#991b1b;font-size:.85rem;margin-top:.85rem}}
.ok{{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:7px;padding:.6rem 1rem;color:#166534;font-size:.82rem;margin-bottom:.75rem}}
</style>
</head>
<body>

<header>
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
       stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="16" y1="13" x2="8" y2="13"/>
    <line x1="16" y1="17" x2="8" y2="17"/>
  </svg>
  <h1>Document Analyzer</h1>
</header>

<main>

  <!-- Step 1: Upload -->
  <div class="card">
    <div class="card-head">
      {badge1}
      <h2>Upload PDF</h2>
    </div>
    <div class="card-body">
      <form action="/upload" method="post" enctype="multipart/form-data" id="upload-form">
        <div class="upload-zone" id="drop-zone">
          <input type="file" name="file" id="file-input" accept=".pdf">
          <div class="uz-icon">📄</div>
          <p>Drop PDF here or <span class="hl">browse files</span></p>
        </div>
        {file_chip}
      </form>
    </div>
  </div>

  <!-- Step 2: Convert -->
  <div class="card {step2_muted}">
    <div class="card-head">
      {badge2}
      <h2>Convert to Images</h2>
    </div>
    <div class="card-body">
      <form action="/image" method="post">
        <button type="submit" class="btn btn-blue" {step2_dis}>🖼 Convert PDF to Images</button>
      </form>
      {thumbs_html}
    </div>
  </div>

  <!-- Step 3: Analyze -->
  <div class="card {step3_muted}">
    <div class="card-head">
      {badge3}
      <h2>Run Analysis</h2>
    </div>
    <div class="card-body">
      <button class="btn btn-green" id="analyze-btn" onclick="startAnalysis()" {step3_dis}>
        ⚡ Run Analysis
      </button>
      <div id="status-area">
        <div class="spin"></div>
        <span id="status-text">Analyzing document…</span>
      </div>
      <div id="results-area"></div>
    </div>
  </div>

</main>

<script>
  // Auto-submit when file chosen via dialog
  const fi = document.getElementById('file-input');
  if (fi) {{
    fi.addEventListener('change', () => {{
      if (fi.files.length) document.getElementById('upload-form').submit();
    }});
  }}

  // Drag-and-drop onto upload zone
  const dz = document.getElementById('drop-zone');
  if (dz) {{
    ['dragover','dragenter'].forEach(ev =>
      dz.addEventListener(ev, e => {{ e.preventDefault(); dz.classList.add('drag'); }})
    );
    ['dragleave','dragend'].forEach(ev =>
      dz.addEventListener(ev, () => dz.classList.remove('drag'))
    );
    dz.addEventListener('drop', e => {{
      e.preventDefault();
      dz.classList.remove('drag');
      if (e.dataTransfer && e.dataTransfer.files.length) {{
        fi.files = e.dataTransfer.files;
        document.getElementById('upload-form').submit();
      }}
    }});
  }}

  async function startAnalysis() {{
    const btn  = document.getElementById('analyze-btn');
    const stat = document.getElementById('status-area');
    const res  = document.getElementById('results-area');

    btn.disabled = true;
    stat.style.display = 'flex';
    res.style.display  = 'none';
    res.innerHTML = '';

    let jobId;
    try {{
      const r = await fetch('/process/task1', {{ method: 'POST' }});
      const d = await r.json();
      if (d.error) {{ showErr(d.error); btn.disabled = false; stat.style.display = 'none'; return; }}
      jobId = d.job_id;
    }} catch (e) {{
      showErr('Could not start analysis: ' + e.message);
      btn.disabled = false;
      stat.style.display = 'none';
      return;
    }}

    const poll = setInterval(async () => {{
      try {{
        const r   = await fetch('/status/' + jobId);
        const job = await r.json();
        if (job.status === 'done') {{
          clearInterval(poll);
          stat.style.display = 'none';
          showResults(job.results);
          btn.disabled = false;
        }} else if (job.status === 'error') {{
          clearInterval(poll);
          stat.style.display = 'none';
          showErr(job.message || 'Analysis failed.');
          btn.disabled = false;
        }}
        // 'running' → keep polling
      }} catch (e) {{
        clearInterval(poll);
        stat.style.display = 'none';
        showErr('Status check failed: ' + e.message);
        btn.disabled = false;
      }}
    }}, 2500);
  }}

  function showErr(msg) {{
    const a = document.getElementById('results-area');
    a.style.display = 'block';
    a.innerHTML = '<div class="err">⚠ ' + esc(msg) + '</div>';
  }}

  function showResults(results) {{
    const a     = document.getElementById('results-area');
    a.style.display = 'block';
    const items = (results && results.results) || [];
    let html = '';
    for (const r of items) {{
      if (r && r.result) {{
        html += '<div class="result-block"><div class="ok">✓ Extraction complete</div><h4>Extracted Data</h4>' + buildTable(r.result) + '</div>';
      }}
    }}
    a.innerHTML = html || '<p style="color:#94a3b8;font-size:.85rem">No data extracted.</p>';
  }}

  function buildTable(obj) {{
    const rows = Object.entries(obj).map(([k, v]) => {{
      const display = (v !== null && typeof v === 'object')
        ? '<pre class="jval">' + esc(JSON.stringify(v, null, 2)) + '</pre>'
        : esc(String(v));
      return '<tr><td>' + esc(k.replace(/_/g, ' ')) + '</td><td>' + display + '</td></tr>';
    }}).join('');
    return '<table class="rtable"><tbody>' + rows + '</tbody></table>';
  }}

  function esc(s) {{
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }}
</script>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return HTMLResponse(_render_page(
        file_path    = request.session.get('file_path'),
        project_name = request.session.get('project_name', ''),
        image_files  = request.session.get('image_files', []),
    ))


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

    image_paths, _ = pdf_to_images(saved_path, project_images_dir, dpi=300)
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

    # Flaw 6 fix: check the directory has actual images, not just that it exists.
    if not any(image_dir.glob("page_*.png")):
        return JSONResponse({'error': 'No images found. Convert the PDF first.'}, status_code=400)
    job_id = uuid.uuid4().hex
    job_store[job_id] = {'status': 'running'}
    asyncio.create_task(_run_analysis(job_id, image_dir, project_name))

    return JSONResponse({'job_id': job_id, 'status': 'started'})


@app.get('/status/{job_id}')
async def job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        return JSONResponse({'error': 'Job not found'}, status_code=404)
    return JSONResponse(job)
