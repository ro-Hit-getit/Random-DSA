#!/usr/bin/env python3
"""
sync_leetcode.py
----------------
Pulls the full public LeetCode problem list (title, number, difficulty, topic
tags) via LeetCode's GraphQL endpoint and writes it to leetcode-problems.json
in the schema The Stacks website expects.

This talks to https://leetcode.com/graphql, LeetCode's own site API (not an
official/documented product, just the same endpoint leetcode.com's front end
calls). It can change without notice -- if this script starts failing, the
likely cause is LeetCode having tweaked their GraphQL schema. Community
projects like "leetcode-query" (npm) or "alfa-leetcode-api" (GitHub) are good
places to check for an updated query shape.

Requirements: Python 3.8+, standard library only (no pip installs needed).

Usage:
    python3 sync_leetcode.py
    python3 sync_leetcode.py --include-premium
    python3 sync_leetcode.py --out leetcode-problems.json --page-size 100

Notes:
    - Premium-only ("subscribe to unlock") problems are excluded by default,
      since most people can't open them anyway. Pass --include-premium to
      keep them (they'll still link to a page you may not be able to view).
    - Per-problem "which companies ask this" tags are a paid LeetCode
      feature and are NOT exposed by this public endpoint. There is no way
      to fetch them live without a premium account's session cookie, which
      this script deliberately does not ask for or use. See
      companies_override.json for a small, manually curated set instead.
    - Be a reasonable citizen: this script paginates with a short delay
      between requests rather than hammering the endpoint.
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error

GRAPHQL_URL = "https://leetcode.com/graphql"

QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      difficulty
      frontendQuestionId: questionFrontendId
      paidOnly: isPaidOnly
      title
      titleSlug
      topicTags {
        name
        slug
      }
    }
  }
}
"""

DIFF_MAP = {"Easy": "E", "Medium": "M", "Hard": "H"}

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "Origin": "https://leetcode.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}


def fetch_page(skip, limit):
    payload = {
        "query": QUERY,
        "variables": {
            "categorySlug": "",
            "skip": skip,
            "limit": limit,
            "filters": {},
        },
        "operationName": "problemsetQuestionList",
    }
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if "errors" in body:
        raise RuntimeError(f"GraphQL error: {body['errors']}")
    return body["data"]["problemsetQuestionList"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="leetcode-problems.json")
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--include-premium", action="store_true")
    ap.add_argument("--delay", type=float, default=0.6, help="seconds between page requests")
    args = ap.parse_args()

    skip = 0
    total = None
    results = []

    print("Fetching problem list from LeetCode...")
    while total is None or skip < total:
        try:
            page = fetch_page(skip, args.page_size)
        except urllib.error.HTTPError as e:
            print(f"HTTP error at skip={skip}: {e.code} {e.reason}", file=sys.stderr)
            print(
                "If this is a 403, LeetCode may be rate-limiting or blocking this "
                "request pattern -- try again later, slow down --delay, or check "
                "whether the GraphQL query shape has changed.",
                file=sys.stderr,
            )
            sys.exit(1)
        except Exception as e:
            print(f"Failed at skip={skip}: {e}", file=sys.stderr)
            sys.exit(1)

        total = page["total"]
        questions = page["questions"]
        if not questions:
            break

        for q in questions:
            if q["paidOnly"] and not args.include_premium:
                continue
            diff = DIFF_MAP.get(q["difficulty"], "M")
            slug = q["titleSlug"]
            fid = q["frontendQuestionId"]
            results.append({
                "id": f"lc{fid}",
                "p": "LC",
                "n": int(fid) if str(fid).isdigit() else None,
                "t": q["title"],
                "url": f"https://leetcode.com/problems/{slug}/",
                "top": [tag["name"] for tag in q["topicTags"]],
                "d": diff,
                "c": [],  # company tags aren't available via this public endpoint
            })

        skip += args.page_size
        print(f"  fetched {min(skip, total)}/{total}")
        time.sleep(args.delay)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)

    print(f"Done. Wrote {len(results)} problems to {args.out}")
    if not args.include_premium:
        print("(Premium-only problems were skipped; use --include-premium to keep them.)")


if __name__ == "__main__":
    main()
