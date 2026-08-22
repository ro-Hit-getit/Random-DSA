# Problem Forge — LeetCode × GeeksforGeeks

A lightweight, no-framework website for generating randomized DSA practice sets.

## What it does

- Browse the local problem catalog.
- Generate a random set by:
  - topic(s)
  - difficulty
  - platform (LeetCode / GeeksforGeeks)
  - number of problems
  - company tag when company data exists
- "Balanced difficulty" mode distributes the generated set across the selected difficulty levels.
- "Avoid previous sets" stores solved/picked problem IDs in browser localStorage so repeated draws are less repetitive.
- Every card has an **Open problem ↗** link to the source platform.
- Copy the generated problem names to your clipboard.
- Works as a static site; no database or API key is required in the browser.

## Run it on Windows

1. Extract this folder.
2. Double-click `serve.bat`.
3. Open `http://localhost:8000` in your browser.

Do **not** double-click `index.html` if your browser blocks local JSON fetches; use `serve.bat`.

## Refreshing the catalog

The included `sync-and-build.bat` runs:

```text
python sync_leetcode.py
python build_site_data.py
```

The LeetCode sync uses the same GraphQL endpoint used by the public LeetCode website. It is not a documented public API and can change, so the script is intentionally isolated.

By default, premium-only LeetCode problems are skipped. To include them:

```text
python sync_leetcode.py --include-premium
python build_site_data.py
```

## Company tags

The data model supports a `c` array for company names, so the UI can show and filter them.

Important limitation: LeetCode's company-question data is a Premium feature and is not exposed by the public problem-list query used by this project. The sync script therefore cannot honestly claim to fetch all LeetCode company tags. The included `companies_override.json` supplies a small manually curated set.

GeeksforGeeks practice pages expose company tags on individual problems, but there is no public catalog API used by this project. `gfg-problems.json` is therefore a curated/static catalog and should be expanded if you want broader GfG coverage.

## Data format

Each problem looks like:

```json
{
  "id": "lc1",
  "p": "LC",
  "n": 1,
  "t": "Two Sum",
  "url": "https://leetcode.com/problems/two-sum/",
  "top": ["Array", "Hash Table"],
  "d": "E",
  "c": ["Amazon"]
}
```

`p` = platform, `n` = problem number when available, `t` = title, `top` = topic tags, `d` = E/M/H, `c` = company tags.

## Recommended next upgrade

If you later want login, progress tracking, solved status, streaks, custom lists, cloud sync, or an actual "mark as solved" workflow, the current static frontend can be kept and a small backend/database can be added without changing the core problem schema.

## Full-catalog mode

`sync-and-build.bat` now refreshes both platforms before rebuilding the site's unified `data.json`.

- **LeetCode:** paginated public problem metadata with title, number, difficulty and topic tags. Premium-only problems are excluded by default; use `python sync_leetcode.py --include-premium` when appropriate.
- **GeeksforGeeks:** `sync_gfg.py` paginates the public Explore/Practice catalog and extracts problem links plus visible difficulty/topic/company metadata. The current GfG Explore page reports **3,060 problems**. citeturn0search1
- For richer GfG topic coverage, run `python sync_gfg.py --topics` before `python build_site_data.py`.

The site stores metadata and links, not copied problem statements. This keeps the website lightweight and sends the user to LeetCode/GfG for the actual question.


## IMPORTANT — why you may still see "223"

`data.json` shipped in the ZIP is only a safe starter cache. It is NOT the full catalog.

**Do not open `index.html` directly.** Double-click **`serve.bat`** instead.

`serve.bat` now automatically runs `update_catalog.py` first. That script attempts to fetch the current public LeetCode and GeeksforGeeks catalogs and then rebuilds `data.json`.

After the first successful refresh, the dashboard numbers will change from 223 to the number actually retrieved.

If the number remains 223, look at the black command window opened by `serve.bat`. It will show whether LeetCode or GfG blocked the request. The website itself cannot magically bypass a platform's rate limit or anti-bot protection.

You can also run `sync-and-build.bat` manually and inspect the final:
- `meta.json`
- `leetcode-problems.json`
- `gfg-problems.json`
- `data.json`
