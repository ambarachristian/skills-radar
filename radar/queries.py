"""Read-only questions about the extracted job posts.

Used by the MCP server (Lesson 5) and the web page (Lesson 7).
Returns only extracted fields and HN links, never the raw post text.
"""
import json
import re
from collections import Counter
from difflib import get_close_matches
from statistics import median

from radar.db import connect_readonly
from radar.skills import SKILLS

# Which extraction the radar reads.
RADAR_MODEL = "claude-opus-5-5"
RADAR_PROMPT = "v2"

HN_URL = "https://news.ycombinator.com/item?id={}"
SKILL_BY_LOWER = {s.lower(): s for s in SKILLS}


# --- Checking inputs -----------------------------------------------------
def available_months() -> list[str]:
    conn = connect_readonly()
    months = [r["month"] for r in conn.execute("SELECT month FROM threads ORDER BY month")]
    conn.close()
    return months


def check_months(months: list[str] | None) -> list[str]:
    known = available_months()
    if not months:
        return known
    unknown = [m for m in months if m not in known]
    if unknown:
        raise ValueError(f"No data for {unknown}. Available months: {known}")
    return months


def check_skill(skill: str) -> str:
    """'kubernetes' -> 'Kubernetes'. Unknown skill -> error with suggestions."""
    name = SKILL_BY_LOWER.get(skill.strip().lower())
    if name is None:
        close = get_close_matches(skill.lower(), SKILL_BY_LOWER, n=3, cutoff=0.6)
        raise ValueError(f"Unknown skill {skill!r}. Did you mean: {[SKILL_BY_LOWER[c] for c in close]}? "
                         "Skills must come from the radar's fixed list.")
    return name


# --- Loading and filtering -----------------------------------------------
def load_jobs(months: list[str]) -> list[dict]:
    """All job posts in these months, with extracted fields. Non-job comments are left out."""
    conn = connect_readonly()
    rows = conn.execute(
        """SELECT p.id, p.month, p.text, e.data
           FROM posts p JOIN extractions e ON e.post_id = p.id
           WHERE e.model = ? AND e.prompt_version = ? AND e.run = 1 AND e.data IS NOT NULL
           ORDER BY p.month, p.id""",
        (RADAR_MODEL, RADAR_PROMPT),
    ).fetchall()
    conn.close()
    jobs = []
    for row in rows:
        data = json.loads(row["data"])
        if row["month"] in months and data.pop("is_job_post"):
            jobs.append({"hn_id": row["id"], "month": row["month"],
                         "url": HN_URL.format(row["id"]), **data,
                         "_text": row["text"].lower()})   # for search only, never returned
    return jobs


def matches(job: dict, work_mode=None, skill=None, country=None, city=None,
            seniority=None, ai_work=None) -> bool:
    """True if the job passes every filter that was given (None = no filter)."""
    if work_mode and work_mode not in job["work_modes"]:
        return False
    if skill and check_skill(skill) not in job["skills"]:
        return False
    if country and country.upper() not in job["countries"]:
        return False
    if city and city.lower() not in [c.lower() for c in job["cities"]]:
        return False
    if seniority and seniority not in [r["seniority"] for r in job["roles"]]:
        return False
    if ai_work is not None and job["ai_work"] != ai_work:
        return False
    return True


def has_words(text: str, query: str) -> bool:
    """Every word of the query appears as a whole word ('rust' doesn't match 'trust')."""
    return all(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in query.lower().split())


def public(job: dict) -> dict:
    """Drop the private keys (those starting with _) before returning a job."""
    return {k: v for k, v in job.items() if not k.startswith("_")}


def usd_salary_summary(jobs: list[dict]) -> dict:
    """Computed in code over ALL matches, so the agent never averages a partial list.
    A post counts if it gives a minimum, a maximum, or both ("up to $750k" counts)."""
    ranges = []
    for j in jobs:
        lo, hi = j["salary_min"], j["salary_max"]
        if j["salary_currency"] == "USD" and (lo or hi):
            ranges.append((lo or hi, hi or lo))      # a missing end takes the other end's value
    if not ranges:
        return {"posts_with_usd_salary": 0}
    return {"posts_with_usd_salary": len(ranges),
            "lowest_min": min(lo for lo, hi in ranges),
            "highest_max": max(hi for lo, hi in ranges),
            "median_midpoint": round(median((lo + hi) / 2 for lo, hi in ranges))}


# --- The four questions --------------------------------------------------
MAX_LIMIT = 25   # never return more postings than this in one call


def search_postings(query: str = "", months=None, limit: int = 10,
                    sort_by_salary: bool = False, **filters) -> dict:
    found = [j for j in load_jobs(check_months(months))
             if matches(j, **filters) and has_words(j["_text"], query)]
    if sort_by_salary:   # highest USD salary first; posts without a USD salary go last
        found.sort(key=lambda j: (j["salary_max"] or j["salary_min"] or 0)
                   if j["salary_currency"] == "USD" else 0, reverse=True)
    limit = max(1, min(limit, MAX_LIMIT))
    return {"total_matches": len(found),
            "salary_usd": usd_salary_summary(found),
            "postings": [public(j) for j in found[:limit]]}
    found = [j for j in load_jobs(check_months(months))
             if matches(j, **filters) and has_words(j["_text"], query)]
    return {"total_matches": len(found),
            "salary_usd": usd_salary_summary(found),
            "postings": [public(j) for j in found[:limit]]}


def get_posting(hn_id: int) -> dict:
    for job in load_jobs(available_months()):
        if job["hn_id"] == hn_id:
            return public(job)
    raise ValueError(f"No job post with id {hn_id}. Find ids with postings_search.")


def top_skills(month: str | None = None, limit: int = 15, **filters) -> dict:
    month = check_months([month])[0] if month else available_months()[-1]
    jobs = [j for j in load_jobs([month]) if matches(j, **filters)]
    skip = check_skill(filters["skill"]) if filters.get("skill") else None
    counts = Counter(s for j in jobs for s in j["skills"] if s != skip)
    return {"month": month, "job_count": len(jobs),
            "skills": [{"skill": s, "count": n, "share": round(n / len(jobs), 3)}
                       for s, n in counts.most_common(limit)]}


def skill_trend(skill: str, months=None) -> dict:
    name = check_skill(skill)
    months = check_months(months)
    jobs = load_jobs(months)
    points = []
    for m in months:
        in_month = [j for j in jobs if j["month"] == m]
        n = sum(name in j["skills"] for j in in_month)
        points.append({"month": m, "count": n, "job_count": len(in_month),
                       "share": round(n / len(in_month), 3) if in_month else None})
    return {"skill": name, "points": points}
