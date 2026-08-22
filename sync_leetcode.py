#!/usr/bin/env python3
"""Fetch the public LeetCode problem catalog.
 
Primary source: LeetCode's current questionList GraphQL endpoint.
Fallback: Zanger67's maintained public LeetCode JSON mirror if LeetCode
blocks the GitHub Actions runner.
"""
 
import argparse
import http.cookiejar
import json
import re
import sys
import time
import urllib.request
import urllib.error
 
GRAPHQL_URL = "https://leetcode.com/graphql/"
FALLBACK_URL = "https://raw.githubusercontent.com/Zanger67/leetcode-question-data/main/data/leetcode.json"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
 
QUERY = """
query problemsetQuestionList(
  $categorySlug: String,
  $limit: Int,
  $skip: Int,
  $filters: QuestionListFilterInput
) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      frontendQuestionId: questionFrontendId
      paidOnly: isPaidOnly
      difficulty
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
 
DIFF = {"EASY": "E", "MEDIUM": "M", "HARD": "H"}
 
 
def get_cookie_jar():
    jar = http.cookiejar.CookieJar()
    req = urllib.request.Request(
        "https://leetcode.com/",
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read(1024)
    except Exception:
        pass
    return jar
 
 
def request_json(url, payload=None, jar=None):
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://leetcode.com/",
        "Origin": "https://leetcode.com",
    }
 
    if payload is None:
        req = urllib.request.Request(url, headers=headers)
    else:
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
 
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar or http.cookiejar.CookieJar())
    )
    with opener.open(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))
 
 
def fetch_graphql(skip, limit, jar):
    payload = {
        "operationName": "problemsetQuestionList",
        "variables": {
            "categorySlug": "",
            "skip": skip,
            "limit": limit,
            "filters": {},
        },
        "query": QUERY,
    }
 
    body = request_json(GRAPHQL_URL, payload, jar)
 
    if body.get("errors"):
        raise RuntimeError(json.dumps(body["errors"]))
 
    result = body.get("data", {}).get("problemsetQuestionList")
    if not result:
        raise RuntimeError("LeetCode returned no problemsetQuestionList")
 
    return result
 
 
def normalize_questions(questions, include_premium=False):
    out = []
 
    for q in questions:
        if q.get("paidOnly") and not include_premium:
            continue
 
        number = str(q.get("frontendQuestionId") or "").strip()
        slug = q.get("titleSlug")
 
        if not number or not slug:
            continue
 
        out.append({
            "id": "lc" + number,
            "p": "LC",
            "n": int(number) if number.isdigit() else None,
            "t": q.get("title") or "Untitled",
            "url": f"https://leetcode.com/problems/{slug}/",
            "top": [
                tag.get("name")
                for tag in (q.get("topicTags") or [])
                if tag.get("name")
            ],
            "d": DIFF.get(str(q.get("difficulty") or "").upper(), "M"),
            "c": [],
        })
 
    return out
 
 
def fetch_from_leetcode(include_premium=False, page_size=100, delay=0.5):
    jar = get_cookie_jar()
    limit = page_size
    skip = 0
    total = None
    result = []
 
    print("Trying LeetCode GraphQL (questionList)...", flush=True)
 
    while total is None or skip < total:
        last_error = None
 
        for attempt in range(3):
            try:
                page = fetch_graphql(skip, limit, jar)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                print(
                    f"  attempt {attempt + 1}/3 failed at skip={skip}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(2 * (attempt + 1))
 
        if last_error is not None:
            raise last_error
 
        if total is None:
            total = int(page.get("total") or 0)
            print(f"LeetCode reports {total} questions.", flush=True)
 
        questions = page.get("questions") or []
 
        if not questions:
            break
 
        result.extend(normalize_questions(questions, include_premium))
        skip += len(questions)
 
        print(
            f"  fetched {skip}/{total} | kept {len(result)} public problems",
            flush=True,
        )
 
        if len(questions) < limit:
            break
 
        time.sleep(delay)
 
    if len(result) < 1000:
        raise RuntimeError(
            f"Only {len(result)} LeetCode problems were retrieved; refusing to use it."
        )
 
    return result
 
 
def fetch_fallback(include_premium=False):
    print("LeetCode API unavailable. Using maintained public JSON mirror...", flush=True)
 
    body = request_json(FALLBACK_URL)
 
    # Mirror format:
    # {"data":{"problemsetQuestionList":{"total":...,"questions":[...]}}}
    questions = (
        body.get("data", {})
        .get("problemsetQuestionList", {})
        .get("questions", [])
    )
 
    if not questions:
        raise RuntimeError("Fallback mirror contained no questions")
 
    result = normalize_questions(questions, include_premium)
 
    if len(result) < 1000:
        raise RuntimeError(
            f"Fallback mirror only produced {len(result)} public problems."
        )
 
    print(f"Fallback produced {len(result)} public LeetCode problems.", flush=True)
    return result
 
 
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="leetcode-problems.json")
    parser.add_argument("--include-premium", action="store_true")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()
 
    try:
        result = fetch_from_leetcode(args.include_premium, args.page_size, args.delay)
        source = "LeetCode GraphQL"
    except Exception as exc:
        print(
            f"LeetCode GraphQL failed: {exc}",
            file=sys.stderr,
            flush=True,
        )
        try:
            result = fetch_fallback(args.include_premium)
            source = "public mirror fallback"
        except Exception as fallback_exc:
            print(
                f"LeetCode fallback also failed: {fallback_exc}",
                file=sys.stderr,
                flush=True,
            )
            return 1
 
    # Deduplicate by LeetCode number.
    unique = {}
    for item in result:
        unique[item["id"]] = item
    result = list(unique.values())
    result.sort(key=lambda x: (x["n"] is None, x["n"] if x["n"] is not None else 10**9))
 
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
 
    print(f"SUCCESS: wrote {len(result)} LeetCode problems from {source}.", flush=True)
    return 0
 
 
if __name__ == "__main__":
    sys.exit(main())
