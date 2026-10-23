"""Hacker News "Ask HN: Who is hiring?" monthly threads (via the public Algolia HN API).

Each top-level comment in a thread is one company's job post. For every month since START we
count posts and the share mentioning AI / LLMs / AI coding tools / roles, so we get a long
history (2018 onward) to compare against the 2026 job-board data.

Usage: python scripts/hn_hiring.py YYYY-MM-DD
Writes:
  data/hn/posts.csv     one row per post: month, post id, first line (company | role | location), flags
  data/hn/monthly.csv   one row per month: posts and % with each flag
Past months are cached; only the two most recent threads are re-fetched each run.
"""
import sys, os, re, time
import requests
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import html_to_text, text_flags  # noqa: E402

START = '2018-01'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'hn')
os.makedirs(OUT, exist_ok=True)
API = 'https://hn.algolia.com/api/v1'
UA = {'User-Agent': 'sweAiTracker class project (github.com/Xenzoro/sweAiTracker)'}

ROLE_FLAGS = {
    'role_ai_ml_engineer': r'\b(ai|ml|machine learning|llm|applied ai)[ /-]*(engineer|developer|scientist)',
    'role_prompt_engineer': r'prompt engineer',
    'role_backend': r'back[ -]?end',
    'role_frontend': r'front[ -]?end',
    'role_fullstack': r'full[ -]?stack',
    'role_architect': r'\barchitect\b',
    'role_junior_or_intern': r'\b(junior|intern|internship|new grad|entry[ -]level)\b',
    'remote': r'\bremote\b',
}
ROLE_RE = {k: re.compile(v, re.I) for k, v in ROLE_FLAGS.items()}


def get(url, params=None):
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 3: raise
            time.sleep(10 * (attempt + 1))


MONTHS = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'], 1)}


def threads():
    out, page = {}, 0
    while True:
        d = get(f'{API}/search_by_date', {'tags': 'story,author_whoishiring', 'hitsPerPage': 200, 'page': page})
        for h in d['hits']:
            m = re.match(r'Ask HN: Who is hiring\? \((\w+) (\d{4})\)', h.get('title') or '')
            if m and m.group(1).lower() in MONTHS:
                key = f'{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}'
                out.setdefault(key, int(h['objectID']))
        page += 1
        if page >= d.get('nbPages', 0): break
    return {k: v for k, v in out.items() if k >= START}


pp = os.path.join(OUT, 'posts.csv')
posts = pd.read_csv(pp) if os.path.exists(pp) else pd.DataFrame()
have = set(posts.month) if len(posts) else set()
th = threads()
recent = sorted(th)[-2:]
todo = [m for m in sorted(th) if m not in have or m in recent]
rows = []
for m in todo:
    item = get(f'{API}/items/{th[m]}')
    for c in item.get('children') or []:
        text = html_to_text(c.get('text'))
        if not text: continue  # deleted / dead
        f = text_flags(text)
        f.update({k: int(bool(r.search(text))) for k, r in ROLE_RE.items()})
        rows.append(dict(month=m, thread_id=th[m], post_id=c.get('id'), first_line=text.split('\n')[0][:200], chars=len(text), **f))
    print(f'{m}: {sum(1 for r in rows if r["month"] == m)} posts')
    time.sleep(1)

if len(posts): posts = posts[~posts.month.isin(todo)]
posts = pd.concat([posts, pd.DataFrame(rows)], ignore_index=True).sort_values(['month', 'post_id'])
posts.to_csv(pp, index=False)

flag_cols = [c for c in posts.columns if c.startswith(('mentions_', 'role_')) or c == 'remote']
monthly = posts.groupby('month').agg(posts=('post_id', 'count'), **{f'{c}_share': (c, 'mean') for c in flag_cols})
for c in monthly.columns:
    if c.endswith('_share'): monthly[c] = (monthly[c] * 100).round(1)
monthly.to_csv(os.path.join(OUT, 'monthly.csv'))
last = monthly.iloc[-1]
print(f"hn ok: {len(monthly)} months, latest {monthly.index[-1]}: {int(last.posts)} posts, "
      f"{last.mentions_llm_genai_share}% mention LLM/GenAI, {last.mentions_ai_coding_tools_share}% AI coding tools")
