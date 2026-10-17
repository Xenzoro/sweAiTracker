"""Pull Indeed Hiring Lab data (CC BY 4.0) and save the US series this project uses.

Writes full history snapshots (overwritten each run) and appends one row per run
to data/indeed/pull_log.csv so we can see when Indeed refreshed its data.
Usage: python scripts/indeed.py YYYY-MM-DD
"""
import subprocess, sys, tempfile, os, csv
import pandas as pd

run_date = sys.argv[1]
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(root, 'data', 'indeed')
os.makedirs(out, exist_ok=True)
tmp = tempfile.mkdtemp()
for repo in ['job_postings_tracker', 'ai-tracker']:
    subprocess.run(['git', 'clone', '-q', '--depth', '1', f'https://github.com/hiring-lab/{repo}.git', f'{tmp}/{repo}'], check=True)

sec = pd.read_csv(f'{tmp}/job_postings_tracker/US/job_postings_by_sector_US.csv')
keep = ['Software Development', 'Data & Analytics', 'IT Systems & Solutions', 'IT Infrastructure, Operations & Support', 'Scientific Research & Development']
sec = sec[sec.display_name.isin(keep)]
sec.to_csv(f'{out}/us_tech_sector_postings_index.csv', index=False)
agg = pd.read_csv(f'{tmp}/job_postings_tracker/US/aggregate_job_postings_US.csv')
agg.to_csv(f'{out}/us_all_postings_index.csv', index=False)

rows = []
for fname, col in [('AI_posting.csv', 'AI_share_postings'), ('GenAI_posting.csv', 'GenAI_share_postings')]:
    p = f'{tmp}/ai-tracker/{fname}'
    if os.path.exists(p):
        d = pd.read_csv(p); d = d[d.jobcountry == 'US']
        d.to_csv(f'{out}/us_{fname.replace(".csv", "").lower()}_share.csv', index=False)
        rows.append((fname, d.date.max(), d[col].iloc[-1] if col in d else ''))

sw = sec[(sec.display_name == 'Software Development') & (sec.variable == 'total postings')]
log = f'{out}/pull_log.csv'
new = not os.path.exists(log)
with open(log, 'a', newline='') as f:
    w = csv.writer(f)
    if new: w.writerow(['run_date', 'software_dev_latest_date', 'software_dev_total_index', 'ai_share_latest_date', 'ai_share_pct', 'genai_share_latest_date', 'genai_share_pct'])
    ai = next((r for r in rows if r[0] == 'AI_posting.csv'), ('', '', ''))
    gen = next((r for r in rows if r[0] == 'GenAI_posting.csv'), ('', '', ''))
    w.writerow([run_date, sw.date.max(), sw.indeed_job_postings_index.iloc[-1], ai[1], ai[2], gen[1], gen[2]])
print('indeed ok', sw.date.max(), ai[1:])
