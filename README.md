# sweAiTracker

Daily data on how AI is changing software engineering roles, pay, and hiring, collected for an Information Systems data analysis project (UNLV, Fall 2026) by Jacob Martinez, with collection automated by Claude.

## Research questions

1. How are software engineers actually using AI, and is "writing code" being handed off?
2. Is back end work more cautious about AI than front end?
3. Is the developer role shifting toward system design and architecture, and does that pay more?
4. Are new roles forming around AI engineering or prompt engineering?

## What gets collected every day

Collection runs automatically each morning in GitHub Actions (`.github/workflows/daily-collect.yml` runs `scripts/run_daily.py`), and the results are committed back to this repo.

| Source | What | Files |
|---|---|---|
| [Indeed Hiring Lab](https://github.com/hiring-lab) (CC BY 4.0) | Daily index of US job postings for Software Development and related sectors since Feb 2020; share of US postings that mention AI since 2019 | `data/indeed/` |
| Company job boards (public Greenhouse, Ashby and Lever APIs) | Every open job at ~45 tech companies (`config/companies.csv`), with job IDs so we can count **new** and **closed** postings each day, flags for what the **job description** mentions (AI coding tools, LLMs/GenAI, system design, hands-on coding), and **salary ranges** where posted | `data/boards/` |
| Hacker News "Ask HN: Who is hiring?" (Algolia API) | Every post in every monthly thread since 2018, with the same AI / role flags, to show the trend over time | `data/hn/` |
| US Bureau of Labor Statistics (public API) | JOLTS job openings, hires and layoffs (information sector), employment in software industries, and OEWS employment and wages for software developers and related jobs. Refreshed Mondays | `data/bls/` |

Survey data (Stack Overflow Developer Survey 2021 to 2025) is used in the analysis but is not collected here, since it is released once a year.

### How the job-board data answers the research questions

| Question | Where to look |
|---|---|
| 1. Are engineers expected to use AI to write code? | `desc_ai_coding_tools_share` in `data/boards/daily_summary.csv` (share of engineering job descriptions naming tools like Copilot, Cursor or Claude, or AI-assisted development); `mentions_ai_coding_tools_share` by month in `data/hn/monthly.csv` |
| 2. Is back end more cautious about AI than front end? | `ai_coding_tools_share` and `llm_genai_share` for `backend` vs `frontend` in `data/boards/category_summary.csv` |
| 3. Is the role shifting to system design, and does it pay more? | `system_design_share` and `us_median_salary_mid` by category (`architect` vs others) in `category_summary.csv`; OEWS wages in `data/bls/series.csv` |
| 4. Are new AI / prompt engineering roles forming? | `new_eng` and `new_eng_ai_title_share` (are newly posted jobs more AI-titled than existing ones?) in `daily_summary.csv`; `role_ai_ml_engineer_share` and `role_prompt_engineer_share` by month in `data/hn/monthly.csv` |

## Files

```
config/companies.csv              companies collected daily (company, ats, slug, group)
scripts/run_daily.py              runs every collector and appends data/run_log.csv
scripts/collect_boards.py         company job boards -> data/boards/
scripts/hn_hiring.py              Hacker News Who's Hiring -> data/hn/
scripts/bls.py                    BLS JOLTS / CES / OEWS -> data/bls/
scripts/indeed.py                 Indeed Hiring Lab -> data/indeed/
scripts/common.py                 shared title categories and description keyword rules
data/boards/postings.csv          one row per job ever seen: title, category, seniority, description flags, salary, first_seen, last_seen
data/boards/snapshots/DATE.csv    job IDs open on DATE
data/boards/daily_summary.csv     one row per day: open / new / closed engineering jobs, AI shares, median pay (open in Excel)
data/boards/category_summary.csv  one row per day per job category
data/boards/company_summary.csv   one row per day per company
data/boards/fetch_log.csv         which company boards worked each day
data/hn/posts.csv, monthly.csv    Hacker News posts and monthly shares
data/bls/series.csv               BLS series, long format
data/run_log.csv                  one row per daily run: what worked, what failed
```

### Old pipeline (Oct 17 to Oct 23, 2026)

Before the switch, Claude fetched titles from 14 departments at 6 companies with WebFetch (`config/panel.csv`, `scripts/classify.py`, `data/jobs/`, `data/jobs_daily_summary.csv`). That list barely changed day to day and had no job IDs, descriptions or pay, so it was replaced. The files are kept for reference; titles are classified with the same rules in both pipelines.

## Columns in `data/jobs/DATE.csv`

| Column | Meaning |
|---|---|
| date | Collection date (Pacific time) |
| company, department | Panel source |
| title, location | As listed on the job board |
| is_us | 1 if the location is in the US (best effort; "Hybrid" or "Distributed" with no city counts as 0) |
| category | ai_ml, prompt_engineering, architect, platform_infra, security, data, fullstack, frontend, backend, mobile, eng_management, general_swe, or non_engineering (keyword rules in `scripts/classify.py`, checked in that order) |
| seniority | entry, mid_or_unspecified, senior, staff_plus, or management |
| is_engineering | 1 unless category is non_engineering |
| ai_in_title | 1 if category is ai_ml or prompt_engineering |
| fetch_status | COMPLETE or TRUNCATED, as reported when the list was collected |

## Known limits

- Description flags are keyword matches. "Mentions Copilot" means the posting names it, not that the team uses it; `cursor` can occasionally match a database cursor.
- Salaries come from the posting (structured on Ashby/Lever, parsed from text on Greenhouse). A `$` range may be non-US dollars, so use `is_us` = 1 rows; `salary_currency` is `USD?` when parsed from text.
- New/closed counts only compare days when that company's board was fetched successfully on both days. The first day of the new pipeline is a baseline (`baseline` = 1) with no new/closed counts.
- The panel includes AI companies (Anthropic, OpenAI, Cohere...), so AI titles are overrepresented; use `group` in `postings.csv` to compare AI labs with other companies. Compare each company to itself over time, not companies to each other.
- Job titles say what a role is called, not how much AI the job uses.
- Indeed refreshes its files on its own schedule (AI share monthly), so some days repeat the previous values; `pull_log.csv` records which date each pull reflects.

## Credit

Indeed Hiring Lab data: Hiring Lab, Indeed, licensed CC BY 4.0. Job listings: public Greenhouse, Ashby and Lever job board APIs. Hacker News data via the Algolia HN Search API. BLS data: U.S. Bureau of Labor Statistics.
