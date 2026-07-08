# 🇺🇸 Tour de France de America (TDFdA)

A tongue-in-cheek tracker for the only riders who matter at the Tour de France:
the Americans. It reruns the Tour as a private race-within-the-race among the
US contingent, hands out four American jerseys, and pits them against each other
as geographic "teams" (state / region / hometown).

**Live in 2026:** 6 Americans started — McNulty (Phoenix AZ), Riccitello (Tucson AZ),
Kuss (Durango CO), Simmons (Durango CO), Sean Quinn (Los Angeles CA), Jorgenson (Boise ID).

## The American jerseys
| Jersey | Meaning |
|---|---|
| 🟡 **Le Maillot June** | Best American on GC (authentic — from real stage times) |
| 🟢 **American Green** | America's points/sprint leader (order-among-Americans, sprint stages weighted) |
| 🔴 **American Polka Dot** | America's climber (order-among-Americans, climbing stages weighted) |
| ⚪ **American White** | Best *young* American (born ≥ 2001) on GC |
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

## Daily automation (planned)
Free path: a GitHub Actions cron (~20:00 CET, after stages settle) runs `run.sh`,
commits `web/data.js`, and GitHub Pages serves `web/`. $0/month. letour.fr is
cloud-accessible, so the same pipeline runs identically on the runner.

## Maintenance
- **Stage profiles** live in `data/roster.json` under `stage_profiles`
  (`tt|flat|hilly|mountain`). They only affect Green-vs-Polka weighting; unknown
  stages default to `flat`. Add each stage's profile from the roadbook for best
  results.
- Roster hometowns/birthdates are curated in `data/roster.json`.

*Not affiliated with A.S.O. Purely for fun.*
