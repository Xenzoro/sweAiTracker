"""Official US government data from the BLS public API (no key needed; 25 requests/day limit).

- JOLTS job openings (Information sector, Professional & business services, all nonfarm), monthly
- CES employment in software / computer-systems-design industries, monthly
- OEWS employment and wages for software developers and related occupations, yearly

Usage: python scripts/bls.py YYYY-MM-DD
Writes data/bls/series.csv (long format: series_id, name, group, year, period, date, value)
Only runs on Mondays (or if the file is missing) to stay far under the daily request limit.
"""
import sys, os, datetime, requests
import pandas as pd

run_date = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'bls')
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, 'series.csv')
if os.path.exists(path) and datetime.date.fromisoformat(run_date).weekday() != 0 and '--force' not in sys.argv:
    print('bls skipped (runs Mondays)'); sys.exit(0)

SERIES = {
    # JOLTS job openings, thousands, seasonally adjusted
    'JTS000000000000000JOL': ('Job openings: total nonfarm (thousands)', 'jolts'),
    'JTS510000000000000JOL': ('Job openings: information sector (thousands)', 'jolts'),
    'JTS540099000000000JOL': ('Job openings: professional & business services (thousands)', 'jolts'),
    'JTS510000000000000HIL': ('Hires: information sector (thousands)', 'jolts'),
    'JTS510000000000000LDL': ('Layoffs & discharges: information sector (thousands)', 'jolts'),
    # CES employment, thousands, seasonally adjusted
    'CES5000000001': ('Employment: information sector (thousands)', 'ces'),
    'CES5051320001': ('Employment: software publishers (thousands)', 'ces'),
    'CES6054150001': ('Employment: computer systems design & related services (thousands)', 'ces'),
    'CES6054151101': ('Employment: custom computer programming services (thousands)', 'ces'),
}
OCC = {'151252': 'Software developers', '151253': 'Software QA analysts & testers', '151254': 'Web developers',
       '151211': 'Computer systems analysts', '152051': 'Data scientists', '151221': 'Computer & info research scientists',
       '151244': 'Network & computer systems admins', '151299': 'Computer occupations, all other'}
OEWS = {}
for code, name in OCC.items():
    for dt, what in [('01', 'employment'), ('04', 'annual mean wage'), ('13', 'annual median wage')]:
        OEWS[f'OEUN0000000000000{code}{dt}'] = (f'{name}: {what}', 'oews')

end = int(run_date[:4])
rows, missing = [], []
for batch in [SERIES, OEWS]:
    r = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/',
                      json={'seriesid': list(batch), 'startyear': str(end - 9), 'endyear': str(end)}, timeout=120)
    r.raise_for_status()
    d = r.json()
    if d.get('status') != 'REQUEST_SUCCEEDED':
        print('bls message:', d.get('message'))
    for s in d.get('Results', {}).get('series', []):
        sid = s['seriesID']
        if not s.get('data'): missing.append(sid); continue
        name, group = batch[sid]
        for p in s['data']:
            if p['value'] in ('-', ''): continue
            per = p['period']
            date = f"{p['year']}-{per[1:]}-01" if per.startswith('M') and per != 'M13' else f"{p['year']}-01-01"
            rows.append(dict(series_id=sid, name=name, group=group, year=int(p['year']), period=per, date=date, value=float(p['value'].replace(',', ''))))

if not rows:
    raise SystemExit('bls returned no data: ' + str(missing))
pd.DataFrame(rows).sort_values(['group', 'series_id', 'date']).to_csv(path, index=False)
print(f'bls ok: {len(rows)} data points from {len(set(r["series_id"] for r in rows))} series; no data for: {missing or "none"}')
