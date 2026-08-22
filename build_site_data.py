#!/usr/bin/env python3
"""
build_site_data.py
-------------------
Merges leetcode-problems.json (from sync_leetcode.py) + gfg-problems.json
(static, hand-curated) + companies_override.json (manual "asked by" data for
a handful of famous problems) into the single data.json that the-stacks.html
loads at runtime.

Run this AFTER sync_leetcode.py. If leetcode-problems.json doesn't exist yet,
this falls back to the small starter snapshot so the site still works.

Usage:
    python3 sync_leetcode.py            # writes leetcode-problems.json
    python3 build_site_data.py          # writes data.json
"""
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path, default):
    full = os.path.join(HERE, path)
    if not os.path.exists(full):
        return default
    with open(full, encoding="utf-8") as f:
        return json.load(f)


def main():
    leetcode = load("leetcode-problems.json", None)
    if leetcode is None:
        print("leetcode-problems.json not found -- using the existing data.json as a fallback.")
        existing = load("data.json", [])
        leetcode = [p for p in existing if p.get("p") == "LC"]

    gfg = load("gfg-problems.json", [])
    overrides = load("companies_override.json", {})

    for p in leetcode:
        if p["t"] in overrides:
            p["c"] = overrides[p["t"]]

    combined = leetcode + gfg

    out_path = os.path.join(HERE, "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False)

    meta = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "leetcode_count": len(leetcode),
        "gfg_count": len(gfg),
        "total": len(combined),
    }
    with open(os.path.join(HERE, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"Wrote {len(combined)} problems ({len(leetcode)} LeetCode, {len(gfg)} GfG) to data.json")


if __name__ == "__main__":
    main()
