#!/usr/bin/env python
"""Refresh both catalogs safely and rebuild the unified data only on success."""
import os, subprocess, sys, json
from datetime import datetime, timezone
HERE=os.path.dirname(os.path.abspath(__file__))
def run(name,args):
    print("\n"+"="*60); print(name); print("="*60)
    return subprocess.run([sys.executable]+args,cwd=HERE).returncode
def count(path):
    try:
        with open(os.path.join(HERE,path),encoding="utf-8") as f: return len(json.load(f))
    except Exception: return 0
def main():
    lc=run("LeetCode catalog",["sync_leetcode.py","--page-size","100","--delay","0.8"])
    if lc: raise SystemExit(lc)
    gfg=run("GeeksforGeeks catalog",["sync_gfg.py","--workers","8"])
    if gfg: raise SystemExit(gfg)
    build=run("Building unified catalog",["build_site_data.py"])
    print("\n"+"="*60); print("CATALOG STATUS"); print("="*60)
    print("LeetCode:",count("leetcode-problems.json")); print("GfG:",count("gfg-problems.json")); print("Unified:",count("data.json"))
    if build: raise SystemExit(build)
    if count("leetcode-problems.json")<1000 or count("gfg-problems.json")<1000: raise SystemExit("Catalog validation failed")
    try:
        with open(os.path.join(HERE,"meta.json"),encoding="utf-8") as f: meta=json.load(f)
    except Exception: meta={}
    meta.update({"lastSync":datetime.now(timezone.utc).isoformat(),"leetcodeSyncExit":lc,"gfgSyncExit":gfg,"buildExit":build})
    with open(os.path.join(HERE,"meta.json"),"w",encoding="utf-8") as f: json.dump(meta,f,indent=2)
if __name__=="__main__": main()
