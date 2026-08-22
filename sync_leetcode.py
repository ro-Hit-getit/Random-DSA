#!/usr/bin/env python3
"""Sync the public LeetCode problem catalog."""
import argparse, json, sys, time, urllib.request, urllib.error

URL="https://leetcode.com/graphql/"
QUERY="""
query problemsetQuestionListV2($filters: QuestionFilterInput, $limit: Int, $searchKeyword: String, $skip: Int, $sortBy: QuestionSortByInput, $categorySlug: String) {
  problemsetQuestionListV2(filters: $filters, limit: $limit, searchKeyword: $searchKeyword, skip: $skip, sortBy: $sortBy, categorySlug: $categorySlug) {
    questions { title titleSlug questionFrontendId paidOnly difficulty topicTags { name slug } }
    totalLength
    hasMore
  }
}
"""
HEADERS={"Content-Type":"application/json","Referer":"https://leetcode.com/","Origin":"https://leetcode.com","User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
DIFF={"EASY":"E","MEDIUM":"M","HARD":"H"}

def fetch(skip,limit):
    payload={"query":QUERY,"variables":{"filters":{},"limit":limit,"searchKeyword":"","skip":skip,"sortBy":{"sortField":"FRONTEND_ID","sortOrder":"ASCENDING"},"categorySlug":""},"operationName":"problemsetQuestionListV2"}
    req=urllib.request.Request(URL,data=json.dumps(payload).encode(),headers=HEADERS,method="POST")
    with urllib.request.urlopen(req,timeout=30) as r: body=json.loads(r.read().decode())
    if body.get("errors"): raise RuntimeError(body["errors"])
    data=body.get("data",{}).get("problemsetQuestionListV2")
    if not data: raise RuntimeError(f"Unexpected response: {body.keys()}")
    return data

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default="leetcode-problems.json"); ap.add_argument("--page-size",type=int,default=100); ap.add_argument("--include-premium",action="store_true"); ap.add_argument("--delay",type=float,default=.8); a=ap.parse_args()
    out=[]; skip=0; total=None
    print("Fetching LeetCode public catalog (GraphQL V2)...",flush=True)
    while total is None or skip<total:
        try: page=fetch(skip,a.page_size)
        except Exception as e:
            print(f"LeetCode sync failed at skip={skip}: {e}",file=sys.stderr); return 1
        total=int(page.get("totalLength") or 0); qs=page.get("questions") or []
        if not qs: break
        for q in qs:
            if q.get("paidOnly") and not a.include_premium: continue
            fid=str(q.get("questionFrontendId") or "")
            out.append({"id":"lc"+fid,"p":"LC","n":int(fid) if fid.isdigit() else None,"t":q.get("title") or "Untitled","url":f"https://leetcode.com/problems/{q.get('titleSlug')}/","top":[x.get("name") for x in (q.get("topicTags") or []) if x.get("name")],"d":DIFF.get(str(q.get("difficulty") or "").upper(),"M"),"c":[]})
        skip += len(qs); print(f"  fetched {min(skip,total)}/{total} | kept {len(out)}",flush=True); time.sleep(a.delay)
        if not page.get("hasMore") and skip>=total: break
    if len(out)<1000:
        print(f"Refusing to overwrite {a.out}: only {len(out)} public problems were retrieved.",file=sys.stderr); return 2
    with open(a.out,"w",encoding="utf-8") as f: json.dump(out,f,ensure_ascii=False)
    print(f"Done: {len(out)} LeetCode problems",flush=True); return 0
if __name__=="__main__": sys.exit(main())
