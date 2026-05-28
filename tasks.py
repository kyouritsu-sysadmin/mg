from dataclasses import dataclass , Field
from pathlib import Path
from pydantic import BaseModel

@dataclass
class Task:
    id : str
    prompt: str
    target_pages : list[int]
    schema: type[BaseModel]
    max_turns:int = 20
    max_attempts : int = 3

    def prompt(self, workspace: Path) -> str:
        images = sorted(workspace.glob("page_*.jpg"))