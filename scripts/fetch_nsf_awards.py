"""
Fetch NSF awards for a fiscal year via api.nsf.gov and save raw xlsx.

NSF API has a silent ~9000-record cap per query window, so a full FY
(11K-13K awards) gets truncated. We split each FY into quarters
(Oct-Dec, Jan-Mar, Apr-Jun, Jul-Sep) and paginate within each quarter,
then dedupe by award id.

Usage:
    python scripts/fetch_nsf_awards.py 2026
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"

API = "https://api.nsf.gov/services/v1/awards.json"
RPP = 3000

QUARTERS = [
    ("10/01", "12/31", -1),  # Q1: Oct-Dec of prior calendar year
    ("01/01", "03/31",  0),
    ("04/01", "06/30",  0),
    ("07/01", "09/30",  0),
]

def fetch_window(date_start: str, date_end: str):
    out = []
    offset = 1
    while True:
        url = f"{API}?dateStart={date_start}&dateEnd={date_end}&rpp={RPP}&offset={offset}"
        with urllib.request.urlopen(url, timeout=120) as r:
            data = json.loads(r.read())
        resp = data.get("response", {})
        awards = resp.get("award", [])
        meta = resp.get("metadata", {})
        total = meta.get("totalCount", 0)
        print(f"    {date_start}~{date_end} offset={offset}: got {len(awards)} (total={total})", flush=True)
        if not awards:
            break
        out.extend(awards)
        if len(awards) < RPP:
            break
        offset += RPP
        time.sleep(0.4)
    return out

def fetch_fy(fy: int):
    all_awards = []
    for ms, me, year_off in QUARTERS:
        ds_year = fy + year_off
        ds = f"{ms}/{ds_year}"
        de = f"{me}/{ds_year}"
        print(f"  Q {ds} ~ {de}", flush=True)
        all_awards.extend(fetch_window(ds, de))
    seen = set()
    uniq = []
    for a in all_awards:
        aid = a.get("id")
        if aid in seen:
            continue
        seen.add(aid)
        uniq.append(a)
    print(f"  total: {len(all_awards)} fetched, {len(uniq)} unique", flush=True)
    return uniq

def to_excel(awards, out_path):
    df = pd.DataFrame(awards)
    for col in df.columns:
        if df[col].apply(lambda v: isinstance(v, list)).any():
            df[col] = df[col].apply(lambda v: " | ".join(map(str, v)) if isinstance(v, list) else v)
    LIMIT = 32_000
    truncated = 0
    def _t(v):
        nonlocal truncated
        if isinstance(v, str) and len(v) > LIMIT:
            truncated += 1
            return v[:LIMIT] + " ...[TRUNCATED]"
        return v
    df = df.apply(lambda c: c.map(_t))
    df.to_excel(out_path, index=False, engine="openpyxl")
    print(f"  wrote {out_path} (rows={len(df)}, cols={len(df.columns)}, truncated_cells={truncated})", flush=True)
    return df

if __name__ == "__main__":
    fy = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    awards = fetch_fy(fy)
    out = RAW_DIR / f"nsf_awards_FY{fy}.xlsx"
    to_excel(awards, out)
