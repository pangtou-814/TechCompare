"""Quick comparison: T65 vs T28 nmos/pmos svt — ft & power."""
import csv, re, math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = Path("E:/deskface/tech_compare")

def parse_val(s):
    if not s or not s.strip(): return None
    s = s.strip().strip('"')
    try: return float(s)
    except ValueError: pass
    m = re.match(r'^([\d.eE+-]+)m$', s)
    return float(m.group(1))*1e-3 if m else None

def read_csv(process, device, vt):
    path = BASE / process / f"{device}_{vt}.csv"
    if not path.exists(): return []
    rows, cur = [], {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        next(f)
        for row in csv.reader(f):
            if not row or not row[0].strip(): continue
            first = row[0].strip()
            if first.startswith("Parameters:") or first.startswith('"Parameters:'):
                text = first.replace("Parameters:","").strip().strip('"').strip()
                cur = {}
                for pair in text.split(","):
                    m = re.match(r'(\w+)=([\d.mue]+)', pair.strip())
                    if m:
                        v = parse_val(m.group(2))
                        if v is not None: cur[m.group(1).lower()] = v
                continue
            try: pt = int(first)
            except ValueError: continue
            if len(row) < 4: continue
            v = parse_val(row[3])
            if v is not None:
                rows.append({**cur, "point": pt, "param": row[2].strip(), "value": v,
                             "process": process, "device": device, "vt": vt})
    return rows

# Read data
data = []
for proc in ["T28", "T65"]:
    for dev in ["nmos", "pmos"]:
        data.extend(read_csv(proc, dev, "svt"))
print(f"Total rows: {len(data)}")

# Organize: for each (process, device, {vds, vgs}) collect params
from collections import defaultdict
groups = defaultdict(dict)
for r in data:
    key = (r["process"], r["device"], r.get("vds"), r.get("vgs"))
    groups[key][r["param"]] = r["value"]

# Convert to list of dicts for plotting
records = []
for (proc, dev, vds, vgs), params in groups.items():
    r = {"process": proc, "device": dev, "vds": vds, "vgs": vgs}
    r.update(params)
    records.append(r)

# Sort
records.sort(key=lambda x: (x["process"], x["device"], x["vgs"] or 0, x["vds"] or 0))

# ── Plot: ft vs VGS at each VDS ──
procs = ["T28", "T65"]
devs = ["nmos", "pmos"]
colors = {"T28": "#2196F3", "T65": "#FF5722"}
markers = {"nmos": "o", "pmos": "s"}

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("T65 vs T28 — NMOS / PMOS SVT Comparison", fontsize=16, fontweight="bold")

for di, dev in enumerate(devs):
    for pi, proc in enumerate(procs):
        ax = axes[di][pi]
        sub = [r for r in records if r["process"]==proc and r["device"]==dev
               and r.get("ft") and r.get("ids") and r.get("vgs") and r.get("vds")]
        if not sub: continue

        # Group by VDS
        vds_vals = sorted(set(r["vds"] for r in sub))
        for vds in vds_vals:
            pts = sorted([r for r in sub if r["vds"]==vds], key=lambda x: x["vgs"])
            vgs = [p["vgs"] for p in pts]
            ft = [p["ft"] for p in pts]
            ids = [p["ids"] for p in pts]
            label = f"VDS={vds:.3f}V"
            if pi==0 or True:
                color = "#4CAF50" if vds==max(vds_vals) else "#FFC107"
            else:
                color = "#E91E63" if vds==max(vds_vals) else "#9C27B0"
            ax.plot(vgs, ft, marker=markers[dev], label=label, color=color, linewidth=2)

        ax.set_title(f"{proc} {dev} svt", fontsize=13)
        ax.set_xlabel("VGS (V)", fontsize=11)
        ax.set_ylabel("ft (GHz)", fontsize=11)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(BASE / "ft_comparison.png", dpi=150)
print("Saved: ft_comparison.png")

# ── Plot: gm_id (efficiency) vs VGS — lower = more efficient ──
fig2, axes2 = plt.subplots(2, 2, figsize=(14, 10))
fig2.suptitle("T65 vs T28 — Power Efficiency Comparison (gm_id)", fontsize=16, fontweight="bold")

for di, dev in enumerate(devs):
    for pi, proc in enumerate(procs):
        ax = axes2[di][pi]
        sub = [r for r in records if r["process"]==proc and r["device"]==dev
               and r.get("gm_id") and r.get("vgs") and r.get("vds")]
        if not sub: continue

        vds_vals = sorted(set(r["vds"] for r in sub))
        palettes = {0: ["#4CAF50", "#FFC107"], 1: ["#E91E63", "#9C27B0"]}
        palette = palettes[pi%2]
        for i, vds in enumerate(vds_vals):
            pts = sorted([r for r in sub if r["vds"]==vds], key=lambda x: x["vgs"])
            vgs = [p["vgs"] for p in pts]
            gm_id = [p["gm_id"] for p in pts]
            ax.plot(vgs, gm_id, marker=markers[dev],
                    label=f"VDS={vds:.3f}V", color=palette[i%len(palette)], linewidth=2)

        ax.set_title(f"{proc} {dev} svt", fontsize=13)
        ax.set_xlabel("VGS (V)", fontsize=11)
        ax.set_ylabel("gm_id (1/V)", fontsize=11)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(BASE / "gm_id_comparison.png", dpi=150)
print("Saved: gm_id_comparison.png")

# ── Scatter: ft vs ids (power) tradeoff ──
fig3, axes3 = plt.subplots(1, 2, figsize=(14, 6))
fig3.suptitle("T65 vs T28 — Speed (ft) vs Power (ids) Tradeoff", fontsize=15, fontweight="bold")

for di, dev in enumerate(devs):
    ax = axes3[di]
    for proc in procs:
        sub = [r for r in records if r["process"]==proc and r["device"]==dev
               and r.get("ft") and r.get("ids")]
        ft_vals = [r["ft"] for r in sub]
        ids_vals = [r["ids"] for r in sub]
        ax.scatter(ids_vals, ft_vals, c=colors[proc], label=proc, alpha=0.6, s=40, edgecolors="white", linewidth=0.5)
    ax.set_title(f"{dev} svt", fontsize=13)
    ax.set_xlabel("IDS (A)", fontsize=11)
    ax.set_ylabel("ft (Hz)", fontsize=11)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(BASE / "ft_vs_ids_scatter.png", dpi=150)
print("Saved: ft_vs_ids_scatter.png")

# ── Summary table ──
print("\n" + "="*80)
print(f"{'Metric':<25} {'T28 nmos':<15} {'T65 nmos':<15} {'T28 pmos':<15} {'T65 pmos':<15}")
print("="*80)

peaks = {}
for dev in devs:
    for proc in procs:
        sub = [r for r in records if r["device"]==dev and r["process"]==proc and r.get("ft")]
        peak_ft = max((r["ft"] for r in sub), default=0)
        sub2 = [r for r in records if r["device"]==dev and r["process"]==proc and r.get("gm_id")]
        avg_gm_id = np.mean([r["gm_id"] for r in sub2]) if sub2 else 0
        peaks[(proc, dev)] = (peak_ft, avg_gm_id)

for metric, key in [("Peak ft (GHz)", lambda x: x[0]/1e9), ("Avg gm_id (1/V)", lambda x: x[1])]:
    vals = {proc: {dev: peaks[(proc, dev)] for dev in devs} for proc in procs}
    t28_n = key(vals["T28"]["nmos"]) if vals["T28"]["nmos"] else 0
    t65_n = key(vals["T65"]["nmos"]) if vals["T65"]["nmos"] else 0
    t28_p = key(vals["T28"]["pmos"]) if vals["T28"]["pmos"] else 0
    t65_p = key(vals["T65"]["pmos"]) if vals["T65"]["pmos"] else 0
    print(f"{metric:<25} {t28_n:<15.4g} {t65_n:<15.4g} {t28_p:<15.4g} {t65_p:<15.4g}")

print("="*80)
print(f"\nNotes:")
print(f"  ft peak: higher = faster")
print(f"  gm_id: higher = more current per transconductance (less efficient at low current)")
print(f"  For low-power design: want moderate ft with low ids (high gm_id desirable in weak inversion)")
print(f"\nImages saved to: {BASE}")
