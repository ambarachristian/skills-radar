"""The 20 questions for the answer eval, with true answers computed by SQL.

The SQL is written independently of radar/queries.py on purpose: if a tool has a
bug, the truth computed here won't share it.
"""
import json
from statistics import median

from radar.db import connect_readonly

# The same data the agent's tools read: v2 extractions, job posts only.
JOBS = """
WITH jobs AS (
    SELECT p.id, p.month, e.data
    FROM posts p JOIN extractions e ON e.post_id = p.id
    WHERE e.model = 'claude-opus-5-5' AND e.prompt_version = 'v2' AND e.run = 1
      AND json_extract(e.data, '$.is_job_post') = 1
)
"""


def rows(sql: str) -> list:
    conn = connect_readonly()
    result = conn.execute(JOBS + sql).fetchall()
    conn.close()
    return result


def has(field: str, value: str) -> str:
    """SQL condition: the JSON list `field` contains `value`."""
    return f"EXISTS (SELECT 1 FROM json_each(data, '$.{field}') WHERE value = '{value}')"


def count(where: str) -> int:
    return rows(f"SELECT COUNT(*) FROM jobs WHERE {where}")[0][0]


def top_skills(where: str, n: int) -> list[str]:
    result = rows(f"""SELECT s.value, COUNT(*) AS n FROM jobs, json_each(jobs.data, '$.skills') s
                      WHERE {where} GROUP BY s.value ORDER BY n DESC LIMIT {n}""")
    return [r[0] for r in result]


# A USD salary is listed if the post gives a minimum, a maximum, or both.
USD = ("json_extract(data, '$.salary_currency') = 'USD' AND "
       "COALESCE(json_extract(data, '$.salary_min'), json_extract(data, '$.salary_max')) IS NOT NULL")
OCT = "month = '2026-10'"
SEP = "month = '2026-09'"


def highest_usd(where: str) -> int:
    return rows(f"""SELECT MAX(COALESCE(json_extract(data, '$.salary_max'), json_extract(data, '$.salary_min')))
                    FROM jobs WHERE {where} AND {USD}""")[0][0]


def median_usd_midpoint(where: str) -> float:
    result = rows(f"""SELECT COALESCE(json_extract(data, '$.salary_min'), json_extract(data, '$.salary_max')),
                             COALESCE(json_extract(data, '$.salary_max'), json_extract(data, '$.salary_min'))
                      FROM jobs WHERE {where} AND {USD}""")
    return median((lo + hi) / 2 for lo, hi in result)


def company(hn_id: int) -> str:
    return rows(f"SELECT json_extract(data, '$.company') FROM jobs WHERE id = {hn_id}")[0][0]


def skills_of(hn_id: int) -> list[str]:
    return json.loads(rows(f"SELECT json_extract(data, '$.skills') FROM jobs WHERE id = {hn_id}")[0][0])


# Each question has ONE kind of expected answer:
#   numbers: every number must appear in the answer (within `tolerance`, relative)
#   words:   every word must appear in the answer
#   no_data: the answer must say the data can't answer it
# Truths are functions, so they're computed fresh from the database at each run.
QUESTIONS = [
    # --- Counting ---
    {"id": "q01", "question": "How many October 2026 job posts allow remote work?",
     "numbers": lambda: [count(f"{OCT} AND {has('work_modes', 'remote')}")]},
    {"id": "q02", "question": "How many September 2026 job posts involve AI/ML work?",
     "numbers": lambda: [count(f"{SEP} AND json_extract(data, '$.ai_work') = 1")]},
    {"id": "q03", "question": "Across all months, how many job posts ask for Rust?",
     "numbers": lambda: [count(has("skills", "Rust"))]},
    {"id": "q04", "question": "How many October 2026 job posts are for jobs in London?",
     "numbers": lambda: [count(f"{OCT} AND EXISTS (SELECT 1 FROM json_each(data, '$.cities') "
                               "WHERE lower(value) = 'london')")]},
    {"id": "q05", "question": "How many October 2026 job posts include at least one senior-level role?",
     "numbers": lambda: [count(f"{OCT} AND EXISTS (SELECT 1 FROM json_each(data, '$.roles') "
                               "WHERE json_extract(value, '$.seniority') = 'senior')")]},
    # --- Top skills ---
    {"id": "q06", "question": "What was the single most requested skill in October 2026?",
     "words": lambda: top_skills(OCT, 1)},
    {"id": "q07", "question": "What were the top 3 skills in September 2026?",
     "words": lambda: top_skills(SEP, 3)},
    {"id": "q08", "question": "Among October 2026 jobs that involve AI work, which skill is asked for most?",
     "words": lambda: top_skills(f"{OCT} AND json_extract(data, '$.ai_work') = 1", 1)},
    {"id": "q09", "question": "In October 2026, which two skills appear most often together with Rust?",
     "words": lambda: top_skills(f"{OCT} AND {has('skills', 'Rust')} AND s.value <> 'Rust'", 2)},
    # --- Trends ---
    {"id": "q10", "question": "How many posts asked for Kubernetes in September 2026, and how many in October 2026?",
     "numbers": lambda: [count(f"{SEP} AND {has('skills', 'Kubernetes')}"),
                         count(f"{OCT} AND {has('skills', 'Kubernetes')}")]},
    {"id": "q11", "question": "Did demand for TypeScript go up or down from September to October 2026? Give the post counts.",
     "numbers": lambda: [count(f"{SEP} AND {has('skills', 'TypeScript')}"),
                         count(f"{OCT} AND {has('skills', 'TypeScript')}")]},
    {"id": "q12", "question": "What percentage of October 2026 job posts asked for Python?",
     "numbers": lambda: [round(100 * count(f"{OCT} AND {has('skills', 'Python')}") / count(OCT), 1)],
     "tolerance": 0.05},
    # --- Salaries ---
    {"id": "q13", "question": "What is the median USD salary (midpoint of the posted range) for remote jobs that ask for Python?",
     "numbers": lambda: [median_usd_midpoint(f"{has('skills', 'Python')} AND {has('work_modes', 'remote')}")],
     "tolerance": 0.02},
    {"id": "q14", "question": "What is the highest USD salary listed in an October 2026 job post?",
     "numbers": lambda: [highest_usd(OCT)]},
    {"id": "q15", "question": "Across all months, how many job posts list a salary in USD?",
     "numbers": lambda: [count(USD)]},
    # --- Looking up one post ---
    {"id": "q16", "question": "Which company posted Hacker News item 49923847?",
     "words": lambda: [company(49923847)]},
    {"id": "q17", "question": "What skills does job post 49925526 ask for?",
     "words": lambda: skills_of(49925526)},
    # --- The data can't answer these ---
    {"id": "q18", "question": "What is the average salary for jobs in Lagos?", "no_data": True},
    {"id": "q19", "question": "What were the top skills in March 2026?", "no_data": True},
    {"id": "q20", "question": "Which company offers the most equity?", "no_data": True},
]
