"""Smoke test: start the MCP server, list its tools, and call some of them. Free (no LLM calls).

Usage (from the project root):  python scripts/try_mcp.py
"""
import asyncio
import sys

from mcp import Client, StdioServerParameters

# How to start the server: the same Python, running radar/mcp_server.py as a module.
SERVER = StdioServerParameters(command=sys.executable, args=["-m", "radar.mcp_server"])


async def main() -> None:
    async with Client(SERVER) as client:              # starts the server as a subprocess
        listed = await client.list_tools()
        print("Tools offered by the server:")
        for tool in listed.tools:
            print(f"  - {tool.name}: {tool.description.splitlines()[0]}")

        calls = [
            ("skills_top", {"limit": 5}),
            ("skills_trend", {"skill": "kubernetes"}),
            ("postings_search", {"skill": "Rust", "work_mode": "remote", "limit": 1}),
            ("skills_trend", {"skill": "kubernets"}),        # typo on purpose
        ]
        for name, arguments in calls:
            result = await client.call_tool(name, arguments)
            status = "ERROR" if result.is_error else "ok"
            print(f"\n{name}({arguments}) -> {status}")
            print(result.content[0].text[:500])


if __name__ == "__main__":
    asyncio.run(main())
