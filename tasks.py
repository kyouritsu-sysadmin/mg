from dataclasses import dataclass, field
from pydantic import BaseModel
import json


@dataclass
class Task:
    id: str
    group: int
    prompt: str
    schema: type[BaseModel]
    target_pages: str = "ALL IMAGES"
    # Declare which page labels this task cares about.
    # Empty list = all pages. Used to focus the agent and for future routing.
    page_types: list[str] = field(default_factory=list)
    max_turns: int = 10
    max_attempts: int = 3
    effort: str = "medium"

    def base_prompt_text(self, image_list: list[dict]) -> str:
        """Text prompt used when images are embedded directly as content blocks.

        Includes a page manifest (page number + label) so the agent knows
        what type of content each attached image contains and where to focus.
        """
        manifest = "\n".join(
            f"  Page {d['page_number']} [{d['label']}]: {d['path']}"
            for d in image_list
        )
        focus = (
            f"Focus on pages labelled: {', '.join(self.page_types)}."
            if self.page_types
            else "Analyse ALL pages."
        )
        return (
            f"{self.prompt}\n\n"
            f"Attached pages:\n{manifest}\n\n"
            f"{focus}\n"
            f"Return ONLY valid JSON matching this schema. "
            f"No prose, no markdown fences.\n"
            f"Schema:\n{json.dumps(self.schema.model_json_schema(), indent=2, ensure_ascii=False)}"
        )

    def continuation(self, previous: dict) -> str:
        return (
            f"{self.prompt}\n\n"
            f"Context from the previous extraction step:\n"
            f"{json.dumps(previous, indent=2, ensure_ascii=False)}\n\n"
            f"Return ONLY valid JSON matching this schema. "
            f"No prose, no markdown fences.\n"
            f"Schema:\n{json.dumps(self.schema.model_json_schema(), indent=2, ensure_ascii=False)}"
        )
    
    def filter_pages(self, image_list : list[dict]):

        if not self.page_types: 
            return image_list
        
        return [img for img in image_list if img['label'] in self.page_types]