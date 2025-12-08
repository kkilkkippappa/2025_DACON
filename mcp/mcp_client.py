from fastmcp import FastMCPClient


client = Client("mcp_manual.py")

async def main():

    async with client:
        print(f"Client connected to MCP server : {client.is_connected()}")

        tools = await client.list_tools()
        print(f"Avatailble Tools: {tools}")

        if any(tool.name == "get_person_mannual" for tool in tools):
            result =  await client.call_tool("get_person_mannual")
            printf("get_person_mannual result : {result}")
    print(f"Client connected to MCP server : {client.is_connected()}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt as e:
        print(f"Client disconnected from MCP server : {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()
