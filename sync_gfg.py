#!/usr/bin/env python3
"""Best-effort synchronizer for the public GeeksforGeeks Practice catalog."""
import argparse,json,re,sys,time
from html import unescape
from urllib.parse import urljoin,urlencode
from urllib.request import Request,urlopen
BASE='https://www.geeksforgeeks.org/'
EXPLORE='https://www.geeksforgeeks.org/explore'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
DIFF={'basic':'E','easy':'E','medium':'M','hard':'H','school':'E'}
TOPICS=['Arrays','Strings','Linked List','Stack','Queue','Tree','Binary Tree','Binary Search Tree','Heap','Graph','Greedy','Dynamic Programming','Backtracking','Searching','Sorting','Hash','Mathematical','Bit Magic','Recursion','Matrix','Trie','Segment Tree','Disjoint Set','Two Pointer','Sliding Window','Prefix Sum','Divide and Conquer','Simulation','Database','SQL']
COMPANIES=['Amazon','Microsoft','Google','Flipkart','Adobe','Samsung','Accolite','Morgan Stanley','Walmart','Meta','Facebook','Goldman Sachs','Atlassian','Uber','PayPal','Oracle','Intuit','Infosys','TCS','Cisco','Deloitte']
def fetch(url):
    req=Request(url,headers={'User-Agent':UA,'Accept-Language':'en-US,en;q=0.9'})
    with urlopen(req,timeout=30) as r:return r.read().decode('utf-8','ignore')
def strip(s):
    s=re.sub(r'<script[^>]*>.*?</script>',' ',s,flags=re.I|re.S);s=re.sub(r'<style[^>]*>.*?</style>',' ',s,flags=re.I|re.S);s=re.sub(r'<[^>]+>',' ',s)
    return re.sub(r'\s+',' ',unescape(s)).strip()
def extract(html):
    out=[]
    pat=r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
    for href,text in re.findall(pat,html,re.I|re.S):
        href=unescape(href)
        if '/problems/' not in href:continue
        u=urljoin(BASE,href).split('#')[0]
        if not re.search(r'/problems/[^/?#]+',u):continue
        title=strip(text)
        if title and len(title)<180:out.append((u,title))
    return out
def context(html,href):
    p=html.find(href)
    return strip(html[max(0,p-5000):min(len(html),p+7000)]) if p>=0 else ''
def meta(title,ctx):
    text=(title+' '+ctx).lower();d='M'
    for k,v in DIFF.items():
        if re.search(r'\b'+re.escape(k)+r'\b',text):d=v;break
    tops=[t for t in TOPICS if re.search(r'\b'+re.escape(t.lower())+r'\b',text)][:8]
    cs=[c for c in COMPANIES if re.search(r'\b'+re.escape(c.lower())+r'\b',text)]
    return d,tops,cs
def url(page,topic=None):
    q={'page':page,'sortBy':'submissions'}
    if topic:q['category']=topic
    return EXPLORE+'?'+urlencode(q)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='gfg-problems.json');ap.add_argument('--max-pages',type=int,default=400);ap.add_argument('--delay',type=float,default=.7);ap.add_argument('--topics',action='store_true');a=ap.parse_args()
    found={};empty=0
    print('Fetching GfG Explore catalog...')
    for page in range(1,a.max_pages+1):
        try:html=fetch(url(page))
        except Exception as e:print('Failed at page',page,e,file=sys.stderr);break
        ls=extract(html);new=0
        for href,title in ls:
            key=href.rstrip('/').lower()
            if key not in found:
                d,t,c=meta(title,context(html,href));found[key]={'id':'gfg:'+key.split('/problems/',1)[-1],'p':'GFG','n':None,'t':title,'url':href,'top':t,'d':d,'c':c};new+=1
        print(f'page {page}: {new} new, {len(found)} total')
        empty=empty+1 if new==0 else 0
        if page>=2 and empty>=2:break
        time.sleep(a.delay)
    if a.topics and found:
        print('Enriching topic tags...')
        for topic in TOPICS:
            seen=0
            for page in range(1,min(a.max_pages,100)+1):
                try:ls=extract(fetch(url(page,topic)))
                except Exception:break
                if not ls:break
                for href,_ in ls:
                    key=href.rstrip('/').lower()
                    if key in found:found[key]['top']=list(dict.fromkeys(found[key]['top']+[topic]))[:8];seen+=1
                time.sleep(a.delay)
                if len(ls)<5:break
            print(topic,seen)
    data=sorted(found.values(),key=lambda x:(x['t'].lower(),x['url']))
    if len(data)<100:
        print(f'Only {len(data)} problems extracted; refusing to overwrite {a.out}.',file=sys.stderr);sys.exit(2)
    with open(a.out,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print(f'Done: {len(data)} GfG problems')
if __name__=='__main__':main()
