"""Inline SVG chart helpers — self-contained, no dependencies needed."""
import math
import html

PALETTE = ["#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899",
           "#06b6d4", "#ef4444", "#84cc16", "#6366f1", "#f97316",
           "#14b8a6", "#a855f7", "#eab308", "#0ea5e9", "#22c55e"]

def _esc(s):
    return html.escape(str(s))

def hbar(rows, value_key, label_key, value_fmt=None, color="#2563eb",
         max_label_chars=42, height_per_bar=24, label_w=300, value_w=110, max_w=900):
    """Horizontal bar chart. rows is list of dicts."""
    if not rows: return ""
    max_v = max(r[value_key] for r in rows) or 1
    bar_area = max_w - label_w - value_w - 20
    n = len(rows)
    height = n * height_per_bar + 20
    svg_rows = []
    for i, r in enumerate(rows):
        y = 10 + i * height_per_bar
        v = r[value_key]
        w = max(2, v / max_v * bar_area)
        label = str(r[label_key])
        if len(label) > max_label_chars:
            label = label[:max_label_chars-1] + "…"
        val = value_fmt(v) if value_fmt else f"{v:,}"
        svg_rows.append(
            f'<text x="{label_w-8}" y="{y+height_per_bar/2}" class="hbar-label" '
            f'text-anchor="end" dominant-baseline="middle">{_esc(label)}</text>'
            f'<rect x="{label_w}" y="{y+2}" width="{w}" height="{height_per_bar-6}" rx="2" fill="{color}"/>'
            f'<text x="{label_w+w+6}" y="{y+height_per_bar/2}" class="hbar-value" '
            f'dominant-baseline="middle">{_esc(val)}</text>'
        )
    return (f'<svg class="chart-svg hbar-chart" viewBox="0 0 {max_w} {height}" '
            f'preserveAspectRatio="xMinYMin meet" style="width:100%;height:auto;max-height:{height}px">'
            f'{"".join(svg_rows)}</svg>')

def vbar(rows, value_key, label_key, value_fmt=None, color="#2563eb",
        height=260, width=720, bar_gap=10):
    """Vertical bar chart. rows: list of dicts (ordered)."""
    if not rows: return ""
    max_v = max(r[value_key] for r in rows) or 1
    n = len(rows)
    pad_l, pad_r, pad_t, pad_b = 50, 30, 28, 50
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    bw = (plot_w - bar_gap*(n-1)) / n
    bars = []
    grid = []
    # gridlines (5)
    for i in range(5):
        gy = pad_t + plot_h * i / 4
        v = max_v * (1 - i/4)
        grid.append(
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l+plot_w}" y2="{gy:.1f}" '
            f'stroke="#e5e7eb" stroke-width="1"/>'
            f'<text x="{pad_l-6}" y="{gy:.1f}" class="axis-label" '
            f'text-anchor="end" dominant-baseline="middle">{_esc(value_fmt(v) if value_fmt else f"{int(v):,}")}</text>'
        )
    for i, r in enumerate(rows):
        v = r[value_key]
        h_ = max(1, v / max_v * plot_h)
        x = pad_l + i * (bw + bar_gap)
        y = pad_t + plot_h - h_
        val = value_fmt(v) if value_fmt else f"{v:,}"
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h_:.1f}" rx="2" fill="{color}">'
            f'<title>{_esc(r[label_key])}: {_esc(val)}</title></rect>'
            f'<text x="{x+bw/2:.1f}" y="{y-4:.1f}" class="bar-value-label" '
            f'text-anchor="middle">{_esc(val)}</text>'
            f'<text x="{x+bw/2:.1f}" y="{height-pad_b+18:.1f}" class="axis-label" '
            f'text-anchor="middle">{_esc(r[label_key])}</text>'
        )
    return (f'<svg class="chart-svg vbar-chart" viewBox="0 0 {width} {height}" '
            f'preserveAspectRatio="xMinYMin meet" style="width:100%;height:auto">'
            f'{"".join(grid)}{"".join(bars)}</svg>')

def grouped_vbar(rows, series_keys, label_key, series_labels=None,
                 colors=None, value_fmt=None, height=300, width=900):
    """Grouped vertical bars. series_keys is list of dict keys per group."""
    if not rows: return ""
    max_v = max(max(r[k] for k in series_keys) for r in rows) or 1
    n = len(rows)
    n_series = len(series_keys)
    pad_l, pad_r, pad_t, pad_b = 60, 30, 40, 50
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    group_w = plot_w / n
    bw = (group_w - 14) / n_series
    colors = colors or PALETTE
    series_labels = series_labels or series_keys

    grid = []
    for i in range(5):
        gy = pad_t + plot_h * i / 4
        v = max_v * (1 - i/4)
        grid.append(
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l+plot_w}" y2="{gy:.1f}" '
            f'stroke="#e5e7eb" stroke-width="1"/>'
            f'<text x="{pad_l-6}" y="{gy:.1f}" class="axis-label" '
            f'text-anchor="end" dominant-baseline="middle">{_esc(value_fmt(v) if value_fmt else f"{int(v):,}")}</text>'
        )
    bars = []
    for i, r in enumerate(rows):
        x_g = pad_l + i * group_w + 7
        for j, k in enumerate(series_keys):
            v = r[k]
            h_ = max(1, v / max_v * plot_h)
            x = x_g + j * bw
            y = pad_t + plot_h - h_
            val = value_fmt(v) if value_fmt else f"{v:,}"
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw-2:.1f}" height="{h_:.1f}" rx="2" '
                f'fill="{colors[j%len(colors)]}"><title>{_esc(r[label_key])} {_esc(series_labels[j])}: {_esc(val)}</title></rect>'
            )
        bars.append(
            f'<text x="{x_g + group_w/2 - 7:.1f}" y="{height-pad_b+18:.1f}" class="axis-label" '
            f'text-anchor="middle">{_esc(r[label_key])}</text>'
        )
    legend_items = "".join(
        f'<span class="legend-item"><span class="legend-swatch" style="background:{colors[j%len(colors)]}"></span>'
        f'{_esc(series_labels[j])}</span>'
        for j in range(n_series)
    )
    return (
        f'<div class="chart-legend">{legend_items}</div>'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMinYMin meet" style="width:100%;height:auto">'
        f'{"".join(grid)}{"".join(bars)}</svg>'
    )

def line(series_dict, x_labels, value_fmt=None, height=280, width=820, colors=None, fill_area=False):
    """Multi-series line chart. series_dict = {label: [values]} aligned with x_labels."""
    n_pts = len(x_labels)
    all_vals = [v for vs in series_dict.values() for v in vs]
    if not all_vals: return ""
    max_v = max(all_vals) or 1
    pad_l, pad_r, pad_t, pad_b = 60, 30, 30, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    colors = colors or PALETTE

    grid = []
    for i in range(5):
        gy = pad_t + plot_h * i / 4
        v = max_v * (1 - i/4)
        grid.append(
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l+plot_w}" y2="{gy:.1f}" '
            f'stroke="#e5e7eb" stroke-width="1"/>'
            f'<text x="{pad_l-6}" y="{gy:.1f}" class="axis-label" '
            f'text-anchor="end" dominant-baseline="middle">{_esc(value_fmt(v) if value_fmt else f"{int(v):,}")}</text>'
        )
    # x labels
    x_step = plot_w / max(1, n_pts-1)
    for i, lbl in enumerate(x_labels):
        x = pad_l + i * x_step
        grid.append(
            f'<text x="{x:.1f}" y="{height-pad_b+18:.1f}" class="axis-label" text-anchor="middle">{_esc(lbl)}</text>'
        )

    paths = []
    legend_items = ""
    for k, (lbl, vals) in enumerate(series_dict.items()):
        color = colors[k % len(colors)]
        pts = []
        for i, v in enumerate(vals):
            x = pad_l + i * x_step
            y = pad_t + plot_h * (1 - v/max_v) if max_v > 0 else pad_t + plot_h
            pts.append(f"{x:.1f},{y:.1f}")
        if fill_area:
            area_pts = pts + [f"{pad_l + (n_pts-1)*x_step:.1f},{pad_t+plot_h:.1f}", f"{pad_l:.1f},{pad_t+plot_h:.1f}"]
            paths.append(f'<polygon points="{" ".join(area_pts)}" fill="{color}" fill-opacity="0.12"/>')
        paths.append(
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" '
            f'stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for i, v in enumerate(vals):
            x = pad_l + i * x_step
            y = pad_t + plot_h * (1 - v/max_v) if max_v > 0 else pad_t + plot_h
            paths.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="white" stroke="{color}" '
                f'stroke-width="2"><title>{_esc(lbl)} {_esc(x_labels[i])}: '
                f'{_esc(value_fmt(v) if value_fmt else f"{v:,}")}</title></circle>'
            )
        legend_items += (f'<span class="legend-item"><span class="legend-swatch" '
                         f'style="background:{color}"></span>{_esc(lbl)}</span>')
    return (
        f'<div class="chart-legend">{legend_items}</div>'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMinYMin meet" style="width:100%;height:auto">'
        f'{"".join(grid)}{"".join(paths)}</svg>'
    )

def donut(rows, value_key, label_key, value_fmt=None, size=320, colors=None):
    """Donut chart with legend."""
    if not rows: return ""
    total = sum(r[value_key] for r in rows)
    cx, cy = size/2, size/2
    r_outer = size/2 - 8
    r_inner = size/2 - 60
    paths = []
    legend = []
    cumulative = 0
    colors = colors or PALETTE
    for i, r in enumerate(rows):
        v = r[value_key]
        frac = v/total if total > 0 else 0
        if frac <= 0: continue
        a0 = cumulative * 2*math.pi - math.pi/2
        a1 = (cumulative + frac) * 2*math.pi - math.pi/2
        cumulative += frac
        x1, y1 = cx + r_outer*math.cos(a0), cy + r_outer*math.sin(a0)
        x2, y2 = cx + r_outer*math.cos(a1), cy + r_outer*math.sin(a1)
        x3, y3 = cx + r_inner*math.cos(a1), cy + r_inner*math.sin(a1)
        x4, y4 = cx + r_inner*math.cos(a0), cy + r_inner*math.sin(a0)
        large = 1 if frac > 0.5 else 0
        d = (f"M{x1:.2f} {y1:.2f} A{r_outer} {r_outer} 0 {large} 1 {x2:.2f} {y2:.2f} "
             f"L{x3:.2f} {y3:.2f} A{r_inner} {r_inner} 0 {large} 0 {x4:.2f} {y4:.2f} Z")
        c = colors[i % len(colors)]
        val = value_fmt(v) if value_fmt else f"{v:,}"
        paths.append(f'<path d="{d}" fill="{c}" stroke="white" stroke-width="1.5">'
                     f'<title>{_esc(r[label_key])}: {_esc(val)} ({frac*100:.1f}%)</title></path>')
        legend.append(
            f'<div class="donut-legend-item">'
            f'<span class="donut-swatch" style="background:{c}"></span>'
            f'<span class="donut-lbl">{_esc(r[label_key])}</span>'
            f'<span class="donut-val">{_esc(val)} <span class="donut-pct">({frac*100:.1f}%)</span></span>'
            f'</div>'
        )
    inner_label = (f'<text x="{cx}" y="{cy-6}" class="donut-center-label" text-anchor="middle">합계</text>'
                   f'<text x="{cx}" y="{cy+18}" class="donut-center-value" text-anchor="middle">'
                   f'{_esc(value_fmt(total) if value_fmt else f"{total:,}")}</text>')
    return (
        f'<div class="donut-container">'
        f'<svg class="chart-svg donut" viewBox="0 0 {size} {size}" style="width:{size}px;height:{size}px">'
        f'{"".join(paths)}{inner_label}</svg>'
        f'<div class="donut-legend">{"".join(legend)}</div>'
        f'</div>'
    )

def histogram_log(values, num_bins=20, color="#2563eb", height=260, width=720,
                  value_fmt_x=None, value_fmt_y=None):
    """Histogram on log10 x-axis."""
    import numpy as np
    arr = np.asarray([v for v in values if v > 0])
    if len(arr) == 0: return ""
    log_v = np.log10(arr)
    edges = np.linspace(log_v.min(), log_v.max(), num_bins+1)
    counts, _ = np.histogram(log_v, bins=edges)
    max_c = max(counts) or 1
    pad_l, pad_r, pad_t, pad_b = 60, 30, 30, 50
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    bw = plot_w / num_bins
    grid = []
    for i in range(5):
        gy = pad_t + plot_h * i/4
        v = max_c * (1 - i/4)
        grid.append(
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l+plot_w}" y2="{gy:.1f}" '
            f'stroke="#e5e7eb" stroke-width="1"/>'
            f'<text x="{pad_l-6}" y="{gy:.1f}" class="axis-label" '
            f'text-anchor="end" dominant-baseline="middle">{_esc(value_fmt_y(v) if value_fmt_y else f"{int(v):,}")}</text>'
        )
    bars = []
    for i, c in enumerate(counts):
        h_ = max(0.5, c/max_c * plot_h)
        x = pad_l + i*bw
        y = pad_t + plot_h - h_
        x0 = 10**edges[i]
        x1 = 10**edges[i+1]
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw-1:.1f}" height="{h_:.1f}" rx="1" fill="{color}">'
            f'<title>${x0:,.0f}–${x1:,.0f}: {c:,} awards</title></rect>'
        )
    # x-axis labels at log boundaries
    x_marks = []
    log_min, log_max = log_v.min(), log_v.max()
    for log_v_mark in range(int(math.ceil(log_min)), int(math.floor(log_max))+1):
        frac = (log_v_mark - log_min) / (log_max - log_min)
        x = pad_l + frac * plot_w
        v = 10**log_v_mark
        if v >= 1e6: lbl = f"${v/1e6:.0f}M"
        elif v >= 1e3: lbl = f"${v/1e3:.0f}K"
        else: lbl = f"${int(v)}"
        x_marks.append(
            f'<line x1="{x:.1f}" y1="{pad_t+plot_h}" x2="{x:.1f}" y2="{pad_t+plot_h+5}" stroke="#9ca3af"/>'
            f'<text x="{x:.1f}" y="{pad_t+plot_h+18}" class="axis-label" text-anchor="middle">{lbl}</text>'
        )
    return (
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMinYMin meet" style="width:100%;height:auto">'
        f'{"".join(grid)}{"".join(bars)}{"".join(x_marks)}</svg>'
    )

def lorenz(values, height=320, width=320, color="#2563eb"):
    """Lorenz curve for inequality visualization."""
    import numpy as np
    arr = np.sort(np.asarray([v for v in values if v > 0]))
    n = len(arr)
    if n == 0: return ""
    cum = np.cumsum(arr)
    pop_pct = np.arange(1, n+1) / n
    wealth_pct = cum / cum[-1]
    pad = 40
    pw = width - 2*pad
    ph = height - 2*pad
    pts = ["{:.1f},{:.1f}".format(pad, pad+ph)]
    for p, w in zip(pop_pct, wealth_pct):
        pts.append(f"{pad + p*pw:.1f},{pad + (1-w)*ph:.1f}")
    return (
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" style="width:{width}px;height:{height}px">'
        # axes
        f'<line x1="{pad}" y1="{pad+ph}" x2="{pad+pw}" y2="{pad+ph}" stroke="#9ca3af"/>'
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{pad+ph}" stroke="#9ca3af"/>'
        # equality line
        f'<line x1="{pad}" y1="{pad+ph}" x2="{pad+pw}" y2="{pad}" stroke="#d1d5db" stroke-dasharray="4 3"/>'
        # lorenz curve
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2.5"/>'
        # labels
        f'<text x="{pad+pw/2}" y="{height-8}" text-anchor="middle" class="axis-label">PI 누적 (적은 돈 → 많은 돈)</text>'
        f'<text x="14" y="{pad+ph/2}" class="axis-label" transform="rotate(-90 14 {pad+ph/2})" text-anchor="middle">누적 펀딩 점유율</text>'
        f'<text x="{pad+pw-4}" y="{pad+10}" class="axis-label" text-anchor="end" fill="#6b7280">완전 평등 (—)</text>'
        f'</svg>'
    )
