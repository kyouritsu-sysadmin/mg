from contextvars import ContextVar
from pathlib import Path


WORKSPACE   = Path(__file__).parent / "data"
CROPS_DIR   = WORKSPACE / "__crops"
SCRATCH_DIR = WORKSPACE / "__scratch"

WORKSPACE.mkdir(exist_ok=True)
CROPS_DIR.mkdir(exist_ok=True)
SCRATCH_DIR.mkdir(exist_ok=True)

# Per-task crop output directory — ContextVar is safe under concurrent async tasks.
_project_crops_dir: ContextVar[Path] = ContextVar("project_crops_dir", default=CROPS_DIR)
