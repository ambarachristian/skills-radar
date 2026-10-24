"""The radar web page: a trend chart and a chat box with the agent.

Run:  uvicorn web.app:app --reload        then open http://127.0.0.1:8000
"""
import contextlib
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from mcp import Client
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

from radar import queries
from radar.agent import SERVER, answer

PAGE = Path(__file__).parent / "index.html"
TOP_SKILLS = 6        # lines shown by default
MAX_LINES = 8         # the chart palette has 8 colors: never more lines than that
MAX_QUESTION = 500    # characters per chat question
MAX_HISTORY = 10      # earlier chat messages sent along with each question


@contextlib.asynccontextmanager
async def lifespan(app):
    """Start the Claude client and the MCP server once, when the web server starts."""
    load_dotenv(override=True)
    app.state.claude = anthropic.AsyncAnthropic()
    async with Client(SERVER) as mcp_client:
        app.state.mcp = mcp_client
        yield                                    # the web server runs while we're here


async def home(request: Request):
    return FileResponse(PAGE)


async def trends(request: Request):
    """Share of posts per month: the latest month's top skills, plus ?add=Rust,Go."""
    names = [s["skill"] for s in queries.top_skills(limit=TOP_SKILLS)["skills"]]
    for extra in request.query_params.get("add", "").split(","):
        if extra.strip():
            try:
                name = queries.check_skill(extra)
            except ValueError as e:
                return JSONResponse({"error": str(e)}, status_code=400)
            if name not in names:
                names.append(name)
    months = queries.available_months()
    series = [queries.skill_trend(name, months) for name in names[:MAX_LINES]]
    return JSONResponse({"months": months, "series": series})


async def chat(request: Request):
    body = await request.json()
    question = str(body.get("question", "")).strip()[:MAX_QUESTION]
    if not question:
        return JSONResponse({"error": "Empty question"}, status_code=400)
    # Keep only well-formed text turns, and start the history with a user turn.
    history = [{"role": m.get("role"), "content": str(m.get("content", ""))[:4000]}
               for m in body.get("history", [])[-MAX_HISTORY:]
               if m.get("role") in ("user", "assistant")]
    while history and history[0]["role"] != "user":
        history.pop(0)
    result = await answer(question, request.app.state.mcp, request.app.state.claude,
                          history=history)
    return JSONResponse(result)


app = Starlette(
    routes=[
        Route("/", home),
        Route("/api/trends", trends),
        Route("/api/chat", chat, methods=["POST"]),
    ],
    lifespan=lifespan,
)
