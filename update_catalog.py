#!/usr/bin/env python3
"""
update_catalog.py
Runs both public catalog synchronizers and ALWAYS rebuilds data.json from
whatever fresh catalogs were successfully obtained. Existing catalogs are
kept if a source is temporarily unavailable.
"""
import os, subprocess, sys, json
from datetime import datetime, timezone

HERE=os.path.dirname(os.path.abspath(__file__))

def run(name, args):
    print("\n"+"="*60)
    print(name)
    print("="*60)
    p=subprocess.run([sys.executable]+args,cwd=HERE)
    return p.returncode

def count(path):
    try:
        with open(os.path.join(HERE,path),encoding="utf-8") as f:
            return len(json.load(f))
    except Exception:
        return 0

def main():
    lc=run("LeetCode catalog",["sync_leetcode.py","--page-size","100","--delay","0.8"])
    gfg=run("GeeksforGeeks catalog",["sync_gfg.py","--max-pages","400","--delay","0.8"])
    build=run("Building unified catalog",["build_site_data.py"])

    meta={}
    try:
        with open(os.path.join(HERE,"meta.json"),encoding="utf-8") as f: meta=json.load(f)
    except Exception: pass
    meta["lastSyncAttempt"]=datetime.now(timezone.utc).isoformat()
    meta["leetcodeSyncExit"]=lc
    meta["gfgSyncExit"]=gfg
    meta["buildExit"]=build
    with open(os.path.join(HERE,"meta.json"),"w",encoding="utf-8") as f:
        json.dump(meta,f,indent=2)

    print("\n"+"="*60)
    print("CATALOG STATUS")
    print("="*60)
    print("LeetCode:",count("leetcode-problems.json"))
    print("GfG:",count("gfg-problems.json"))
    print("Unified:",count("data.json"))
    if lc or gfg:
        print("\nOne source failed to refresh. Any existing catalog was preserved.")
    if build:
        sys.exit(build)

if __name__=="__main__":
    main()
