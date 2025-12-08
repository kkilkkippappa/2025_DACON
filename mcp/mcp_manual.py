from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv

mcp = FastMCP("manual_mcp")

@mcp.resource()


@mcp.tool()
def get_person_mannual():
    try:
        pass
    catch:
        return {"error": "Failed to get manual from LLM."}