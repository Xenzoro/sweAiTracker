# sweAiTracker

Daily data on how AI is changing software engineering roles, pay, and hiring, collected for an Information Systems data analysis project (UNLV, Fall 2026) by Jacob Martinez, with collection automated by Claude.

## Research questions

1. How are software engineers actually using AI, and is "writing code" being handed off?
2. Is back end work more cautious about AI than front end?
3. Is the developer role shifting toward system design and architecture, and does that pay more?
4. Are new roles forming around AI engineering or prompt engineering?

## What gets collected every day

| Source | What | How | Files |
|---|---|---|---|
| [Indeed Hiring Lab](https://github.com/hiring-lab) (CC BY 4.0) | Daily index of US job postings for Software Development and related tech sectors since Feb 2020; share of US postings that mention AI since 2019 | Cloned raw from Hiring Lab's GitHub repos | `data/indeed/` |
| Company job boards (Greenhouse public API) | Every open job title in the engineering departments of a fixed panel of companies | Fetched daily, one line per job | `data/jobs/raw/DATE/`, `data/jobs/DATE.csv` |

The company panel lives in `config/panel.csv`: Anthropic, Databricks, Figma, Cloudflare, GitLab, and Discord. Departments were chosen so each listing comes back complete (large boards get cut off when fetched whole).

Survey data (Stack Overflow Developer Survey 2021 to 2025) is used in the analysis but is not collected here, since it is released once a year.

## Files

```
config/panel.csv              companies and job board departments collected daily
scripts/indeed.py             pulls and saves Indeed Hiring Lab data
scripts/classify.py           classifies job titles and rebuilds the daily summary
data/indeed/                  Indeed series (full history, refreshed each run) + pull_log.csv
data/jobs/raw/DATE/           raw job lists exactly as collected ("title | location")
data/jobs/DATE.csv            one row per job, classified
data/jobs_daily_summary.csv   one row per day: counts and shares (open in Excel)
data/run_log.csv              one row per daily run: what worked, what failed
.claude/skills/daily-collect/ the instructions Claude follows each day
```

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

- The panel is six companies, and Anthropic is an AI company, so AI titles are overrepresented. Compare each company to itself over time, not companies to each other.
- Job titles say what a role is called, not how much AI the job uses.
- Indeed refreshes its files on its own schedule (AI share monthly), so some days repeat the previous values; `pull_log.csv` records which date each pull reflects.

## Credit

Indeed Hiring Lab data: Hiring Lab, Indeed, licensed CC BY 4.0. Job listings: public Greenhouse job board API for each company.
