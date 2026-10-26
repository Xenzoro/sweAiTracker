"""Run every collector for today (America/Los_Angeles date) and append one row to data/run_log.csv.

Used by .github/workflows/daily-collect.yml. Each step runs on its own; one failing does not
stop the others. Exits 1 if any step failed so the GitHub Actions run shows red.
Usage: python scripts/run_daily.py [YYYY-MM-DD] [--only bls]
  --only bls  re-run just the BLS step and update that step in today's run_log row
              (leaves today's job board snapshot and new/closed counts alone)
"""
import sys, os, re, subprocess, json, datetime, csv
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = sys.argv[1:]
ONLY = ARGS[ARGS.index('--only') + 1] if '--only' in ARGS else ''
POS = [a for i, a in enumerate(ARGS) if a != '--only' and (i == 0 or ARGS[i - 1] != '--only')]
DATE = POS[0] if POS else datetime.datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
END = '2026-11-30'
if DATE > END:
    print(f'{DATE} is after {END}: collection has ended, nothing to do.')
    sys.exit(0)


def step(name, script, *extra):
    p = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', script), DATE, *extra], cwd=ROOT, capture_output=True, text=True)
    print(f'===== {name} (exit {p.returncode})\n{p.stdout[-4000:]}{p.stderr[-4000:]}')
    lines = [l for l in p.stdout.strip().splitlines() if l.strip()]
    return p.returncode == 0, (lines[-1] if lines else p.stderr.strip().splitlines()[-1:] or [''])


def bls_status(ok, out):
    return ('skipped' if 'skipped' in str(out) else 'ok') if ok else 'FAILED'


if ONLY == 'bls':
    bls_ok, bls_out = step('bls', 'bls.py', '--force')  # manual re-run: ignore the Mondays-only rule
    log = os.path.join(ROOT, 'data', 'run_log.csv')
    rows = list(csv.reader(open(log)))
    for r in rows:
        if r and r[0] == DATE and len(r) > 7 and r[7].startswith('actions v2'):
            r[7] = re.sub(r'bls=[A-Za-z]+', f'bls={bls_status(bls_ok, bls_out)}', r[7])
            print('RUN LOG:', r[7])
    with open(log, 'w', newline='') as f: csv.writer(f).writerows(rows)
    sys.exit(0 if bls_ok else 1)
elif ONLY:
    sys.exit(f'unknown --only step: {ONLY}')

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
         f"hn={'ok' if hn_ok else 'FAILED'}; bls={bls_status(bls_ok, bls_out)}; "
         f"boards={'ok' if b_ok else 'FAILED'}; failed companies: {', '.join(failed_cos) or 'none'}")
log = os.path.join(ROOT, 'data', 'run_log.csv')
if os.path.exists(log):  # a re-run on the same day replaces that day's earlier Actions row
    keep = [r for r in csv.reader(open(log)) if not (r and r[0] == DATE and len(r) > 7 and r[7].startswith('actions v2'))]
    with open(log, 'w', newline='') as f: csv.writer(f).writerows(keep)
new = not os.path.exists(log)
with open(log, 'a', newline='') as f:
    w = csv.writer(f)
    if new: w.writerow(['run_date', 'indeed_ok', 'sources_ok', 'sources_failed', 'sources_truncated', 'total_jobs', 'engineering_jobs', 'notes'])
    w.writerow([DATE, int(ind_ok), b.get('companies_ok', 0), b.get('companies_failed', len(failed_cos)), 0,
                b.get('open_jobs', ''), b.get('open_eng', ''), notes])
print('RUN LOG:', notes)
sys.exit(0 if (ind_ok and b_ok and hn_ok and bls_ok) else 1)
