import hashlib, json, re, html as html_lib, time
from datetime import datetime, timezone
from urllib.parse import quote, urlparse, parse_qsl, urlencode, urlunparse
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
import feedparser
import requests

SEARCH_TERMS = ['"Assistant Librarian" India recruitment vacancy', '"Librarian" university recruitment India notification', '"Library Assistant" OR "Professional Assistant" library vacancy India', '"Deputy Librarian" OR "Library Officer" recruitment India', '"Library Attendant" OR "Semi Professional Assistant" vacancy India', '"Library and Information Science" faculty recruitment India', '"Library Science" JRF OR SRF OR "Project Associate" India', 'library deputation recruitment India librarian', 'library contractual recruitment India vacancy', 'library contractual appointment library assistant India', 'library trainee recruitment India', 'PhD admission Library and Information Science India', 'PhD admission library science university India', 'B.Lib admission OR B.Lib.I.Sc admission India', 'M.Lib admission OR M.Lib.I.Sc admission India', 'Library and Information Science conference India call for papers', 'Library and Information Science webinar India registration', 'library walk-in interview India recruitment', 'site:lisportal.com library OR librarian OR LIS recruitment OR admission OR conference OR webinar', 'site:lisnews.in library OR librarian OR LIS recruitment OR admission OR conference OR webinar', 'site:lislinks.com library OR librarian OR LIS recruitment OR admission OR conference OR webinar', 'site:bibliophilevirtuallibrary.com library OR librarian OR LIS recruitment OR admission OR conference OR webinar', 'site:libraryjob.in library OR librarian OR LIS recruitment OR admission OR conference OR webinar', 'site:jagranjosh.com library OR librarian OR LIS recruitment OR admission OR conference OR webinar', 'site:timesofindia.indiatimes.com library OR librarian OR LIS recruitment OR admission OR conference OR webinar', 'site:freejobalert.com library OR librarian OR LIS recruitment OR admission OR conference OR webinar', 'site:sarkari-naukri.in library OR librarian OR LIS recruitment OR admission OR conference OR webinar', 'site:sarkariresult.com library OR librarian OR LIS recruitment OR admission OR conference OR webinar', '(site:iitbbs.ac.in OR site:library.iitbbs.ac.in OR site:iitb.ac.in OR site:library.iitb.ac.in OR site:iitmandi.ac.in OR site:library.iitmandi.ac.in OR site:home.iitd.ac.in) (librarian OR library OR recruitment OR admission)', '(site:library.iitd.ac.in OR site:iiti.ac.in OR site:library.iiti.ac.in OR site:iitkgp.ac.in OR site:library.iitkgp.ac.in OR site:iith.ac.in OR site:library.iith.ac.in) (librarian OR library OR recruitment OR admission)', '(site:iitj.ac.in OR site:library.iitj.ac.in OR site:iitk.ac.in OR site:pkklib.iitk.ac.in OR site:iitm.ac.in OR site:cenlib.iitm.ac.in OR site:iitgn.ac.in) (librarian OR library OR recruitment OR admission)', '(site:iitp.ac.in OR site:library.iitp.ac.in OR site:iitr.ac.in OR site:mgcl.iitr.ac.in OR site:iitrpr.ac.in OR site:iitbhu.ac.in OR site:iitg.ac.in) (librarian OR library OR recruitment OR admission)', '(site:iitbhilai.ac.in OR site:iitgoa.ac.in OR site:iitjammu.ac.in OR site:iitpkd.ac.in OR site:iittp.ac.in OR site:iitdh.ac.in OR site:iitism.ac.in) (librarian OR library OR recruitment OR admission)', '(site:nitj.ac.in OR site:mnit.ac.in OR site:library.mnit.ac.in OR site:manit.ac.in OR site:mnnit.ac.in OR site:nita.ac.in OR site:nitandhra.ac.in) (librarian OR library OR recruitment OR admission)', '(site:nitap.ac.in OR site:nitc.ac.in OR site:library.nitc.ac.in OR site:nitdelhi.ac.in OR site:nitdgp.ac.in OR site:nitgoa.ac.in OR site:nith.ac.in) (librarian OR library OR recruitment OR admission)', '(site:nitjsr.ac.in OR site:nitk.ac.in OR site:nitkkr.ac.in OR site:nitmanipur.ac.in OR site:nitm.ac.in OR site:nitmz.ac.in OR site:nitnagaland.ac.in) (librarian OR library OR recruitment OR admission)', '(site:nitp.ac.in OR site:nitpy.ac.in OR site:nitrr.ac.in OR site:nitsikkim.ac.in OR site:nits.ac.in OR site:nitsri.ac.in OR site:nitt.edu) (librarian OR library OR recruitment OR admission)', '(site:nituk.ac.in OR site:nitw.ac.in OR site:nitrkl.ac.in OR site:svnit.ac.in OR site:vnit.ac.in) (librarian OR library OR recruitment OR admission)']
OFFICIAL_SUFFIXES = ('.ac.in','.edu.in','.gov.in','.nic.in','.res.in','.gov','.edu')
MEDIA_DOMAINS = ['lisportal.com', 'lisnews.in', 'lislinks.com', 'bibliophilevirtuallibrary.com', 'libraryjob.in', 'jagranjosh.com', 'timesofindia.indiatimes.com', 'freejobalert.com', 'sarkari-naukri.in', 'sarkariresult.com']
INSTITUTION_DOMAINS = ['iitbbs.ac.in', 'library.iitbbs.ac.in', 'iitb.ac.in', 'library.iitb.ac.in', 'iitmandi.ac.in', 'library.iitmandi.ac.in', 'home.iitd.ac.in', 'library.iitd.ac.in', 'iiti.ac.in', 'library.iiti.ac.in', 'iitkgp.ac.in', 'library.iitkgp.ac.in', 'iith.ac.in', 'library.iith.ac.in', 'iitj.ac.in', 'library.iitj.ac.in', 'iitk.ac.in', 'pkklib.iitk.ac.in', 'iitm.ac.in', 'cenlib.iitm.ac.in', 'iitgn.ac.in', 'iitp.ac.in', 'library.iitp.ac.in', 'iitr.ac.in', 'mgcl.iitr.ac.in', 'iitrpr.ac.in', 'iitbhu.ac.in', 'iitg.ac.in', 'iitbhilai.ac.in', 'iitgoa.ac.in', 'iitjammu.ac.in', 'iitpkd.ac.in', 'iittp.ac.in', 'iitdh.ac.in', 'iitism.ac.in', 'nitj.ac.in', 'mnit.ac.in', 'library.mnit.ac.in', 'manit.ac.in', 'mnnit.ac.in', 'nita.ac.in', 'nitandhra.ac.in', 'nitap.ac.in', 'nitc.ac.in', 'library.nitc.ac.in', 'nitdelhi.ac.in', 'nitdgp.ac.in', 'nitgoa.ac.in', 'nith.ac.in', 'nitjsr.ac.in', 'nitk.ac.in', 'nitkkr.ac.in', 'nitmanipur.ac.in', 'nitm.ac.in', 'nitmz.ac.in', 'nitnagaland.ac.in', 'nitp.ac.in', 'nitpy.ac.in', 'nitrr.ac.in', 'nitsikkim.ac.in', 'nits.ac.in', 'nitsri.ac.in', 'nitt.edu', 'nituk.ac.in', 'nitw.ac.in', 'nitrkl.ac.in', 'svnit.ac.in', 'vnit.ac.in']
IIT_NIT_FALLBACKS = {
 'iit bhubaneswar': ('IIT Bhubaneswar','https://www.iitbbs.ac.in/'),
 'iit bombay': ('IIT Bombay','https://www.iitb.ac.in/'),
 'iit mandi': ('IIT Mandi','https://www.iitmandi.ac.in/'),
 'iit delhi': ('IIT Delhi','https://home.iitd.ac.in/'),
 'iit indore': ('IIT Indore','https://www.iiti.ac.in/'),
 'iit kharagpur': ('IIT Kharagpur','https://www.iitkgp.ac.in/'),
 'iit hyderabad': ('IIT Hyderabad','https://iith.ac.in/'),
 'iit jodhpur': ('IIT Jodhpur','https://iitj.ac.in/'),
 'iit kanpur': ('IIT Kanpur','https://www.iitk.ac.in/'),
 'iit madras': ('IIT Madras','https://www.iitm.ac.in/'),
 'iit gandhinagar': ('IIT Gandhinagar','https://iitgn.ac.in/'),
 'iit patna': ('IIT Patna','https://www.iitp.ac.in/'),
 'iit roorkee': ('IIT Roorkee','https://www.iitr.ac.in/'),
 'iit ropar': ('IIT Ropar','https://www.iitrpr.ac.in/'),
 'iit bhu': ('IIT (BHU) Varanasi','https://iitbhu.ac.in/'),
 'iit guwahati': ('IIT Guwahati','https://www.iitg.ac.in/'),
 'iit bhilai': ('IIT Bhilai','https://www.iitbhilai.ac.in/'),
 'iit goa': ('IIT Goa','https://iitgoa.ac.in/'),
 'iit jammu': ('IIT Jammu','https://www.iitjammu.ac.in/'),
 'iit palakkad': ('IIT Palakkad','https://iitpkd.ac.in/'),
 'iit tirupati': ('IIT Tirupati','https://www.iittp.ac.in/'),
 'iit dharwad': ('IIT Dharwad','https://www.iitdh.ac.in/'),
 'iit ism dhanbad': ('IIT (ISM) Dhanbad','https://www.iitism.ac.in/'),
 'nit jalandhar': ('Dr. B. R. Ambedkar NIT Jalandhar','https://www.nitj.ac.in/'),
 'mnit jaipur': ('Malaviya NIT Jaipur','https://mnit.ac.in/'),
 'manit bhopal': ('Maulana Azad NIT Bhopal','https://www.manit.ac.in/'),
 'mnnit allahabad': ('Motilal Nehru NIT Prayagraj','https://www.mnnit.ac.in/'),
 'nit agartala': ('NIT Agartala','https://www.nita.ac.in/'),
 'nit andhra pradesh': ('NIT Andhra Pradesh','https://www.nitandhra.ac.in/'),
 'nit arunachal pradesh': ('NIT Arunachal Pradesh','https://www.nitap.ac.in/'),
 'nit calicut': ('NIT Calicut','https://nitc.ac.in/'),
 'nit delhi': ('NIT Delhi','https://nitdelhi.ac.in/'),
 'nit durgapur': ('NIT Durgapur','https://nitdgp.ac.in/'),
 'nit goa': ('NIT Goa','https://www.nitgoa.ac.in/'),
 'nit hamirpur': ('NIT Hamirpur','https://nith.ac.in/'),
 'nit jamshedpur': ('NIT Jamshedpur','https://www.nitjsr.ac.in/'),
 'nit surathkal': ('NIT Karnataka Surathkal','https://www.nitk.ac.in/'),
 'nit kurukshetra': ('NIT Kurukshetra','https://nitkkr.ac.in/'),
 'nit manipur': ('NIT Manipur','https://www.nitmanipur.ac.in/'),
 'nit meghalaya': ('NIT Meghalaya','https://www.nitm.ac.in/'),
 'nit mizoram': ('NIT Mizoram','https://nitmz.ac.in/'),
 'nit nagaland': ('NIT Nagaland','https://nitnagaland.ac.in/'),
 'nit patna': ('NIT Patna','https://www.nitp.ac.in/'),
 'nit puducherry': ('NIT Puducherry','https://www.nitpy.ac.in/'),
 'nit raipur': ('NIT Raipur','https://www.nitrr.ac.in/'),
 'nit sikkim': ('NIT Sikkim','https://www.nitsikkim.ac.in/'),
 'nit silchar': ('NIT Silchar','https://www.nits.ac.in/'),
 'nit srinagar': ('NIT Srinagar','https://nitsri.ac.in/'),
 'nit trichy': ('NIT Tiruchirappalli','https://www.nitt.edu/'),
 'nit uttarakhand': ('NIT Uttarakhand','https://nituk.ac.in/'),
 'nit warangal': ('NIT Warangal','https://nitw.ac.in/'),
 'nit rourkela': ('NIT Rourkela','https://nitrkl.ac.in/'),
 'svnit surat': ('Sardar Vallabhbhai NIT Surat','https://www.svnit.ac.in/'),
 'vnit nagpur': ('Visvesvaraya NIT Nagpur','https://vnit.ac.in/')
}
BLOCK_TERMS = ['book fair','library week','library inauguration','library opening hours','library membership','library rules','library renovation']
LIS_TERMS = ['librarian','library assistant','assistant librarian','deputy librarian','professional assistant','semi professional assistant','library attendant','library science','library and information science','information scientist','library officer','library professional','documentation officer','jrf','srf','project associate','research assistant','walk-in','walk in','phd admission','doctoral admission','b.lib','b.lib.i.sc','m.lib','m.lib.i.sc','conference','webinar','call for papers','trainee','deputation','library admission']
START_PATTERNS = [
 r'(?i)(?:application(?:s)? (?:start|begin|commence)|starting date|opening date|registration begins|apply from|online application from)\\s*[:\\-]?\\s*(\\d{1,2}[ ./-](?:\\d{1,2}|[A-Za-z]{3,9})[ ./,-]\\d{2,4}|\\d{1,2}\\s+[A-Za-z]{3,9}\\s+\\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\\s+\\d{1,2},?\\s+\\d{4})'
]
END_PATTERNS = [
 r'(?i)(?:last date|closing date|apply (?:by|before)|deadline|last date for (?:submission|application)|applications? close(?:s)? on)\\s*[:\\-]?\\s*(\\d{1,2}[ ./-](?:\\d{1,2}|[A-Za-z]{3,9})[ ./,-]\\d{2,4}|\\d{1,2}\\s+[A-Za-z]{3,9}\\s+\\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\\s+\\d{1,2},?\\s+\\d{4})'
]
COUNT_PATTERNS = [r'(?i)(\\d{1,4})\\s+(?:posts?|vacanc(?:y|ies)|positions?|seats?)\\b',r'(?i)(?:no\\.?\\s+of\\s+posts?|number\\s+of\\s+posts?|vacanc(?:y|ies))\\s*[:\\-]?\\s*(\\d{1,4})\\b']

def clean(s):
    return re.sub(r'\\s+',' ',html_lib.unescape(re.sub(r'<[^>]+>',' ',s or ''))).strip()

def canonical(url):
    try:
        p=urlparse(url); q=[(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in ('oc','ved','usg')]
        return urlunparse((p.scheme,p.netloc.lower(),p.path.rstrip('/'),'',urlencode(q),'')).lower()
    except Exception: return (url or '').strip().lower()

def parse_date(text, patterns):
    for pattern in patterns:
        m=re.search(pattern,text)
        if not m: continue
        raw=m.group(1).strip().replace(',',' ')
        for fmt in ('%d %m %Y','%d %b %Y','%d %B %Y','%d-%m-%Y','%d/%m/%Y','%d.%m.%Y','%b %d %Y','%B %d %Y'):
            try: return datetime.strptime(raw,fmt).date().isoformat()
            except ValueError: pass
    return ''

def parse_count(text):
    for p in COUNT_PATTERNS:
        m=re.search(p,text)
        if m: return int(m.group(1))
    return None

def category(text):
    t=text.lower()
    if any(k in t for k in ['conference','webinar','call for papers','seminar','symposium','workshop','registration for']):
        return 'Conference / Webinar'
    if any(k in t for k in ['m.lib','m.lib.i.sc','master of library','b.lib','b.lib.i.sc','bachelor of library','blib','mlib','library science admission','library and information science admission']):
        return 'B.Lib / M.Lib Admission'
    if any(k in t for k in ['phd admission','ph.d admission','doctoral admission','phd in library','ph.d. in library','research admission']):
        return 'PhD Admission'
    if any(k in t for k in ['trainee','apprentice','library internship','internship']):
        return 'Trainee'
    if 'deputation' in t or 'on deputation' in t:
        return 'Deputation'
    if any(k in t for k in ['contractual','contract basis','purely temporary','temporary basis','fixed term','consolidated remuneration']):
        return 'Contractual'
    return 'Regular Recruitment'

def is_official_host(host):
    host=(host or '').lower().split(':')[0].removeprefix('www.')
    return host.endswith(OFFICIAL_SUFFIXES) or host in INSTITUTION_DOMAINS

def identify_institution(text):
    t=text.lower()
    for key,(name,url) in sorted(IIT_NIT_FALLBACKS.items(),key=lambda z:len(z[0]),reverse=True):
        if key in t: return name,url
    return '', ''

def resolve_article(url):
    if not url: return ''
    try:
        r=requests.get(url,allow_redirects=True,timeout=8,headers={'User-Agent':'Mozilla/5.0 EduLISOpportunityBot/1.0'})
        return r.url
    except Exception: return url

def parse_organization(title, summary, final_url):
    text=(title+' '+summary).lower()
    name,home=identify_institution(text)
    if name: return name,home
    host=urlparse(final_url).netloc.lower().removeprefix('www.')
    if is_official_host(host):
        # Prefer a direct official notification/page if the final URL is institutional.
        return host,final_url
    # Try common title forms: "Organization - Post ..." or "Post at Organization".
    patterns=[
      r'(?i)^(.{3,100}?)\\s+(?:recruitment|invites? applications?|walk[ -]?in|admission|notification|vacanc(?:y|ies)|hiring)\\b',
      r'(?i)\\b(?:at|in|for)\\s+([A-Z][A-Za-z0-9&()., -]{2,75}?)(?:\\s*[-|:]|$)'
    ]
    for p in patterns:
        m=re.search(p,title)
        if m:
            candidate=re.sub(r'\\s*[-:|]+\\s*$','',m.group(1)).strip()
            if len(candidate.split())>=2 and not any(k in candidate.lower() for k in ['freejobalert','sarkari','jagran','times of india','lisportal','lisnews','lislinks','libraryjob']):
                return candidate,''
    return 'Organization not identified',''

def main():
    now=datetime.now(timezone.utc); collected={}
    for query in SEARCH_TERMS:
        rss='https://news.google.com/rss/search?q='+quote(query)+'&hl=en-IN&gl=IN&ceid=IN:en'
        try:
            feed=feedparser.parse(rss)
            for e in feed.entries:
                title=clean(e.get('title','')); summary=clean(e.get('summary',''))
                text=title+' '+summary
                if not title or not any(k in text.lower() for k in LIS_TERMS) or any(k in text.lower() for k in BLOCK_TERMS): continue
                raw_url=e.get('link','')
                final_url=resolve_article(raw_url)
                source=e.get('source') or {}
                publisher=clean(source.get('title',''))
                org,org_home=parse_organization(title,summary,final_url)
                final_host=urlparse(final_url).netloc.lower().removeprefix('www.')
                if is_official_host(final_host):
                    official_url=final_url; link_type='official_notification'
                elif org_home:
                    official_url=org_home; link_type='official_website'
                else:
                    official_url=''; link_type=''
                start=parse_date(text,START_PATTERNS)
                last=parse_date(text,END_PATTERNS)
                count=parse_count(text)
                # Remove trailing publisher suffixes from common RSS headline patterns.
                post=title
                if publisher:
                    post=re.sub(r'\\s*[-|–—:]\\s*'+re.escape(publisher)+r'\\s*$','',post,flags=re.I).strip()
                uid=hashlib.sha256((canonical(final_url) or re.sub(r'\\W+',' ',post.lower())).encode()).hexdigest()[:24]
                record={'id':uid,'post_name':post,'organization':org,'vacancies':count,'start_date':start,'last_date':last,'category':category(text),'published':e.get('published',''),'official_url':official_url,'link_type':link_type,'_discovery_publisher':publisher,'_discovery_url':final_url}
                old=collected.get(uid)
                if not old or (old['organization']=='Organization not identified' and org!='Organization not identified') or (not old['last_date'] and last) or (not old['official_url'] and official_url):
                    collected[uid]=record
        except Exception as ex:
            print('Feed error for query:',query,repr(ex))
        time.sleep(0.12)
    # Near-duplicate title suppression; keep the richest record when duplicates recur.
    unique=[]; norm=lambda s:re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()
    for item in sorted(collected.values(),key=lambda x:x.get('published') or '',reverse=True):
        match=next((i for i,x in enumerate(unique) if norm(x['post_name'])==norm(item['post_name']) or SequenceMatcher(None,norm(x['post_name']),norm(item['post_name'])).ratio()>=0.95),None)
        if match is None: unique.append(item)
        else:
            old=unique[match]
            for key in ('vacancies','start_date','last_date','official_url'):
                if not old.get(key) and item.get(key): old[key]=item[key]
            if old['organization']=='Organization not identified' and item['organization']!='Organization not identified': old['organization']=item['organization']
    # Internal discovery fields remain in JSON for debugging but are never rendered by the webpage.
    out={'opportunities':unique,'updated_at':now.isoformat(),'total_collected':len(unique)}
    with open('docs/opportunities.json','w',encoding='utf-8') as f: json.dump(out,f,ensure_ascii=False,indent=2)
    print('Collected',len(unique),'deduplicated opportunities.')
    for c in ['Regular Recruitment','Deputation','Contractual','Trainee','PhD Admission','B.Lib / M.Lib Admission','Conference / Webinar']:
        print(c+':',sum(x['category']==c for x in unique))
    print('With official link:',sum(bool(x['official_url']) for x in unique))
    print('With post count:',sum(x['vacancies'] is not None for x in unique))
    print('With start date:',sum(bool(x['start_date']) for x in unique))
    print('With last date:',sum(bool(x['last_date']) for x in unique))

if __name__=='__main__': main()
