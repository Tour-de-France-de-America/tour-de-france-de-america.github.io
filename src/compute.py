#!/usr/bin/env python3
"""
Tour de France de America - compute layer.

Reads the cached stage results and the curated roster, then reconstructs the
"race within the race": the American General Classification, the four American
jerseys (+ how long each has been held), the Stage MVP, and the geographic team
standings (state / region / Durango).

GC is reconstructed from official stage finish times (time - bonus + penalty,
summed across stages). This sidesteps the unreliable classification subtabs on
letour.fr and gives us an authoritative, self-contained standing.

Output: web/data.js   ->   window.TDFDA = { ... }
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")

# ----- scoring knobs (all tweakable) ---------------------------------------
# Points a rider earns by finishing order AMONG the Americans on a stage.
# 1st American gets the most. Length auto-scales to # of Americans that stage.
def order_points(place, n):
    return max(n - place + 1, 0)  # 1st of 6 -> 6, 2nd -> 5, ... last -> 1

# How much each stage type feeds the Green (sprint) vs KOM (climb) jerseys.
GREEN_WEIGHT = {"tt": 0.5, "flat": 2.0, "hilly": 1.0, "mountain": 0.5}
KOM_WEIGHT   = {"tt": 0.0, "flat": 0.0, "hilly": 1.0, "mountain": 2.0}

# Team "USA points": order points + jersey bonus + real-race achievement bonus.
JERSEY_BONUS = 2               # per American jersey held after the stage
REAL_PODIUM = {1: 8, 2: 5, 3: 3}   # actual overall stage finish 1/2/3
REAL_TOP10 = 2                 # actual overall stage finish 4-10
# ---------------------------------------------------------------------------

# letour 3-letter country codes -> (flag emoji, display name)
COUNTRIES = {
    "USA": ("🇺🇸", "United States"), "BEL": ("🇧🇪", "Belgium"), "FRA": ("🇫🇷", "France"),
    "NED": ("🇳🇱", "Netherlands"), "GER": ("🇩🇪", "Germany"), "ITA": ("🇮🇹", "Italy"),
    "ESP": ("🇪🇸", "Spain"), "AUS": ("🇦🇺", "Australia"), "NOR": ("🇳🇴", "Norway"),
    "GBR": ("🇬🇧", "Great Britain"), "DEN": ("🇩🇰", "Denmark"), "COL": ("🇨🇴", "Colombia"),
    "SUI": ("🇨🇭", "Switzerland"), "SLO": ("🇸🇮", "Slovenia"), "CZE": ("🇨🇿", "Czechia"),
    "POL": ("🇵🇱", "Poland"), "NZL": ("🇳🇿", "New Zealand"), "LAT": ("🇱🇻", "Latvia"),
    "ERI": ("🇪🇷", "Eritrea"), "CAN": ("🇨🇦", "Canada"), "AUT": ("🇦🇹", "Austria"),
    "ECU": ("🇪🇨", "Ecuador"), "RSA": ("🇿🇦", "South Africa"), "POR": ("🇵🇹", "Portugal"),
    "KAZ": ("🇰🇿", "Kazakhstan"), "IRL": ("🇮🇪", "Ireland"), "LUX": ("🇱🇺", "Luxembourg"),
    "EST": ("🇪🇪", "Estonia"), "SVK": ("🇸🇰", "Slovakia"), "UKR": ("🇺🇦", "Ukraine"),
    "MEX": ("🇲🇽", "Mexico"), "JPN": ("🇯🇵", "Japan"),
}


def country_meta(code):
    return COUNTRIES.get(code, ("🏳️", code or "?"))


def fmt_time(s):
    if s is None:
        return "-"
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    return f"{h}h{m:02d}'{sec:02d}\"" if h else f"{m}'{sec:02d}\""


def fmt_gap(s):
    if s is None:
        return "-"
    if s == 0:
        return "—"
    m, sec = divmod(int(s), 60)
    h, m = divmod(m, 60)
    if h:
        return f"+{h}h{m:02d}'{sec:02d}\""
    return f"+{m}'{sec:02d}\"" if m else f"+{sec}\""


def load_roster():
    with open(os.path.join(ROOT, "data", "roster.json")) as f:
        return json.load(f)


def load_stages():
    stages = []
    for n in range(1, 22):
        p = os.path.join(CACHE, f"stage-{n}.json")
        if os.path.exists(p):
            with open(p) as f:
                stages.append(json.load(f))
    return stages


def gc_delta(row):
    """Time this rider contributes to GC on a stage."""
    if row["time_s"] is None:
        return None
    return row["time_s"] - (row["bonus_s"] or 0) + (row["penalty_s"] or 0)


def build():
    roster = load_roster()
    stages = load_stages()
    if not stages:
        raise SystemExit("No stage data cached. Run src/fetch.py first.")

    riders = {r["bib"]: r for r in roster["riders"]}
    us_bibs = set(riders)
    profiles = roster.get("stage_profiles", {})
    cutoff = roster["race"]["youth_cutoff_year"]

    def is_young(bib):
        return int(riders[bib]["birthdate"][:4]) >= cutoff

    # ---- cumulative GC + per-stage American standings (for streaks) --------
    cum = {}                       # bib -> cumulative gc seconds (all riders)
    seen_last = {}                 # bib -> last stage index rider had a result
    # American jersey / points accumulators
    green_pts = {b: 0.0 for b in us_bibs}
    kom_pts = {b: 0.0 for b in us_bibs}
    holder_history = {"june": [], "green": [], "kom": [], "white": []}
    team_points = {}               # (grouping,key) -> points
    timeline = []

    for idx, st in enumerate(stages, start=1):
        prof = profiles.get(str(st["stage"]), "flat")
        # update cumulative time for everyone with a result
        for row in st["result"]:
            d = gc_delta(row)
            if row["bib"] is None or d is None:
                continue
            cum[row["bib"]] = cum.get(row["bib"], 0) + d
            seen_last[row["bib"]] = idx

        # Americans present this stage, ordered by their stage rank
        us_rows = sorted(
            [r for r in st["result"] if r["bib"] in us_bibs],
            key=lambda r: r["rank"],
        )
        n_us = len(us_rows)
        for place, row in enumerate(us_rows, start=1):
            op = order_points(place, n_us)
            green_pts[row["bib"]] += op * GREEN_WEIGHT.get(prof, 1.0)
            kom_pts[row["bib"]] += op * KOM_WEIGHT.get(prof, 0.0)

        # who is "active" (has a result in this, the latest processed stage)
        active_us = [r["bib"] for r in us_rows]

        # American GC leader (Maillot June) after this stage
        june_bib = min(active_us, key=lambda b: cum[b]) if active_us else None
        holder_history["june"].append(june_bib)
        # White: best young American on GC
        young_active = [b for b in active_us if is_young(b)]
        white_bib = min(young_active, key=lambda b: cum[b]) if young_active else None
        holder_history["white"].append(white_bib)
        # Green / KOM leaders so far
        green_bib = max(active_us, key=lambda b: green_pts[b]) if active_us else None
        kom_bib = max(active_us, key=lambda b: kom_pts[b]) if active_us else None
        holder_history["green"].append(green_bib)
        holder_history["kom"].append(kom_bib)

        # ---- team USA points for this stage --------------------------------
        held_now = {june_bib, green_bib, kom_bib, white_bib}
        for place, row in enumerate(us_rows, start=1):
            b = row["bib"]
            pts = order_points(place, n_us)
            if b in held_now:
                pts += JERSEY_BONUS * sum(1 for j in (june_bib, green_bib, kom_bib, white_bib) if j == b)
            pts += REAL_PODIUM.get(row["rank"], 0)
            if 4 <= row["rank"] <= 10:
                pts += REAL_TOP10
            r = riders[b]
            for grouping, key in (("state", r["state"]), ("region", r["region"]), ("hometown", f"{r['city']}, {r['state']}")):
                team_points[(grouping, key)] = team_points.get((grouping, key), 0) + pts

        # ---- timeline entry ------------------------------------------------
        winner = next((x for x in st["result"] if x["rank"] == 1), None)
        mvp = us_rows[0] if us_rows else None
        timeline.append({
            "stage": st["stage"],
            "profile": prof,
            "winner": winner["name"] if winner else "-",
            "winner_team": winner["team"] if winner else "",
            "mvp_bib": mvp["bib"] if mvp else None,
            "mvp_name": riders[mvp["bib"]]["name"] if mvp else "-",
            "mvp_rank": mvp["rank"] if mvp else None,
            "june_bib": june_bib,
        })

    through = stages[-1]["stage"]

    # ---- current streaks ---------------------------------------------------
    def streak(key):
        h = holder_history[key]
        if not h or h[-1] is None:
            return 0
        cur = h[-1]
        s = 0
        for b in reversed(h):
            if b == cur:
                s += 1
            else:
                break
        return s

    # ---- full GC to locate Americans' overall positions --------------------
    active_all = [b for b, last in seen_last.items() if last == len(stages)]
    gc_sorted = sorted(active_all, key=lambda b: cum[b])
    gc_rank = {b: i + 1 for i, b in enumerate(gc_sorted)}
    leader_time = cum[gc_sorted[0]] if gc_sorted else 0
    leader_row = next((x for x in stages[-1]["result"] if x["bib"] == gc_sorted[0]), None)

    # American GC table (ordered by overall position)
    us_active = sorted([b for b in active_us_final(stages, us_bibs)], key=lambda b: cum.get(b, 1e18))
    june_time = cum[us_active[0]] if us_active else 0
    last_stage_rank = {r["bib"]: r["rank"] for r in stages[-1]["result"]}
    americans = []
    for b in us_active:
        r = riders[b]
        americans.append({
            "bib": b, "name": r["name"], "team": r["team"], "emoji": r["emoji"],
            "city": r["city"], "state": r["state"], "state_name": r["state_name"],
            "region": r["region"], "type": r["type"], "blurb": r["blurb"],
            "is_young": is_young(b),
            "gc_rank": gc_rank.get(b),
            "gc_time": fmt_time(cum[b]),
            "gc_gap": fmt_gap(cum[b] - leader_time),
            "us_gap": fmt_gap(cum[b] - june_time),
            "stage_rank": last_stage_rank.get(b),
            "green_pts": round(green_pts[b], 1),
            "kom_pts": round(kom_pts[b], 1),
        })

    def standings(metric, fmt=None, reverse=False):
        rows = sorted(us_active, key=lambda b: metric(b), reverse=reverse)
        out = []
        top = metric(rows[0]) if rows else 0
        for b in rows:
            v = metric(b)
            out.append({
                "bib": b, "name": riders[b]["name"], "emoji": riders[b]["emoji"],
                "team": riders[b]["team"],
                "value": fmt(v) if fmt else round(v, 1),
                "gap": fmt_gap(v - top) if fmt else round(v - top, 1),
            })
        return out

    jerseys = {
        "june": {
            "label": "Le Maillot June des États-Unis", "sub": "Best American on GC", "color": "yellow",
            "holder": holder_history["june"][-1], "streak": streak("june"),
            "standings": standings(lambda b: cum[b], fmt=fmt_time),
        },
        "green": {
            "label": "Le Maillot Vert des Patriotes", "sub": "America's points / sprint jersey", "color": "green",
            "holder": holder_history["green"][-1], "streak": streak("green"),
            "standings": standings(lambda b: green_pts[b], reverse=True),
        },
        "kom": {
            "label": "Le Maillot à Pois de la Liberté", "sub": "America's king of the mountains", "color": "polka",
            "holder": holder_history["kom"][-1], "streak": streak("kom"),
            "standings": standings(lambda b: kom_pts[b], reverse=True),
        },
        "white": {
            "label": "Le Maillot Blanc des Jeunes Aigles", "sub": "Best young American (u26)", "color": "white",
            "holder": holder_history["white"][-1], "streak": streak("white"),
            "standings": standings(lambda b: cum[b] if is_young(b) else 1e18, fmt=fmt_time),
        },
    }
    # white standings: only young riders
    jerseys["white"]["standings"] = [s for s in jerseys["white"]["standings"] if is_young(s["bib"])]

    # ---- teams -------------------------------------------------------------
    def team_table(grouping, labeler):
        rows = [(k, v) for (g, k), v in team_points.items() if g == grouping]
        out = []
        for key, pts in rows:
            members = [riders[b] for b in us_bibs if labeler(riders[b]) == key]
            n = max(len(members), 1)
            out.append({
                "key": key,
                "label": _team_label(grouping, key, roster),
                "emoji": _team_emoji(grouping, key, roster),
                "points": round(pts, 1),          # combined total
                "per_rider": round(pts / n, 1),   # fair, rider-normalized score
                "n_riders": len(members),
                "members": [{"bib": m["bib"], "name": m["name"], "emoji": m["emoji"]} for m in members],
            })
        # rank on the fair per-rider score
        out.sort(key=lambda r: -r["per_rider"])
        return out

    teams = {
        "state": team_table("state", lambda r: r["state"]),
        "region": team_table("region", lambda r: r["region"]),
        "hometown": team_table("hometown", lambda r: f"{r['city']}, {r['state']}"),
    }

    # ---- country classification (the honest scoreboard) --------------------
    last_country = {r["bib"]: r.get("country") for r in stages[-1]["result"]}
    last_name = {r["bib"]: r["name"] for r in stages[-1]["result"]}
    stage_wins = {}
    for st in stages:
        w = next((x for x in st["result"] if x["rank"] == 1), None)
        if w and w.get("country"):
            stage_wins[w["country"]] = stage_wins.get(w["country"], 0) + 1
    cinfo = {}
    for b in gc_sorted:
        cc = last_country.get(b)
        if not cc:
            continue
        e = cinfo.setdefault(cc, {"best_rank": gc_rank[b], "best_bib": b, "n": 0, "times": []})
        e["n"] += 1
        e["times"].append(cum[b])
        if gc_rank[b] < e["best_rank"]:
            e["best_rank"], e["best_bib"] = gc_rank[b], b
    countries = []
    for cc, e in cinfo.items():
        emoji, name = country_meta(cc)
        avg = sum(e["times"]) / len(e["times"])
        countries.append({
            "code": cc, "emoji": emoji, "name": name,
            "best_rank": e["best_rank"], "best_rider": last_name.get(e["best_bib"], "-"),
            "riders": e["n"], "stage_wins": stage_wins.get(cc, 0),
            "avg_time_s": round(avg), "avg_time": fmt_time(avg),
            "is_usa": cc == "USA",
        })
    # default order is best-rider (JS re-sorts per the metric the user picks)
    countries.sort(key=lambda r: r["best_rank"])

    data = {
        "meta": {
            "race": roster["race"]["name"],
            "through_stage": through,
            "total_stages": 21,
            "field_size": len(stages[-1]["result"]),
            "n_americans": len(americans),
            "note": "GC reconstructed from official letour.fr stage times (time − bonus + penalty).",
        },
        "gc_leader": {
            "name": leader_row["name"] if leader_row else "-",
            "team": leader_row["team"] if leader_row else "",
            "time": fmt_time(leader_time),
            "is_american": bool(gc_sorted and gc_sorted[0] in us_bibs),
        },
        "jerseys": jerseys,
        "stage_mvp": {
            "stage": through,
            "bib": timeline[-1]["mvp_bib"],
            "name": timeline[-1]["mvp_name"],
            "rank": timeline[-1]["mvp_rank"],
        },
        "americans": americans,
        "teams": teams,
        "countries": countries,
        "timeline": timeline,
        "riders": roster["riders"],
    }
    return data


def active_us_final(stages, us_bibs):
    last = {r["bib"] for r in stages[-1]["result"]}
    return [b for b in us_bibs if b in last]


def _team_label(grouping, key, roster):
    if grouping == "region":
        return roster["regions"].get(key, {}).get("label", key)
    if grouping == "state":
        for r in roster["riders"]:
            if r["state"] == key:
                return r["state_name"]
    return key


def _team_emoji(grouping, key, roster):
    if grouping == "region":
        return roster["regions"].get(key, {}).get("emoji", "🇺🇸")
    if grouping == "state":
        e = {"AZ": "🌵", "CO": "⛰️", "CA": "🐻", "ID": "🥔"}
        return e.get(key, "🇺🇸")
    return "🏙️"


def main():
    data = build()
    os.makedirs(os.path.join(ROOT, "web"), exist_ok=True)
    out = os.path.join(ROOT, "web", "data.js")
    with open(out, "w") as f:
        f.write("window.TDFDA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"[compute] wrote {out}")
    print(f"[compute] through stage {data['meta']['through_stage']}. "
          f"Maillot June: {data['jerseys']['june']['standings'][0]['name']} "
          f"(held {data['jerseys']['june']['streak']} stages)")
    print(f"[compute] real GC leader: {data['gc_leader']['name']}")
    for t in data["teams"]["state"]:
        print(f"           state {t['emoji']} {t['label']}: {t['points']}")


if __name__ == "__main__":
    main()
