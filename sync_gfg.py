#!/usr/bin/env python3
"""Build a large GfG Practice catalog from the public sitemap and problem pages.

The Explore page is client-rendered, so parsing its visible HTML is unreliable.
GfG publishes a sitemap index; we use that for complete URL discovery, then
optionally enrich each problem page with difficulty, company and topic tags.
"""
import argparse, json, re, sys, time, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE="https://www.geeksforgeeks.org/"
SITEMAP_INDEX=BASE+"sitemap_index_new.xml"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
DIFF={"basic":"E","easy":"E","medium":"M","hard":"H","school":"E"}
COMPANIES=["Amazon","Microsoft","Google","Meta","Facebook","Apple","Adobe","Flipkart","Accolite","Samsung","Morgan Stanley","Walmart","Goldman Sachs","Atlassian","Uber","PayPal","Oracle","Intuit","Infosys","TCS","Cisco","Deloitte","OYO Rooms","MakeMyTrip","Salesforce","Zoho","Wipro","SAP Labs","Twitter","LinkedIn","Bloomberg","D-E-Shaw","Hike","Ola Cabs","NPCI","Codenation"]
TOPICS=["Arrays","Strings","Linked List","Stack","Queue","Tree","Binary Tree","Binary Search Tree","Heap","Graph","Greedy","Dynamic Programming","Backtracking","Searching","Sorting","Hashing","Mathematical","Bit Magic","Recursion","Matrix","Trie","Segment Tree","Disjoint Set","Two Pointers","Sliding Window","Prefix Sum","Divide and Conquer","Simulation","Database","SQL","Data Structures","Algorithms","BFS","DFS","Shortest Path"]

def get(url,timeout=25):
    req=Request(url,headers={"User-Agent":UA,"Accept-Language":"en-US,en;q=0.9"})
    with urlopen(req,timeout=timeout) as r: return r.read().decode("utf-8","ignore")

def xml_locs(text):
    try:
        root=ET.fromstring(text)
        return [unescape(x.text.strip()) for x in root.iter() if x.tag.lower().endswith("loc") and x.text]
    except Exception:
        return re.findall(r"<loc>\s*(.*?)\s*</loc>",text,re.I|re.S)

def slug_title(url):
    slug=url.rstrip('/').rsplit('/',1)[-1]
    slug=re.sub(r"[-_](?:\d{3,})$","",slug)
    return re.sub(r"\s+"," ",slug.replace('-',' ').replace('_',' ')).strip().title()

def strip_html(s):
    s=re.sub(r"<script[^>]*>.*?</script>"," ",s,flags=re.I|re.S); s=re.sub(r"<style[^>]*>.*?</style>"," ",s,flags=re.I|re.S); s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",unescape(s)).strip()

def enrich(item):
    url=item["url"]
    try:
        h=get(url)
        # Prefer explicit metadata in the server-rendered problem page.
        title=re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',h,re.I)
        if title: item["t"]=re.sub(r"\s*\|\s*Practice.*$","",unescape(title.group(1))).strip()
        elif re.search(r"<title[^>]*>(.*?)</title>",h,re.I|re.S): item["t"]=re.sub(r"\s*\|\s*Practice.*$","",strip_html(re.search(r"<title[^>]*>(.*?)</title>",h,re.I|re.S).group(1))).strip()
        txt=strip_html(h)
        dm=re.search(r"Difficulty\s*:\s*(Basic|Easy|Medium|Hard|School)",txt,re.I)
        if dm: item["d"]=DIFF[dm.group(1).lower()]
        # Metadata sections are rendered as contiguous text on GfG problem pages.
        low=txt.lower()
        for label,key,choices in [("company tags","c",COMPANIES),("topic tags","top",TOPICS)]:
            pos=low.find(label)
            if pos>=0:
                section=txt[pos:pos+1800]
                vals=[x for x in choices if re.search(r"(?<![A-Za-z])"+re.escape(x)+r"(?![A-Za-z])",section,re.I)]
                item[key]=vals[:12]
    except Exception:
        pass
    return item

def discover():
    print("Fetching GfG sitemap index...",flush=True)
    index=get(SITEMAP_INDEX,40); children=xml_locs(index)
    # Prefer sitemap files that look like practice/problem sitemaps.
    preferred=[u for u in children if re.search(r"problem|practice",u,re.I)]
    targets=preferred or children
    urls=set()
    for i,u in enumerate(targets,1):
        try:
            text=get(u,40)
            for loc in xml_locs(text):
                loc=loc.split('#')[0]
                if re.search(r"/problems/[^/?#]+",loc,re.I): urls.add(loc.rstrip('/'))
            print(f"  sitemap {i}/{len(targets)} -> {len(urls)} problem URLs",flush=True)
        except Exception as e: print(f"  skipped sitemap {u}: {e}",file=sys.stderr)
    return sorted(urls)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default="gfg-problems.json"); ap.add_argument("--workers",type=int,default=8); ap.add_argument("--enrich",action="store_true",default=True); a=ap.parse_args()
    try: urls=discover()
    except Exception as e:
        print(f"GfG discovery failed: {e}",file=sys.stderr); return 1
    if len(urls)<1000:
        print(f"Refusing to overwrite {a.out}: only {len(urls)} problem URLs discovered.",file=sys.stderr); return 2
    existing={}
    try:
        with open(a.out,encoding="utf-8") as f: existing={x.get("url","").rstrip('/'):x for x in json.load(f)}
    except Exception: pass
    items=[]
    for u in urls:
        old=existing.get(u,{})
        items.append({"id":old.get("id") or "gfg:"+u.split('/problems/',1)[-1],"p":"GFG","n":old.get("n"),"t":old.get("t") or slug_title(u),"url":u+"/","top":old.get("top") or [],"d":old.get("d") or "M","c":old.get("c") or []})
    todo=[x for x in items if not existing.get(x["url"].rstrip("/"),{}).get("top") or not existing.get(x["url"].rstrip("/"),{}).get("c")]
    # Enrich missing metadata; use bounded concurrency so the first build is practical.
    if a.enrich and todo:
        print(f"Enriching {len(todo)} GfG problem pages...",flush=True)
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            futures=[ex.submit(enrich,x) for x in todo]
            done=0
            for f in as_completed(futures):
                f.result(); done+=1
                if done%100==0: print(f"  enriched {done}/{len(todo)}",flush=True)
    items.sort(key=lambda x:(x["t"].lower(),x["url"]))
    with open(a.out,"w",encoding="utf-8") as f: json.dump(items,f,ensure_ascii=False)
    print(f"Done: {len(items)} GfG problems",flush=True); return 0
if __name__=="__main__": sys.exit(main())
