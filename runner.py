'''

The main job of run_task is to safely execute an AI agent job from start to finish. 
It takes a raw task instruction, creates a secure physical workspace for it, 
lets the AI agent do its work, double-checks that the AI's output isn't broken, saves the valid results, 
and cleanly destroys the temporary workspace afterward.

It cuses: 
1. directory: data/__scratch 
2. working on the pgs fed via image list 
3. Gate keep for the agnts --> permissions, tools, rules, hooks 
4. Self correction feedbackloop 
5. result validation and clean up temps


'''

import shutil
import json
from directories import CROPS_DIR
from claude_agent_sdk import PermissionResultDeny
from claude_agent_sdk.types import PermissionResultAllow
from tools import ALLOWED_TOOLS
from pathlib import Path
from typing import Optional
import asyncio , json , tempfile
from tasks import Task
from agent import main

async def gatekeep(tool_name: str | Optional, path : Path | Optional,  context: str | Optional):

    if tool_name in ALLOWED_TOOLS:
        return PermissionResultAllow()
    
    if path  and path.resolve().is_relative_to(CROPS_DIR):
        return PermissionResultAllow()
    
    return PermissionResultDeny(message='write command denied')



async def run_task(task: Task, ImageList : list[str], result_dir : Path):

    __scratchpad = Path(tempfile.mkdtemp(prefix=f"bom_{task.id}_"))
    WRITE_DIR = CROPS_DIR / __scratchpad

    try: 
        
        results = await main(project_name='',image_path=ImageList, gate=gatekeep, cwd = WRITE_DIR)
        if not results:
            return 


    except json.JSONDecodeError as e:
        if not results:
            raise Exception('No results found')




