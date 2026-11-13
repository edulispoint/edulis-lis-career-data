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
    for item in sorted(
        collected.values(),
        key=lambda x: parse_published_date(x.get('published')),
        reverse=True
    ):
        match=next((i for i,x in enumerate(unique) if norm(x['post_name'])==norm(item['post_name']) or SequenceMatcher(None,norm(x['post_name']),norm(item['post_name'])).ratio()>=0.95),None)
        if match is None: unique.append(item)
        else:
            old=unique[match]
            for key in ('vacancies','start_date','last_date','official_url'):
                if not old.get(key) and item.get(key): old[key]=item[key]
            if old['organization']=='Organization not identified' and item['organization']!='Organization not identified': old['organization']=item['organization']
    # Final display order: upcoming deadlines first, undated opportunities next,
    # and expired opportunities last. Within each group, publication date breaks ties.
    today = datetime.now(timezone.utc).date()
    unique.sort(key=lambda item: opportunity_sort_key(item, today))

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
