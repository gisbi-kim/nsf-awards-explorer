"""Build a single self-contained HTML EDA report with charts-first design.

Tabs:
 1. Overview        - yearly bars + key metrics + findings
 2. Institutions    - Top hbar (count/funding), US tile map, top table
 3. Prefixes        - Top hbar, prefix-by-year heatmap, CAREER deep, duration
 4. People          - top PIs hbar, top POs hbar
 5. Directorate     - donut + TIP deep dive bars
 6. Robotics        - yearly line, top inst/PI hbar, partners
 7. Funding         - histogram + Lorenz + percentiles
 8. Keywords        - mini-bar charts (already viz)
 9. Robotics Browser - embedded searchable table of all robotics awards
"""
import re
import json
import datetime
from pathlib import Path
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chart_helpers import hbar, vbar, grouped_vbar, line, donut, histogram_log, lorenz, PALETTE

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "slim"

slim_files = sorted(DATA_DIR.glob("nsf_awards_FY*_slim.xlsx"))
years_found = sorted(int(re.search(r"FY(\d{4})", f.name).group(1)) for f in slim_files)
print(f"FYs found: {years_found}")

YR_LABEL = f"FY{years_found[0]} – FY{years_found[-1]}"
YR_RANGE = f"FY{years_found[0]}-{years_found[-1]}"
OUT_HTML = ROOT / "index.html"  # Serve as GitHub Pages root

# ---------- Load & prep ----------
dfs = []
for y in years_found:
    df = pd.read_excel(DATA_DIR / f"nsf_awards_FY{y}_slim.xlsx")
    df.insert(0, "fy", y)
    dfs.append(df)
all_df = pd.concat(dfs, ignore_index=True)
all_df["amount_usd"] = pd.to_numeric(all_df["amount_usd"], errors="coerce").fillna(0)
all_df["start_date"] = pd.to_datetime(all_df["start_date"], errors="coerce")
all_df["end_date"]   = pd.to_datetime(all_df["end_date"],   errors="coerce")
all_df["duration_months"] = ((all_df["end_date"] - all_df["start_date"]).dt.days / 30.44).round(1)
all_df["abstract_lc"] = all_df["abstract"].fillna("").astype(str).str.lower()
all_df["title_lc"]    = all_df["title_clean"].fillna("").astype(str).str.lower()
all_df["pi_last_norm"] = all_df["pi_last"].fillna("").astype(str).str.strip()

TOTAL = len(all_df)
TOTAL_FUNDING_B = all_df["amount_usd"].sum() / 1e9

TODAY = datetime.date.today()
TREND_YEARS = sorted([y for y in years_found if y != years_found[-1] or y < TODAY.year])
if not TREND_YEARS: TREND_YEARS = years_found
FIRST_YR, LAST_YR = TREND_YEARS[0], TREND_YEARS[-1]

# Strict robotics pattern: must contain robot* stem OR specific robotics terms.
# Excludes generic words ("navigation", "manipulation", "perception", "embodied",
# "drone", "uav", "actuator", "grasping") that appear heavily in non-robotics fields
# (oceanography, chemistry, cognitive science, atmospheric, mechanical eng.).
# ---------- Institution name normalization ----------
SPECIAL_INST = {
    "Massachusetts Institute of Technology": ("MIT", ""),
    "California Institute of Technology": ("Caltech", ""),
    "Pennsylvania State Univ University Park": ("Penn State", "UP"),
    "Pennsylvania State Univ-University Park": ("Penn State", "UP"),
    "Pennsylvania State Univ The": ("Penn State", "Univ Park"),
    "Cornell University": ("Cornell", ""),
    "Purdue University": ("Purdue", ""),
    "Arizona State University": ("Arizona State", ""),
    "Stanford University": ("Stanford", ""),
    "Yale University": ("Yale", ""),
    "Princeton University": ("Princeton", ""),
    "Duke University": ("Duke", ""),
    "Columbia University": ("Columbia", ""),
    "Northwestern University": ("Northwestern", ""),
    "Carnegie-Mellon University": ("CMU", ""),
    "Carnegie Mellon University": ("CMU", ""),
}

INST_PATTERNS = [
    # "Regents of (the )?University of X ( - Campus)?" → "U X-Campus (Regents)"
    (re.compile(r"^Regents of(?: the)? University of (.+?)(?:\s*[-–]\s*(.+))?$"),
     lambda m: f"U {m.group(1)}" + (f"-{m.group(2)}" if m.group(2) else "") + " (Regents)"),
    # "(The )?Board of Trustees of (the )?(Leland Stanford Junior )?X" → "X (BoT)"
    (re.compile(r"^(?:The )?Board of Trustees of(?: the)? (?:Leland Stanford Junior )?(.+)$"),
     lambda m: f"{m.group(1)} (BoT)"),
    # "(The )?Trustees of (the )?X (in the City of …)?" → "X (Trustees)"
    (re.compile(r"^(?:The )?Trustees of(?: the)? (.+?)(?:\s+in the City of\s+.+)?$"),
     lambda m: f"{m.group(1)} (Trustees)"),
    # "President and Fellows of X" → "X (Pres. & Fellows)"
    (re.compile(r"^President and Fellows of (.+)$"),
     lambda m: f"{m.group(1)} (Pres. & Fellows)"),
    # "X Research Corporation" → "X (Res. Corp.)"
    (re.compile(r"^(.+?)\s+Research Corporation(?:\s+of\s+.+)?$"),
     lambda m: f"{m.group(1)} (Res. Corp.)"),
    # "X Research Foundation (of …)?" → "X (Res. Found.)"
    (re.compile(r"^(.+?)\s+Research Foundation(?:\s+of\s+.+)?$"),
     lambda m: f"{m.group(1)} (Res. Found.)"),
    # "X Engineering Experiment Station" → "X (Eng. Exp. Sta.)"
    (re.compile(r"^(.+?)\s+Engineering Experiment Station$"),
     lambda m: f"{m.group(1)} (Eng. Exp. Sta.)"),
    # "X Memorial Institute" → "X (Mem. Inst.)"
    (re.compile(r"^(.+?)\s+Memorial Institute$"),
     lambda m: f"{m.group(1)} (Mem. Inst.)"),
    # "X Oceanographic Institution" → "X (Ocean. Inst.)"
    (re.compile(r"^(.+?)\s+Oceanographic Institution$"),
     lambda m: f"{m.group(1)} (Ocean. Inst.)"),
]

INST_GENERIC = [
    ("The University of ", "U "),
    ("University of ", "U "),
    (" University at ", " Univ at "),
    (" University-", " Univ-"),
    (" University ", " Univ "),
    (", Inc.", " (Inc.)"),
    (" Inc.", " (Inc.)"),
    ("Institute of Technology", "Inst. Tech."),
]

def normalize_inst(name):
    if not isinstance(name, str) or not name.strip():
        return name if isinstance(name, str) else ""
    s = name.strip()
    if s in SPECIAL_INST:
        disp, legal = SPECIAL_INST[s]
        return f"{disp} ({legal})" if legal else disp
    for pat, fn in INST_PATTERNS:
        m = pat.match(s)
        if m:
            r = fn(m)
            r = r.replace(" University", " Univ")
            return r
    if s.endswith(" University"):
        return s[:-len(" University")] + " Univ"
    for full, abbr in INST_GENERIC:
        s = s.replace(full, abbr)
    return s

ROBOT_PAT = re.compile(
    r"\b(?:"
    r"robot|robots|robotic|robotics|robotically|"
    r"slam|"
    r"human-robot|hri|"
    r"teleoperation|teleoperated|"
    r"legged locomotion|"
    r"autonomous (?:vehicle|vehicles|driving|mobility)|"
    r"self-driving|"
    r"unmanned aerial vehicle|"
    r"unmanned ground vehicle|"
    r"unmanned aircraft system|"
    r"motion planning|"
    r"robot learning|"
    r"manipulator arm|"
    r"robot manipulation"
    r")\b",
    re.IGNORECASE,
)
all_df["is_robotics"] = all_df["abstract_lc"].str.contains(ROBOT_PAT, regex=True, na=False) | \
                       all_df["title_lc"].str.contains(ROBOT_PAT, regex=True, na=False)

# ---------- Helpers ----------
def fmt_M(v): return f"${v/1e6:,.1f}M" if v >= 1e6 else f"${v/1e3:,.0f}K"
def fmt_int(v): return f"{int(v):,}"
def fmt_money_short(v):
    if v >= 1e9: return f"${v/1e9:.1f}B"
    if v >= 1e6: return f"${v/1e6:.0f}M"
    if v >= 1e3: return f"${v/1e3:.0f}K"
    return f"${int(v)}"
def fmt_M_short(v):  # input already in M
    if v >= 1000: return f"${v/1000:.1f}B"
    return f"${v:.0f}M"

sections = {}

# =====================================================
# 1. OVERVIEW
# =====================================================
yearly = all_df.groupby("fy").agg(
    n_awards=("award_id","count"),
    total_funding_M=("amount_usd", lambda s: s.sum()/1e6),
    median_amount_K=("amount_usd", lambda s: s.median()/1e3),
    n_inst=("institution","nunique"),
    n_pis=("pi_email","nunique"),
).round(1).reset_index()

yearly_chart_rows = [
    {"label": f"FY{int(r['fy'])}", "n": int(r['n_awards']), "M": float(r['total_funding_M'])}
    for _, r in yearly.iterrows()
]
chart_yearly_count = vbar(yearly_chart_rows, "n", "label",
                          value_fmt=fmt_int, color="#2563eb", height=240)
chart_yearly_funding = vbar(yearly_chart_rows, "M", "label",
                            value_fmt=lambda v: f"${v:,.0f}M", color="#10b981", height=240)

yearly_disp = yearly.copy()
yearly_disp.columns = ["FY","건수","총펀딩 ($M)","중앙값 ($K)","기관 수","PI 수"]

overview_html = f"""
<div class="key-metrics">
  <div class="metric"><div class="m-label">총 awards</div><div class="m-value">{TOTAL:,}</div></div>
  <div class="metric"><div class="m-label">총 펀딩</div><div class="m-value">${TOTAL_FUNDING_B:.2f}B</div></div>
  <div class="metric"><div class="m-label">평균 grant</div><div class="m-value">${all_df['amount_usd'].mean()/1e3:,.0f}K</div></div>
  <div class="metric"><div class="m-label">중앙값</div><div class="m-value">${all_df['amount_usd'].median()/1e3:,.0f}K</div></div>
  <div class="metric"><div class="m-label">고유 PI</div><div class="m-value">{all_df['pi_email'].nunique():,}</div></div>
  <div class="metric"><div class="m-label">고유 기관</div><div class="m-value">{all_df['institution'].nunique():,}</div></div>
</div>

<h3>📊 연도별 건수</h3>
{chart_yearly_count}

<h3>💰 연도별 총 펀딩 ($M)</h3>
{chart_yearly_funding}

<h3>📋 연도별 요약 표</h3>
<p class="note">FY{years_found[-1]}은 진행 중 (회계연도 절반쯤). 추세 비교 시 제외 권장.</p>
{yearly_disp.to_html(classes='data-table', index=False, border=0)}

<h3>🔑 핵심 발견</h3>
<ol class="findings">
  <li><b>"climate" 키워드 펀딩이 FY2025에 71% 절벽 감소</b> — 정치적 정렬 신호 (1,428→417건)</li>
  <li><b>"AI"는 +90% 폭증, "ML"은 정체</b> — AI가 더 broader buzzword로 자리잡음</li>
  <li><b>NSF 펀딩 Gini = 0.605</b> — 상위 1% grant가 전체 $$의 27% 차지</li>
  <li><b>UT Austin이 $$ 1위인 이유는 단일 $457M LCCF 슈퍼컴 grant 1건</b> (총합의 58%)</li>
  <li><b>FY2020-2021 robotics 펀딩 정점 후 점진적 감소</b> — FY2025 -17% 위축</li>
</ol>
"""
sections["overview"] = ("📊 Overview", overview_html)

# =====================================================
# 2. INSTITUTIONS (with charts first)
# =====================================================
inst_count_top = all_df.groupby("institution").agg(
    n=("award_id","count"), total_M=("amount_usd", lambda s: s.sum()/1e6)
).sort_values("n", ascending=False).head(20).round(1).reset_index()
inst_count_top["institution"] = inst_count_top["institution"].apply(normalize_inst)

inst_funding_top = all_df.groupby("institution").agg(
    n=("award_id","count"), total_M=("amount_usd", lambda s: s.sum()/1e6)
).sort_values("total_M", ascending=False).head(20).round(1).reset_index()
inst_funding_top["institution"] = inst_funding_top["institution"].apply(normalize_inst)

state_full = all_df.groupby("state").agg(
    n=("award_id","count"), total_M=("amount_usd", lambda s: s.sum()/1e6)
).round(1).reset_index()

# Build hbar charts
chart_inst_count = hbar(
    [{"institution": r["institution"], "n": r["n"], "total_M": r["total_M"]}
     for _, r in inst_count_top.iterrows()],
    "n", "institution", value_fmt=fmt_int, color="#2563eb"
)
chart_inst_funding = hbar(
    [{"institution": r["institution"], "n": r["n"], "total_M": r["total_M"]}
     for _, r in inst_funding_top.iterrows()],
    "total_M", "institution",
    value_fmt=lambda v: f"${v:,.0f}M", color="#10b981"
)

# US tile map (carry over from before)
import math
TILES = {
    'AK': (0, 1), 'HI': (0, 5),
    'ME': (11, 0),
    'VT': (10, 1), 'NH': (11, 1),
    'WA': (1, 2), 'MT': (2, 2), 'ND': (3, 2), 'MN': (4, 2), 'WI': (5, 2), 'MI': (6, 2), 'NY': (9, 2), 'MA': (11, 2),
    'OR': (1, 3), 'ID': (2, 3), 'WY': (3, 3), 'SD': (4, 3), 'IA': (5, 3), 'IL': (6, 3), 'IN': (7, 3), 'OH': (8, 3), 'PA': (9, 3), 'NJ': (10, 3), 'CT': (11, 3), 'RI': (12, 3),
    'CA': (1, 4), 'NV': (2, 4), 'UT': (3, 4), 'CO': (4, 4), 'NE': (5, 4), 'MO': (6, 4), 'KY': (7, 4), 'WV': (8, 4), 'VA': (9, 4), 'MD': (10, 4), 'DC': (11, 4), 'DE': (12, 4),
    'AZ': (3, 5), 'NM': (4, 5), 'KS': (5, 5), 'AR': (6, 5), 'TN': (7, 5), 'NC': (8, 5), 'SC': (9, 5),
    'TX': (4, 6), 'OK': (5, 6), 'LA': (6, 6), 'MS': (7, 6), 'AL': (8, 6), 'GA': (9, 6),
    'FL': (10, 7), 'PR': (12, 7),
}
state_dict = state_full.set_index("state").to_dict("index")
max_count = state_full["n"].max()
max_funding_M = state_full["total_M"].max()
tiles_html = ""
for code, (col, row) in TILES.items():
    info = state_dict.get(code, {"n": 0, "total_M": 0.0})
    n_v = int(info.get("n", 0))
    f_v = float(info.get("total_M", 0.0))
    intensity = math.log10(n_v + 1) / math.log10(max_count + 1) if n_v > 0 else 0
    bg = f"rgba(37,99,235,{0.05 + intensity*0.85:.3f})"
    txt = "#fff" if intensity > 0.55 else "#1f2937"
    tiles_html += (
        f'<div class="tile" style="grid-column:{col+1};grid-row:{row+1};background:{bg};color:{txt};" '
        f'data-state="{code}" data-count="{n_v}" data-funding="{f_v:.0f}" '
        f'data-tip="{code}: {n_v:,} awards · ${f_v:,.0f}M">'
        f'<div class="tile-code">{code}</div>'
        f'<div class="tile-num">{n_v:,}</div></div>'
    )

us_map_html = f"""
<div class="us-map-container">
  <div class="us-map-controls">
    <button class="map-mode active" data-mode="count">건수 기준</button>
    <button class="map-mode" data-mode="funding">총 펀딩 ($M)</button>
  </div>
  <div class="us-map-tooltip" id="usMapTooltip"></div>
  <div class="us-map" id="usMap" data-max-count="{max_count}" data-max-funding="{max_funding_M:.1f}">
    {tiles_html}
  </div>
  <div class="us-map-legend">
    <span class="legend-label">적음</span>
    <div class="us-map-gradient"></div>
    <span class="legend-label">많음</span>
    <span class="legend-note">로그 스케일 · 호버 시 상세</span>
  </div>
</div>
"""

state_top = state_full.sort_values("n", ascending=False).head(20).copy()
state_top.columns = ["주","건수","총$ ($M)"]
inst_count_disp = inst_count_top.copy()
inst_count_disp["avg ($K/건)"] = (inst_count_disp["total_M"]*1000/inst_count_disp["n"]).round(0)
inst_count_disp.columns = ["기관","건수","총$ ($M)","건당 평균($K)"]
inst_funding_disp = inst_funding_top.copy()
inst_funding_disp["avg ($K/건)"] = (inst_funding_disp["total_M"]*1000/inst_funding_disp["n"]).round(0)
inst_funding_disp.columns = ["기관","건수","총$ ($M)","건당 평균($K)"]

inst_html = f"""
<h3>🥇 건수 Top 20</h3>
<p class="note">공립 R1 large state universities가 헤게모니. 막대 = 건수.</p>
{chart_inst_count}

<h3>💰 총 $ Top 20</h3>
<p class="note">⭐ <b>UT Austin이 1등인 이유: 단일 $457M LCCF 슈퍼컴 grant 1건 (총합의 58%)</b>. 그거 빼면 #6~7 평범한 R1.</p>
{chart_inst_funding}

<h3>🗺️ 미국 주별 분포 (타일 지도)</h3>
<p class="note">미국 50개 주 + DC + PR 지리적 배치. 색상 = 규모 (로그 스케일). 토글 버튼으로 건수/펀딩 전환. 마우스 호버 = 상세.</p>
{us_map_html}

<h4>주별 Top 20 표</h4>
{state_top.to_html(classes='data-table', index=False, border=0)}

<h4>건수 Top 20 표</h4>
{inst_count_disp.to_html(classes='data-table', index=False, border=0)}

<h4>총$ Top 20 표</h4>
{inst_funding_disp.to_html(classes='data-table', index=False, border=0)}
"""
sections["institutions"] = ("🏛️ Institutions", inst_html)

# =====================================================
# 3. PREFIXES
# =====================================================
pfx = all_df.assign(prefix=all_df["program_prefix"].fillna("").replace("", "(none)"))
pfx_specs = pfx.groupby("prefix").agg(
    n=("award_id","count"),
    avg_K=("amount_usd", lambda s: s.mean()/1e3),
    median_K=("amount_usd", lambda s: s.median()/1e3),
    avg_dur_mo=("duration_months","mean"),
    total_M=("amount_usd", lambda s: s.sum()/1e6),
).sort_values("n", ascending=False).head(20).round(1).reset_index()

# Bar chart by count + by avg amount
chart_prefix_count = hbar(
    [{"prefix": r["prefix"], "n": r["n"]} for _, r in pfx_specs.head(15).iterrows()],
    "n", "prefix", value_fmt=fmt_int, color="#2563eb"
)
chart_prefix_avg = hbar(
    [{"prefix": r["prefix"], "avg": r["avg_K"]} for _, r in pfx_specs.head(15).iterrows()],
    "avg", "prefix", value_fmt=lambda v: f"${v:,.0f}K", color="#f59e0b"
)

pfx_specs_disp = pfx_specs.copy()
pfx_specs_disp.columns = ["Prefix","건수","평균 ($K)","중앙값 ($K)","평균 기간 (개월)","총$ ($M)"]

# Heatmap (already nice)
prefix_year = (pfx.groupby(["prefix","fy"]).size().unstack(fill_value=0))
prefix_year["total"] = prefix_year.sum(axis=1)
prefix_year = prefix_year.sort_values("total", ascending=False).head(20)
years_cols = [c for c in prefix_year.columns if c != "total"]
mx = prefix_year[years_cols].values.max()
heatmap_rows = ""
for p_, row in prefix_year.iterrows():
    cells = ""
    for y in years_cols:
        v = row[y]
        intensity = (v / mx) ** 0.5 if mx > 0 else 0
        cells += f'<td class="hm-cell" style="background:rgba(37,99,235,{intensity*0.7:.2f})">{int(v)}</td>'
    heatmap_rows += f'<tr><td class="hm-label">{p_}</td>{cells}<td class="hm-total">{int(row["total"]):,}</td></tr>'
heatmap_html = f"""
<div class="hm-wrap"><table class="data-table heatmap">
<thead><tr><th>Prefix</th>{''.join(f'<th>FY{y}</th>' for y in years_cols)}<th>합계</th></tr></thead>
<tbody>{heatmap_rows}</tbody>
</table></div>
"""

# CAREER deep
career = all_df[all_df["program_prefix"].fillna("").str.contains("CAREER", case=False)]
career_dir = career.groupby("directorate").agg(
    n=("award_id","count"),
    avg_K=("amount_usd", lambda s: s.mean()/1e3)
).sort_values("n", ascending=False).round(1).reset_index()
career_year = career.groupby("fy").size().reset_index(name="n")

chart_career_year = vbar(
    [{"label": f"FY{int(r['fy'])}", "n": int(r['n'])} for _, r in career_year.iterrows()],
    "n", "label", value_fmt=fmt_int, color="#8b5cf6", height=220
)
chart_career_dir = hbar(
    [{"d": r["directorate"], "n": r["n"], "avg": r["avg_K"]} for _, r in career_dir.iterrows()],
    "n", "d", value_fmt=fmt_int, color="#8b5cf6"
)
career_dir_disp = career_dir.copy()
career_dir_disp.columns = ["Directorate","건수","평균 ($K)"]

# Duration
bins = [0,12,24,36,48,60,72,120,360]
labels = ["<1y","1-2y","2-3y","3-4y","4-5y","5-6y","6-10y","10y+"]
all_df["duration_bucket"] = pd.cut(all_df["duration_months"], bins=bins, labels=labels, include_lowest=True)
dur_hist = all_df.groupby("duration_bucket", observed=True).agg(
    n=("award_id","count")
).reset_index()
dur_hist["pct"] = (dur_hist["n"]/dur_hist["n"].sum()*100).round(1)
chart_duration = vbar(
    [{"label": str(r["duration_bucket"]), "n": int(r["n"])} for _, r in dur_hist.iterrows()],
    "n", "label", value_fmt=fmt_int, color="#06b6d4", height=240
)

# Prefix glossary
PREFIX_GLOSSARY = [
    # (prefix, expansion, korean meaning, type)
    ("CAREER",  "Faculty Early CAREER Development Program",
     "신진교수 연구·교육 통합 5년 grant. <b>NSF 최고 권위 신진과제</b>. 평생 1회만 가능.",
     "📛 단어 강조"),
    ("EAGER",   "EArly-concept Grants for Exploratory Research",
     "고위험·early-stage 아이디어. peer review 없이 PO 재량.",
     "🎭 bacronym (\"eager\"=열정적)"),
    ("RAPID",   "RApid Response Research",
     "시간 임계 (자연재해, 팬데믹 등). peer review 없이 즉시.",
     "🎭 bacronym (\"rapid\"=신속)"),
    ("GOALI",   "Grant Opportunities for Academic Liaison with Industry",
     "학계 + 산업체 공동 PI.",
     "🎭 bacronym (\"goal\"+I)"),
    ("REU",     "Research Experiences for Undergraduates",
     "학부생 여름 연구체험 site grant.",
     "✅ 진짜 약어"),
    ("MRI",     "Major Research Instrumentation",
     "대형 연구 장비 구입/개발 ($100K~4M).",
     "✅ 진짜 약어"),
    ("SBIR",    "Small Business Innovation Research",
     "중소기업 혁신연구 (Phase I/II).",
     "✅ 진짜 약어"),
    ("STTR",    "Small Business Technology Transfer",
     "중소기업 기술이전 (대학과 공동).",
     "✅ 진짜 약어"),
    ("GRFP",    "Graduate Research Fellowship Program",
     "박사과정생 펠로우십.",
     "✅ 진짜 약어"),
    ("NRT",     "NSF Research Traineeship",
     "대학원생 통합 트레이닝 프로그램 신설.",
     "✅ 진짜 약어"),
    ("EPSCoR",  "Established Program to Stimulate Competitive Research",
     "연구비 적게 받는 25개 주 형평성 program. 소문자 'o'가 들어간 mixed-case 약어.",
     "✅ 진짜 약어"),
    ("IUCRC",   "Industry-University Cooperative Research Centers",
     "산학협력 컨소시엄 5+5년.",
     "✅ 진짜 약어"),
    ("PFI",     "Partnerships for Innovation",
     "TRL 4-7 사업화·기술이전.",
     "✅ 진짜 약어"),
    ("CRII",    "CISE Research Initiation Initiative",
     "CISE 신진 PI (PhD 후 3년 이내).",
     "✅ 진짜 약어"),
    ("RUI",     "Research at Undergraduate Institutions",
     "학부 중심 대학 PI 옵션.",
     "✅ 진짜 약어"),
    ("ROA",     "Research Opportunity Awards",
     "RUI 학사대학 교수 mobility (큰 연구중심대학에서 협업).",
     "✅ 진짜 약어"),
    ("DDRIG",   "Doctoral Dissertation Research Improvement Grant",
     "박사논문 보조연구비 (~$25K).",
     "✅ 진짜 약어"),
    ("ATE",     "Advanced Technological Education",
     "직업기술교육 (community college 중심).",
     "✅ 진짜 약어"),
    ("IUSE",    "Improving Undergraduate STEM Education",
     "학부 STEM 교육 개선 (EDU directorate flagship).",
     "✅ 진짜 약어"),
    ("ERI",     "Engineering Research Initiation",
     "공학 신진 연구자 진입 grant.",
     "✅ 진짜 약어"),
    ("CAS",     "Centers for Advanced Studies / Critical Aspects of Sustainability",
     "맥락에 따라 다름.",
     "✅ 진짜 약어"),
    ("Collaborative Research", "(prefix이지만 약어 아님)",
     "여러 기관이 같은 제목으로 따로 제출. NSF가 묶어서 평가.",
     "📝 그냥 표기"),
    ("Conference / Workshop", "(약어 아님)",
     "학회·워크숍 개최 grant ($5K~50K).",
     "📝 그냥 표기"),
    ("Travel", "(약어 아님)",
     "국제회의 참가 보조.",
     "📝 그냥 표기"),
    ("LEAPS-MPS", "Launching Early-career Academic Pathways in MPS",
     "MPS directorate 신진 launch grant.",
     "✅ 진짜 약어"),
    ("PostDoctoral Fellowship / PRFB", "Postdoctoral Research Fellowship in Biology",
     "BIO 분야 박사후 펠로우십.",
     "✅ 진짜 약어"),
]
glossary_rows = ""
for px, exp, ko, typ in PREFIX_GLOSSARY:
    glossary_rows += (
        f'<tr><td><b>{px}</b></td><td>{exp}</td>'
        f'<td>{ko}</td><td>{typ}</td></tr>'
    )

prefix_html = f"""
<h3>🔤 Prefix 약어 사전</h3>
<p class="note">NSF는 program 이름을 <b>ALL CAPS</b>로 표기 (federal 컨벤션, NASA·DARPA 같은 식). 두 부류:
<b>✅ 진짜 약어</b> (글자별 의미 풀이) vs <b>🎭 bacronym</b> (catchy 단어 먼저 정하고 풀이 끼워맞춤).
영어권 PI에게 program 정체성을 직관적으로 전달하려는 marketing 의도.</p>
<table class="data-table">
  <thead><tr><th>Prefix</th><th>Full Name (EN)</th><th>설명 (KR)</th><th>약어 종류</th></tr></thead>
  <tbody>{glossary_rows}</tbody>
</table>

<h3>📐 Top 15 Prefix — 건수</h3>
{chart_prefix_count}

<h3>💵 Top 15 Prefix — 건당 평균 금액</h3>
<p class="note"><b>SBIR Phase II ($1M)</b>이 단일 mechanism 평균액 1위. CAREER는 $642K로 중위권. Conference·Travel·DDR은 $30~70K로 작음.</p>
{chart_prefix_avg}

<h3>📋 Prefix 스펙 시트</h3>
{pfx_specs_disp.to_html(classes='data-table', index=False, border=0)}

<h3>🌡️ Prefix × 연도 히트맵</h3>
<p class="note">색이 진할수록 그 해에 그 prefix 많이 발급됨.</p>
{heatmap_html}

<h3>🌟 CAREER 심층 — 연도별 건수</h3>
<p class="note">총 {len(career):,}건 / ${career['amount_usd'].sum()/1e6:.0f}M / 평균 ${career['amount_usd'].mean()/1e3:.0f}K.</p>
{chart_career_year}

<h3>🌟 CAREER 심층 — Directorate별</h3>
<p class="note"><b>BIO/EDU CAREER 평균액이 ENG/CSE보다 1.7배 큼</b> ($1M vs $580K).</p>
{chart_career_dir}
{career_dir_disp.to_html(classes='data-table', index=False, border=0)}

<h3>⏱️ Award Duration 분포</h3>
<p class="note">NSF 표준 grant = 2-3년. CAREER만 5년 표준.</p>
{chart_duration}
"""
sections["prefixes"] = ("🏷️ Prefixes", prefix_html)

# =====================================================
# 5. DIRECTORATE
# =====================================================
direc = all_df.groupby("directorate").agg(
    n=("award_id","count"),
    total_M=("amount_usd", lambda s: s.sum()/1e6),
    avg_K=("amount_usd", lambda s: s.mean()/1e3)
).sort_values("n", ascending=False).round(1).reset_index()

# Donut by funding
direc_donut_data = [{"directorate": r["directorate"] or "?", "total_M": r["total_M"]}
                    for _, r in direc.iterrows() if r["total_M"] > 0]
chart_direc_donut = donut(direc_donut_data, "total_M", "directorate",
                          value_fmt=lambda v: f"${v:,.0f}M", size=340)

chart_direc_count = hbar(
    [{"d": r["directorate"] or "?", "n": r["n"]} for _, r in direc.iterrows()],
    "n", "d", value_fmt=fmt_int, color="#2563eb", label_w=140
)

direc_disp = direc.copy()
direc_disp.columns = ["Directorate","건수","총$ ($M)","건당 평균 ($K)"]

# TIP deep
tip = all_df[all_df["directorate"]=="TIP"]
tip_year = tip.groupby("fy").size().reset_index(name="n")
chart_tip_year = vbar(
    [{"label": f"FY{int(r['fy'])}", "n": int(r['n'])} for _, r in tip_year.iterrows()],
    "n", "label", value_fmt=fmt_int, color="#10b981", height=220
)

tip_program = tip.groupby("program_name").agg(
    n=("award_id","count"), total_M=("amount_usd", lambda s: s.sum()/1e6)
).sort_values("n", ascending=False).head(15).round(1).reset_index()
chart_tip_program = hbar(
    [{"p": r["program_name"] or "?", "n": r["n"]} for _, r in tip_program.iterrows()],
    "n", "p", value_fmt=fmt_int, color="#10b981", max_label_chars=40, label_w=320
)
tip_program_disp = tip_program.copy()
tip_program_disp.columns = ["프로그램","건수","총$ ($M)"]

DIRECTORATE_FULL = {
    "MPS": ("Mathematical and Physical Sciences", "수학·물리과학 (수학·물리·화학·재료·천문)"),
    "CSE": ("Computer and Information Science and Engineering", "컴퓨터·정보과학공학"),
    "ENG": ("Engineering", "공학 (전기·기계·재료·화학공학 등)"),
    "GEO": ("Geosciences", "지구과학 (해양·대기·극지·지질)"),
    "EDU": ("Education and Human Resources / EHR", "교육·인력 (STEM 교육·학생훈련 프로그램)"),
    "BIO": ("Biological Sciences", "생명과학"),
    "TIP": ("Technology, Innovation and Partnerships", "기술·혁신·파트너십 (2022 신설, I-Corps·Regional Innovation Engines)"),
    "SBE": ("Social, Behavioral and Economic Sciences", "사회·행동·경제 과학"),
    "O/D": ("Office of the Director", "이사장실 (cross-cutting 프로그램, EPSCoR 포함)"),
    "BFA": ("Budget, Finance & Award Management", "예산·재무"),
    "IRM": ("Information & Resource Management", "정보·자원 관리"),
    "NSB": ("National Science Board", "NSF 이사회"),
}
direc_legend_rows = ""
for _, r in direc.iterrows():
    code = r["directorate"] or "?"
    full_en, ko = DIRECTORATE_FULL.get(code, ("(unknown)", "—"))
    direc_legend_rows += (
        f'<tr><td><b>{code}</b></td><td>{full_en}</td>'
        f'<td>{ko}</td><td>{int(r["n"]):,}</td>'
        f'<td>${r["total_M"]:,.0f}M</td><td>${r["avg_K"]:,.0f}K</td></tr>'
    )

direc_html = f"""
<h3>🔤 Directorate 약어 설명</h3>
<p class="note">NSF는 8개 메인 + 몇 개 보조 directorate로 조직돼있어요. 약어 풀네임과 한국어 설명:</p>
<table class="data-table">
  <thead><tr><th>약어</th><th>Full Name (EN)</th><th>설명 (KR)</th><th>건수</th><th>총$</th><th>건당 평균</th></tr></thead>
  <tbody>{direc_legend_rows}</tbody>
</table>

<h3>🍩 Directorate별 펀딩 비중 (도넛)</h3>
{chart_direc_donut}

<h3>📊 Directorate별 건수</h3>
{chart_direc_count}

<h4>Directorate 표</h4>
{direc_disp.to_html(classes='data-table', index=False, border=0)}

<h3>🆕 TIP Directorate 심층 (2022 신설)</h3>
<p class="note">총 {len(tip):,}건 / ${tip['amount_usd'].sum()/1e6:.0f}M / 평균 ${tip['amount_usd'].mean()/1e3:.0f}K.</p>

<h4>TIP 연도별 건수</h4>
{chart_tip_year}

<h4>TIP 내부 프로그램 Top 15</h4>
{chart_tip_program}

{tip_program_disp.to_html(classes='data-table', index=False, border=0)}
"""
sections["directorate"] = ("📚 Directorate", direc_html)

# =====================================================
# 6. ROBOTICS
# =====================================================
rob = all_df[all_df["is_robotics"]]
rob_year = rob.groupby("fy").agg(
    n=("award_id","count"),
    total_M=("amount_usd", lambda s: s.sum()/1e6)
).round(1).reset_index()

# Line chart for robotics yearly trend
rob_line = line(
    {"건수": [int(r["n"]) for _, r in rob_year.iterrows()],
     "총$ ($M)": [float(r["total_M"]) for _, r in rob_year.iterrows()]},
    [f"FY{int(r['fy'])}" for _, r in rob_year.iterrows()],
    value_fmt=lambda v: f"{v:,.0f}",
    height=300, fill_area=True,
    colors=["#2563eb", "#10b981"]
)

rob_inst_raw = rob.groupby("institution").agg(
    n=("award_id","count"), total_M=("amount_usd", lambda s: s.sum()/1e6)
).sort_values("n", ascending=False).head(100).round(1).reset_index()
# Chart uses abbreviated names (limited space)
chart_rob_inst = hbar(
    [{"inst": normalize_inst(r["institution"]), "n": r["n"]}
     for _, r in rob_inst_raw.iterrows()],
    "n", "inst", value_fmt=fmt_int, color="#ef4444",
    max_label_chars=46, height_per_bar=20, label_w=340
)
# Table uses full raw names + abbreviated for cross-reference
rob_inst_disp = rob_inst_raw.copy()
rob_inst_disp.insert(0, "rank", range(1, len(rob_inst_disp)+1))
rob_inst_disp["abbr"] = rob_inst_disp["institution"].apply(normalize_inst)
rob_inst_disp["avg ($K/건)"] = (rob_inst_disp["total_M"]*1000/rob_inst_disp["n"]).round(0)
rob_inst_disp = rob_inst_disp[["rank","abbr","institution","n","total_M","avg ($K/건)"]]
rob_inst_disp.columns = ["#","약칭","기관 풀네임 (NSF 공식)","건수","총$ ($M)","건당 평균($K)"]

robotics_html = f"""
<h3>📈 Robotics 키워드 트렌드 ({YR_LABEL})</h3>
<p class="note">총 {len(rob):,}건 / ${rob['amount_usd'].sum()/1e6:.0f}M. <b>FY2020-2021 정점 후 감소세</b>. 자세한 awards는 'Robotics Browser' 탭에서 검색 가능.</p>
{rob_line}

<h3>🏛️ Robotics 강세 기관 Top 100</h3>
<p class="note">건수 기준. 막대 위 호버 = 정확한 값. 자세한 통계는 아래 표.</p>
{chart_rob_inst}

<h4>표 — Robotics Top 100 기관</h4>
{rob_inst_disp.to_html(classes='data-table', index=False, border=0)}
"""
sections["robotics"] = ("🤖 Robotics", robotics_html)

# =====================================================
# 7. FUNDING SHAPE
# =====================================================
amt = all_df["amount_usd"][all_df["amount_usd"]>0].values
amt_sorted = np.sort(amt)
n = len(amt_sorted)
cum = np.cumsum(amt_sorted)
gini = (2 * np.sum(np.arange(1, n+1) * amt_sorted) / (n * cum[-1]) - (n+1)/n)
top1 = amt_sorted[-int(n*0.01):].sum() / cum[-1]
top10 = amt_sorted[-int(n*0.10):].sum() / cum[-1]

chart_histogram = histogram_log(
    amt, num_bins=24, color="#2563eb", height=280,
    value_fmt_y=fmt_int
)
chart_lorenz = lorenz(amt, color="#2563eb")

bins_amt = [0, 50e3, 100e3, 250e3, 500e3, 1e6, 5e6, 50e6, 1e9]
labels_amt = ["<$50K","$50-100K","$100-250K","$250-500K","$500K-1M","$1-5M","$5-50M","$50M+"]
all_df["amt_bucket"] = pd.cut(all_df["amount_usd"], bins=bins_amt, labels=labels_amt, include_lowest=True)
size_dist = all_df.groupby("amt_bucket", observed=True).agg(
    n=("award_id","count"),
    total_M=("amount_usd", lambda s: s.sum()/1e6)
).reset_index()

chart_size_count = vbar(
    [{"label": str(r["amt_bucket"]), "n": int(r["n"])} for _, r in size_dist.iterrows()],
    "n", "label", value_fmt=fmt_int, color="#2563eb", height=240
)
chart_size_funding = vbar(
    [{"label": str(r["amt_bucket"]), "M": float(r["total_M"])} for _, r in size_dist.iterrows()],
    "M", "label", value_fmt=lambda v: f"${v:,.0f}M", color="#10b981", height=240
)

size_dist_disp = size_dist.copy()
size_dist_disp["count_pct"] = (size_dist_disp["n"]/size_dist_disp["n"].sum()*100).round(1).astype(str) + "%"
size_dist_disp["funding_pct"] = (size_dist_disp["total_M"]/size_dist_disp["total_M"].sum()*100).round(1).astype(str) + "%"
size_dist_disp.columns = ["금액 구간","건수","$M","건수 비중","$ 비중"]

pct_data = pd.DataFrame([
    {"메트릭":"건수", "값": f"{n:,}"},
    {"메트릭":"min", "값": fmt_money_short(amt_sorted[0])},
    {"메트릭":"median (p50)", "값": fmt_money_short(np.percentile(amt, 50))},
    {"메트릭":"평균", "값": fmt_money_short(amt.mean())},
    {"메트릭":"p90", "값": fmt_money_short(np.percentile(amt, 90))},
    {"메트릭":"p99", "값": fmt_money_short(np.percentile(amt, 99))},
    {"메트릭":"p99.9", "값": fmt_money_short(np.percentile(amt, 99.9))},
    {"메트릭":"max", "값": fmt_money_short(amt_sorted[-1])},
    {"메트릭":"Gini 계수", "값": f"{gini:.3f}"},
    {"메트릭":"상위 1% grant 점유율", "값": f"{top1*100:.1f}% of total $"},
    {"메트릭":"상위 10% grant 점유율", "값": f"{top10*100:.1f}% of total $"},
])

funding_html = f"""
<h3>📈 Grant 크기 히스토그램 (로그 스케일)</h3>
<p class="note">x축은 로그 스케일 (log10) — 작은 grant가 압도적 다수, 거대 grant는 길게 꼬리. 막대 위 호버 = 구간 상세.</p>
{chart_histogram}

<h3>📉 Lorenz Curve — Gini = {gini:.3f}</h3>
<div style="display:flex;gap:1.5em;align-items:center;flex-wrap:wrap">
<div>{chart_lorenz}</div>
<div style="flex:1;min-width:280px">
<p class="note">곡선이 대각선에서 멀수록 불평등 강함. NSF는 facility/center grant 때문에 자연스럽게 큼.</p>
<ul>
<li><b>Gini = 0</b>: 모두 같은 액수</li>
<li><b>Gini = 1</b>: 1명이 다 가져감</li>
<li><b>일반 사회 부 Gini ≈ 0.4</b></li>
<li><b>NSF Gini = {gini:.3f}</b>: 매우 불평등 (남아공 수준)</li>
<li><b>상위 1% grant = 전체 $$의 {top1*100:.1f}%</b></li>
<li><b>상위 10% = {top10*100:.1f}%</b></li>
</ul>
</div>
</div>

<h3>📊 금액 구간별 — 건수 분포</h3>
{chart_size_count}

<h3>💰 금액 구간별 — $$ 분포</h3>
<p class="note"><b>$1M 미만 grant가 건수의 90%</b>인데 펀딩의 절반밖에 안 됨. 나머지 절반은 $1M+ grant 10% 손에. 같은 금액 구간 시각화 둘이 완전 다른 모양.</p>
{chart_size_funding}

<h3>📋 통계 요약 표</h3>
{pct_data.to_html(classes='data-table', index=False, border=0)}

<h3>📋 금액 구간별 표</h3>
{size_dist_disp.to_html(classes='data-table', index=False, border=0)}
"""
sections["funding"] = ("💸 Funding Shape", funding_html)

# =====================================================
# 8. KEYWORDS
# =====================================================
KEYWORDS = ["artificial intelligence","machine learning","deep learning",
            "large language model","llm","foundation model",
            "quantum","climate","robot","autonomous",
            "blockchain","covid","cybersecurity",
            "fairness","bias","ethical","renewable",
            "synthetic biology","crispr","gene","neuro",
            "battery","semiconductor","5g","6g","wireless","edge computing"]
kw_rows = []
for kw in KEYWORDS:
    pat = re.compile(r"\b" + re.escape(kw) + r"\b")
    mask = all_df["abstract_lc"].str.contains(pat, regex=True, na=False)
    yearly = all_df[mask].groupby("fy").size()
    row = {"keyword": kw, "total": int(mask.sum())}
    for y in TREND_YEARS:
        row[f"FY{y}"] = int(yearly.get(y, 0))
    kw_rows.append(row)
kw_df = pd.DataFrame(kw_rows).sort_values("total", ascending=False)

trend_cols = [f"FY{y}" for y in TREND_YEARS]
kw_max = kw_df[trend_cols].values.max() if len(trend_cols)>0 else 1
kw_html_rows = ""
for _, r in kw_df.iterrows():
    first_v = r[f"FY{FIRST_YR}"]
    last_v  = r[f"FY{LAST_YR}"]
    delta_pct = (last_v/first_v*100 - 100) if first_v > 0 else float('inf')
    delta_class = "delta-up" if delta_pct > 20 else ("delta-down" if delta_pct < -20 else "delta-flat")
    delta_str = f"{delta_pct:+.0f}%" if first_v > 0 else "신규"
    bars = ""
    for y in TREND_YEARS:
        v = r[f"FY{y}"]
        h = (v / kw_max * 60) if kw_max > 0 else 0
        bars += f'<div class="kw-bar-col" title="FY{y}: {v}"><div class="kw-bar" style="height:{h:.1f}px"></div><div class="kw-bar-yr">{str(y)[-2:]}</div></div>'
    kw_html_rows += f"""
    <tr>
      <td class="kw-label"><b>{r['keyword']}</b></td>
      <td class="kw-total">{r['total']:,}</td>
      <td><div class="kw-bars">{bars}</div></td>
      <td class="{delta_class}">{delta_str}</td>
    </tr>"""

keywords_html = f"""
<h3>🔍 Abstract 키워드 트렌드 (FY{FIRST_YR}–FY{LAST_YR})</h3>
<p class="note">abstract에 등장한 키워드 빈도. 막대는 연도별 추이 (왼쪽=과거, 오른쪽=최근), 우측 % = FY{FIRST_YR} 대비 FY{LAST_YR} 변화.</p>
<table class="data-table kw-table">
  <thead><tr><th>키워드</th><th>합계</th><th>연도별 추이</th><th>변화</th></tr></thead>
  <tbody>{kw_html_rows}</tbody>
</table>

<div class="callout">
  <h4>주목할 시그널</h4>
  <ul>
    <li>🚨 <b>"climate" -71%</b> — 정치적 정렬, 가장 강한 신호</li>
    <li>⬆️ <b>"AI" +90%</b> (740→1409) — 폭증, 정점 갱신 중</li>
    <li>🆕 <b>"LLM", "foundation model"</b> — FY2023부터 새로 등장</li>
    <li>📉 <b>"fairness", "bias", "ethical"</b> 동반 감소 — DEI 정책 후퇴</li>
  </ul>
</div>
"""
sections["keywords"] = ("🔍 Keywords", keywords_html)

# =====================================================
# 9. ROBOTICS BROWSER (embedded searchable)
# =====================================================
# Build JSON for browser — keep FULL abstracts for modal, no truncation
rob_export = rob[["fy","award_id","award_url","program_prefix","title_clean",
                  "pi_first","pi_last","pi_email","institution","state",
                  "directorate","division","program_name","amount_usd",
                  "start_date","end_date","abstract"]].copy()
rob_export["start_date"] = rob_export["start_date"].dt.strftime("%Y-%m-%d").fillna("")
rob_export["end_date"]   = rob_export["end_date"].dt.strftime("%Y-%m-%d").fillna("")
rob_export["amount_usd"] = rob_export["amount_usd"].fillna(0).astype(int)
# Strip the boilerplate NSF closing line to save ~150 chars per record
NSF_BOILERPLATE = ("This award reflects NSF's statutory mission and has been deemed "
                   "worthy of support through evaluation using the Foundation's "
                   "intellectual merit and broader impacts review criteria.")
def clean_abstract(s):
    s = str(s) if pd.notna(s) else ""
    return s.replace(NSF_BOILERPLATE, "").strip()

# Use compact key names to reduce payload
rob_data = []
for _, r in rob_export.iterrows():
    pi_name = (str(r["pi_first"] or "") + " " + str(r["pi_last"] or "")).strip()
    rob_data.append({
        "fy": int(r["fy"]),
        "id": str(r["award_id"]),
        "url": str(r["award_url"]) if pd.notna(r["award_url"]) else "",
        "px": str(r["program_prefix"] or ""),
        "t":  str(r["title_clean"] or ""),
        "pi": pi_name,
        "em": str(r["pi_email"] or ""),
        "in": str(r["institution"] or ""),
        "st": str(r["state"] or ""),
        "d":  str(r["directorate"] or ""),
        "dv": str(r["division"] or ""),
        "pn": str(r["program_name"] or ""),
        "$":  int(r["amount_usd"] or 0),
        "sd": str(r["start_date"] or ""),
        "ed": str(r["end_date"] or ""),
        "ab": clean_abstract(r["abstract"]),
    })

rob_data_json = json.dumps(rob_data, ensure_ascii=False, separators=(",",":"))
print(f"  robotics browser data size: {len(rob_data_json)/1024/1024:.2f} MB ({len(rob_data):,} rows)")

browser_html = f"""
<h3>🔎 Robotics Awards Browser ({len(rob_data):,}건)</h3>
<p class="note">11년치 robotics 관련 award 모두 검색 가능. 검색어는 <b>제목·PI 이름·이메일·기관·프로그램</b>에서 모두 매칭. 컬럼 헤더 클릭 = 정렬. 행 클릭 = abstract 전문 모달.<br>
🔗 <b>검색·필터 상태가 URL에 반영됨</b> — 결과 링크 그대로 공유 가능. 예: <code>#browser?q=Xiao</code>, <code>#browser?q=SLAM&fy=2024</code></p>

<div class="browser-controls">
  <input type="text" id="robSearch" placeholder="🔎 검색어 (제목·PI·기관·프로그램)..." class="browser-search"/>
  <select id="robFY" class="browser-select">
    <option value="">전체 FY</option>
    {''.join(f'<option value="{y}">FY{y}</option>' for y in years_found)}
  </select>
  <select id="robPrefix" class="browser-select">
    <option value="">전체 prefix</option>
  </select>
  <select id="robDir" class="browser-select">
    <option value="">전체 directorate</option>
  </select>
  <span class="browser-count" id="robCount">{len(rob_data):,}건</span>
</div>

<div class="browser-table-wrap">
<table class="browser-table" id="robTable">
  <thead>
    <tr>
      <th data-sort="fy">FY</th>
      <th data-sort="px">Prefix</th>
      <th data-sort="t">제목</th>
      <th data-sort="pi">PI</th>
      <th data-sort="in">기관</th>
      <th data-sort="d">Dir</th>
      <th data-sort="$">금액</th>
      <th>링크</th>
    </tr>
  </thead>
  <tbody id="robBody"></tbody>
</table>
<div id="robPager" class="browser-pager"></div>
</div>

<div id="robModal" class="browser-modal"><div class="browser-modal-content">
  <span class="browser-modal-close" id="robModalClose">&times;</span>
  <div id="robModalBody"></div>
</div></div>

<script id="robotics-data" type="application/json">{rob_data_json}</script>
"""
sections["browser"] = ("🔎 Robotics Browser", browser_html)

# ---------- CSS ----------
CSS = """
:root {
  --primary: #2563eb;
  --primary-light: #dbeafe;
  --bg: #fafafa;
  --surface: #ffffff;
  --text: #1f2937;
  --text-light: #6b7280;
  --border: #e5e7eb;
  --green: #059669;
  --red: #dc2626;
  --amber: #d97706;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Pretendard", "Noto Sans KR", sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6;
}
header {
  background: linear-gradient(135deg, #1e3a8a, #2563eb);
  color: white; padding: 2.5em 2em 2em; text-align: center;
}
header h1 { margin: 0 0 0.3em; font-size: 1.8em; font-weight: 700; }
header .meta { margin: 0; opacity: 0.9; font-size: 0.95em; }
.container { max-width: 1280px; margin: 0 auto; padding: 0 2em 4em; }
nav.tabs {
  display: flex; gap: 4px; flex-wrap: wrap;
  background: var(--surface); padding: 12px;
  border-radius: 12px; margin: -1.5em auto 1.5em;
  max-width: 1280px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  position: sticky; top: 8px; z-index: 10;
}
nav.tabs button {
  background: transparent; border: 1px solid transparent;
  padding: 10px 16px; border-radius: 8px;
  font-size: 0.92em; cursor: pointer; color: var(--text);
  font-family: inherit; font-weight: 500;
  transition: all 0.15s ease;
}
nav.tabs button:hover { background: var(--primary-light); }
nav.tabs button.active { background: var(--primary); color: white; }
.tab-panel { display: none; background: var(--surface); padding: 2em; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
.tab-panel.active { display: block; }
.tab-panel h3 {
  margin: 1.6em 0 0.8em; font-size: 1.18em; padding-bottom: 0.4em;
  border-bottom: 2px solid var(--primary-light); color: var(--primary);
}
.tab-panel h3:first-child { margin-top: 0; }
.tab-panel h4 { margin: 1.2em 0 0.5em; color: var(--text); font-size: 1em; }
.note { color: var(--text-light); font-size: 0.9em; margin: 0.4em 0 1em; line-height: 1.5; }
.note b { color: var(--text); }

/* Tables */
.data-table { width: 100%; border-collapse: collapse; font-size: 0.88em; margin: 0.8em 0 1.5em; }
.data-table th { background: #f9fafb; text-align: left; padding: 8px 12px; font-weight: 600; border-bottom: 2px solid var(--border); }
.data-table td { padding: 7px 12px; border-bottom: 1px solid var(--border); }
.data-table tr:hover { background: #f9fafb; }
.data-table td:first-child { font-weight: 500; }

/* Key metrics */
.key-metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 1em 0 1.5em; }
.metric { background: var(--primary-light); padding: 14px 16px; border-radius: 10px; }
.m-label { font-size: 0.78em; color: var(--text-light); margin-bottom: 4px; font-weight: 500; }
.m-value { font-size: 1.4em; font-weight: 700; color: var(--primary); }

/* Findings */
.findings { line-height: 1.8; padding-left: 1.2em; }
.findings li { margin-bottom: 0.4em; }

/* Charts */
.chart-svg { font-family: inherit; margin: 0.6em 0 0.3em; max-width: 100%; }
.hbar-label { font-size: 12px; fill: var(--text); font-family: inherit; }
.hbar-value { font-size: 11px; fill: var(--text-light); font-family: inherit; }
.bar-value-label { font-size: 10px; fill: var(--text); font-family: inherit; }
.axis-label { font-size: 10px; fill: var(--text-light); font-family: inherit; }
.chart-legend { display: flex; flex-wrap: wrap; gap: 14px; justify-content: center; margin: 6px 0; font-size: 0.85em; }
.legend-item { display: inline-flex; align-items: center; gap: 6px; color: var(--text-light); }
.legend-swatch { width: 10px; height: 10px; border-radius: 2px; }

/* Donut */
.donut-container { display: flex; gap: 1.5em; align-items: center; flex-wrap: wrap; }
.donut-legend { flex: 1; min-width: 280px; max-width: 480px; font-size: 0.88em; }
.donut-legend-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; border-bottom: 1px dashed #f0f0f0; }
.donut-swatch { width: 12px; height: 12px; border-radius: 2px; flex-shrink: 0; }
.donut-lbl { flex: 1; }
.donut-val { color: var(--text-light); font-variant-numeric: tabular-nums; }
.donut-pct { color: var(--text-light); font-size: 0.85em; }
.donut-center-label { font-size: 11px; fill: var(--text-light); font-weight: 500; }
.donut-center-value { font-size: 18px; fill: var(--text); font-weight: 700; }

/* Heatmap */
.hm-wrap { overflow-x: auto; }
.heatmap td.hm-label { text-align: left; font-weight: 500; padding-left: 12px; white-space: nowrap; max-width: 280px; overflow: hidden; text-overflow: ellipsis; }
.heatmap td.hm-cell { text-align: center; min-width: 50px; }
.heatmap td.hm-total { text-align: right; font-weight: 600; padding-right: 12px; background: #f9fafb; }

/* Keyword */
.kw-bars { display: flex; gap: 3px; align-items: flex-end; height: 60px; }
.kw-bar-col { display: flex; flex-direction: column; align-items: center; }
.kw-bar { width: 12px; background: var(--primary); border-radius: 2px 2px 0 0; min-height: 1px; }
.kw-bar-yr { font-size: 0.6em; color: var(--text-light); margin-top: 2px; }
.delta-up { color: var(--green); font-weight: 600; }
.delta-down { color: var(--red); font-weight: 600; }
.delta-flat { color: var(--text-light); }
.kw-label { padding-right: 16px; }
.kw-total { color: var(--text-light); font-variant-numeric: tabular-nums; }

/* Callout */
.callout { background: #fef3c7; border-left: 4px solid var(--amber); padding: 12px 18px; margin: 1.4em 0; border-radius: 4px; }
.callout h4 { margin-top: 0; color: var(--amber); }
.callout ul { margin: 0.5em 0 0; padding-left: 1.2em; }
.callout li { margin-bottom: 0.3em; }

a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }

/* US Tile Map */
.us-map-container { margin: 1.5em 0; position: relative; }
.us-map-controls { display: flex; gap: 8px; justify-content: center; margin-bottom: 1em; }
.us-map-controls button.map-mode {
  background: var(--surface); border: 1px solid var(--border);
  padding: 6px 14px; border-radius: 6px; font-family: inherit;
  font-size: 0.88em; cursor: pointer; color: var(--text);
}
.us-map-controls button.map-mode:hover { background: var(--primary-light); }
.us-map-controls button.map-mode.active { background: var(--primary); color: white; border-color: var(--primary); }
.us-map {
  display: grid;
  grid-template-columns: repeat(13, 1fr);
  grid-template-rows: repeat(8, 1fr);
  gap: 4px; max-width: 720px; margin: 0 auto;
  aspect-ratio: 13 / 8;
}
.tile {
  border-radius: 4px;
  display: flex; flex-direction: column; justify-content: center; align-items: center;
  font-size: 0.7em; cursor: default;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  position: relative; border: 1px solid rgba(255,255,255,0.5);
  min-height: 0; overflow: hidden;
}
.tile:hover {
  transform: scale(1.15); box-shadow: 0 4px 12px rgba(0,0,0,0.2); z-index: 100;
  border: 1px solid var(--primary);
}
.tile-code { font-weight: 700; font-size: 1em; line-height: 1.1; }
.tile-num { font-size: 0.78em; opacity: 0.85; line-height: 1.1; margin-top: 1px; }
.us-map-tooltip {
  position: absolute; pointer-events: none;
  background: rgba(31,41,55,0.95);
  color: white; padding: 6px 10px; border-radius: 6px;
  font-size: 0.85em; font-weight: 500;
  display: none; z-index: 200; transform: translate(-50%, -110%);
  white-space: nowrap;
}
.us-map-legend {
  display: flex; align-items: center; gap: 10px;
  justify-content: center; margin-top: 1.2em;
  font-size: 0.85em; color: var(--text-light);
  flex-wrap: wrap;
}
.us-map-gradient {
  width: 200px; height: 12px; border-radius: 4px;
  background: linear-gradient(to right, rgba(37,99,235,0.05), rgba(37,99,235,0.9));
}
.legend-note { font-size: 0.78em; opacity: 0.7; }

/* Browser table */
.browser-controls {
  display: flex; gap: 8px; flex-wrap: wrap; align-items: center;
  background: #f9fafb; padding: 12px; border-radius: 8px; margin-bottom: 12px;
}
.browser-search {
  flex: 1; min-width: 240px;
  padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px;
  font-family: inherit; font-size: 0.92em;
}
.browser-search:focus { outline: none; border-color: var(--primary); }
.browser-select {
  padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px;
  font-family: inherit; font-size: 0.88em; background: white;
}
.browser-count { color: var(--text-light); font-size: 0.88em; margin-left: auto; padding: 4px 8px; }
.browser-table-wrap { max-height: 720px; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px; }
.browser-table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
.browser-table th {
  background: #f9fafb; padding: 8px 10px; font-weight: 600;
  border-bottom: 2px solid var(--border);
  position: sticky; top: 0; cursor: pointer; user-select: none;
  text-align: left;
}
.browser-table th:hover { background: var(--primary-light); }
.browser-table td { padding: 7px 10px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }
.browser-table tr.row-clickable { cursor: pointer; }
.browser-table tr.row-clickable:hover { background: #fef3c7; }
.browser-table .col-title { max-width: 480px; }
.browser-table .col-amt { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.browser-pager { padding: 12px; text-align: center; color: var(--text-light); font-size: 0.88em; }
.browser-pager button {
  background: var(--surface); border: 1px solid var(--border); padding: 6px 12px;
  border-radius: 4px; cursor: pointer; margin: 0 4px; font-family: inherit;
}
.browser-pager button:hover:not(:disabled) { background: var(--primary-light); }
.browser-pager button:disabled { opacity: 0.4; cursor: not-allowed; }

/* Modal */
.browser-modal {
  display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center;
}
.browser-modal.active { display: flex; }
.browser-modal-content {
  background: white; padding: 2em; border-radius: 12px; max-width: 880px;
  max-height: 85vh; overflow-y: auto; width: 92%; position: relative;
}
.modal-abstract {
  white-space: pre-wrap; word-wrap: break-word;
}
.browser-modal-close {
  position: absolute; top: 12px; right: 18px; font-size: 1.6em;
  cursor: pointer; color: var(--text-light); font-weight: 700;
}
.browser-modal-close:hover { color: var(--red); }
.modal-meta { display: grid; grid-template-columns: auto 1fr; gap: 4px 14px; margin-bottom: 1em; font-size: 0.92em; }
.modal-meta dt { color: var(--text-light); font-weight: 500; }
.modal-meta dd { margin: 0; }
.modal-abstract { background: #f9fafb; padding: 14px; border-radius: 6px; margin-top: 1em; line-height: 1.6; font-size: 0.9em; }

@media (max-width: 760px) {
  header { padding: 2em 1em 1.5em; }
  .container { padding: 0 1em 2em; }
  .tab-panel { padding: 1.2em; }
  nav.tabs { margin: -1em auto 1em; padding: 8px; }
  nav.tabs button { padding: 8px 10px; font-size: 0.85em; }
  .data-table { font-size: 0.8em; }
}
"""

JS = """
// ---- URL hash routing helpers ----
function getHashTab() {
  const h = location.hash.slice(1);
  const qi = h.indexOf('?');
  return qi === -1 ? h : h.slice(0, qi);
}
function getHashParams() {
  const h = location.hash.slice(1);
  const qi = h.indexOf('?');
  return new URLSearchParams(qi === -1 ? '' : h.slice(qi+1));
}
function setHash(tab, params) {
  const ps = params ? params.toString() : '';
  const newHash = tab + (ps ? '?' + ps : '');
  if (location.hash.slice(1) !== newHash) {
    history.replaceState(null, '', '#' + newHash);
  }
}

// ---- Tab switching ----
function activateTab(tabId) {
  const btn = document.querySelector(`nav.tabs button[data-tab="${tabId}"]`);
  const panel = document.getElementById(tabId);
  if (!btn || !panel) return false;
  document.querySelectorAll('nav.tabs button').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  panel.classList.add('active');
  return true;
}
document.querySelectorAll('nav.tabs button').forEach(b => {
  b.onclick = () => {
    const tab = b.dataset.tab;
    activateTab(tab);
    setHash(tab, null);
    window.scrollTo({top:0,behavior:'smooth'});
  };
});
// Restore tab from URL on load
(function restoreTab(){
  const tab = getHashTab();
  if (tab) activateTab(tab);
})();

// US Map mode toggle + tooltip
(function(){
  const map = document.getElementById('usMap');
  if (!map) return;
  const tooltip = document.getElementById('usMapTooltip');
  const tiles = map.querySelectorAll('.tile');
  const maxCount = parseFloat(map.dataset.maxCount);
  const maxFunding = parseFloat(map.dataset.maxFunding);
  function recolor(mode) {
    const max = mode === 'count' ? maxCount : maxFunding;
    tiles.forEach(tile => {
      const v = parseFloat(tile.dataset[mode]) || 0;
      const intensity = v > 0 ? Math.log10(v + 1) / Math.log10(max + 1) : 0;
      tile.style.background = `rgba(37,99,235,${(0.05 + intensity * 0.85).toFixed(3)})`;
      tile.style.color = intensity > 0.55 ? '#fff' : '#1f2937';
      const num = tile.querySelector('.tile-num');
      if (mode === 'count') num.textContent = v.toLocaleString();
      else num.textContent = '$' + Math.round(v) + 'M';
    });
  }
  document.querySelectorAll('.map-mode').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('.map-mode').forEach(x => x.classList.remove('active'));
      btn.classList.add('active');
      recolor(btn.dataset.mode);
    };
  });
  tiles.forEach(tile => {
    tile.addEventListener('mousemove', e => {
      tooltip.textContent = tile.dataset.tip;
      tooltip.style.display = 'block';
      const rect = map.getBoundingClientRect();
      tooltip.style.left = (e.clientX - rect.left) + 'px';
      tooltip.style.top  = (e.clientY - rect.top)  + 'px';
    });
    tile.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });
  });
})();

// Robotics Browser
(function(){
  const dataEl = document.getElementById('robotics-data');
  if (!dataEl) return;
  const ALL = JSON.parse(dataEl.textContent);
  const tbody = document.getElementById('robBody');
  const search = document.getElementById('robSearch');
  const fyEl = document.getElementById('robFY');
  const pxEl = document.getElementById('robPrefix');
  const dirEl = document.getElementById('robDir');
  const countEl = document.getElementById('robCount');
  const pager = document.getElementById('robPager');
  const PAGE = 100;
  let filtered = ALL.slice();
  let currentPage = 0;
  let sortKey = 'fy';
  let sortDir = -1; // -1 desc

  // Populate prefix and dir filters
  const prefixes = new Set(), dirs = new Set();
  ALL.forEach(r => {
    if (r.px) prefixes.add(r.px);
    if (r.d) dirs.add(r.d);
  });
  Array.from(prefixes).sort().forEach(p => {
    const o = document.createElement('option');
    o.value = p; o.textContent = p; pxEl.appendChild(o);
  });
  Array.from(dirs).sort().forEach(d => {
    const o = document.createElement('option');
    o.value = d; o.textContent = d; dirEl.appendChild(o);
  });

  function fmtAmount(v) {
    if (v >= 1e6) return '$' + (v/1e6).toFixed(1) + 'M';
    if (v >= 1e3) return '$' + (v/1e3).toFixed(0) + 'K';
    return '$' + v;
  }

  function escapeHtml(s) {
    return String(s||'').replace(/[&<>"']/g, c => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    })[c]);
  }

  function render() {
    const start = currentPage * PAGE;
    const end = Math.min(start + PAGE, filtered.length);
    const rows = filtered.slice(start, end);
    tbody.innerHTML = rows.map((r, i) => `
      <tr class="row-clickable" data-idx="${ALL.indexOf(r)}">
        <td>FY${r.fy}</td>
        <td>${escapeHtml(r.px)}</td>
        <td class="col-title">${escapeHtml(r.t)}</td>
        <td>${escapeHtml(r.pi)}<br><span style="color:#6b7280;font-size:0.85em">${escapeHtml(r['in'])}</span></td>
        <td>${escapeHtml(r.st)}</td>
        <td>${escapeHtml(r.d)}</td>
        <td class="col-amt">${fmtAmount(r['$'])}</td>
        <td>${r.url ? `<a href="${escapeHtml(r.url)}" target="_blank" onclick="event.stopPropagation()">↗</a>` : ''}</td>
      </tr>
    `).join('');
    countEl.textContent = filtered.length.toLocaleString() + '건';
    const totalPages = Math.ceil(filtered.length / PAGE);
    pager.innerHTML = filtered.length > PAGE
      ? `<button id="prevPage" ${currentPage===0?'disabled':''}>이전</button>
         페이지 ${currentPage+1} / ${totalPages} (${start+1}–${end} / ${filtered.length.toLocaleString()})
         <button id="nextPage" ${currentPage>=totalPages-1?'disabled':''}>다음</button>`
      : '';
    document.getElementById('prevPage')?.addEventListener('click', () => { currentPage--; render(); });
    document.getElementById('nextPage')?.addEventListener('click', () => { currentPage++; render(); });

    // row click → modal
    tbody.querySelectorAll('tr.row-clickable').forEach(tr => {
      tr.onclick = () => {
        const idx = parseInt(tr.dataset.idx);
        showModal(ALL[idx]);
      };
    });
  }

  function showModal(r) {
    const body = document.getElementById('robModalBody');
    body.innerHTML = `
      <h3 style="margin-top:0">${escapeHtml(r.t)}</h3>
      <dl class="modal-meta">
        <dt>Award ID</dt><dd>${escapeHtml(r.id)}</dd>
        <dt>FY</dt><dd>FY${r.fy}</dd>
        <dt>Prefix</dt><dd>${escapeHtml(r.px) || '(없음)'}</dd>
        <dt>PI</dt><dd>${escapeHtml(r.pi)} (<a href="mailto:${r.em}">${escapeHtml(r.em)}</a>)</dd>
        <dt>기관</dt><dd>${escapeHtml(r['in'])} (${escapeHtml(r.st)})</dd>
        <dt>Directorate</dt><dd>${escapeHtml(r.d)} / ${escapeHtml(r.dv)}</dd>
        <dt>Program</dt><dd>${escapeHtml(r.pn)}</dd>
        <dt>금액</dt><dd>${fmtAmount(r['$'])}</dd>
        <dt>기간</dt><dd>${escapeHtml(r.sd)} ~ ${escapeHtml(r.ed)}</dd>
        <dt>NSF 페이지</dt><dd>${r.url ? `<a href="${r.url}" target="_blank">${r.url}</a>` : '(없음)'}</dd>
      </dl>
      <div class="modal-abstract"><b>Abstract:</b><br>${escapeHtml(r.ab).replace(/\\n/g,'<br>').replace(/\\r/g,'')}</div>
    `;
    document.getElementById('robModal').classList.add('active');
  }
  document.getElementById('robModalClose').onclick = () => document.getElementById('robModal').classList.remove('active');
  document.getElementById('robModal').onclick = (e) => {
    if (e.target.id === 'robModal') e.target.classList.remove('active');
  };

  function applyFilter() {
    const q = search.value.trim().toLowerCase();
    const fy = fyEl.value;
    const px = pxEl.value;
    const dir = dirEl.value;
    filtered = ALL.filter(r => {
      if (fy && r.fy != fy) return false;
      if (px && r.px !== px) return false;
      if (dir && r.d !== dir) return false;
      if (q) {
        const hay = (r.t + ' ' + r.pi + ' ' + r['in'] + ' ' + r.em + ' ' + r.pn + ' ' + r.dv).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    sort();
    currentPage = 0;
    render();
    // Update URL with filter state
    if (getHashTab() === 'browser') {
      const params = new URLSearchParams();
      if (search.value)  params.set('q',   search.value);
      if (fyEl.value)    params.set('fy',  fyEl.value);
      if (pxEl.value)    params.set('px',  pxEl.value);
      if (dirEl.value)   params.set('dir', dirEl.value);
      setHash('browser', params);
    }
  }

  function sort() {
    filtered.sort((a, b) => {
      const va = a[sortKey], vb = b[sortKey];
      if (typeof va === 'number' && typeof vb === 'number') return sortDir * (va - vb);
      return sortDir * String(va || '').localeCompare(String(vb || ''));
    });
  }

  document.querySelectorAll('#robTable th[data-sort]').forEach(th => {
    th.onclick = () => {
      const k = th.dataset.sort;
      if (sortKey === k) sortDir *= -1;
      else { sortKey = k; sortDir = (k === 'fy' || k === '$') ? -1 : 1; }
      sort(); render();
    };
  });
  search.addEventListener('input', applyFilter);
  fyEl.addEventListener('change', applyFilter);
  pxEl.addEventListener('change', applyFilter);
  dirEl.addEventListener('change', applyFilter);

  // Restore filter state from URL on initial load
  if (getHashTab() === 'browser') {
    const p = getHashParams();
    if (p.has('q'))   search.value = p.get('q');
    if (p.has('fy'))  fyEl.value   = p.get('fy');
    if (p.has('px'))  pxEl.value   = p.get('px');
    if (p.has('dir')) dirEl.value  = p.get('dir');
  }
  applyFilter();  // applies any restored filters or no-op
})();
"""

# ---------- Build doc ----------
tab_buttons = "\n".join(
    f'<button data-tab="{key}" class="{"active" if i==0 else ""}">{label}</button>'
    for i, (key, (label, _)) in enumerate(sections.items())
)
tab_panels = "\n".join(
    f'<section id="{key}" class="tab-panel {"active" if i==0 else ""}">{html}</section>'
    for i, (key, (_, html)) in enumerate(sections.items())
)

html_doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NSF Awards EDA · {YR_LABEL}</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>NSF Awards EDA — {YR_LABEL}</h1>
  <p class="meta">{TOTAL:,} awards · ${TOTAL_FUNDING_B:.2f}B 총펀딩 · {all_df['institution'].nunique():,} 기관 · {all_df['pi_email'].nunique():,} PI</p>
  <p class="meta" style="font-size:0.85em">데이터 출처: api.nsf.gov · 분기별 fetch · 마지막 회계연도는 진행 중</p>
</header>
<div class="container">
  <nav class="tabs">{tab_buttons}</nav>
  <main>{tab_panels}</main>
</div>
<script>{JS}</script>
</body>
</html>
"""

OUT_HTML.parent.mkdir(exist_ok=True)
OUT_HTML.write_text(html_doc, encoding="utf-8")
print(f"wrote {OUT_HTML} ({len(html_doc)/1024:.1f} KB)")
print(f"sections: {list(sections.keys())}")
