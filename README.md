# NSF Awards Explorer · FY2016 – FY2026

> Interactive EDA dashboard for **120,075 NSF awards** ($31B+ visible) across 11 fiscal years.
> Single self-contained HTML, fully offline-capable, ~6 MB.

[![Live](https://img.shields.io/badge/Live-Dashboard-2563eb?style=flat-square)](https://gisbi-kim.github.io/nsf-awards-explorer/)
[![Data](https://img.shields.io/badge/Data-api.nsf.gov-10b981?style=flat-square)](https://api.nsf.gov/services/v1/awards.json)
[![Awards](https://img.shields.io/badge/Awards-120,075-f59e0b?style=flat-square)](#)
[![FY](https://img.shields.io/badge/FY-2016~2026-8b5cf6?style=flat-square)](#)

## 🌐 [Open Live Dashboard ▸](https://gisbi-kim.github.io/nsf-awards-explorer/)

---

## ✨ What it is

A one-shot interactive EDA dashboard for the **U.S. National Science Foundation** awards database. All data and analysis baked into a single HTML file — no backend, no CDN, works offline once loaded.

Built to answer questions like:
- *Which institutions actually dominate NSF funding, and why?*
- *Has the keyword "climate" really been deprioritized? By how much?*
- *What's the typical CAREER award size by directorate?*
- *Where are robotics grants concentrated, and what is the trend?*
- *How unequal is NSF funding distribution? (Spoiler: Gini = 0.605)*

---

## 📑 Tabs

| Tab | What you'll find |
|---|---|
| 📊 **Overview** | Yearly bar charts, headline metrics, top 5 findings |
| 🏛️ **Institutions** | Top 20 by count + by $$, interactive **US tile map** with count/funding toggle |
| 🏷️ **Prefixes** | Glossary of every NSF program prefix (CAREER, EAGER, RAPID, REU, MRI…), Top 15 charts, FY × prefix heatmap, CAREER deep dive, duration histogram |
| 📚 **Directorate** | Abbreviation reference (MPS, CSE, ENG, GEO, EDU, BIO, TIP, SBE…), donut chart, TIP (2022 new directorate) deep dive |
| 🤖 **Robotics** | Robotics keyword trend (FY2016-2026), Top 100 institutions chart + table |
| 💸 **Funding Shape** | Power-law histogram (log-scale), Lorenz curve (Gini = 0.605), grant size distribution by bucket |
| 🔍 **Keywords** | 27 keyword trends across 11 years (climate, AI, LLM, quantum, blockchain, fairness, …) with mini bar charts |
| 🔎 **Robotics Browser** | Searchable embedded table of **6,369 robotics-related awards** with full metadata + abstract preview + click-to-expand modal |

---

## 🎯 Headline findings

1. **"climate" funding fell 71% in FY2025** (1,428 → 417 keyword mentions) — strongest political-alignment signal in the dataset
2. **"AI" mentions +90%** while "machine learning" stayed flat — AI replaced ML as the broader buzzword
3. **NSF funding is highly unequal**: Gini = 0.605, top 1% of grants take 27% of total $$, top 10% take 51%
4. **UT Austin's $$ ranking is dominated by a single $457M LCCF supercomputer grant** (58% of their 11-year total). Without it, they would rank around #6-7
5. **Robotics funding peaked FY2020-2021, declining since** (706 → 612 awards by FY2025, -13%)
6. **"LLM" and "foundation model" appeared from FY2023** — 0 mentions before, now ~80/year
7. **MRI (Major Research Instrumentation) grants collapsed** — 146 → 6 from FY2022 to FY2026, suggesting infrastructure budget pressure
8. **TIP** (Technology, Innovation & Partnerships, the 2022-new directorate) already exceeds BIO in funding share

---

## 📡 Data source & methodology

**Source:** [api.nsf.gov/services/v1/awards.json](https://api.nsf.gov/services/v1/awards.json)

**Why API instead of CSV/JSON dump?** The official `nsf.gov/awardsearch/download.jsp` page was redesigned (early 2025) and now shows "No export files available at this time" because of the SPA migration. The REST API at `api.nsf.gov` remains stable and well-documented.

**API quirk we worked around:** Single-query results are silently capped at **9,000 records** per date window, even though the `totalCount` metadata can exceed that (showing `10000` for any larger result). Solution: split each fiscal year into **4 quarters** and fetch each separately, then dedupe by award ID. This recovers ~3,000 awards per year that would otherwise be lost.

**Pipeline:**
1. **Fetch raw** per FY: 4 quarterly queries → merge by award ID → 65-68 column raw `xlsx`
2. **Slim transform**: extract 22 essential columns + parse `program_prefix` from title regex + add NSF award URL
3. **Robotics filter**: strict regex matching `robot|robotic|slam|teleoperation|autonomous (vehicle|driving|mobility)|self-driving|legged locomotion|motion planning|robot learning|manipulator arm|robot manipulation`. Excludes ambiguous singular words like `navigation` (oceanography), `manipulation` (chemistry), `embodied` (cognitive science) which over-match in non-robotics fields
4. **Build HTML**: inline SVG charts (custom-built helpers — no Chart.js/D3 dependency), tile-grid US map, vanilla-JS searchable table

**Robotics dataset size:** 6,369 awards out of 120,075 total (5.3%)

---

## 🗂️ Repo contents

```
nsf-awards-explorer/
├── index.html          # 6.2 MB self-contained dashboard
├── README.md           # this file
└── .nojekyll           # disable Jekyll processing for faster Pages serving
```

The dashboard HTML embeds all data inline — robotics-browser data alone is ~4.3 MB JSON. No external network calls except the optional NSF Award detail page links (clicking ↗ in the browser opens nsf.gov in a new tab).

---

## 🔄 Updating the dashboard

Pipeline source code lives in [the analysis project](https://github.com/) (private). Once new data is regenerated, update the dashboard with:

```bash
git -C nsf-awards-explorer pull
cp /path/to/output/nsf_eda_report_FY2016-2026.html nsf-awards-explorer/index.html
git -C nsf-awards-explorer add index.html
git -C nsf-awards-explorer commit -m "Refresh dashboard"
git -C nsf-awards-explorer push
```

GitHub Pages auto-rebuilds within ~30 seconds.

---

## ⚖️ License & attribution

- **Code & analysis**: MIT License (free to fork, modify, redistribute)
- **Data**: U.S. Government work under NSF — public domain. Attribute the National Science Foundation for any reuse of award data
- **Charts/visualizations**: CC BY 4.0 — attribution requested

If you build something interesting from this dataset, please open an issue and link back. Happy to feature derivative work.

---

## 🛠️ Tech notes

- **No external dependencies**: zero CDN calls, no Chart.js/D3/Plotly — all charts hand-rolled in inline SVG (~200 lines of Python helpers)
- **Tile-grid US map**: 13×8 CSS grid with state postal codes, log-scale color, hover tooltip, mode toggle (count vs funding $)
- **Searchable browser**: vanilla JS with sticky-header sortable table, instant client-side filter (no backend), 6,369 rows × 7 columns, click row → modal with full metadata + abstract preview + NSF page link
- **Mobile responsive**: tables scroll horizontally, charts auto-fit to viewport
- **Korean + English mixed**: Pretendard / Noto Sans KR / system font stack

---

## 🙋 Author

**Giseop Kim** · DGIST APRL · gisbi.kim@gmail.com · [Lab](https://aprl.dgist.ac.kr)

Built with [Claude Code](https://claude.com/code).
