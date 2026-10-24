"""MCP server: four read-only tools over the skills radar.

An MCP client starts it for you. To start it by hand:  python -m radar.mcp_server
"""
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

from radar import queries

WorkMode = Literal["remote", "hybrid", "onsite"]
Seniority = Literal["intern", "junior", "mid", "senior", "staff+", "manager", "unspecified"]

mcp = MCPServer(
    name="skills-radar",
    instructions=(
        "Job posts from Hacker News 'Who is hiring?' threads, one post per company. "
        f"Months available: {', '.join(queries.available_months())}. "
        "Fields were extracted by an LLM and checked on 50 hand-labeled posts "
        "(93-100% accurate depending on the field). About 250 posts per month, "
        "so say when a number rests on only a few posts."
    ),
)
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)


def ask(question, **kwargs) -> dict:
    """Run a query. Turn a ValueError into a ToolError the agent can read and fix."""
    try:
        return question(**kwargs)
    except ValueError as e:
        raise ToolError(str(e)) from e


@mcp.tool(annotations=READ_ONLY)
def postings_search(query: str = "", months: list[str] | None = None,
                    work_mode: WorkMode | None = None, skill: str | None = None,
                    country: str | None = None, city: str | None = None,
                    seniority: Seniority | None = None, ai_work: bool | None = None,
                    limit: int = 10) -> dict:
    """Find and count job posts.

    Returns total_matches (counted over ALL matching posts), a USD salary summary
    over all matches, and up to `limit` postings with their fields and HN link.
    For "how many" questions use total_matches, never the length of the list.

    Args:
        query: words that must all appear in the post, e.g. "rust embedded". "" = any.
        months: e.g. ["2026-10"]. Default: all months.
        work_mode: only posts that allow this mode.
        skill: only posts tagged with this skill, e.g. "Kubernetes".
        country: two-letter code, e.g. "US", "DE".
        city: e.g. "London", "New York".
        seniority: only posts with at least one role at this level.
        ai_work: true = roles doing AI/ML work only, false = non-AI roles only.
        limit: max postings returned. Counts and salaries always use all matches.
    """
    return ask(queries.search_postings, query=query, months=months, limit=limit,
               work_mode=work_mode, skill=skill, country=country, city=city,
               seniority=seniority, ai_work=ai_work)


@mcp.tool(annotations=READ_ONLY)
def posting_get(hn_id: int) -> dict:
    """All extracted fields of one job post, plus its HN link. Get ids from postings_search."""
    return ask(queries.get_posting, hn_id=hn_id)


@mcp.tool(annotations=READ_ONLY)
def skills_top(month: str | None = None, work_mode: WorkMode | None = None,
               skill: str | None = None, country: str | None = None,
               city: str | None = None, seniority: Seniority | None = None,
               ai_work: bool | None = None, limit: int = 15) -> dict:
    """Most requested skills in one month, with counts and share of matching posts.

    Args:
        month: e.g. "2026-10". Default: the latest month.
        skill: only posts that also need this skill ("what goes with Rust?").
               That skill itself is left out of the results.
        work_mode, country, city, seniority, ai_work: same filters as postings_search.
        limit: how many skills to return.
    """
    return ask(queries.top_skills, month=month, limit=limit, work_mode=work_mode,
               skill=skill, country=country, city=city, seniority=seniority,
               ai_work=ai_work)


@mcp.tool(annotations=READ_ONLY)
def skills_trend(skill: str, months: list[str] | None = None) -> dict:
    """How often one skill is asked for, month by month (count and share of posts).

    Compare shares, not counts: months have different numbers of posts.

    Args:
        skill: a skill from the radar's list, e.g. "Kubernetes". Case doesn't matter.
        months: e.g. ["2026-09", "2026-10"]. Default: all months.
    """
    return ask(queries.skill_trend, skill=skill, months=months)


if __name__ == "__main__":
    mcp.run()
