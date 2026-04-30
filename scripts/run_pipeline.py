"""Pipeline orchestrator — fetch raw + build slim + extract robotics + build HTML.

Usage:
    python scripts/run_pipeline.py                      # current FY only
    python scripts/run_pipeline.py 2026                 # one specific FY
    python scripts/run_pipeline.py 2025 2026            # multiple FYs
    python scripts/run_pipeline.py --all                # all years 2016 onwards
    python scripts/run_pipeline.py --html-only          # skip fetch, just rebuild HTML

Skips fetch if raw xlsx already exists (>1MB), so re-running is cheap.
"""
import sys
import subprocess
import time
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
RAW_DIR = ROOT / "data" / "raw"

START_FY = 2016

def current_fy():
    """NSF FY = Oct 1 - Sep 30. So FY2026 = Oct 2025 - Sep 2026."""
    today = datetime.date.today()
    return today.year + 1 if today.month >= 10 else today.year

def run(cmd):
    print(f"\n$ {' '.join(map(str, cmd))}", flush=True)
    subprocess.run(cmd, check=True)

def main():
    args = sys.argv[1:]
    html_only = "--html-only" in args
    all_flag  = "--all" in args
    args = [a for a in args if not a.startswith("--")]

    if html_only:
        years = []
    elif all_flag:
        years = list(range(START_FY, current_fy() + 1))
    elif args:
        years = [int(y) for y in args]
    else:
        years = [current_fy()]

    print(f"ROOT: {ROOT}")
    print(f"Pipeline plan:")
    print(f"  fetch + slim for years: {years if years else '(none)'}")
    print(f"  extract robotics + build HTML: yes")

    t0 = time.time()
    for y in years:
        print(f"\n{'='*60}\n  FY{y}\n{'='*60}")
        raw_path = RAW_DIR / f"nsf_awards_FY{y}.xlsx"
        if raw_path.exists() and raw_path.stat().st_size > 1_000_000:
            print(f"  (raw exists, skip fetch — delete file to force refetch)")
        else:
            run([sys.executable, str(SCRIPTS / "fetch_nsf_awards.py"), str(y)])
        run([sys.executable, str(SCRIPTS / "make_slim_xlsx.py"), str(y)])
        print(f"  elapsed so far: {time.time()-t0:.1f}s")

    print(f"\n{'='*60}\n  Extract robotics + build HTML\n{'='*60}")
    run([sys.executable, str(SCRIPTS / "extract_robotics.py")])
    run([sys.executable, str(SCRIPTS / "build_html_report.py")])

    elapsed = time.time() - t0
    print(f"\n✓ DONE — total {elapsed:.1f}s")
    print(f"  Dashboard: {ROOT / 'index.html'}")
    print(f"  Slim data: {ROOT / 'data' / 'slim'}")
    print(f"  Robotics:  {ROOT / 'data' / 'nsf_robotics_awards_all_years.xlsx'}")

if __name__ == "__main__":
    main()
