"""Collect every open job from each company's public job board API (Greenhouse, Ashby, Lever).

Usage: python scripts/collect_boards.py YYYY-MM-DD

Writes:
  data/boards/snapshots/DATE.csv   job_key list of jobs open today (one row per job)
  data/boards/postings.csv         one row per job ever seen: title, classification, description
                                   flags, salary, first_seen / last_seen
  data/boards/fetch_log.csv        one row per company per run: ok/failed, job count, error
  data/boards/daily_summary.csv    one row per day: open, NEW and CLOSED engineering jobs, AI shares, pay
  data/boards/category_summary.csv one row per day x category
  data/boards/company_summary.csv  one row per day x company
Safe to re-run on the same day (that day's snapshot and log rows are replaced).
Descriptions are not stored (size); only the flags and salary parsed from them.
"""
import sys, os, csv, glob, time, json
import requests
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import is_us, category, seniority, html_to_text, text_flags, salary_from_text, TEXT_FLAGS  # noqa: E402

DATE = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'boards')
SNAP = os.path.join(OUT, 'snapshots')
os.makedirs(SNAP, exist_ok=True)
FLAGS = list(TEXT_FLAGS)
UA = {'User-Agent': 'sweAiTracker class project (github.com/Xenzoro/sweAiTracker)'}


def get_json(url):
    last = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=90)
            if r.status_code == 404:
                raise RuntimeError('404 not found (wrong slug or board moved)')
            r.raise_for_status()
            return r.json()
        except RuntimeError:
            raise
        except Exception as e:  # network / 5xx / bad json -> retry
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f'{type(last).__name__}: {last}')


def fetch_greenhouse(slug):
    data = get_json(f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true')
    for j in data.get('jobs', []):
        text = html_to_text(j.get('content'))
        lo, hi = salary_from_text(text)
        yield dict(job_id=j['id'], title=j.get('title', ''), location=(j.get('location') or {}).get('name', ''),
                   department='; '.join(d.get('name', '') for d in j.get('departments') or []),
                   posted_at=j.get('first_published') or '', updated_at=j.get('updated_at') or '',
                   url=j.get('absolute_url', ''), text=text, salary_min=lo, salary_max=hi,
                   salary_currency='USD?' if lo else '', salary_source='text' if lo else '')


def fetch_ashby(slug):
    data = get_json(f'https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true')
    for j in data.get('jobs', []):
        if j.get('isListed') is False:
            continue
        locs = [j.get('location') or ''] + [(s.get('location') or '') for s in j.get('secondaryLocations') or []]
        text = j.get('descriptionPlain') or html_to_text(j.get('descriptionHtml'))
        lo = hi = None; cur = src = ''
        for c in ((j.get('compensation') or {}).get('summaryComponents') or []):
            if c.get('compensationType') == 'Salary' and c.get('interval') == '1 YEAR' and c.get('minValue'):
                lo, hi, cur, src = c.get('minValue'), c.get('maxValue') or c.get('minValue'), c.get('currencyCode', ''), 'structured'
                break
        if lo is None:
            lo, hi = salary_from_text(text)
            cur, src = ('USD?', 'text') if lo else ('', '')
        yield dict(job_id=j.get('id'), title=j.get('title', ''), location='; '.join(l for l in locs if l),
                   department=' / '.join(x for x in [j.get('department'), j.get('team')] if x),
                   posted_at=j.get('publishedAt') or '', updated_at='', url=j.get('jobUrl', ''), text=text,
                   salary_min=lo, salary_max=hi, salary_currency=cur, salary_source=src)


def fetch_lever(slug):
    data = get_json(f'https://api.lever.co/v0/postings/{slug}?mode=json')
    for j in data:
        cat = j.get('categories') or {}
        locs = cat.get('allLocations') or [cat.get('location') or '']
        text = '\n'.join([j.get('descriptionPlain') or ''] + [html_to_text(l.get('content')) for l in j.get('lists') or []] + [j.get('additionalPlain') or ''])
        sr = j.get('salaryRange') or {}
        if sr.get('min') and 'year' in str(sr.get('interval', '')):
            lo, hi, cur, src = sr.get('min'), sr.get('max') or sr.get('min'), sr.get('currency', ''), 'structured'
        else:
            lo, hi = salary_from_text(text)
            cur, src = ('USD?', 'text') if lo else ('', '')
        created = j.get('createdAt')
        yield dict(job_id=j.get('id'), title=j.get('text', ''), location='; '.join(l for l in locs if l),
                   department=' / '.join(x for x in [cat.get('department'), cat.get('team')] if x),
                   posted_at=pd.to_datetime(created, unit='ms').strftime('%Y-%m-%dT%H:%M:%SZ') if created else '',
                   updated_at='', url=j.get('hostedUrl', ''), text=text,
                   salary_min=lo, salary_max=hi, salary_currency=cur, salary_source=src)


FETCHERS = {'greenhouse': fetch_greenhouse, 'ashby': fetch_ashby, 'lever': fetch_lever}

# ---------------------------------------------------------------- collect today
companies = list(csv.DictReader(open(os.path.join(ROOT, 'config', 'companies.csv'))))
today, log = [], []
for c in companies:
    try:
        jobs = list(FETCHERS[c['ats']](c['slug']))
        for j in jobs:
            text = j.pop('text') or ''
            cat = category(j['title'])
            j.update(job_key=f"{c['ats']}:{c['slug']}:{j['job_id']}", ats=c['ats'], company=c['company'], group=c['group'],
                     is_us=is_us(j['location']), category=cat, seniority=seniority(j['title']),
                     is_engineering=int(cat != 'non_engineering'), ai_in_title=int(cat in ('ai_ml', 'prompt_engineering')),
                     desc_chars=len(text), **text_flags(text))
            today.append(j)
        status = 'ok' if jobs else 'empty'
        log.append(dict(date=DATE, company=c['company'], ats=c['ats'], slug=c['slug'], status=status, jobs=len(jobs), error=''))
        print(f"{c['company']:<20} {len(jobs):>5} jobs")
    except Exception as e:
        log.append(dict(date=DATE, company=c['company'], ats=c['ats'], slug=c['slug'], status='failed', jobs=0, error=str(e)[:200]))
        print(f"{c['company']:<20} FAILED {e}")

# fetch log (replace today's rows)
lp = os.path.join(OUT, 'fetch_log.csv')
old = pd.read_csv(lp) if os.path.exists(lp) else pd.DataFrame()
if len(old): old = old[old.date != DATE]
flog = pd.concat([old, pd.DataFrame(log)], ignore_index=True)
flog.to_csv(lp, index=False)

# snapshot
td = pd.DataFrame(today).drop_duplicates('job_key')
td[['job_key', 'company']].sort_values('job_key').to_csv(os.path.join(SNAP, f'{DATE}.csv'), index=False)

# registry: update existing jobs seen today, add new ones
rp = os.path.join(OUT, 'postings.csv')
REG_COLS = ['job_key', 'ats', 'company', 'group', 'job_id', 'title', 'department', 'location', 'is_us', 'category', 'seniority',
            'is_engineering', 'ai_in_title'] + FLAGS + ['salary_min', 'salary_max', 'salary_currency', 'salary_source',
            'desc_chars', 'posted_at', 'updated_at', 'first_seen', 'last_seen', 'url']
reg = pd.read_csv(rp, dtype={'job_id': str}) if os.path.exists(rp) else pd.DataFrame(columns=REG_COLS)
td['job_id'] = td['job_id'].astype(str)
first = reg.set_index('job_key')['first_seen'].to_dict()
td['first_seen'] = td.job_key.map(first).fillna(DATE)
td['first_seen'] = td['first_seen'].where(td['first_seen'] <= DATE, DATE)
td['last_seen'] = DATE
reg = pd.concat([reg[~reg.job_key.isin(td.job_key)], td[REG_COLS]], ignore_index=True)
reg = reg.sort_values(['company', 'job_key'])
reg.to_csv(rp, index=False)

# ---------------------------------------------------------------- summaries (rebuilt from all snapshots)
ok = flog[flog.status == 'ok'].groupby('date').company.apply(set).to_dict()
attrs = reg.set_index('job_key')
snaps = sorted(glob.glob(os.path.join(SNAP, '*.csv')))
daily, bycat, bycomp = [], [], []
prev_keys, prev_ok = None, set()


def share(df, col):
    return round(df[col].mean() * 100, 1) if len(df) else None


def med_pay(df):
    p = df[(df.is_us == 1) & df.salary_min.notna() & df.salary_currency.isin(['USD', 'USD?'])]
    return (round(((p.salary_min + p.salary_max) / 2).median()), len(p)) if len(p) else (None, 0)


for sp in snaps:
    d = os.path.basename(sp)[:-4]
    keys = pd.read_csv(sp)
    okd = ok.get(d, set())
    openj = attrs.loc[attrs.index.intersection(keys.job_key)]
    eng = openj[openj.is_engineering == 1]
    if prev_keys is not None:
        both = okd & prev_ok
        new_k = keys[(~keys.job_key.isin(prev_keys.job_key)) & keys.company.isin(both)].job_key
        clo_k = prev_keys[(~prev_keys.job_key.isin(keys.job_key)) & prev_keys.company.isin(both)].job_key
    else:
        new_k = clo_k = pd.Series([], dtype=str)
    new = attrs.loc[attrs.index.intersection(new_k)]; new = new[new.is_engineering == 1]
    clo = attrs.loc[attrs.index.intersection(clo_k)]; clo = clo[clo.is_engineering == 1]
    pay, npay = med_pay(eng)
    daily.append(dict(date=d, baseline=int(prev_keys is None), companies_ok=len(okd), companies_failed=int((flog.date == d).sum() - len(okd)),
                      open_jobs=len(openj), open_eng=len(eng), open_eng_us=int(eng.is_us.sum()),
                      new_eng=len(new), closed_eng=len(clo),
                      ai_title_share=share(eng, 'ai_in_title'),
                      desc_ai_coding_tools_share=share(eng, 'mentions_ai_coding_tools'),
                      desc_llm_genai_share=share(eng, 'mentions_llm_genai'),
                      desc_ai_any_share=share(eng, 'mentions_ai_any'),
                      desc_system_design_share=share(eng, 'mentions_system_design'),
                      desc_hands_on_coding_share=share(eng, 'mentions_hands_on_coding'),
                      staff_plus_share=share(eng.assign(x=eng.seniority == 'staff_plus'), 'x'),
                      entry_share=share(eng.assign(x=eng.seniority == 'entry'), 'x'),
                      new_eng_ai_title_share=share(new, 'ai_in_title'),
                      new_eng_ai_coding_tools_share=share(new, 'mentions_ai_coding_tools'),
                      us_eng_with_salary=npay, us_eng_median_salary_mid=pay))
    for cat_, g in eng.groupby('category'):
        pay, npay = med_pay(g)
        bycat.append(dict(date=d, category=cat_, open=len(g), new=int((new.category == cat_).sum()), closed=int((clo.category == cat_).sum()),
                          ai_coding_tools_share=share(g, 'mentions_ai_coding_tools'), llm_genai_share=share(g, 'mentions_llm_genai'),
                          system_design_share=share(g, 'mentions_system_design'), hands_on_coding_share=share(g, 'mentions_hands_on_coding'),
                          staff_plus_share=share(g.assign(x=g.seniority == 'staff_plus'), 'x'),
                          us_with_salary=npay, us_median_salary_mid=pay))
    for comp, g in eng.groupby('company'):
        bycomp.append(dict(date=d, company=comp, open_eng=len(g), new_eng=int((new.company == comp).sum()), closed_eng=int((clo.company == comp).sum()),
                           ai_title_share=share(g, 'ai_in_title'), ai_coding_tools_share=share(g, 'mentions_ai_coding_tools'),
                           llm_genai_share=share(g, 'mentions_llm_genai')))
    prev_keys, prev_ok = keys, okd

pd.DataFrame(daily).to_csv(os.path.join(OUT, 'daily_summary.csv'), index=False)
pd.DataFrame(bycat).to_csv(os.path.join(OUT, 'category_summary.csv'), index=False)
pd.DataFrame(bycomp).to_csv(os.path.join(OUT, 'company_summary.csv'), index=False)
t = daily[-1]
print(json.dumps(dict(companies_ok=t['companies_ok'], companies_failed=t['companies_failed'], open_jobs=t['open_jobs'], open_eng=t['open_eng'],
                      new_eng=t['new_eng'], closed_eng=t['closed_eng'], ai_title_share=t['ai_title_share'],
                      ai_coding_tools_share=t['desc_ai_coding_tools_share'])))
