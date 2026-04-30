# NSF Awards Explorer · FY2016 – FY2026

> Interactive EDA dashboard for **120,075 NSF awards** across 11 fiscal years.
> Single self-contained HTML, fully offline-capable, ~21 MB.

[![Live](https://img.shields.io/badge/Live-Dashboard-2563eb?style=flat-square)](https://gisbi-kim.github.io/nsf-awards-explorer/)
[![Data](https://img.shields.io/badge/Data-api.nsf.gov-10b981?style=flat-square)](https://api.nsf.gov/services/v1/awards.json)
[![Awards](https://img.shields.io/badge/Awards-120,075-f59e0b?style=flat-square)](#)
[![FY](https://img.shields.io/badge/FY-2016~2026-8b5cf6?style=flat-square)](#)

## 🌐 [Open Live Dashboard ▸](https://gisbi-kim.github.io/nsf-awards-explorer/)

---

## ✨ What it is

One-shot interactive EDA dashboard for the **U.S. National Science Foundation** awards database. All data + charts baked into a single HTML — no backend, no CDN, works offline once loaded.

**8 tabs**, all charts custom-built inline SVG (no Chart.js / D3):

| Tab | Contents |
|---|---|
| 📊 Overview | Yearly bars + key metrics + headline findings |
| 🏛️ Institutions | Top 20 (count + $$), interactive **US tile map** |
| 🏷️ Prefixes | Glossary of all NSF program prefixes (CAREER, EAGER, RAPID, REU, MRI…), Top 15 charts, FY heatmap, CAREER deep dive, duration histogram |
| 📚 Directorate | Abbreviation reference, donut chart, TIP (2022-new) deep dive |
| 🤖 Robotics | Yearly trend line, **Top 100 institutions** chart + table |
| 💸 Funding Shape | Power-law histogram, **Lorenz curve** (Gini = 0.605), distribution buckets |
| 🔍 Keywords | 27 keyword trends across 11 years (climate, AI, LLM, quantum…) |
| 🔎 Robotics Browser | **Searchable embedded table** of 6,369 robotics awards · click for full abstract · shareable URLs |

🔗 **Shareable URLs** — every tab + browser filter state is encoded in the URL hash:
- `#robotics` — robotics tab
- `#browser?q=Xiao` — browser tab pre-filtered by name
- `#browser?q=SLAM&fy=2024` — search "SLAM" in FY2024
- `#browser?px=CAREER&dir=CSE` — CAREER awards in CSE directorate

---

## 🎯 Headline findings

1. **"climate" funding fell 71% in FY2025** — strongest political-alignment signal
2. **"AI" mentions +90%** while "machine learning" stayed flat
3. **NSF Gini = 0.605** — top 1% of grants take 27% of total $$
4. **UT Austin's $$ #1 rank dominated by single $457M LCCF supercomputer grant** (58% of their 11-yr total)
5. **Robotics funding peaked FY2020-2021, declining since** (-13% by FY2025)
6. **"LLM" / "foundation model" appeared from FY2023** — 0 → ~80/year
7. **MRI (instrumentation) collapsed**: 146 → 6 from FY2022 to FY2026
8. **TIP** (2022 new directorate) already exceeds BIO in funding

---

## 📁 Repo structure

```
nsf-awards-explorer/
├── index.html                  # 21 MB self-contained dashboard
├── README.md
├── .nojekyll                   # disable Jekyll for faster Pages serving
├── .gitignore
├── update.ps1                  # Windows pipeline runner (Docker)
├── update.sh                   # macOS/Linux pipeline runner (Docker)
├── scripts/
│   ├── run_pipeline.py         # ★ orchestrator — fetch + slim + robotics + HTML
│   ├── fetch_nsf_awards.py     # NSF API → raw xlsx (one FY)
│   ├── make_slim_xlsx.py       # raw → slim 22-col xlsx (one FY)
│   ├── extract_robotics.py     # filter robotics-only across all years
│   ├── build_html_report.py    # build the dashboard HTML
│   └── chart_helpers.py        # inline SVG chart helpers
└── data/
    ├── slim/                   # ★ committed — processed per-FY xlsx (22 columns each)
    │   └── nsf_awards_FY{2016..2026}_slim.xlsx
    ├── raw/                    # gitignored — large raw API responses (~30 MB each)
    └── nsf_robotics_awards_all_years.xlsx   # 6,369 robotics-only awards across all FYs
```

The **slim xlsx files are version-controlled** so anyone can rerun the analysis without re-querying the NSF API. Raw files (gitignored) are regenerated on demand by the pipeline.

---

## 🔄 Updating the dashboard

**Prerequisite**: Docker Desktop running.

### Add a new fiscal year
```powershell
# Windows
.\update.ps1 2027
git add . ; git commit -m "Add FY2027" ; git push
```
```bash
# macOS/Linux
./update.sh 2027
git add . && git commit -m "Add FY2027" && git push
```

### Refresh current year (FY in progress)
```powershell
.\update.ps1                 # default = current FY (computed from system date)
```

### Refresh multiple years
```powershell
.\update.ps1 2024 2025 2026
```

### Rebuild HTML only (no API calls)
Useful after editing `scripts/build_html_report.py`:
```powershell
.\update.ps1 --html-only
```

### Refetch everything from scratch (slow!)
```powershell
.\update.ps1 --all           # ~35 minutes for 11 years
```

### Force-refetch a single FY
```bash
rm data/raw/nsf_awards_FY2026.xlsx
./update.sh 2026
```

The pipeline skips the slow API fetch step if `data/raw/nsf_awards_FYXXXX.xlsx` already exists, so re-runs are cheap. Delete the raw file to force a refetch.

---

## 📡 Data source & methodology

**Source**: [api.nsf.gov/services/v1/awards.json](https://api.nsf.gov/services/v1/awards.json)

**API quirk we work around**: a single query is silently capped at **9,000 records**, even though the `totalCount` metadata can show higher numbers. Solution: fetch each FY in **4 quarterly windows** (Oct-Dec, Jan-Mar, Apr-Jun, Jul-Sep) and dedupe by award ID. This recovers ~3,000 awards per year that would otherwise be lost.

**Pipeline stages**:
1. **Fetch raw** per FY (`fetch_nsf_awards.py`): 4 quarterly queries → merge → 65–68 column raw xlsx
2. **Slim** (`make_slim_xlsx.py`): pick 22 useful columns + parse `program_prefix` from title regex + add NSF award URL
3. **Robotics filter** (`extract_robotics.py`): strict regex matching `robot|robotic|slam|teleoperation|autonomous (vehicle|driving|mobility)|self-driving|legged locomotion|motion planning|robot learning|manipulator arm|robot manipulation`. Excludes ambiguous singles (`navigation`, `manipulation`, `embodied`, `drone`, `actuator`, `grasping`) which over-match in non-robotics fields
4. **Build HTML** (`build_html_report.py`): inline SVG charts + tile-grid US map + vanilla-JS searchable browser

---

## ⚖️ License & attribution

- **Code**: MIT License — free to fork, modify, redistribute
- **NSF data**: U.S. Government work — public domain. Attribute the National Science Foundation for any reuse
- **Visualizations**: CC BY 4.0 — attribution requested

---

## 🛠️ Tech notes

- **Zero external runtime deps**: no CDN, no Chart.js / D3 / Plotly — all charts hand-rolled in inline SVG (~300 lines of Python in `chart_helpers.py`)
- **Tile-grid US map**: 13×8 CSS grid, log-scale color, hover tooltip, count/funding toggle
- **Searchable browser**: vanilla JS, sticky-header sortable table, instant client-side filter, 6,369 rows × 7 cols, click row → modal with full abstract + NSF page link
- **URL-based state**: tabs + filters persist in `location.hash` for shareable links
- **Mobile responsive**: tables scroll horizontally, charts auto-fit viewport
- **Build deps**: Python 3.12 + pandas + openpyxl + numpy (Docker-isolated, no host install needed)

---

## 🙋 Author

**Giseop Kim** · DGIST APRL · gisbi.kim@gmail.com · [Lab](https://aprl.dgist.ac.kr)

Built with [Claude Code](https://claude.com/code).
