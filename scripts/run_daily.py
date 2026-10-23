"""Run every collector for today (America/Los_Angeles date) and append one row to data/run_log.csv.

Used by .github/workflows/daily-collect.yml. Each step runs on its own; one failing does not
stop the others. Exits 1 if any step failed so the GitHub Actions run shows red.
Usage: python scripts/run_daily.py [YYYY-MM-DD]
"""
import sys, os, subprocess, json, datetime, csv
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
END = '2026-11-30'
if DATE > END:
    print(f'{DATE} is after {END}: collection has ended, nothing to do.')
    sys.exit(0)


def step(name, script):
    p = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', script), DATE], cwd=ROOT, capture_output=True, text=True)
    print(f'===== {name} (exit {p.returncode})\n{p.stdout[-4000:]}{p.stderr[-4000:]}')
    lines = [l for l in p.stdout.strip().splitlines() if l.strip()]
    return p.returncode == 0, (lines[-1] if lines else p.stderr.strip().splitlines()[-1:] or [''])


ind_ok, ind_out = step('indeed', 'indeed.py')
b_ok, b_out = step('job boards', 'collect_boards.py')
hn_ok, hn_out = step('hacker news', 'hn_hiring.py')
bls_ok, bls_out = step('bls', 'bls.py')

b = {}
if b_ok:
    try: b = json.loads(b_out)
    except Exception: b_ok = False

failed_cos = []
try:
    import pandas as pd
    fl = pd.read_csv(os.path.join(ROOT, 'data', 'boards', 'fetch_log.csv'))
    failed_cos = sorted(fl[(fl.date == DATE) & (fl.status != 'ok')].company)
except Exception:
    pass

notes = (f"actions v2 ({b.get('companies_ok', 0)} company boards); new_eng={b.get('new_eng', '')}; closed_eng={b.get('closed_eng', '')}; "
         f"ai_title_share={b.get('ai_title_share', '')}; ai_coding_tools_share={b.get('ai_coding_tools_share', '')}; "
         f"hn={'ok' if hn_ok else 'FAILED'}; bls={('skipped' if 'skipped' in str(bls_out) else 'ok') if bls_ok else 'FAILED'}; "
         f"boards={'ok' if b_ok else 'FAILED'}; failed companies: {', '.join(failed_cos) or 'none'}")
log = os.path.join(ROOT, 'data', 'run_log.csv')
new = not os.path.exists(log)
with open(log, 'a', newline='') as f:
    w = csv.writer(f)
    if new: w.writerow(['run_date', 'indeed_ok', 'sources_ok', 'sources_failed', 'sources_truncated', 'total_jobs', 'engineering_jobs', 'notes'])
    w.writerow([DATE, int(ind_ok), b.get('companies_ok', 0), b.get('companies_failed', len(failed_cos)), 0,
                b.get('open_jobs', ''), b.get('open_eng', ''), notes])
print('RUN LOG:', notes)
sys.exit(0 if (ind_ok and b_ok and hn_ok and bls_ok) else 1)
