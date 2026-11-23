"""Sinh notebooks/F_rq2_encoders.ipynb: RQ2 cho encoder (PhoBERT, XLM-R) – huấn luyện chỉ câu sạch vs có tăng cường câu bỏ dấu.
Chạy: python3 scripts/make_notebook_f.py
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
# Bước F – RQ2 với encoder: tăng cường câu bỏ dấu có giúp không?

**Câu hỏi (RQ2):** huấn luyện thêm câu bỏ dấu có giúp mô hình xử lý ticket không dấu không, và có làm giảm điểm trên ticket có dấu không?

**Hai chế độ huấn luyện** (so sánh trên cùng mô hình, cùng seed):
- `clean`: mỗi epoch dùng 630 câu train có dấu.
- `aug`: mỗi epoch vẫn 630 câu, nhưng mỗi câu có xác suất `aug_ratio` (mặc định 50%) được **thay** bằng bản bỏ dấu của chính nó. Không thêm câu mới → **số bước huấn luyện bằng nhau** giữa 2 chế độ.

Chọn epoch theo macro-F1 trên val **có dấu** ở cả 2 chế độ (cùng một quy tắc). Đo trên:
- tập test tổng hợp (135 câu × 6 biến thể),
- tập test **do người viết** `data/human_test/human_test.csv` (nếu có): bản có dấu, bản người gõ không dấu, bản bỏ dấu bằng quy tắc.

Mô hình: **PhoBERT-base** (cần tách từ) và **XLM-RoBERTa-base** (Transformer đa ngôn ngữ, không cần tách từ). Mặc định 20 epoch (bước B dùng 10 epoch và chưa hội tụ).

**Chạy trên Colab:** Runtime → T4 GPU → Run all → tải `mlr501_data.zip` lên. 2 mô hình × 2 chế độ × 3 seed = 12 lần chạy, ước tính 30–60 phút. Kết quả lưu sau **mỗi lần chạy**; bật `USE_DRIVE` để không mất khi Colab ngắt, chạy lại sẽ bỏ qua lần đã xong.
""")

md("## 1. Cài thư viện")
code("""
!pip -q install underthesea
""")

md("## 2. Tải dữ liệu lên")
code("""
import os, zipfile
if os.path.basename(os.getcwd()) == "notebooks":
    os.chdir("..")
if not os.path.exists("data/superapp/dataset_all.csv"):
    try:
        from google.colab import files
        up = files.upload()                      # chọn mlr501_data.zip
        zipfile.ZipFile(next(iter(up))).extractall(".")
    except ImportError:
        raise SystemExit("Không phải Colab: chạy notebook từ thư mục gốc dự án.")
HUMAN = "data/human_test/human_test.csv"
print("Có tập test do người viết:", os.path.exists(HUMAN))
""")

md("## 3. Nơi lưu kết quả")
code("""
USE_DRIVE = False
RESULTS_DIR = "results"
if USE_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
    RESULTS_DIR = "/content/drive/MyDrive/mlr501_results"
os.makedirs(RESULTS_DIR, exist_ok=True)
print("Lưu kết quả vào:", RESULTS_DIR)
""")

md("## 4. Cấu hình")
code("""
import json, math, random, time, unicodedata
import numpy as np, pandas as pd, torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
from sklearn.metrics import accuracy_score, f1_score

CFG = dict(
    models=[
        dict(name="PhoBERT-base", hf="vinai/phobert-base-v2", segment=True, lr=2e-5),
        dict(name="XLM-R-base", hf="FacebookAI/xlm-roberta-base", segment=False, lr=3e-5),
    ],
    modes=["hier"],            # đầu ra 2 tầng (service + issue); thêm "flat" nếu muốn
    train_modes=["clean", "aug"],
    aug_ratio=0.5,             # tỉ lệ câu train được thay bằng bản bỏ dấu mỗi epoch
    epochs=20,
    batch_size=16,
    max_len=96,
    warmup_ratio=0.1,
    seeds=[42, 43, 44],
)
TAG = "R2_encoders"
VARIANTS = ["clean", "no_diacritics", "teencode", "telex", "code_switch", "mixed"]
HVARIANTS = ["human_clean", "human_nodiac", "human_nodiac_rule"]
device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
print("device:", device, "| aug_ratio:", CFG["aug_ratio"])
""")

md("## 5. Đọc dữ liệu")
code("""
schema = json.load(open("labels/label_schema.json", encoding="utf-8"))
SERVICES = list(schema["services"])
ISSUES = list(schema["issues"])
PAIRS = sorted(f"{s}/{i}" for i, v in schema["issues"].items() for s in v["services"])
s2id = {s: k for k, s in enumerate(SERVICES)}
i2id = {s: k for k, s in enumerate(ISSUES)}
p2id = {s: k for k, s in enumerate(PAIRS)}
PAIR_S = torch.tensor([s2id[p.split("/")[0]] for p in PAIRS])
PAIR_I = torch.tensor([i2id[p.split("/")[1]] for p in PAIRS])

wide = pd.read_csv("data/superapp/dataset_all.csv")
train_w = wide[wide.split == "train"].reset_index(drop=True)       # 630 câu, có cả cột clean và no_diacritics
val_df = wide[wide.split == "val"].assign(variant="clean", text=lambda d: d.clean).reset_index(drop=True)
test_df = (wide[wide.split == "test"].melt(id_vars=["id", "split", "service", "issue", "label", "explicit"],
                                           value_vars=VARIANTS, var_name="variant", value_name="text"))
EVAL = {v: test_df[test_df.variant == v].reset_index(drop=True) for v in VARIANTS}

if os.path.exists(HUMAN):
    h = pd.read_csv(HUMAN)
    assert set(h.label) <= set(PAIRS), "human_test.csv có nhãn không hợp lệ"
    for v, col in zip(HVARIANTS, ["text", "text_nodiac", "text_nodiac_rule"]):
        EVAL[v] = h.assign(variant=v, text=h[col])[["id", "service", "issue", "label", "explicit", "variant", "text"]]
print("train", len(train_w), "| val", len(val_df), "| tập đánh giá:", {k: len(v) for k, v in EVAL.items()})
""")

md("""
## 6. Mô hình và hàm phụ
Giống bước B: vector của token đầu → đầu ra `flat` (45 nhãn) hoặc `hier` (9 service + 26 issue, chỉ chọn trong 45 cặp hợp lệ).
""")
code("""
class Classifier(nn.Module):
    def __init__(self, name, mode):
        super().__init__()
        self.mode = mode
        self.encoder = AutoModel.from_pretrained(name)
        h = self.encoder.config.hidden_size
        self.drop = nn.Dropout(0.1)
        if mode == "flat":
            self.head = nn.Linear(h, len(PAIRS))
        else:
            self.head_s = nn.Linear(h, len(SERVICES))
            self.head_i = nn.Linear(h, len(ISSUES))

    def forward(self, input_ids, attention_mask):
        x = self.drop(self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0])
        if self.mode == "flat":
            return {"pair": self.head(x)}
        return {"service": self.head_s(x), "issue": self.head_i(x)}


_seg_cache = {}
def make_seg(segment):
    if not segment:
        return lambda t: t
    from underthesea import word_tokenize
    def seg(t):
        if t not in _seg_cache:
            _seg_cache[t] = word_tokenize(t, format="text")
        return _seg_cache[t]
    return seg


def encode(tok, seg, texts):
    e = tok([seg(t) for t in texts], truncation=True, max_length=CFG["max_len"], padding="max_length",
            return_tensors="pt")
    return e["input_ids"], e["attention_mask"]


def labels_of(df):
    return (torch.tensor(df.label.map(p2id).values), torch.tensor(df.service.map(s2id).values),
            torch.tensor(df.issue.map(i2id).values))


@torch.no_grad()
def predict(model, ids, mask):
    model.eval()
    out = []
    for b in range(0, len(ids), 64):
        o = model(ids[b:b + 64].to(device), mask[b:b + 64].to(device))
        if model.mode == "flat":
            out.append(o["pair"].argmax(-1).cpu())
        else:
            ls, li = o["service"].log_softmax(-1).cpu(), o["issue"].log_softmax(-1).cpu()
            out.append((ls[:, PAIR_S] + li[:, PAIR_I]).argmax(-1))
    return [PAIRS[k] for k in torch.cat(out).tolist()]


def metrics(df, pred):
    ps = [p.split("/")[0] for p in pred]
    pi = [p.split("/")[1] for p in pred]
    return dict(acc=accuracy_score(df.label, pred),
                f1=f1_score(df.label, pred, labels=PAIRS, average="macro", zero_division=0),
                f1_service=f1_score(df.service, ps, labels=SERVICES, average="macro", zero_division=0),
                f1_issue=f1_score(df.issue, pi, labels=ISSUES, average="macro", zero_division=0))


def set_seed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(s)
""")

md("""
## 7. Huấn luyện một lần chạy
Mỗi epoch: chọn ngẫu nhiên (theo seed) `aug_ratio` câu train để dùng bản bỏ dấu (chế độ `aug`), còn lại dùng bản có dấu.
Số câu mỗi epoch luôn là 630 → số bước như nhau ở 2 chế độ.
""")
code("""
def train_one(m, mode, train_mode, seed, D):
    set_seed(seed)
    model = Classifier(m["hf"], mode).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=m["lr"], weight_decay=0.01)
    n = len(train_w)
    steps_per_ep = math.ceil(n / CFG["batch_size"])
    total = steps_per_ep * CFG["epochs"]
    sch = get_linear_schedule_with_warmup(opt, int(total * CFG["warmup_ratio"]), total)
    ce = nn.CrossEntropyLoss()
    rng = np.random.default_rng(seed)
    best = (-1, None, 0)
    for ep in range(1, CFG["epochs"] + 1):
        use_nd = rng.random(n) < (CFG["aug_ratio"] if train_mode == "aug" else 0.0)
        u = torch.tensor(use_nd)[:, None]
        ids = torch.where(u, D["tr_nd"][0], D["tr_cl"][0])
        mask = torch.where(u, D["tr_nd"][1], D["tr_cl"][1])
        g = torch.Generator().manual_seed(seed * 1000 + ep)
        loader = DataLoader(TensorDataset(ids, mask, *D["tr_y"]), batch_size=CFG["batch_size"], shuffle=True,
                            generator=g)
        model.train()
        tot = 0.0
        for bi, bm, yp, ys, yi in loader:
            o = model(bi.to(device), bm.to(device))
            loss = (ce(o["pair"], yp.to(device)) if mode == "flat"
                    else ce(o["service"], ys.to(device)) + ce(o["issue"], yi.to(device)))
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sch.step()
            tot += loss.item()
        vf = metrics(val_df, predict(model, *D["val"]))["f1"]
        if ep % 5 == 0 or ep == 1:
            print(f"    epoch {ep:2d} loss={tot / len(loader):.3f} val_f1={vf:.3f} (câu bỏ dấu: {use_nd.mean():.0%})")
        if vf > best[0]:
            best = (vf, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}, ep)
    model.load_state_dict(best[1])
    print(f"    -> chọn epoch {best[2]} (val_f1={best[0]:.3f})")
    return model, best[2]
""")

md("## 8. Chạy thực nghiệm\nGhi kết quả sau **mỗi lần chạy**; chạy lại ô này sẽ bỏ qua lần đã có.")
code("""
MET = f"{RESULTS_DIR}/{TAG}_metrics.csv"
PRED = f"{RESULTS_DIR}/{TAG}_predictions.csv"
done = set()
if os.path.exists(MET):
    done = set(map(tuple, pd.read_csv(MET)[["model", "mode", "train", "seed"]].drop_duplicates().values.tolist()))
TRAIN_TAG = {"clean": "clean", "aug": f"aug{int(CFG['aug_ratio'] * 100)}"}

for m in CFG["models"]:
    tok = AutoTokenizer.from_pretrained(m["hf"])
    seg = make_seg(m["segment"])
    D = {"tr_cl": encode(tok, seg, train_w.clean), "tr_nd": encode(tok, seg, train_w.no_diacritics),
         "tr_y": labels_of(train_w), "val": encode(tok, seg, val_df.text)}
    E = {v: encode(tok, seg, d.text) for v, d in EVAL.items()}
    for mode in CFG["modes"]:
        for tm in CFG["train_modes"]:
            for seed in CFG["seeds"]:
                key = (m["name"], mode, TRAIN_TAG[tm], seed)
                if key in done:
                    print("bỏ qua (đã có):", key); continue
                print("==", key)
                t0 = time.time()
                model, best_ep = train_one(m, mode, tm, seed, D)
                rows, preds = [], []
                for v, d in EVAL.items():
                    p = predict(model, *E[v])
                    rows.append(dict(model=m["name"], mode=mode, train=TRAIN_TAG[tm], seed=seed, variant=v,
                                     best_epoch=best_ep, **metrics(d, p)))
                    preds.append(d.assign(pred=p, model=m["name"], mode=mode, train=TRAIN_TAG[tm], seed=seed))
                pd.DataFrame(rows).to_csv(MET, mode="a", header=not os.path.exists(MET), index=False)
                pd.concat(preds).to_csv(PRED, mode="a", header=not os.path.exists(PRED), index=False)
                r = {x["variant"]: round(x["f1"], 3) for x in rows}
                print(f"   xong {time.time() - t0:.0f}s | clean {r['clean']} | no_diacritics {r['no_diacritics']}"
                      + (f" | human_nodiac {r['human_nodiac']}" if "human_nodiac" in r else ""))
                del model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
res = pd.read_csv(MET)
""")

md("## 9. Xem nhanh\nmacro-F1 (TB 3 seed). Cột `gain` = aug − clean. Phân tích đầy đủ (khoảng tin cậy, biểu đồ) ở notebook H.")
code("""
pd.set_option("display.precision", 3)
show = [v for v in ["clean", "no_diacritics", "human_clean", "human_nodiac", "human_nodiac_rule"] if v in set(res.variant)]
t = res[res.variant.isin(show)].groupby(["model", "mode", "variant", "train"]).f1.mean().unstack("train")
t["gain"] = t[TRAIN_TAG["aug"]] - t["clean"]
t
""")

md("## 10. Lưu cấu hình và tải kết quả về")
code("""
json.dump({**CFG, "device": device, "human_test": os.path.exists(HUMAN)},
          open(f"{RESULTS_DIR}/{TAG}_config.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
zname = f"results_{TAG}.zip"
with zipfile.ZipFile(zname, "w") as z:
    for f in os.listdir(RESULTS_DIR):
        if f.startswith(TAG + "_"):
            z.write(f"{RESULTS_DIR}/{f}", f"results/{f}")
try:
    from google.colab import files
    files.download(zname)
except ImportError:
    print("Đã lưu vào", RESULTS_DIR)
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python"}, "accelerator": "GPU",
                                   "colab": {"provenance": [], "gpuType": "T4"}},
      "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks/F_rq2_encoders.ipynb"
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Đã tạo", out.relative_to(ROOT), "-", len(cells), "ô")
