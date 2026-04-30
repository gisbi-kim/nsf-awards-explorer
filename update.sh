#!/usr/bin/env bash
# Update NSF Awards Explorer dashboard via Docker.
#
# Usage:
#   ./update.sh                      # refresh current FY
#   ./update.sh 2026                 # one specific FY
#   ./update.sh 2025 2026            # multiple
#   ./update.sh --all                # all years from FY2016
#   ./update.sh --html-only          # no fetch, just rebuild HTML
#
# Requires: Docker.

set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "→ Repo: $repo"
echo "→ Pipeline args: $*"
echo

docker run --rm \
  -v "$repo:/work" \
  -w /work \
  python:3.12-slim \
  bash -c "pip install -q pandas openpyxl numpy && python scripts/run_pipeline.py $*"

echo
echo "✓ Pipeline complete."
echo "  Review: $repo/index.html"
echo "  Then:   git add . && git commit -m 'Refresh dashboard' && git push"
