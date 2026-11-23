"""Sinh notebooks/E_compare.ipynb: gộp kết quả B (PhoBERT), C (Qwen + LoRA), D (GPT-4o) thành bảng, biểu đồ, phân tích lỗi.
Chạy: python3 scripts/make_notebook_e.py
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
# Bước E – So sánh các mô hình

Gộp mọi file `results/*_metrics.csv` và `results/*_predictions.csv` (B: PhoBERT, C: Qwen + LoRA, D: GPT-4o) thành:
1. **Bảng chính:** macro-F1 theo mô hình × biến thể (trung bình ± độ lệch giữa các seed) và mức giảm so với câu chuẩn.
2. **Biểu đồ** F1 theo biến thể và cơ cấu lỗi (sai service / sai issue).
3. **Phân tích lỗi:** câu không nêu rõ dịch vụ, cặp hay nhầm, câu mọi mô hình đều sai.
4. **Khoảng tin cậy bootstrap** cho chênh lệch F1 so với mô hình tham chiếu (test chỉ 135 câu nên chênh lệch nhỏ có thể do ngẫu nhiên).

Kết quả lưu vào `results/E_*` (bảng `E_summary.md`, hình `E_fig*.png`). Không cần GPU.

**Trên Colab:** ô 1 hỏi tải lên các file `results_*.zip` (chọn nhiều file một lúc). **Trên máy:** chạy từ thư mục gốc dự án, đọc thẳng `results/`.
""")

md("## 1. Tải kết quả lên")
code("""
import os, glob, zipfile
if os.path.basename(os.getcwd()) == "notebooks":
    os.chdir("..")
USE_DRIVE = False          # True: đọc từ Google Drive (MyDrive/mlr501_results) nếu bước C/D lưu ở đó
RESULTS_DIR = "results"
if USE_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
    RESULTS_DIR = "/content/drive/MyDrive/mlr501_results"
if not glob.glob(f"{RESULTS_DIR}/*_metrics.csv"):
    from google.colab import files
    for name in files.upload():              # chọn các file results_*.zip
        zipfile.ZipFile(name).extractall(".")
print(sorted(f for f in os.listdir(RESULTS_DIR) if f.endswith("_metrics.csv")))
""")

md("## 2. Đọc và gộp kết quả\nMỗi *hệ thống* = mô hình + kiểu (vd PhoBERT flat/hier, GPT-4o zero-shot/few-shot). Bỏ qua file chạy thử (`*_trial_*`).")
code("""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

VARIANTS = ["clean", "no_diacritics", "teencode", "telex", "code_switch", "mixed"]
VN = {"clean": "Chuẩn", "no_diacritics": "Bỏ dấu", "teencode": "Teencode", "telex": "Telex lỗi",
      "code_switch": "Trộn tiếng Anh", "mixed": "Trộn cả 3"}
ORDER = ["PhoBERT-base (flat)", "PhoBERT-base (hier)", "Qwen2.5-1.5B+LoRA", "Qwen2.5-3B+LoRA",
         "GPT-4o zero-shot", "GPT-4o few-shot"]


def system(model, mode):
    if model == "PhoBERT":
        return f"PhoBERT-base ({mode})"
    if model == "GPT-4o":
        return "GPT-4o " + mode.replace("_", "-")
    return model


mets, preds = [], []
for f in sorted(glob.glob(f"{RESULTS_DIR}/*_metrics.csv")):
    if "_trial_" in f or os.path.basename(f).startswith("R2_"):   # R2_*: thí nghiệm RQ2, phân tích ở notebook H
        continue
    m = pd.read_csv(f)
    mets.append(m)
    pf = f.replace("_metrics.csv", "_predictions.csv")
    if os.path.exists(pf):
        p = pd.read_csv(pf)
        if "model" not in p:                      # file của bước B không có cột model
            p["model"] = m.model.iloc[0]
        preds.append(p)
res = pd.concat(mets, ignore_index=True)
pred = pd.concat(preds, ignore_index=True)
res, pred = res[res.variant.isin(VARIANTS)], pred[pred.variant.isin(VARIANTS)]
for df in (res, pred):
    df["system"] = [system(a, b) for a, b in zip(df.model, df["mode"])]
if "invalid" not in res:
    res["invalid"] = 0.0
res["invalid"] = res["invalid"].fillna(0.0)
SYSTEMS = [s for s in ORDER if s in set(res.system)] + sorted(set(res.system) - set(ORDER))
print("Hệ thống:", SYSTEMS)
print(res.groupby("system").seed.nunique().rename("số seed/lần chạy").reindex(SYSTEMS).to_string())
""")

md("## 3. Bảng chính – macro-F1 nhãn đầy đủ (45 nhãn)\nGiá trị = trung bình ± độ lệch chuẩn giữa các seed (GPT-4o chỉ 1 lần chạy nên không có ±). Cột **TB nhiễu** = trung bình 5 biến thể không chuẩn.")
code("""
def fmt(mu, sd):
    return f"{mu:.3f}" if pd.isna(sd) else f"{mu:.3f} ± {sd:.3f}"


g = res.groupby(["system", "variant"]).f1
mean = g.mean().unstack().reindex(index=SYSTEMS, columns=VARIANTS)
std = g.std().unstack().reindex(index=SYSTEMS, columns=VARIANTS)
noisy = res[res.variant != "clean"].groupby(["system", "seed"]).f1.mean().groupby("system")
table_main = pd.DataFrame({VN[v]: [fmt(mean.loc[s, v], std.loc[s, v]) for s in SYSTEMS] for v in VARIANTS}, index=SYSTEMS)
table_main["TB nhiễu"] = [fmt(noisy.mean()[s], noisy.std()[s]) for s in SYSTEMS]
table_main
""")
code("""
# Mức giảm so với câu chuẩn (âm = giảm) và tỉ lệ giữ lại điểm
drop = mean.sub(mean["clean"], axis=0).drop(columns="clean").rename(columns=VN).round(3)
keep = (mean.div(mean["clean"], axis=0) * 100).drop(columns="clean").rename(columns=VN).round(0)
print("Mức giảm F1 so với câu chuẩn:"); display(drop)
print("Giữ lại bao nhiêu % điểm câu chuẩn:"); display(keep)
""")
code("""
# Chi tiết trên câu chuẩn và câu bỏ dấu: accuracy, F1 service, F1 issue, tỉ lệ đầu ra không hợp lệ
cols = ["acc", "f1", "f1_service", "f1_issue", "invalid"]
table_detail = (res[res.variant.isin(["clean", "no_diacritics"])]
                .groupby(["variant", "system"])[cols].mean().round(3)
                .reindex(pd.MultiIndex.from_product([["clean", "no_diacritics"], SYSTEMS]))
                .dropna(how="all"))
table_detail
""")

md("""
## 4. Biểu đồ 1 – F1 theo biến thể
Mỗi hàng là một biến thể, mỗi điểm là một hệ thống (màu + hình dạng riêng); thanh ngang mảnh = ± 1 độ lệch chuẩn giữa các seed.
""")
code("""
INK, INK2, GRID, SURF = "#1f1f1e", "#5f5e58", "#e4e3de", "#fcfcfb"
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]  # thứ tự cố định
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
COLOR = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(SYSTEMS)}
MARK = {s: MARKERS[i % len(MARKERS)] for i, s in enumerate(SYSTEMS)}
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
                     "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.edgecolor": GRID, "font.size": 10})


def style(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


fig, ax = plt.subplots(figsize=(8, 5.2))
n = len(SYSTEMS)
for k, s in enumerate(SYSTEMS):
    y = np.arange(len(VARIANTS)) + (k - (n - 1) / 2) * 0.14
    x, e = mean.loc[s].values, std.loc[s].fillna(0).values
    ax.errorbar(x, y, xerr=e, fmt="none", ecolor=COLOR[s], elinewidth=1.2, capsize=0)
    ax.scatter(x, y, s=50, marker=MARK[s], color=COLOR[s], edgecolor=SURF, linewidth=1, zorder=3, label=s)
ax.set_yticks(range(len(VARIANTS)), [VN[v] for v in VARIANTS])
ax.invert_yaxis()
ax.set_xlim(0, 1)
ax.set_xlabel("macro-F1 (45 nhãn)")
style(ax)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=min(3, n), frameon=False)
ax.set_title("F1 trên tập test theo biến thể (train chỉ bằng câu chuẩn)", loc="left", fontsize=11)
fig.tight_layout()
fig.savefig(f"{RESULTS_DIR}/E_fig1_f1_by_variant.png", dpi=200)
plt.show()
""")

md("""
## 5. Biểu đồ 2 – Cơ cấu lỗi
Mỗi dự đoán thuộc 1 trong 4 loại: **đúng**, **sai issue** (đúng dịch vụ), **sai service** (đúng loại vấn đề), **sai cả hai**. Gộp mọi seed.
Giúp trả lời: mô hình yếu vì nhận sai *dịch vụ* hay sai *loại vấn đề*?
""")
code("""
p = pred.copy()
p["ps"] = p.pred.str.split("/").str[0]
p["pi"] = p.pred.str.split("/").str[-1]
p["kind"] = np.select([p.pred == p.label, p.ps == p.service, p.pi == p.issue],
                      ["Đúng", "Sai issue", "Sai service"], "Sai cả hai")
KINDS = ["Đúng", "Sai issue", "Sai service", "Sai cả hai"]
KCOL = dict(zip(KINDS, ["#2a78d6", "#eb6834", "#6250d6", "#eda100"]))
err = (p.groupby(["variant", "system"]).kind.value_counts(normalize=True).unstack().reindex(columns=KINDS).fillna(0))

show = ["clean", "no_diacritics", "telex"]
fig, axes = plt.subplots(1, len(show), figsize=(12, 0.45 * len(SYSTEMS) + 1.6), sharey=True)
for ax, v in zip(axes, show):
    d = err.loc[v].reindex(SYSTEMS)
    left = np.zeros(len(d))
    for kd in KINDS:
        w = d[kd].values
        ax.barh(range(len(d)), w, left=left, color=KCOL[kd], edgecolor=SURF, linewidth=2, height=0.7,
                label=kd if v == show[0] else None)
        for i, (l, ww) in enumerate(zip(left, w)):
            if ww >= 0.08:
                ax.text(l + ww / 2, i, f"{ww:.0%}", ha="center", va="center", fontsize=8,
                        color="white" if kd in ("Đúng", "Sai service") else INK)
        left += w
    ax.set_title(VN[v], loc="left", fontsize=10)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
    style(ax)
axes[0].set_yticks(range(len(SYSTEMS)), SYSTEMS)
axes[0].invert_yaxis()
fig.legend(loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.06, 1, 1))
fig.savefig(f"{RESULTS_DIR}/E_fig2_error_types.png", dpi=200, bbox_inches="tight")
plt.show()
err.round(3)
""")

md("## 6. Câu không nêu rõ dịch vụ (`explicit = 0`)\nTỉ lệ đoán đúng **service** trên câu chuẩn, gộp mọi seed. Lưu ý: test chỉ có ít câu `explicit=0` (cột `n_câu`).")
code("""
c = p[p.variant == "clean"].assign(service_ok=lambda d: d.ps == d.service)
table_explicit = c.groupby(["system", "explicit"]).service_ok.mean().unstack().reindex(SYSTEMS).round(3)
table_explicit.columns = [f"explicit={k}" for k in table_explicit.columns]
table_explicit["n_câu explicit=0"] = c[c.explicit == 0].id.nunique()
table_explicit
""")

md("## 7. Cặp hay nhầm nhất (câu chuẩn)\nTop 5 mỗi hệ thống, đếm gộp mọi seed.")
code("""
wrong = p[(p.variant == "clean") & (p.pred != p.label)]
conf = (wrong.groupby(["system", "label", "pred"]).size().rename("lần").reset_index()
        .sort_values(["system", "lần"], ascending=[True, False]).groupby("system").head(5))
conf["system"] = pd.Categorical(conf.system, SYSTEMS)
conf.sort_values(["system", "lần"], ascending=[True, False]).reset_index(drop=True)
""")

md("## 8. Câu khó: hệ thống nào cũng sai (câu chuẩn)\nMột hệ thống \"sai\" một câu nếu sai ở quá nửa số seed. Những câu này đáng đọc lại: có thể nhãn mơ hồ hoặc gán nhãn sai.")
code("""
cc = p[p.variant == "clean"].assign(ok=lambda d: d.pred == d.label)
vote = cc.groupby(["id", "system"]).ok.mean().unstack()
hard_ids = vote.index[(vote < 0.5).all(axis=1)]
top = (cc[cc.id.isin(hard_ids)].groupby(["id", "system"]).pred.agg(lambda s: s.value_counts().index[0])
       .unstack().reindex(columns=SYSTEMS))
info = cc.drop_duplicates("id").set_index("id")[["text", "label", "explicit"]]
hard = info.loc[hard_ids].join(top)
print(len(hard), "câu mọi hệ thống đều sai")
hard
""")

md("""
## 9. Chênh lệch có ý nghĩa không? (bootstrap ghép cặp)
Lấy mẫu lại 135 câu test có hoàn lại (2.000 lần), tính chênh lệch macro-F1 của mỗi hệ thống so với **hệ thống tham chiếu** (mặc định PhoBERT hier).
Hệ thống nhiều seed → F1 trung bình các seed trên cùng mẫu. Nếu khoảng tin cậy 95% chứa 0 → chưa đủ bằng chứng kết luận hơn/kém.
""")
code("""
REF = "PhoBERT-base (hier)" if "PhoBERT-base (hier)" in SYSTEMS else SYSTEMS[0]
B, rng = 2000, np.random.default_rng(0)
LABELS = sorted(set(pred.label))
L2I = {l: i for i, l in enumerate(LABELS)}
K = len(LABELS)
ids = sorted(pred.id.unique())
I2R = {i: r for r, i in enumerate(ids)}
truth = pred.drop_duplicates("id").set_index("id").label.map(L2I).reindex(ids).values


def macro_f1(t, q):
    tp = np.bincount(t[t == q], minlength=K + 1)[:K]
    tc = np.bincount(t, minlength=K + 1)[:K]
    pc = np.bincount(q, minlength=K + 1)[:K]
    m = (tc + pc) > 0
    return (2 * tp[m] / (tc + pc)[m]).mean()


arr = {}   # (system, variant) -> mảng [số seed, số câu] chỉ số nhãn dự đoán (K = INVALID)
for (s, v, sd), d in pred.groupby(["system", "variant", "seed"]):
    a = np.full(len(ids), K)
    a[d.id.map(I2R).values] = d.pred.map(L2I).fillna(K).astype(int).values
    arr.setdefault((s, v), []).append(a)
arr = {k: np.array(v) for k, v in arr.items()}
samples = rng.integers(0, len(ids), size=(B, len(ids)))

rows = []
for v in VARIANTS:
    if (REF, v) not in arr:
        continue
    ref_b = np.array([np.mean([macro_f1(truth[ix], a[ix]) for a in arr[(REF, v)]]) for ix in samples])
    for s in SYSTEMS:
        if s == REF or (s, v) not in arr:
            continue
        sb = np.array([np.mean([macro_f1(truth[ix], a[ix]) for a in arr[(s, v)]]) for ix in samples])
        dlt = sb - ref_b
        lo, hi = np.percentile(dlt, [2.5, 97.5])
        rows.append(dict(variant=VN[v], system=s, delta=dlt.mean(), ci_low=lo, ci_high=hi,
                         significant=not (lo <= 0 <= hi)))
table_boot = pd.DataFrame(rows).round(3)
print("Tham chiếu:", REF)
table_boot
""")

md("## 10. Xuất bảng tổng hợp và tải về\n`E_summary.md` chứa mọi bảng ở trên (dán được vào báo cáo); kèm 2 hình PNG.")
code("""
def to_md(df, index=True):
    d = df.reset_index() if index else df
    head = "| " + " | ".join(map(str, d.columns)) + " |"
    sep = "| " + " | ".join("---" for _ in d.columns) + " |"
    body = ["| " + " | ".join("" if pd.isna(x) else str(x) for x in r) + " |" for r in d.itertuples(index=False)]
    return "\\n".join([head, sep, *body])


parts = [
    "# Kết quả so sánh mô hình", "",
    "## Bảng 1. macro-F1 nhãn đầy đủ (TB ± độ lệch giữa seed)", "", to_md(table_main.rename_axis("Hệ thống")), "",
    "## Bảng 2. Mức giảm F1 so với câu chuẩn", "", to_md(drop.rename_axis("Hệ thống")), "",
    "## Bảng 3. Giữ lại % điểm câu chuẩn", "", to_md(keep.rename_axis("Hệ thống")), "",
    "## Bảng 4. Chi tiết (câu chuẩn, bỏ dấu)", "", to_md(table_detail.rename_axis(["Biến thể", "Hệ thống"])), "",
    "## Bảng 5. Cơ cấu lỗi", "", to_md(err.round(3).rename_axis(["Biến thể", "Hệ thống"])), "",
    "## Bảng 6. Đoán đúng service theo explicit (câu chuẩn)", "", to_md(table_explicit.rename_axis("Hệ thống")), "",
    "## Bảng 7. Cặp nhầm nhiều nhất (câu chuẩn)", "", to_md(conf, index=False), "",
    f"## Bảng 8. Câu mọi hệ thống đều sai ({len(hard)} câu)", "", to_md(hard), "",
    f"## Bảng 9. Bootstrap: chênh lệch F1 so với {REF} (CI 95%)", "", to_md(table_boot, index=False), "",
    "Số seed / lần chạy: " + ", ".join(f"{s}: {n}" for s, n in res.groupby('system').seed.nunique().reindex(SYSTEMS).items()),
]
open(f"{RESULTS_DIR}/E_summary.md", "w", encoding="utf-8").write("\\n".join(parts))
pd.DataFrame({"mean": mean.stack(), "std": std.stack()}).to_csv(f"{RESULTS_DIR}/E_f1_table.csv")

with zipfile.ZipFile("results_E_compare.zip", "w") as z:
    for f in os.listdir(RESULTS_DIR):
        if f.startswith("E_"):
            z.write(f"{RESULTS_DIR}/{f}", f"results/{f}")
try:
    from google.colab import files
    files.download("results_E_compare.zip")
except ImportError:
    print("Đã lưu vào", RESULTS_DIR)
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python"}, "colab": {"provenance": []}},
      "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks/E_compare.ipynb"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Đã tạo", out.relative_to(ROOT), "-", len(cells), "ô")
