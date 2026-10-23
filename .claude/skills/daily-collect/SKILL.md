---
name: daily-collect
description: Check (and if needed start) the daily sweAiTracker data collection, which runs as a GitHub Actions workflow, then report the results. Use when asked to run or check the daily collection for sweAiTracker.
---

# Daily collection for sweAiTracker

Collection runs automatically every morning in GitHub Actions (`.github/workflows/daily-collect.yml`,
which runs `scripts/run_daily.py`). Claude's job is to confirm it ran, fix or report problems, and summarize.
Do not collect job titles with WebFetch any more, and never invent titles or numbers.

DATE is today's date in America/Los_Angeles (YYYY-MM-DD). After 2026-11-30 collection is over: do nothing.

## 1. Find today's run

`git pull` the repo, then check `data/run_log.csv` for a row with `run_date` = DATE.
If there is none, list runs of `daily-collect.yml` with the GitHub tools. If no run has started today, trigger it
(`run_workflow`, ref `main`), wait for it to finish (it takes 5 to 15 minutes; check back with a scheduled message
rather than sleeping), then `git pull` again.

## 2. Check the results

- `data/run_log.csv` (today's row): which steps worked, failed companies.
- `data/boards/daily_summary.csv` (today's row): open_eng, new_eng, closed_eng, ai_title_share,
  desc_ai_coding_tools_share, desc_llm_genai_share, us_eng_median_salary_mid.
- `data/boards/fetch_log.csv`: any company with status `failed` or `empty`.
- If the workflow failed, read its job log and fix the cause if it is small and clear (for example a company's job
  board slug changed: look up the right one and update `config/companies.csv`). Commit and push fixes to main.

## 3. Report

Short summary: engineering jobs open, new and closed today, AI title share, share of engineering descriptions that
mention AI coding tools, failed companies or steps, and anything you fixed. Send a notification only if something
failed or needs Jacob's attention.
