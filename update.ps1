# Update NSF Awards Explorer dashboard via Docker.
#
# Usage:
#   .\update.ps1                    # refresh current FY
#   .\update.ps1 2026               # one specific FY
#   .\update.ps1 2025 2026          # multiple
#   .\update.ps1 --all              # all years from FY2016
#   .\update.ps1 --html-only        # no fetch, just rebuild HTML
#
# Requires: Docker Desktop running.
# After this script, review changes and run: git add . && git commit -m "Refresh" && git push

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$pyArgs = $args -join " "

Write-Host "→ Repo: $repo" -ForegroundColor Cyan
Write-Host "→ Pipeline args: $pyArgs" -ForegroundColor Cyan
Write-Host ""

docker run --rm `
    -v "${repo}:/work" `
    -w /work `
    python:3.12-slim `
    bash -c "pip install -q pandas openpyxl numpy && python scripts/run_pipeline.py $pyArgs"

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Pipeline failed (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n✓ Pipeline complete." -ForegroundColor Green
Write-Host "  Review: $repo\index.html"
Write-Host "  Then:   git add . ; git commit -m 'Refresh dashboard' ; git push"
