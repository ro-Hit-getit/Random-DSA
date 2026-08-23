#!/usr/bin/env python3
 
import argparse
import gzip
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from urllib.parse import urlparse
from urllib.request import Request, urlopen
 
 
BASE = "https://www.geeksforgeeks.org/"
SITEMAP_INDEX = BASE + "sitemap_index_new.xml"
 
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 Chrome/124 Safari/537.36"
)
 
DIFFICULTY = {
    "school": "E",
    "basic": "E",
    "easy": "E",
    "medium": "M",
    "hard": "H",
}
 
TOPICS = [
    "Arrays",
    "Strings",
    "Linked List",
    "Stack",
    "Queue",
    "Tree",
    "Binary Tree",
    "Binary Search Tree",
    "Heap",
    "Graph",
    "Greedy",
    "Dynamic Programming",
    "Backtracking",
    "Searching",
    "Sorting",
    "Hashing",
    "Mathematical",
    "Bit Magic",
    "Recursion",
    "Matrix",
    "Trie",
    "Segment Tree",
    "Disjoint Set",
    "Two Pointer",
    "Two Pointers",
    "Sliding Window",
    "Prefix Sum",
    "Divide and Conquer",
    "Simulation",
    "Database",
    "SQL",
    "Data Structures",
    "Algorithms",
    "BFS",
    "DFS",
    "Shortest Path",
]
 
COMPANIES = [
    "Amazon",
    "Microsoft",
    "Google",
    "Meta",
    "Facebook",
    "Apple",
    "Adobe",
    "Flipkart",
    "Accolite",
    "Samsung",
    "Morgan Stanley",
    "Walmart",
    "Goldman Sachs",
    "Atlassian",
    "Uber",
    "PayPal",
    "Oracle",
    "Intuit",
    "Infosys",
    "TCS",
    "Cisco",
    "Deloitte",
    "OYO Rooms",
    "MakeMyTrip",
    "Salesforce",
    "Zoho",
    "Wipro",
    "SAP Labs",
    "Twitter",
    "LinkedIn",
    "Bloomberg",
    "D-E-Shaw",
    "Hike",
    "Ola Cabs",
    "NPCI",
]
 
 
def fetch(url, timeout=45):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/xml,text/xml,text/html,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
 
    with urlopen(request, timeout=timeout) as response:
        return response.read()
 
 
def extract_locations(data):
    """
    Extract <loc> values from normal XML or .xml.gz sitemap files.
    Handles XML namespaces automatically.
    """
 
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
 
    text = data.decode("utf-8", errors="ignore")
 
    try:
        root = ET.fromstring(text)
 
        locations = []
 
        for element in root.iter():
            if element.tag.lower().endswith("loc"):
                if element.text:
                    locations.append(unescape(element.text.strip()))
 
        if locations:
            return locations
 
    except ET.ParseError:
        pass
 
    # Fallback for malformed XML
    return [
        unescape(value.strip())
        for value in re.findall(
            r"<loc>\s*(.*?)\s*</loc>",
            text,
            re.IGNORECASE | re.DOTALL,
        )
    ]
 
 
def is_sitemap(url):
    path = urlparse(url).path.lower()
 
    return (
        path.endswith(".xml")
        or path.endswith(".xml.gz")
        or "sitemap" in path
    )
 
 
# GfG's interactive /problems/... pages are NOT listed in the public
# sitemap (they sit behind the practice app, not the WordPress blog).
# What IS in the sitemap are ordinary article pages that round up
# problems by language/topic, e.g.:
#   .../java/java-basics-coding-practice-problems/
#   .../python/python-exercises-practice-questions-and-solutions/
# Those articles contain plain <a href="https://www.geeksforgeeks.org/
# problems/...\"> links. So discovery is two stages: find these hub
# articles via the sitemap, then scrape each hub article for the
# problem links it contains.
HUB_PATTERN = re.compile(
    r"(coding-practice-problems|practice-problems|practice-questions"
    r"|practice-exercises|coding-problems|-exercises\b)",
    re.IGNORECASE,
)
 
PROBLEM_LINK_PATTERN = re.compile(
    r"https?://(?:www\.)?geeksforgeeks\.org/problems/[A-Za-z0-9\-]+"
    r"(?:/\d+)?",
    re.IGNORECASE,
)
 
 
def discover_hub_pages():
 
    pending = [SITEMAP_INDEX]
 
    visited = set()
    hubs = set()
 
    print("Starting GfG sitemap discovery (hub pages)...", flush=True)
 
    while pending:
 
        sitemap_url = pending.pop()
 
        if sitemap_url in visited:
            continue
 
        visited.add(sitemap_url)
 
        try:
            data = fetch(sitemap_url)
            locations = extract_locations(data)
 
        except Exception as error:
            print(
                f"Could not read sitemap: {sitemap_url} -> {error}",
                file=sys.stderr,
                flush=True,
            )
            continue
 
        new_hubs = 0
        new_sitemaps = 0
 
        for location in locations:
 
            location = location.split("#")[0].rstrip("/")
 
            if is_sitemap(location):
 
                if location not in visited:
                    pending.append(location)
                    new_sitemaps += 1
 
                continue
 
            if HUB_PATTERN.search(location):
 
                if location not in hubs:
                    hubs.add(location)
                    new_hubs += 1
 
        print(
            f"Sitemaps visited: {len(visited)} | "
            f"New hub pages: {new_hubs} | "
            f"Total hub pages: {len(hubs)} | "
            f"Sitemaps pending: {len(pending)}",
            flush=True,
        )
 
    return sorted(hubs)
 
 
def extract_problems_from_hub(url):
    try:
        html = fetch(url).decode("utf-8", errors="ignore")
    except Exception as error:
        print(
            f"  could not fetch hub page {url}: {error}",
            file=sys.stderr,
            flush=True,
        )
        return []
 
    found = []
 
    for link in PROBLEM_LINK_PATTERN.findall(html):
        link = link.split("#")[0].rstrip("/")
        link = link.replace("http://", "https://")
        found.append(link)
 
    return found
 
 
def discover_problem_urls(workers=6):
 
    hub_pages = discover_hub_pages()
 
    print(
        f"\nFound {len(hub_pages)} candidate hub pages; "
        f"scraping each for problem links...",
        flush=True,
    )
 
    problems = set()
 
    with ThreadPoolExecutor(max_workers=workers) as executor:
 
        futures = {
            executor.submit(extract_problems_from_hub, url): url
            for url in hub_pages
        }
 
        completed = 0
 
        for future in as_completed(futures):
 
            completed += 1
 
            links = future.result() or []
 
            new = 0
 
            for link in links:
                if link not in problems:
                    problems.add(link)
                    new += 1
 
            if completed % 25 == 0 or completed == len(hub_pages):
                print(
                    f"  hub pages scraped: {completed}/{len(hub_pages)} | "
                    f"total problems: {len(problems)}",
                    flush=True,
                )
 
    return sorted(problems)
 
 
def title_from_url(url):
 
    parts = url.rstrip("/").split("/")
    slug = parts[-1]
 
    # GfG problem URLs end in a numeric page/version index, e.g.
    # .../problems/geek-and-bridges/0 or .../problems/kadanes-algorithm-.../1
    # That trailing segment is NOT the slug -- if it's purely numeric,
    # the real slug is the segment before it.
    if slug.isdigit() and len(parts) >= 2:
        slug = parts[-2]
 
    # Remove common numeric GfG problem-id suffixes baked into the slug
    # itself (with or without a separator), e.g. "...-1587115620" or
    # "...problem0945".
    # Some GfG slugs carry more than one numeric ID suffix chained
    # together, e.g. "fibonacci-number-1605700704--152305". Match one
    # or more repetitions of (optional separator run + 3-plus digits)
    # anchored at the end, so every trailing numeric-ID segment gets
    # stripped, not just the last one.
    slug = re.sub(
        r"(?:[-_]*\d{3,})+$",
        "",
        slug,
    )
 
    slug = slug.replace("-", " ")
    slug = slug.replace("_", " ")
 
    slug = re.sub(r"\s+", " ", slug).strip()
 
    return slug.title() or "Untitled"
 
 
def clean_html(html):
 
    html = re.sub(
        r"<script[^>]*>.*?</script>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
 
    html = re.sub(
        r"<style[^>]*>.*?</style>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
 
    html = re.sub(
        r"<[^>]+>",
        " ",
        html,
    )
 
    return re.sub(
        r"\s+",
        " ",
        unescape(html),
    ).strip()
 
 
def enrich_problem(problem):
 
    try:
 
        html = fetch(
            problem["url"],
            timeout=30,
        )
 
        text = clean_html(html)
 
        # Title
        title_match = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
            html,
            re.IGNORECASE,
        )
 
        if title_match:
 
            problem["t"] = re.sub(
                r"\s*\|\s*(?:GeeksforGeeks|Practice).*$",
                "",
                unescape(title_match.group(1)),
                flags=re.IGNORECASE,
            ).strip()
 
        # Difficulty
        difficulty_match = re.search(
            r"(?:Difficulty|difficulty)"
            r"\s*[:\-]?\s*"
            r"(School|Basic|Easy|Medium|Hard)",
            text,
            re.IGNORECASE,
        )
 
        if difficulty_match:
 
            problem["d"] = DIFFICULTY[
                difficulty_match.group(1).lower()
            ]
 
        lower_text = text.lower()
 
        # Topics
        topic_section = ""
 
        for marker in (
            "topic tags",
            "topics",
            "tags",
        ):
 
            position = lower_text.find(marker)
 
            if position >= 0:
 
                topic_section = text[
                    position : position + 2500
                ]
 
                break
 
        if topic_section:
 
            problem["top"] = [
                topic
                for topic in TOPICS
                if re.search(
                    r"(?<![A-Za-z])"
                    + re.escape(topic)
                    + r"(?![A-Za-z])",
                    topic_section,
                    re.IGNORECASE,
                )
            ][:12]
 
        # Companies
        company_section = ""
 
        for marker in (
            "company tags",
            "companies",
            "company",
        ):
 
            position = lower_text.find(marker)
 
            if position >= 0:
 
                company_section = text[
                    position : position + 2500
                ]
 
                break
 
        if company_section:
 
            problem["c"] = [
                company
                for company in COMPANIES
                if re.search(
                    r"(?<![A-Za-z])"
                    + re.escape(company)
                    + r"(?![A-Za-z])",
                    company_section,
                    re.IGNORECASE,
                )
            ][:12]
 
    except Exception:
 
        # Metadata enrichment is optional.
        # The problem URL remains valid.
        pass
 
    return problem
 
 
def main():
 
    parser = argparse.ArgumentParser()
 
    parser.add_argument(
        "--out",
        default="gfg-problems.json",
    )
 
    parser.add_argument(
        "--workers",
        type=int,
        default=6,
    )
 
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Fetch individual problem pages for metadata.",
    )
 
    parser.add_argument(
        "--delay",
        type=float,
        default=0.15,
    )
 
    args = parser.parse_args()
 
    # ---------------------------------------------------------
    # STEP 1: Discover ALL problem URLs
    # ---------------------------------------------------------
 
    urls = discover_problem_urls(workers=args.workers)
 
    print(
        f"\nGfG URLs discovered: {len(urls)}",
        flush=True,
    )
 
    # NEVER replace the database with a partial result.
    if len(urls) < 1000:
 
        print(
            "\nERROR: GfG discovery returned fewer than 1000 "
            "problems. Existing catalog was NOT replaced.",
            file=sys.stderr,
        )
 
        return 2
 
    # ---------------------------------------------------------
    # STEP 2: Load existing metadata if available
    # ---------------------------------------------------------
 
    existing = {}
 
    try:
 
        with open(
            args.out,
            encoding="utf-8",
        ) as file:
 
            for problem in json.load(file):
 
                if problem.get("url"):
 
                    existing[
                        problem["url"].rstrip("/")
                    ] = problem
 
    except Exception:
 
        pass
 
    # ---------------------------------------------------------
    # STEP 3: Build catalog
    # ---------------------------------------------------------
 
    problems = []
 
    for url in urls:
 
        key = url.rstrip("/")
 
        old = existing.get(
            key,
            {},
        )
 
        problems.append(
            {
                "id": old.get(
                    "id",
                    "gfg:"
                    + url.split(
                        "/problems/",
                        1,
                    )[-1],
                ),
 
                "p": "GFG",
 
                "n": old.get("n"),
 
                # Title is always re-derived fresh from the URL, never
                # carried over from a previous run's gfg-problems.json.
                # An earlier (buggy) version of title_from_url() used to
                # emit the trailing "/1" or "/0" page-index segment as
                # the title itself; if we ever preserved that via
                # old.get("t", ...), it would get baked in permanently
                # and survive even after title_from_url() was fixed.
                "t": title_from_url(url),
 
                "url": key + "/",
 
                "top": old.get(
                    "top",
                    [],
                ),
 
                # If GfG doesn't expose the value during discovery,
                # keep the existing value or use M as a neutral fallback.
                "d": old.get(
                    "d",
                    "M",
                ),
 
                "c": old.get(
                    "c",
                    [],
                ),
            }
        )
 
    # ---------------------------------------------------------
    # STEP 4: Optional metadata enrichment
    # ---------------------------------------------------------
 
    if args.enrich:
 
        print(
            f"\nEnriching {len(problems)} GfG pages...",
            flush=True,
        )
 
        batch_size = max(
            args.workers * 10,
            30,
        )
 
        for start in range(
            0,
            len(problems),
            batch_size,
        ):
 
            batch = problems[
                start : start + batch_size
            ]
 
            with ThreadPoolExecutor(
                max_workers=args.workers
            ) as executor:
 
                futures = [
                    executor.submit(
                        enrich_problem,
                        problem,
                    )
                    for problem in batch
                ]
 
                for future in as_completed(
                    futures
                ):
 
                    future.result()
 
            completed = min(
                start + batch_size,
                len(problems),
            )
 
            print(
                f"Enriched {completed}/{len(problems)}",
                flush=True,
            )
 
            time.sleep(args.delay)
 
    # ---------------------------------------------------------
    # STEP 5: Save
    # ---------------------------------------------------------
 
    problems.sort(
        key=lambda problem: (
            problem["t"].lower(),
            problem["url"],
        )
    )
 
    with open(
        args.out,
        "w",
        encoding="utf-8",
    ) as file:
 
        json.dump(
            problems,
            file,
            ensure_ascii=False,
        )
 
    print(
        f"\nSUCCESS: wrote {len(problems)} GfG problems.",
        flush=True,
    )
 
    return 0
 
 
if __name__ == "__main__":
    sys.exit(main())
