#!/usr/bin/env bash
# Tour de France de America — refresh everything.
# Fetches the latest stage results from letour.fr, recomputes the American
# standings, and rebuilds web/data.js for the dashboard.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Fetching stage results from letour.fr"
python3 src/fetch.py

echo "==> Recomputing American standings"
python3 src/compute.py

echo "==> Done. Open web/index.html in a browser (or refresh it)."
