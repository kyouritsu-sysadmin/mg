from dataclasses import dataclass , Field
from pathlib import Path
from pydantic import BaseModel

@dataclass
class Task:
    id : str # id for tasks 
    prompt: str # core instruction for model 
    target_pages : str # how many pages this tasks will hold for processing 
    schema: type[BaseModel] # the output schema to be followed 
    max_turns:int = 20 # max turs for clientsdk 
    max_attempts : int = 3 # retries will schema fails 

    def base_prompt(self, Imagelist : list[str]) -> str: 
        #this function guides agent what to do 
            # locates the files to be processed by the agent 
            #  create a input list of th eimages 
                #  takes from __images/project=xyx folder and creates a list of the images to tbe processed
            # This holds the main prompt for the agentic sdk client for start, this promptis coming from the task class defined 
            # The main prompt is fed to the taskclass. so that full guideworks properly   


        # images = sorted(workspace.glob("page_*.jpg")) --. not going to impplement now based on the profermance. 

        return (
            f"{self.prompt}\n\n"
            f"Images in workspace:\n{Imagelist}\n\n"
            f"Use the {self.target_pages} to searchand xtraction definitive data from the provided resources"
            f"Return ONLY valid JSON matching this schema. "
            f"No prose, no markdown fences.\n"
            f"Schema:\n{self.schema.model_json_schema()}"
        )