import asyncio
# pyrefly: ignore [missing-import]
from claude_agent_sdk import  ClaudeSDKClient, ClaudeAgentOptions , AssistantMessage, TextBlock, ResultMessage


# async with ClaudeSDKClient() as client:
#     await client.query('')




options = ClaudeAgentOptions(
    thinking={'type': 'adaptive', "budget_tokens" : 500000},
    tools={},
    allowed_tools=['Read' ,'Write', 'Bash'],
    permission_mode = "acceptEdits" 
)

async def main():
    async with ClaudeSDKClient() as client:
        await client.query(input(''))


