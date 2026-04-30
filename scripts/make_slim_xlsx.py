"""Build a slim, focused xlsx from a raw FY NSF awards xlsx.

Reads:  data/raw/nsf_awards_FY{YYYY}.xlsx
Writes: data/slim/nsf_awards_FY{YYYY}_slim.xlsx

Usage:
    python scripts/make_slim_xlsx.py 2026
"""
import re
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR  = ROOT / "data" / "raw"
SLIM_DIR = ROOT / "data" / "slim"

FY = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
RAW = RAW_DIR  / f"nsf_awards_FY{FY}.xlsx"
OUT = SLIM_DIR / f"nsf_awards_FY{FY}_slim.xlsx"

PREFIX_TOKEN = re.compile(r'^([A-Z][A-Za-z0-9 \-/&]{1,40}?:\s+)')

def split_prefix(title: str):
    if not isinstance(title, str):
        return "", ""
    rest = title
    parts = []
    while True:
        m = PREFIX_TOKEN.match(rest)
        if not m:
            break
        parts.append(m.group(1).rstrip(" :").strip())
        rest = rest[m.end():]
    return ", ".join(parts), rest.strip()

def extract_copis(pi_field, lead_first: str, lead_last: str) -> str:
    if not isinstance(pi_field, str) or not pi_field.strip():
        return ""
    entries = [e.strip() for e in pi_field.split("|") if e.strip()]
    lead_full = f"{lead_first or ''} {lead_last or ''}".lower().strip()
    co = []
    for e in entries:
        name = re.sub(r'\s+\S+@\S+\s*$', '', e).strip()
        if (name.lower() == lead_full
                or (lead_last
                    and name.lower().endswith(lead_last.lower())
                    and lead_first.lower() in name.lower())):
            continue
        co.append(name)
    return "; ".join(co)

def main():
    SLIM_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_excel(RAW)
    print(f"raw: {df.shape}")

    prefixes, titles_clean = zip(*df["title"].map(split_prefix))

    pi_col  = df.get("pi", pd.Series([""]*len(df))).fillna("").astype(str)
    pif_col = df.get("piFirstName", pd.Series([""]*len(df))).fillna("").astype(str)
    pil_col = df.get("piLastName",  pd.Series([""]*len(df))).fillna("").astype(str)
    co_pi = [extract_copis(p, f, l) for p, f, l in zip(pi_col, pif_col, pil_col)]

    award_url = "https://www.nsf.gov/awardsearch/showAward?AWD_ID=" + df["id"].astype(str)

    slim = pd.DataFrame({
        "award_id":          df["id"],
        "award_url":         award_url,
        "program_prefix":    prefixes,
        "title_clean":       titles_clean,
        "pi_first":          df.get("piFirstName", ""),
        "pi_last":           df.get("piLastName", ""),
        "pi_email":          df.get("piEmail", ""),
        "co_pi_names":       co_pi,
        "institution":       df.get("awardeeName", ""),
        "state":             df.get("awardeeStateCode", ""),
        "directorate":       df.get("dirAbbr", ""),
        "directorate_full":  df.get("orgLongName", ""),
        "division":          df.get("divAbbr", ""),
        "division_full":     df.get("orgLongName2", ""),
        "program_name":      df.get("fundProgramName", ""),
        "po_name":           df.get("poName", ""),
        "po_email":          df.get("poEmail", ""),
        "amount_usd":        pd.to_numeric(df.get("estimatedTotalAmt"), errors="coerce"),
        "transaction_type":  df.get("transType", ""),
        "start_date":        df.get("startDate", ""),
        "end_date":          df.get("expDate", ""),
        "abstract":          df.get("abstractText", ""),
    })

    print(f"slim: {slim.shape}")
    print(f"prefix coverage: {(slim['program_prefix'] != '').sum()} / {len(slim)} have a prefix")
    print(f"co-PI coverage:  {(slim['co_pi_names']    != '').sum()} have co-PIs")

    LIMIT = 32_000
    def _t(v):
        if isinstance(v, str) and len(v) > LIMIT:
            return v[:LIMIT] + " ...[TRUNCATED]"
        return v
    slim = slim.apply(lambda c: c.map(_t))

    sheet_name = f"FY{FY} awards (slim)"
    with pd.ExcelWriter(OUT, engine="openpyxl") as w:
        slim.to_excel(w, sheet_name=sheet_name, index=False)
        ws = w.sheets[sheet_name]
        widths = {"A":12,"B":48,"C":18,"D":60,"E":14,"F":14,"G":28,"H":28,
                  "I":36,"J":8,"K":8,"L":30,"M":8,"N":36,"O":28,"P":22,
                  "Q":28,"R":14,"S":18,"T":12,"U":12,"V":80}
        for col, width in widths.items():
            ws.column_dimensions[col].width = width
        ws.freeze_panes = "B2"
        from openpyxl.styles import Font, Alignment
        link_font = Font(color="0563C1", underline="single")
        for r in range(2, len(slim) + 2):
            cell = ws.cell(row=r, column=2)
            if cell.value:
                cell.hyperlink = str(cell.value)
                cell.font = link_font
        for r in range(2, len(slim) + 2):
            ws.cell(row=r, column=22).alignment = Alignment(wrap_text=True, vertical="top")

    print(f"wrote {OUT}")

if __name__ == "__main__":
    main()
