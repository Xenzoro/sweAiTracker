"""Classify job titles collected from company job boards and update the summary.

Input: a raw text file of lines 'title | location' for ONE panel source.
Usage: python scripts/classify.py RAW_FILE DATE COMPANY "DEPT NAME" STATUS
STATUS is COMPLETE or TRUNCATED (what the fetch reported).
Appends to data/jobs/YYYY-MM-DD.csv, then rebuilds data/jobs_daily_summary.csv.
"""
import sys, os, re, csv, glob
import pandas as pd

raw, date, company, dept, status = sys.argv[1:6]
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

US_STATES = ['alabama','alaska','arizona','arkansas','california','colorado','connecticut','delaware','florida','georgia','hawaii','idaho','illinois','indiana','iowa','kansas','kentucky','louisiana','maine','maryland','massachusetts','michigan','minnesota','mississippi','missouri','montana','nebraska','nevada','new hampshire','new jersey','new mexico','new york','north carolina','north dakota','ohio','oklahoma','oregon','pennsylvania','rhode island','south carolina','south dakota','tennessee','texas','utah','vermont','virginia','washington','west virginia','wisconsin','wyoming','district of columbia']
US_HINTS = ['united states','usa','u.s.','us remote','remote, us','remote - us','remote (us','san francisco','new york','seattle','austin','boston','chicago','denver','los angeles','mountain view','bellevue','sunnyvale','palo alto','atlanta','miami','washington dc','washington, dc','sf bay','bay area','nyc']

def has(t, words): return any(re.search(w, t) for w in words)

def is_us(loc):
    l = ' ' + loc.lower() + ' '
    if any(h in l for h in US_HINTS): return 1
    if re.search(r',\s*(ca|ny|wa|tx|ma|co|il|ga|fl|or|va|nc|ut|az|dc)\b', l): return 1
    if any(re.search(r'\b' + s + r'\b', l) for s in US_STATES):
        if 'british columbia' in l: return 0
        return 1
    return 0

NON_ENG = [r'product manager', r'program manager', r'product design', r'designer', r'analyst', r'\bsales\b', r'finance', r'marketing', r'operations manager', r'administrator', r'policy', r'recruit', r'executive assistant', r'strategist', r'evangelist', r'operator', r'research operations', r'events', r'transformation owner', r'\bfellow', r'program lead', r'deal desk', r'supply chain', r'stock admin']

def category(title):
    t = title.lower()
    if has(t, NON_ENG): return 'non_engineering'
    if 'prompt' in t: return 'prompt_engineering'
    if has(t, [r'\bai\b', r'\bml\b', r'machine learning', r'\bllm', r'genai', r'generative', r'applied ai', r'model serving', r'inference', r'foundation model', r'research (engineer|scientist)', r'\bagent']): return 'ai_ml'
    if has(t, [r'architect']): return 'architect'
    if has(t, [r'site reliability', r'\bsre\b', r'devops', r'platform', r'infrastructure', r'\bcloud\b', r'production engineer', r'kernel', r'network', r'runtime', r'compute', r'observability']): return 'platform_infra'
    if has(t, [r'security', r'red team']): return 'security'
    if has(t, [r'data engineer', r'data scien', r'analytics engineer', r'\bdata\b']): return 'data'
    if has(t, [r'full ?-?stack']): return 'fullstack'
    if has(t, [r'front ?-?end', r'\bui\b', r'\bweb\b']): return 'frontend'
    if has(t, [r'back ?-?end', r'\bapi\b', r'distributed systems', r'server']): return 'backend'
    if has(t, [r'\bios\b', r'android', r'mobile']): return 'mobile'
    if has(t, [r'manager', r'director', r'head of', r'\bvp\b', r'tech lead manager']): return 'eng_management'
    if has(t, [r'software engineer', r'developer', r'engineer']): return 'general_swe'
    return 'non_engineering'

def seniority(title):
    t = title.lower()
    if has(t, [r'intern', r'new grad', r'early career', r'junior', r'associate']): return 'entry'
    if has(t, [r'manager', r'director', r'head of', r'\bvp\b']): return 'management'
    if has(t, [r'principal', r'distinguished', r'staff', r'architect', r'fellow']): return 'staff_plus'
    if has(t, [r'senior', r'\bsr\.?\b', r'lead']): return 'senior'
    return 'mid_or_unspecified'

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
