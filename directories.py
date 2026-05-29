from pathlib import Path


WORKSPACE   = Path(__file__).parent / "data"
CROPS_DIR   = WORKSPACE / "__crops"
SCRATCH_DIR = WORKSPACE / "__scratch"

WORKSPACE.mkdir(exist_ok=True)
CROPS_DIR.mkdir(exist_ok=True)
SCRATCH_DIR.mkdir(exist_ok=True)

# Set per-job before query; crop_region closes over this variable.
_project_crops_dir: Path = CROPS_DIR

