import asyncio
from dotenv import load_dotenv
load_dotenv()

from openai import AsyncOpenAI
from fastapi import Client as MCPClient
client = AsyncOpenAI()
mcp_client = MCPClient("mcp_manual.py")

async def main():
    msg = "Hello, how are you?"
    response = await client.responses.create(
        model="gpt-4o-mini",
        input = [
            {
                "role": "user",
                "context" : msg
            }
        ]

    )
    print(response.output_text)

if __name__ == "__main__":
    asyncio.run(main())