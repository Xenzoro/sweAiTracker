"""Shared rules: title classification, US location check, and job-description text flags.

Used by classify.py (old WebFetch pipeline), collect_boards.py and hn_hiring.py.
"""
import re, html

US_STATES = ['alabama','alaska','arizona','arkansas','california','colorado','connecticut','delaware','florida','georgia','hawaii','idaho','illinois','indiana','iowa','kansas','kentucky','louisiana','maine','maryland','massachusetts','michigan','minnesota','mississippi','missouri','montana','nebraska','nevada','new hampshire','new jersey','new mexico','new york','north carolina','north dakota','ohio','oklahoma','oregon','pennsylvania','rhode island','south carolina','south dakota','tennessee','texas','utah','vermont','virginia','washington','west virginia','wisconsin','wyoming','district of columbia']
US_HINTS = ['united states','usa','u.s.','us remote','remote, us','remote - us','remote (us','san francisco','new york','seattle','austin','boston','chicago','denver','los angeles','mountain view','bellevue','sunnyvale','palo alto','atlanta','miami','washington dc','washington, dc','sf bay','bay area','nyc']


def has(t, words):
    return any(re.search(w, t) for w in words)


def is_us(loc):
    l = ' ' + str(loc).lower() + ' '
    if any(h in l for h in US_HINTS): return 1
    if re.search(r',\s*(ca|ny|wa|tx|ma|co|il|ga|fl|or|va|nc|ut|az|dc)\b', l): return 1
    if any(re.search(r'\b' + s + r'\b', l) for s in US_STATES):
        if 'british columbia' in l: return 0
        return 1
    return 0


# Original rules (always non-engineering; unchanged so the Oct 2026 panel data stays comparable)
NON_ENG = [r'product manager', r'program manager', r'product design', r'designer', r'analyst', r'\bsales\b', r'finance', r'marketing', r'operations manager', r'administrator', r'policy', r'recruit', r'executive assistant', r'strategist', r'evangelist', r'operator', r'research operations', r'events', r'transformation owner', r'\bfellow', r'program lead', r'deal desk', r'supply chain', r'stock admin']
# Extra rules for whole company boards: non-engineering unless the title also says engineer/developer/scientist
NON_ENG_EXTRA = [r'account executive', r'account manager', r'customer success', r'counsel', r'attorney', r'legal', r'paralegal', r'accountant', r'accounting', r'payroll', r'\btax\b', r'people partner', r'\bhr\b', r'human resources', r'talent', r'communications', r'copywriter', r'content', r'brand', r'partnerships manager', r'business development', r'\bbdr\b', r'\bsdr\b', r'office manager', r'workplace', r'facilities', r'support specialist', r'customer support', r'customer experience', r'\bcx\b', r'community', r'social media', r'controller', r'treasury', r'procurement', r'compliance', r'\baudit', r'investigator', r'writer', r'editor', r'chief of staff', r'\bpr\b', r'public relations', r'executive', r'coordinator', r'specialist', r'representative', r'\bgtm\b', r'go-to-market', r'revenue operations', r'solutions consultant', r'consultant']


def category(title):
    t = str(title).lower()
    if has(t, NON_ENG): return 'non_engineering'
    if has(t, NON_ENG_EXTRA) and not has(t, [r'engineer', r'developer', r'scientist']): return 'non_engineering'
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
    t = str(title).lower()
    if has(t, [r'intern', r'new grad', r'early career', r'junior', r'associate']): return 'entry'
    if has(t, [r'manager', r'director', r'head of', r'\bvp\b']): return 'management'
    if has(t, [r'principal', r'distinguished', r'staff', r'architect', r'fellow']): return 'staff_plus'
    if has(t, [r'senior', r'\bsr\.?\b', r'lead']): return 'senior'
    return 'mid_or_unspecified'


# ---- job description text flags -------------------------------------------------
# Each flag is 1 if the description text matches any pattern (case-insensitive).
TEXT_FLAGS = {
    # names a specific AI coding tool, or says AI-assisted development is part of the job
    'mentions_ai_coding_tools': [r'github copilot', r'\bcopilot\b', r'\bcursor\b(?![ -]?(position|based|pagination))', r'claude code', r'\bclaude\b', r'chatgpt', r'\bcodex\b', r'windsurf', r'codeium', r'tabnine', r'\bdevin\b',
                                 r'ai[- ]assisted (coding|development|software|engineering)', r'ai[- ]powered (coding|developer|development) tools', r'ai coding', r'coding assistants?', r'ai (developer|dev|engineering|coding) tools',
                                 r'(use|using|leverag\w*|embrac\w*|adopt\w*|fluen\w*|comfortable with|experience (with|using)) (modern |the latest )?(ai|llm|genai|generative ai)[- ]?(based )?(tools|assistants|agents|coding)'],
    # LLM / generative AI technology (building with it or using it)
    'mentions_llm_genai': [r'\bllms?\b', r'large language models?', r'generative ai', r'\bgen ?ai\b', r'foundation models?', r'\brag\b', r'retrieval[- ]augmented', r'prompt engineering', r'\bagentic\b', r'ai agents?', r'\bmcp\b', r'model context protocol', r'fine[- ]tun\w+', r'embeddings', r'vector (database|db|store)'],
    # any AI / ML mention at all
    'mentions_ai_any': [r'\bai\b', r'artificial intelligence', r'machine learning', r'\bml\b', r'\bllms?\b', r'generative', r'\bgen ?ai\b', r'copilot', r'chatgpt', r'\bclaude\b'],
    # system design / architecture emphasis (research question 3)
    'mentions_system_design': [r'system design', r'systems design', r'architect\w*', r'distributed systems', r'design (and|&) (build|implement)\w* (scalable|large-scale)', r'scalab\w+', r'technical design'],
    # hands-on coding emphasis
    'mentions_hands_on_coding': [r'hands[- ]on (coding|code|engineering|development)', r'write (high[- ]quality |clean |production[- ]?(quality |grade )?)?code', r'writing (high[- ]quality |clean |production[- ]?(quality |grade )?)?code'],
}
_FLAG_RE = {k: re.compile('|'.join(v), re.I) for k, v in TEXT_FLAGS.items()}


def html_to_text(s):
    if not s: return ''
    s = html.unescape(html.unescape(str(s)))
    s = re.sub(r'<(br|/p|/li|/h\d|/div)[^>]*>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html.unescape(s)
    return re.sub(r'[ \t\xa0]+', ' ', s).strip()


def text_flags(text):
    return {k: int(bool(r.search(text or ''))) for k, r in _FLAG_RE.items()}


# ---- salary parsing from text ---------------------------------------------------
_NUM = r'(\d{2,3}(?:,\d{3})+(?:\.\d+)?|\d{2,3}(?:\.\d+)?\s?[kK]\b)'
_RANGE = re.compile(r'(US)?\$\s?' + _NUM + r'(?:\s?USD)?\s*(?:-|–|—|to|and)\s*(?:US)?\$?\s?' + _NUM, re.I)


def _val(x):
    x = x.replace(',', '').replace(' ', '')
    return float(x[:-1]) * 1000 if x[-1] in 'kK' else float(x)


def salary_from_text(text):
    """First plausible annual USD-sign range in the text -> (min, max) or (None, None).
    '$' can also mean CAD/AUD etc.; is_us helps filter in analysis."""
    for m in _RANGE.finditer(text or ''):
        lo, hi = _val(m.group(2)), _val(m.group(3))
        if 30000 <= lo <= hi <= 2000000 and hi <= lo * 4:
            return lo, hi
    return None, None
