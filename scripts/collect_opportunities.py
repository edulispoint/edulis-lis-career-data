import hashlib, json, re, html as html_lib
from datetime import datetime, timezone, date
from urllib.parse import quote, urlparse, parse_qsl, urlencode, urlunparse
from difflib import SequenceMatcher
import feedparser

SEARCH_TERMS = [
    '"Assistant Librarian" India recruitment', '"Librarian" university recruitment India',
    '"Library Assistant" recruitment India', '"Professional Assistant" library vacancy India',
    '"Deputy Librarian" recruitment India', '"Library Attendant" vacancy India',
    '"Assistant Professor" "Library and Information Science" recruitment India',
    '"Library Science" JRF OR SRF OR "Project Associate" India',
    'library walk-in interview India recruitment', 'library contractual recruitment India university',
]
BLOCK_TERMS = ["book fair", "library week", "library inauguration", "library opening hours", "library membership", "library rules", "library renovation"]
LIS_TERMS = ["librarian", "library assistant", "assistant librarian", "deputy librarian", "professional assistant", "semi professional assistant", "library attendant", "library science", "library and information science", "information scientist", "library officer", "library professional", "documentation officer", "jrf", "srf", "project associate", "research assistant", "walk-in", "walk in"]
# Date patterns deliberately cover common written deadline formats; uncertain dates remain blank.
DATE_PATTERNS = [
    r'(?i)(?:last date|closing date|apply (?:by|before)|applications? (?:close|must be submitted) (?:by|before)|deadline)\s*[:\-]?\s*(\d{1,2}[ ./-](?:\d{1,2}|[A-Za-z]{3,9})[ ./,-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})',
    r'(?i)(?:last date|closing date|apply (?:by|before)|deadline)\s*[:\-]?\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})'
]

def clean_text(value):
    value = html_lib.unescape(re.sub(r'<[^>]+>', ' ', value or ''))
    return re.sub(r'\s+', ' ', value).strip()

def likely_lis(text):
    t=text.lower()
    return any(k in t for k in LIS_TERMS) and not any(b in t for b in BLOCK_TERMS)

def classify(text):
    t=text.lower()
    if any(x in t for x in ['walk-in','walk in','walkin']): return 'Walk-in Interview'
    if any(x in t for x in ['jrf','srf','project associate','research assistant','project fellow','research fellow']): return 'Research & Project Posts'
    if 'assistant professor' in t or 'faculty' in t or 'professor' in t: return 'Academic Positions'
    if any(x in t for x in ['librarian','library assistant','professional assistant','library attendant','library officer','information scientist','documentation officer']): return 'Library Recruitment'
    return 'Other LIS Opportunities'

def parse_pub(entry):
    for key in ('published_parsed','updated_parsed'):
        v=entry.get(key)
        if v:
            try: return datetime(*v[:6],tzinfo=timezone.utc).isoformat()
            except Exception: pass
    return ''

def parse_deadline(text):
    for pattern in DATE_PATTERNS:
        m=re.search(pattern,text)
        if not m: continue
        raw=m.group(1).strip().replace(',', ' ')
        for fmt in ('%d %m %Y','%d %b %Y','%d %B %Y','%d-%m-%Y','%d/%m/%Y','%d.%m.%Y','%b %d %Y','%B %d %Y'):
            try: return datetime.strptime(raw,fmt).date().isoformat()
            except ValueError: pass
        # Handle numeric dates with separators
        for fmt in ('%d/%m/%Y','%d-%m-%Y','%d.%m.%Y'):
            try: return datetime.strptime(raw,fmt).date().isoformat()
            except ValueError: pass
    return ''

def canonical_url(url):
    try:
        p=urlparse(url)
        q=[(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in ('oc','ved','usg')]
        return urlunparse((p.scheme,p.netloc.lower(),p.path.rstrip('/'),'',urlencode(q),'')).lower()
    except Exception: return (url or '').strip().lower()

def source_type(url, publisher):
    host=urlparse(url).netloc.lower().split(':')[0]
    host=host[4:] if host.startswith('www.') else host
    # Only mark likely institutional/government domains; still explicitly require notice verification.
    official_suffixes=('.gov.in','.nic.in','.ac.in','.edu.in','.res.in')
    if host.endswith(official_suffixes):
        return 'official_domain','Apparent institutional/government domain; verify the original notice and PDF.'
    if host.endswith('.gov') or host.endswith('.edu'):
        return 'official_domain','Apparent government/education domain; verify the original notice and PDF.'
    return 'third_party','Third-party report; locate and verify the institution’s original notification.'

def main():
    now=datetime.now(timezone.utc)
    collected={}
    for query in SEARCH_TERMS:
        feed_url='https://news.google.com/rss/search?q='+quote(query)+'&hl=en-IN&gl=IN&ceid=IN:en'
        try:
            feed=feedparser.parse(feed_url)
            for entry in feed.entries:
                title=clean_text(entry.get('title',''))
                summary=clean_text(entry.get('summary',''))
                url=entry.get('link','')
                combined=f'{title} {summary}'
                if not title or not likely_lis(combined): continue
                publisher=clean_text((entry.get('source') or {}).get('title','')) or 'Google News RSS'
                stype,note=source_type(url,publisher)
                deadline=parse_deadline(combined)
                deadline_status='expired' if deadline and date.fromisoformat(deadline)<now.date() else ('upcoming' if deadline else 'not_found')
                uid=hashlib.sha256((canonical_url(url) or re.sub(r'\W+',' ',title.lower())).encode()).hexdigest()[:24]
                record={'id':uid,'title':title,'organization':publisher,'category':classify(combined),'state':'India','location':'India','published':parse_pub(entry),'deadline':deadline,'deadline_status':deadline_status,'source_type':stype,'verification_note':note,'summary':summary[:650],'url':url,'source':publisher,'is_new':True}
                # Exact URL deduplication. Retain richer summary/deadline if duplicate query results recur.
                old=collected.get(uid)
                if not old or (len(record['summary'])>len(old['summary'])): collected[uid]=record
        except Exception as exc: print(f'Feed failed for {query}: {exc}')
    # Conservative near-duplicate title suppression: only when titles are highly similar.
    unique=[]
    for item in sorted(collected.values(),key=lambda x:x.get('published') or '',reverse=True):
        norm=lambda s: re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()
        if any(SequenceMatcher(None,norm(item['title']),norm(x['title'])).ratio()>=0.94 for x in unique): continue
        unique.append(item)
    output={'opportunities':unique,'updated_at':now.isoformat(),'total_collected':len(unique),'source_note':'Automated discovery leads, not verified vacancies. Check the recruiting institution’s original notification. Official-domain labels identify apparent domain type only; they do not certify a notice. Deadlines are shown only when detected in indexed text.'}
    with open('docs/opportunities.json','w',encoding='utf-8') as f: json.dump(output,f,ensure_ascii=False,indent=2)
    print(f'Wrote {len(unique)} matching entries after duplicate checks.')
    print(f'Apparent official-domain links: {sum(x["source_type"]=="official_domain" for x in unique)}')
    print(f'Third-party reports: {sum(x["source_type"]=="third_party" for x in unique)}')
    print(f'Deadlines detected: {sum(bool(x["deadline"]) for x in unique)}')
    print(f'Expired by detected deadline: {sum(x["deadline_status"]=="expired" for x in unique)}')

if __name__=='__main__': main()
