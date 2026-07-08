# 🇺🇸 Tour de France de America (TDFdA)

**Live: https://tour-de-france-de-america.github.io/** — rebuilt automatically during the race.

A tongue-in-cheek tracker for the only riders who matter at the Tour de France:
the Americans. It reruns the Tour as a private race-within-the-race among the
US contingent, hands out four American jerseys, and pits them against each other
as geographic "teams" (state / region / hometown).

**Live in 2026:** 6 Americans started — McNulty (Phoenix AZ), Riccitello (Tucson AZ),
Kuss (Durango CO), Simmons (Durango CO), Sean Quinn (Los Angeles CA), Jorgenson (Boise ID).

## The American jerseys
| Jersey | Meaning |
|---|---|
| 🟡 **Le Maillot June des États-Unis** | Best American on GC (authentic — from real stage times) |
| 🟢 **Le Maillot Vert des Patriotes** | America's points/sprint leader (order-among-Americans, sprint stages weighted) |
| 🔴 **Le Maillot à Pois de la Liberté** | America's climber (order-among-Americans, climbing stages weighted) |
| ⚪ **Le Maillot Blanc des Jeunes Aigles** | Best *young* American (born ≥ 2001) on GC |
| 🎖️ **Stage MVP** | Top-finishing American each day |

Each jersey shows a **"held for N stages"** streak.

## How it works
```
data/roster.json        curated: the 6 Americans, hometowns, regions, stage profiles
src/fetch.py            pulls letour.fr stage pages → data/cache/stage-N.json
src/compute.py          reconstructs GC + jerseys + team scores → web/data.js
web/index.html          the dashboard (opens as a file; reads web/data.js)
run.sh                  fetch + compute in one shot
```

**Data source:** the official `letour.fr` stage-result pages, which carry the full
field with finish times, time bonuses, and penalties. GC is *reconstructed* by
summing each rider's `time − bonus + penalty` across stages (the classification
tabs on letour only expose the jersey leader, and ProCyclingStats blocks
datacenter IPs — so this self-computed approach is the robust one, and it
reconciles correctly against the real yellow jersey).

## Run it locally
```bash
./run.sh                          # fetch latest + rebuild
open web/index.html               # or refresh the browser tab
```

## Hosting & automation (live)
Hosted free on **GitHub Pages** at https://tour-de-france-de-america.github.io/.
`.github/workflows/deploy.yml` runs on a schedule — **18:00 & 20:30 CEST** (after
each stage finishes, then again once the jury settles results) — plus a manual
"Run workflow" button. Each run fetches letour.fr, recomputes, and deploys `web/`
straight to Pages (no secrets, nothing committed back). $0/month.

To force a refresh manually: `gh workflow run deploy.yml` (or the Actions tab).

## Maintenance
- **Stage profiles** (`tt|flat|hilly|mountain`, in `data/roster.json`) are
  scraped for all 21 stages up front by `python3 src/stage_profiles.py` (pulls
  letour.fr/en/overall-route). The route is fixed once the race starts, so this
  is a one-time run — no per-stage edits. They only affect Green-vs-Polka weighting.
- Roster hometowns/birthdates are curated in `data/roster.json`.

*Not affiliated with A.S.O. Purely for fun.*
