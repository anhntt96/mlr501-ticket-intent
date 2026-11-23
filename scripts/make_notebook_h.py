"""Sinh notebooks/H_rq2_analysis.ipynb: phân tích RQ2 (clean vs aug) từ results/R2_*_metrics.csv và *_predictions.csv.
Chạy: python3 scripts/make_notebook_h.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cells = []


def md(s):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)})


def code(s):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                  "source": s.strip("\n").splitlines(keepends=True)})


md("""
# Bước H – Phân tích RQ2: tăng cường câu bỏ dấu

Đọc `results/R2_*` (từ notebook F và G) và trả lời đúng 2 câu hỏi thầy đặt ra, cho từng mô hình:
1. **Mức tăng** macro-F1 trên ticket **không dấu** khi huấn luyện có câu bỏ dấu (`aug`) so với chỉ câu sạch (`clean`).
2. **Mức thay đổi** macro-F1 trên ticket **có dấu** (tăng cường có làm hại câu có dấu không).

Cả hai đo trên test tổng hợp và test **do người viết** (nếu có). Mỗi mức thay đổi kèm khoảng tin cậy 95% (bootstrap ghép cặp).
Kết quả: `results/R2_summary.md`, `results/R2_fig_gain.png`. Không cần GPU.
""")

md("## 1. Đọc kết quả")
code("""
import os, glob, zipfile, json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

if os.path.basename(os.getcwd()) == "notebooks":
    os.chdir("..")
RESULTS_DIR = "results"
if not glob.glob(f"{RESULTS_DIR}/R2_*_metrics.csv"):
    from google.colab import files
    for name in files.upload():              # chọn các file results_R2_*.zip
        zipfile.ZipFile(name).extractall(".")

mets, preds = [], []
for f in sorted(glob.glob(f"{RESULTS_DIR}/R2_*_metrics.csv")):
    mets.append(pd.read_csv(f))
    preds.append(pd.read_csv(f.replace("_metrics.csv", "_predictions.csv")))
res, pred = pd.concat(mets, ignore_index=True), pd.concat(preds, ignore_index=True)


def system(model, mode):
    return model if mode == "lora" else f"{model} ({mode})"


for df in (res, pred):
    df["system"] = [system(a, b) for a, b in zip(df.model, df["mode"])]
AUG = sorted(t for t in res.train.unique() if t != "clean")
assert len(AUG) == 1, f"Cần đúng 1 chế độ aug, đang có {AUG}"
AUG = AUG[0]
ORDER = ["PhoBERT-base (hier)", "PhoBERT-base (flat)", "XLM-R-base (hier)", "XLM-R-base (flat)",
         "Qwen2.5-1.5B+LoRA", "Qwen2.5-3B+LoRA"]
SYSTEMS = [s for s in ORDER if s in set(res.system)] + sorted(set(res.system) - set(ORDER))
HAS_HUMAN = "human_nodiac" in set(res.variant)
EVALS = ["no_diacritics", "clean"] + (["human_nodiac", "human_nodiac_rule", "human_clean"] if HAS_HUMAN else [])
NAME = {"no_diacritics": "Test tổng hợp – không dấu", "clean": "Test tổng hợp – có dấu",
        "human_nodiac": "Người viết – gõ không dấu", "human_nodiac_rule": "Người viết – bỏ dấu bằng quy tắc",
        "human_clean": "Người viết – có dấu"}
print("Hệ thống:", SYSTEMS, "| chế độ tăng cường:", AUG, "| có test người viết:", HAS_HUMAN)
print(res.groupby(["system", "train"]).seed.nunique().unstack().to_string())
""")

md("""
## 2. Bảng chính – mức tăng / thay đổi theo từng seed
`gain` = F1(aug) − F1(clean) tính trên **cùng seed**, rồi lấy trung bình ± độ lệch của 3 seed.
""")
code("""
pd.set_option("display.precision", 1)
w = (res[res.variant.isin(EVALS)].pivot_table(index=["system", "variant", "seed"], columns="train", values="f1") * 100)
w["gain"] = w[AUG] - w["clean"]
g = w.groupby(["system", "variant"]).agg(clean=("clean", "mean"), aug=(AUG, "mean"),
                                         gain=("gain", "mean"), gain_sd=("gain", "std"))
g = g.reindex(pd.MultiIndex.from_product([SYSTEMS, EVALS], names=["system", "variant"])).dropna(how="all")
g
""")

md("""
## 3. Khoảng tin cậy 95% (bootstrap ghép cặp)
Lấy mẫu lại các ticket test có hoàn lại 2.000 lần; trên mỗi mẫu tính F1 (TB 3 seed) của 2 chế độ **trên cùng các ticket**, lấy hiệu.
Khoảng không chứa 0 → thay đổi có ý nghĩa.
""")
code("""
B, rng = 2000, np.random.default_rng(0)
LABELS = sorted(set(pred.label))
L2I = {l: i for i, l in enumerate(LABELS)}
K = len(LABELS)


def macro_f1(t, q):
    tp = np.bincount(t[t == q], minlength=K + 1)[:K]
    tc = np.bincount(t, minlength=K + 1)[:K]
    pc = np.bincount(q, minlength=K + 1)[:K]
    m = (tc + pc) > 0
    return (2 * tp[m] / (tc + pc)[m]).mean()


rows = []
for (s, v), d in pred[pred.variant.isin(EVALS)].groupby(["system", "variant"]):
    ids = sorted(d.id.unique())
    r = {i: k for k, i in enumerate(ids)}
    truth = d.drop_duplicates("id").set_index("id").label.map(L2I).reindex(ids).values
    arr = {}
    for (tr, sd), x in d.groupby(["train", "seed"]):
        a = np.full(len(ids), K)
        a[x.id.map(r).values] = x.pred.map(L2I).fillna(K).astype(int).values
        arr.setdefault(tr, []).append(a)
    if "clean" not in arr or AUG not in arr:
        continue
    samp = rng.integers(0, len(ids), size=(B, len(ids)))
    diff = np.array([np.mean([macro_f1(truth[ix], a[ix]) for a in arr[AUG]])
                     - np.mean([macro_f1(truth[ix], a[ix]) for a in arr["clean"]]) for ix in samp]) * 100
    lo, hi = np.percentile(diff, [2.5, 97.5])
    rows.append(dict(system=s, variant=v, ci_low=lo, ci_high=hi, significant=not (lo <= 0 <= hi), n_ticket=len(ids)))
ci = pd.DataFrame(rows).set_index(["system", "variant"])
table = g.join(ci)
table
""")

md("## 4. Biểu đồ – F1 của 2 chế độ huấn luyện\nMỗi hàng là một mô hình; chấm tròn = chỉ câu sạch, hình vuông = có câu bỏ dấu; đoạn nối = mức thay đổi.")
code("""
INK, INK2, GRID, SURF = "#1f1f1e", "#5f5e58", "#e4e3de", "#fcfcfb"
C_CLEAN, C_AUG = "#2a78d6", "#eb6834"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "text.color": INK,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID,
                     "font.size": 10})
panels = [v for v in EVALS if v != "human_nodiac_rule"]
fig, axes = plt.subplots(1, len(panels), figsize=(3.3 * len(panels), 0.5 * len(SYSTEMS) + 1.5), sharey=True)
axes = np.atleast_1d(axes)
for ax, v in zip(axes, panels):
    for k, s in enumerate(SYSTEMS):
        if (s, v) not in g.index:
            continue
        a, b = g.loc[(s, v), "clean"], g.loc[(s, v), "aug"]
        ax.plot([a, b], [k, k], color=GRID, linewidth=3, zorder=1)
        ax.scatter([a], [k], s=50, color=C_CLEAN, marker="o", zorder=3, label="Chỉ câu sạch" if k == 0 else None)
        ax.scatter([b], [k], s=50, color=C_AUG, marker="s", zorder=3, label=f"Có câu bỏ dấu ({AUG})" if k == 0 else None)
        ax.text(max(a, b) + 2, k, f"{b - a:+.1f}", va="center", fontsize=8, color=INK2)
    ax.set_title(NAME[v], loc="left", fontsize=9)
    ax.set_xlim(0, 108)
    ax.grid(axis="x", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.set_xlabel("macro-F1 (%)", fontsize=9)
axes[0].set_yticks(range(len(SYSTEMS)), SYSTEMS)
axes[0].invert_yaxis()
fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0))
fig.tight_layout(rect=(0, 0.1, 1, 1))
fig.savefig(f"{RESULTS_DIR}/R2_fig_gain.png", dpi=200, bbox_inches="tight")
plt.show()
""")

md("## 5. Tác dụng phụ trên các biến thể khác (test tổng hợp)\nTăng cường bỏ dấu có ảnh hưởng tới teencode, Telex, trộn tiếng Anh không?")
code("""
VARIANTS = ["clean", "no_diacritics", "teencode", "telex", "code_switch", "mixed"]
side = (res[res.variant.isin(VARIANTS)].groupby(["system", "train", "variant"]).f1.mean().unstack("variant")
        .reindex(columns=VARIANTS) * 100).round(1)
side = side.reindex(pd.MultiIndex.from_product([SYSTEMS, ["clean", AUG]])).dropna(how="all")
side
""")

md("## 6. Câu không nêu tên dịch vụ (`explicit = 0`) – dữ liệu cho RQ3\nTỉ lệ đoán đúng **service**, gộp các seed.")
code("""
p = pred[pred.variant.isin(["clean", "human_clean", "human_nodiac"])].copy()
p["service_ok"] = p.pred.str.split("/").str[0] == p.service
rq3 = (p.groupby(["system", "train", "variant", "explicit"]).service_ok.mean().unstack("explicit") * 100).round(1)
rq3.columns = [f"explicit={c}" for c in rq3.columns]
rq3["n_ticket explicit=0"] = p[p.explicit == 0].groupby(["system", "train", "variant"]).id.nunique()
rq3
""")

md("## 7. Xuất bảng tổng hợp")
code("""
def to_md(df, index=True):
    d = df.reset_index() if index else df
    head = "| " + " | ".join(map(str, d.columns)) + " |"
    sep = "| " + " | ".join("---" for _ in d.columns) + " |"
    fmt = lambda x: "" if pd.isna(x) else (f"{x:.1f}" if isinstance(x, (float, np.floating)) else str(x))
    return "\\n".join([head, sep] + ["| " + " | ".join(fmt(x) for x in r) + " |" for r in d.itertuples(index=False)])


parts = ["# RQ2 – Tăng cường câu bỏ dấu", "",
         f"Chế độ tăng cường: `{AUG}`. gain = F1(aug) − F1(clean), điểm %, TB ± độ lệch 3 seed; "
         "CI = khoảng tin cậy 95% bootstrap ghép cặp.", "",
         "## Bảng 1. Mức tăng trên câu không dấu và thay đổi trên câu có dấu", "",
         to_md(table.rename(index=NAME, level=1)), "",
         "## Bảng 2. Tất cả biến thể test tổng hợp theo chế độ huấn luyện", "", to_md(side), "",
         "## Bảng 3. Đoán đúng service theo explicit (RQ3)", "", to_md(rq3), "",
         "Số seed: " + res.groupby(["system", "train"]).seed.nunique().to_string().replace("\\n", "; ")]
open(f"{RESULTS_DIR}/R2_summary.md", "w", encoding="utf-8").write("\\n".join(parts))
with zipfile.ZipFile("results_R2_analysis.zip", "w") as z:
    for f in ["R2_summary.md", "R2_fig_gain.png"]:
        z.write(f"{RESULTS_DIR}/{f}", f"results/{f}")
try:
    from google.colab import files
    files.download("results_R2_analysis.zip")
except ImportError:
    print("Đã lưu results/R2_summary.md và results/R2_fig_gain.png")
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python"}, "colab": {"provenance": []}},
      "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks/H_rq2_analysis.ipynb"
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Đã tạo", out.relative_to(ROOT), "-", len(cells), "ô")
