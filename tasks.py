from dataclasses import dataclass
from pydantic import BaseModel
import json


@dataclass
class Task:
    id: str
    prompt: str
    schema: type[BaseModel]
    target_pages: str = "ALL IMAGES"
    max_turns: int = 20 
    max_attempts: int = 3

    def base_prompt(self, Imagelist: list[str]) -> str:
        return (
            f"{self.prompt}\n\n"
            f"Images in workspace:\n{Imagelist}\n\n"
            f"Use {self.target_pages} to search and extract definitive data from the provided resources.\n"
            f"Return ONLY valid JSON matching this schema. "
            f"No prose, no markdown fences.\n"
            f"Schema:\n{self.schema.model_json_schema()}"
        )

    def continuation(self, previous: dict) -> str:
        return (
            f"{self.prompt}\n\n"
            f"Context from the previous extraction step:\n"
            f"{json.dumps(previous, indent=2)}\n\n"
            f"Return ONLY valid JSON matching this schema.\n"
            f"No prose, no markdown fences.\n"
            f"Schema:\n{self.schema.model_json_schema()}"
        )