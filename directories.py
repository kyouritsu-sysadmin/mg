from contextvars import ContextVar
from pathlib import Path
from typing import Callable
import datetime
import json


WORKSPACE   = Path(__file__).parent / "workspace"
CROPS_DIR   = WORKSPACE / "__crops"
SCRATCH_DIR = WORKSPACE / "__scratch"

WORKSPACE.mkdir(exist_ok=True)
CROPS_DIR.mkdir(exist_ok=True)
SCRATCH_DIR.mkdir(exist_ok=True)

# Per-task crop output directory — ContextVar is safe under concurrent async tasks.
_project_crops_dir: ContextVar[Path] = ContextVar("project_crops_dir", default=CROPS_DIR)

# Per-run structured log writer — set once in run_agents(), inherited by both
# parallel pipeline groups via asyncio.gather() context copy.
_LOG_NOOP: Callable[[dict], None] = lambda _: None
_log_writer: ContextVar[Callable[[dict], None]] = ContextVar("log_writer", default=_LOG_NOOP)


def make_log_writer(log_path: Path) -> Callable[[dict], None]:
    """Return a callable that appends one JSON line per event to log_path."""
    def write(event: dict) -> None:
        line = json.dumps({"ts": datetime.datetime.now().isoformat(), **event},
                          ensure_ascii=False)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return write
