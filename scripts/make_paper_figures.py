"""Vẽ hình cho paper (nhãn tiếng Anh, PDF vừa 1 cột IEEE) từ results/*_metrics.csv và *_predictions.csv.
Đầu ra: paper/figures/fig_f1_by_variant.pdf, paper/figures/fig_error_types.pdf
Chạy: python3 scripts/make_paper_figures.py   (cần pandas, matplotlib)
"""
import glob
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper/figures"
OUT.mkdir(parents=True, exist_ok=True)

VARIANTS = ["clean", "no_diacritics", "teencode", "telex", "code_switch", "mixed"]
VN = {"clean": "Clean", "no_diacritics": "No diacritics", "teencode": "Teencode", "telex": "Telex typos",
      "code_switch": "Code-switching", "mixed": "Mixed"}
ORDER = ["PhoBERT-base (flat)", "PhoBERT-base (hier)", "Qwen2.5-1.5B + LoRA", "Qwen2.5-3B + LoRA",
         "GPT-4o zero-shot", "GPT-4o few-shot"]


def system(model, mode):
    if model == "PhoBERT":
        return f"PhoBERT-base ({mode})"
    if model == "GPT-4o":
        return "GPT-4o " + mode.replace("_", "-")
    return model.replace("+LoRA", " + LoRA")


mets, preds = [], []
for f in sorted(glob.glob(str(ROOT / "results/*_metrics.csv"))):
    if "_trial_" in f or Path(f).name.startswith("R2_"):
        continue
    m = pd.read_csv(f)
    mets.append(m)
    p = pd.read_csv(f.replace("_metrics.csv", "_predictions.csv"))
    if "model" not in p:
        p["model"] = m.model.iloc[0]
    preds.append(p)
res, pred = pd.concat(mets), pd.concat(preds)
for df in (res, pred):
    df["system"] = [system(a, b) for a, b in zip(df.model, df["mode"])]
SYSTEMS = [s for s in ORDER if s in set(res.system)]

INK, INK2, GRID = "#1f1f1e", "#5f5e58", "#e4e3de"
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
MARKERS = ["o", "s", "^", "D", "v", "P"]
plt.rcParams.update({"font.family": "serif", "font.size": 8, "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID, "pdf.fonttype": 42})


def style(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


# Hình 1: macro-F1 theo biến thể
g = res.groupby(["system", "variant"]).f1
mean = g.mean().unstack().reindex(index=SYSTEMS, columns=VARIANTS) * 100
std = g.std().unstack().reindex(index=SYSTEMS, columns=VARIANTS) * 100
fig, ax = plt.subplots(figsize=(3.5, 2.9))
n = len(SYSTEMS)
for k, s in enumerate(SYSTEMS):
    y = np.arange(len(VARIANTS)) + (k - (n - 1) / 2) * 0.17
    ax.errorbar(mean.loc[s], y, xerr=std.loc[s].fillna(0), fmt="none", ecolor=PALETTE[k], elinewidth=0.9)
    ax.scatter(mean.loc[s], y, s=16, marker=MARKERS[k], color=PALETTE[k], edgecolor="white", linewidth=0.6,
               zorder=3, label=s)
ax.set_yticks(range(len(VARIANTS)), [VN[v] for v in VARIANTS])
ax.invert_yaxis()
ax.set_xlim(0, 100)
ax.set_xlabel("Macro-F1 (%)")
style(ax)
ax.legend(loc="upper center", bbox_to_anchor=(0.42, -0.17), ncol=2, frameon=False, fontsize=7,
          handletextpad=0.3, columnspacing=1.0)
fig.tight_layout()
fig.savefig(OUT / "fig_f1_by_variant.pdf", bbox_inches="tight")

# Hình 2: cơ cấu lỗi (clean, no diacritics)
p = pred.copy()
p["ps"] = p.pred.str.split("/").str[0]
p["pi"] = p.pred.str.split("/").str[-1]
p["kind"] = np.select([p.pred == p.label, p.ps == p.service, p.pi == p.issue],
                      ["Correct", "Wrong issue", "Wrong service"], "Both wrong")
KINDS = ["Correct", "Wrong issue", "Wrong service", "Both wrong"]
KCOL = dict(zip(KINDS, ["#2a78d6", "#eb6834", "#6250d6", "#eda100"]))
err = p.groupby(["variant", "system"]).kind.value_counts(normalize=True).unstack().reindex(columns=KINDS).fillna(0)
show = ["clean", "no_diacritics"]
fig, axes = plt.subplots(len(show), 1, figsize=(3.5, 0.32 * n * len(show) + 0.9), sharex=True)
for ax, v in zip(axes, show):
    d = err.loc[v].reindex(SYSTEMS) * 100
    left = np.zeros(n)
    for kd in KINDS:
        w = d[kd].values
        ax.barh(range(n), w, left=left, color=KCOL[kd], edgecolor="white", linewidth=1, height=0.72,
                label=kd if v == show[0] else None)
        for i, (l, ww) in enumerate(zip(left, w)):
            if ww >= 9:
                ax.text(l + ww / 2, i, f"{ww:.0f}", ha="center", va="center", fontsize=6.5,
                        color="white" if kd in ("Correct", "Wrong service") else INK)
        left += w
    ax.set_yticks(range(n), SYSTEMS)
    ax.invert_yaxis()
    ax.set_title(VN[v], loc="left", fontsize=8)
    ax.set_xlim(0, 100)
    style(ax)
axes[-1].set_xlabel("Share of test predictions (%)")
fig.legend(loc="lower center", ncol=4, frameon=False, fontsize=7, bbox_to_anchor=(0.5, -0.03),
           handlelength=1.2, columnspacing=0.8)
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.savefig(OUT / "fig_error_types.pdf", bbox_inches="tight")
print("Đã lưu:", *sorted(x.name for x in OUT.iterdir()))
