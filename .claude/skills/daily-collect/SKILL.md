---
name: daily-collect
description: Run the daily sweAiTracker data collection (Indeed Hiring Lab pull plus company job board titles), save CSVs, and commit to GitHub. Use when asked to run the daily collection for sweAiTracker.
---

# Daily collection for sweAiTracker

Run every step in order. Work in the repo root. DATE is today's date in America/Los_Angeles (YYYY-MM-DD). If `data/jobs/DATE.csv` already exists, today's run already happened: stop and report that.

## 1. Indeed Hiring Lab

```
python3 scripts/indeed.py DATE
```
If it fails, note the error for the run log and continue.

## 2. Company job boards

For every row in `config/panel.csv`, call WebFetch on the row's `url` with exactly this prompt:

> Output every job in this JSON as one line in the exact format: title | location. Use location.name. No numbering, no commentary. After the last job, output one final line: COMPLETE <count> if the JSON is complete, or TRUNCATED <count> if it is cut off.

Fetch several rows in parallel. For each result:
- Save the job lines exactly as returned (not the final COMPLETE/TRUNCATED line) to `data/jobs/raw/DATE/{board}_{dept_id}.txt`, using `board` instead of dept_id when dept_id is empty (for example `discord_board.txt`). Write the file with the Write tool; never retype or summarize titles.
- Read the status from the final line (COMPLETE or TRUNCATED).
- Run: `python3 scripts/classify.py data/jobs/raw/DATE/FILE.txt DATE "COMPANY" "DEPT_NAME" STATUS`
- If a fetch errors or returns no job lines, skip classify for that row and record it as failed.

Never invent or fill in job titles. A missing source is fine; fabricated data is not.

## 3. Run log

Append one row to `data/run_log.csv` (create it with this header if missing):
`run_date,indeed_ok,sources_ok,sources_failed,sources_truncated,total_jobs,engineering_jobs,notes`
Get the totals from `data/jobs_daily_summary.csv` for DATE and the count of rows in `data/jobs/DATE.csv`.

## 4. Commit and push

```
git add -A
git commit -m "Daily collection DATE"
git push origin HEAD:main
```
If the push is rejected because the remote changed, run `git pull --rebase origin main` and push again once.

## 5. Report

Finish with a short summary: engineering jobs found, AI title share, any failed or truncated sources, and whether the push succeeded.
