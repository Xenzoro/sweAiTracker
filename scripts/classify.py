"""(Old pipeline, used Oct 2026 until the GitHub Actions collector replaced it.)
Classify job titles collected from company job boards and update the summary.

Input: a raw text file of lines 'title | location' for ONE panel source.
Usage: python scripts/classify.py RAW_FILE DATE COMPANY "DEPT NAME" STATUS
STATUS is COMPLETE or TRUNCATED (what the fetch reported).
Appends to data/jobs/YYYY-MM-DD.csv, then rebuilds data/jobs_daily_summary.csv.
"""
import sys, os, re, csv, glob
import pandas as pd

raw, date, company, dept, status = sys.argv[1:6]
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import is_us, category, seniority  # noqa: E402

rows = []
for line in open(raw, encoding='utf-8'):
    line = line.strip()
    if not line or '|' not in line or line.upper().startswith(('COMPLETE', 'TRUNCATED')): continue
    title, loc = [x.strip() for x in line.split('|', 1)]
    cat = category(title)
    rows.append(dict(date=date, company=company, department=dept, title=title, location=loc, is_us=is_us(loc),
                     category=cat, seniority=seniority(title), is_engineering=int(cat != 'non_engineering'),
                     ai_in_title=int(cat in ('ai_ml', 'prompt_engineering')), fetch_status=status))

day = os.path.join(root, 'data', 'jobs', f'{date}.csv')
new = not os.path.exists(day)
with open(day, 'a', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['date'])
    if new and rows: w.writeheader()
    w.writerows(rows)

files = sorted(glob.glob(os.path.join(root, 'data', 'jobs', '20*.csv')))
allj = pd.concat([pd.read_csv(p) for p in files], ignore_index=True)
eng = allj[allj.is_engineering == 1]
summ = eng.groupby(['date', 'category']).size().unstack(fill_value=0)
summ['total_engineering'] = summ.sum(axis=1)
summ['us_engineering'] = eng[eng.is_us == 1].groupby('date').size()
summ['ai_title_share'] = (eng.groupby('date').ai_in_title.mean() * 100).round(1)
summ['staff_plus_share'] = (eng.assign(sp=(eng.seniority == 'staff_plus')).groupby('date').sp.mean() * 100).round(1)
summ['entry_share'] = (eng.assign(en=(eng.seniority == 'entry')).groupby('date').en.mean() * 100).round(1)
summ['sources_truncated'] = allj[allj.fetch_status == 'TRUNCATED'].groupby('date').department.nunique()
summ = summ.fillna(0)
summ.to_csv(os.path.join(root, 'data', 'jobs_daily_summary.csv'))
print(f'{company} / {dept}: {len(rows)} jobs ({status})')
