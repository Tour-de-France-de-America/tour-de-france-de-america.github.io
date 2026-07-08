#!/usr/bin/env python3
"""
Tour de France de America - data fetcher.

Pulls the official letour.fr stage-result pages (full field, with times, bonuses,
and penalties) plus the leader of each jersey classification. Everything here is
cloud-accessible (works from a home Mac and from GitHub Actions alike) and uses
only the Python standard library -- no fragile scraping dependencies.

Output: data/cache/stage-<n>.json  (one file per stage, marked final when settled)

Run:  python3 src/fetch.py            # fetch every available stage
      python3 src/fetch.py 4          # fetch just stage 4
"""
import html
import json
import os
import re
import sys
import time
import urllib.request

BASE = "https://www.letour.fr"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")

# letour classification tab codes -> our jersey keys
CLASS_TABS = {
    "ice": "gc",      # yellow  / general classification
    "ipe": "points",  # green   / points
    "ime": "kom",     # polka   / mountains
    "ije": "youth",   # white   / best young rider
    "ete": "teams",   # teams classification
}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def _cells(row_html):
    cs = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)
    return [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in cs]


def parse_time(s):
    """'04h 10' 45''' -> seconds (int). Returns None if unparseable."""
    if not s or s == "-":
        return None
    s = s.replace("+", "").strip()
    h = re.search(r"(\d+)\s*h", s)
    m = re.search(r"(\d+)\s*'", s)
    sec = re.search(r"(\d+)\s*''", s)
    if not (h or m or sec):
        return None
    return (int(h.group(1)) * 3600 if h else 0) + \
           (int(m.group(1)) * 60 if m else 0) + \
           (int(sec.group(1)) if sec else 0)


def parse_seconds_field(s):
    """'B : 10''' or 'P : 20''' -> 10 / 20 (int seconds). 0 if none."""
    if not s or s == "-":
        return 0
    m = re.search(r"(\d+)\s*''", s)
    return int(m.group(1)) if m else 0


def parse_stage_result(page_html):
    """First rankingTable on the page is the full stage result. Returns list of rows."""
    rows = re.findall(r'<tr class="rankingTables__row.*?</tr>', page_html, re.S)
    out = []
    for r in rows:
        c = [x for x in _cells(r) if x != ""]
        if len(c) < 4 or not c[0].isdigit():
            continue
        # columns: rank, name, bib, team, time, gap, bonus, penalty (bonus/penalty optional)
        bonus = pen = 0
        for extra in c[4:]:
            if extra.startswith("B"):
                bonus = parse_seconds_field(extra)
            elif extra.startswith("P"):
                pen = parse_seconds_field(extra)
        flag = re.search(r'data-class="flag--([a-z]{2,3})"', r)
        out.append({
            "rank": int(c[0]),
            "name": c[1],
            "bib": int(c[2]) if c[2].isdigit() else None,
            "team": c[3],
            "country": flag.group(1).upper() if flag else None,
            "time_s": parse_time(c[4]) if len(c) > 4 else None,
            "bonus_s": bonus,
            "penalty_s": pen,
        })
    return out


def parse_jersey_leaders(page_html):
    """Fetch each classification subtab and read its leader (rank 1) row."""
    leaders = {}
    for tab_code, key in CLASS_TABS.items():
        m = re.search(rf"/en/ajax/ranking/\d+/{tab_code}/[a-f0-9]+/subtab", page_html)
        if not m:
            continue
        try:
            sub = _get(BASE + m.group(0))
        except Exception:
            continue
        cells = [x for x in _cells(sub) if x != ""]
        if len(cells) >= 3 and cells[0] == "1":
            leaders[key] = {"name": cells[1], "bib": _int(cells[2]), "team": cells[3] if len(cells) > 3 else ""}
        time.sleep(1.5)
    return leaders


def _int(s):
    return int(s) if str(s).isdigit() else None


def fetch_stage(n):
    url = f"{BASE}/en/rankings/stage-{n}"
    try:
        page = _get(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    result = parse_stage_result(page)
    if not result:
        return None
    leaders = parse_jersey_leaders(page)
    # A stage is "final" for our purposes once it has a full-ish field.
    return {
        "stage": n,
        "url": url,
        "result": result,
        "official_leaders": leaders,
        "field_size": len(result),
    }


def main():
    os.makedirs(CACHE, exist_ok=True)
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    fetched = []
    for n in range(1, 22):
        if only and n != only:
            continue
        print(f"[fetch] stage {n} ...", end=" ", flush=True)
        data = fetch_stage(n)
        if data is None:
            print("not available (stop)")
            if not only:
                break
            continue
        path = os.path.join(CACHE, f"stage-{n}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"ok  ({data['field_size']} riders, "
              f"{len(data['official_leaders'])} jersey leaders)")
        fetched.append(n)
        time.sleep(2.5)
    print(f"[fetch] done. stages: {fetched}")


if __name__ == "__main__":
    main()
