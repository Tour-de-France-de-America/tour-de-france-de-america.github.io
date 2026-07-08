#!/usr/bin/env python3
"""
Scrape the full planned-route stage types from letour.fr and write all 21 stage
profiles into data/roster.json. Run once (the route doesn't change mid-race) and
the Green-vs-Polka-Dot weighting is set for the whole Tour — no per-stage edits.

    python3 src/stage_profiles.py
"""
import html
import json
import os
import re
import urllib.request

URL = "https://www.letour.fr/en/overall-route"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = {
    "team time-trial": "tt", "individual time-trial": "tt",
    "flat": "flat", "hilly": "hilly", "mountain": "mountain",
}


def scrape():
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        t = r.read().decode("utf-8", "replace")
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        m = re.search(r'class="type generalRace__col--light"[^>]*>(.*?)</', row, re.S)
        if not m:
            continue
        typ = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip().lower()
        td = re.search(r"<td[^>]*>(.*?)</td>", row, re.S)  # first cell = stage number
        num = html.unescape(re.sub(r"<[^>]+>", "", td.group(1))).strip() if td else ""
        if num.isdigit() and typ in MAP:
            out[num] = MAP[typ]
    return out


def main():
    profiles = scrape()
    if len(profiles) < 15:
        raise SystemExit(f"Only parsed {len(profiles)} stages — letour markup may have "
                         "changed; roster.json left untouched.")
    path = os.path.join(ROOT, "data", "roster.json")
    with open(path) as f:
        roster = json.load(f)
    ordered = {str(n): profiles[str(n)] for n in sorted(map(int, profiles))}
    ordered["_note"] = ("tt|flat|hilly|mountain. Scraped once from letour.fr/en/overall-route "
                        "by src/stage_profiles.py; only affects Green vs Polka-Dot weighting.")
    roster["stage_profiles"] = ordered
    with open(path, "w") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(profiles)} stage profiles to data/roster.json:")
    for n in sorted(map(int, profiles)):
        print(f"  stage {n:>2}: {profiles[str(n)]}")


if __name__ == "__main__":
    main()
