"""Sinh notebooks/B_phobert.ipynb (chạy trên Google Colab hoặc máy có PyTorch).
Chạy: python3 scripts/make_notebook_b.py
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
# Bước B – Baseline PhoBERT cho phân loại ticket CSKH super-app

**Mục tiêu:** fine-tune PhoBERT trên câu **chuẩn** (clean) rồi đo trên tập test ở **6 biến thể** (chuẩn, bỏ dấu, teencode, Telex, trộn tiếng Anh, trộn cả 3).

Hai kiểu đầu ra:
- **flat** (phẳng): 1 bộ phân loại 45 nhãn `service/issue`.
- **hier** (2 tầng): 2 đầu ra dùng chung encoder: service (9) + issue (26); khi dự đoán chỉ chọn trong **45 cặp hợp lệ** (điểm = log p(service) + log p(issue)).

Mỗi kiểu chạy **3 seed** → báo cáo trung bình ± độ lệch chuẩn (test chỉ 3 câu/nhãn nên 1 lần chạy dễ hên xui).

**Cách chạy trên Colab**
1. Runtime → Change runtime type → **T4 GPU**.
2. Chạy từng ô từ trên xuống. Ô 2 sẽ hỏi tải file **`mlr501_data.zip`** lên.
3. Hết khoảng 10–15 phút. Ô cuối tải về `results_B_phobert.zip`.
""")

md("## 1. Cài thư viện\nColab có sẵn PyTorch, Transformers, scikit-learn. Chỉ cần thêm `underthesea` để tách từ (PhoBERT được huấn luyện trên văn bản đã tách từ, vd `hủy_đơn`).")
code("""
!pip -q install underthesea
""")

md("## 2. Tải dữ liệu lên")
code("""
import os, zipfile
if os.path.basename(os.getcwd()) == "notebooks":   # chạy trên máy: về thư mục gốc dự án
    os.chdir("..")
if not os.path.exists("data/superapp/train.csv"):
    try:
        from google.colab import files
        up = files.upload()                      # chọn mlr501_data.zip
        zipfile.ZipFile(next(iter(up))).extractall(".")
    except ImportError:
        raise SystemExit("Không phải Colab: chạy notebook từ thư mục gốc dự án (có data/ và labels/).")
print(sorted(os.listdir("data/superapp")))
""")

md("## 3. Cấu hình\nĐổi ở đây khi muốn thử khác (vd thêm `train_variants` để huấn luyện cả câu không chuẩn).")
code("""
import json, random, time
import numpy as np, pandas as pd, torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
from sklearn.metrics import accuracy_score, f1_score

CFG = dict(
    model_name="vinai/phobert-base-v2",
    segment=True,              # tách từ bằng underthesea
    max_len=64,
    batch_size=16,
    lr=2e-5,
    epochs=10,
    warmup_ratio=0.1,
    seeds=[42, 43, 44],
    modes=["flat", "hier"],
    train_variants=["clean"],  # baseline: chỉ học câu chuẩn
)
VARIANTS = ["clean", "no_diacritics", "teencode", "telex", "code_switch", "mixed"]
device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
print("device:", device)
""")

md("## 4. Đọc dữ liệu và bảng nhãn")
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

train_df = pd.read_csv("data/superapp/train.csv")
train_df = train_df[train_df.variant.isin(CFG["train_variants"])].reset_index(drop=True)
val_df = pd.read_csv("data/superapp/val.csv").query("variant == 'clean'").reset_index(drop=True)
test_df = pd.read_csv("data/superapp/test.csv")
print(f"{len(SERVICES)} service, {len(ISSUES)} issue, {len(PAIRS)} cặp")
print("train", len(train_df), "| val", len(val_df), "| test", len(test_df), "(=", len(test_df) // 6, "câu x 6 biến thể)")
""")

md("## 5. Tách từ")
code("""
if CFG["segment"]:
    from underthesea import word_tokenize
    _cache = {}
    def seg(t):
        if t not in _cache:
            _cache[t] = word_tokenize(t, format="text")
        return _cache[t]
else:
    seg = lambda t: t
for df in (train_df, val_df, test_df):
    df["input"] = df.text.map(seg)
test_df[["variant", "text", "input"]].head(6)
""")

md("## 6. Mô hình\nLấy vector của token đầu `<s>` từ PhoBERT → lớp tuyến tính.")
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
        x = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0]
        x = self.drop(x)
        if self.mode == "flat":
            return {"pair": self.head(x)}
        return {"service": self.head_s(x), "issue": self.head_i(x)}


def make_loader(df, tok, shuffle):
    enc = tok(list(df["input"]), truncation=True, max_length=CFG["max_len"], padding=True, return_tensors="pt")
    ds = TensorDataset(enc["input_ids"], enc["attention_mask"],
                       torch.tensor(df.label.map(p2id).values),
                       torch.tensor(df.service.map(s2id).values),
                       torch.tensor(df.issue.map(i2id).values))
    return DataLoader(ds, batch_size=CFG["batch_size"], shuffle=shuffle)


@torch.no_grad()
def predict(model, loader):
    model.eval()
    out = []
    for ids, mask, *_ in loader:
        o = model(ids.to(device), mask.to(device))
        if model.mode == "flat":
            out.append(o["pair"].argmax(-1).cpu())
        else:
            ls = o["service"].log_softmax(-1).cpu()
            li = o["issue"].log_softmax(-1).cpu()
            out.append((ls[:, PAIR_S] + li[:, PAIR_I]).argmax(-1))   # chỉ chọn trong 45 cặp hợp lệ
    return torch.cat(out).numpy()


def metrics(df, pred_ids):
    pred = [PAIRS[k] for k in pred_ids]
    ps = [p.split("/")[0] for p in pred]
    pi = [p.split("/")[1] for p in pred]
    return dict(
        acc=accuracy_score(df.label, pred),
        f1=f1_score(df.label, pred, average="macro", zero_division=0),
        f1_service=f1_score(df.service, ps, average="macro", zero_division=0),
        f1_issue=f1_score(df.issue, pi, average="macro", zero_division=0),
    )
""")

md("## 7. Huấn luyện\nChọn epoch tốt nhất theo macro-F1 trên tập val (câu chuẩn).")
code("""
def set_seed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(s)


def train_one(mode, seed, loaders):
    set_seed(seed)
    model = Classifier(CFG["model_name"], mode).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=CFG["lr"], weight_decay=0.01)
    steps = len(loaders["train"]) * CFG["epochs"]
    sch = get_linear_schedule_with_warmup(opt, int(steps * CFG["warmup_ratio"]), steps)
    ce = nn.CrossEntropyLoss()
    best_f1, best_state, best_ep = -1, None, 0
    for ep in range(1, CFG["epochs"] + 1):
        model.train()
        total = 0.0
        for ids, mask, yp, ys, yi in loaders["train"]:
            o = model(ids.to(device), mask.to(device))
            if mode == "flat":
                loss = ce(o["pair"], yp.to(device))
            else:
                loss = ce(o["service"], ys.to(device)) + ce(o["issue"], yi.to(device))
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sch.step()
            total += loss.item()
        vm = metrics(val_df, predict(model, loaders["val"]))
        print(f"  [{mode} seed={seed}] epoch {ep:2d} loss={total / len(loaders['train']):.3f} val_f1={vm['f1']:.3f}")
        if vm["f1"] > best_f1:
            best_f1, best_ep = vm["f1"], ep
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    print(f"  -> chọn epoch {best_ep} (val_f1={best_f1:.3f})")
    return model, best_ep
""")

md("## 8. Chạy thực nghiệm (2 kiểu × 3 seed)")
code("""
tok = AutoTokenizer.from_pretrained(CFG["model_name"])
loaders = {"train": make_loader(train_df, tok, True), "val": make_loader(val_df, tok, False)}
test_sets = {v: test_df[test_df.variant == v].reset_index(drop=True) for v in VARIANTS}
test_loaders = {v: make_loader(d, tok, False) for v, d in test_sets.items()}

rows, preds = [], []
for mode in CFG["modes"]:
    for seed in CFG["seeds"]:
        t0 = time.time()
        model, best_ep = train_one(mode, seed, loaders)
        for v in VARIANTS:
            p = predict(model, test_loaders[v])
            rows.append(dict(model="PhoBERT", mode=mode, seed=seed, variant=v, best_epoch=best_ep, **metrics(test_sets[v], p)))
            preds.append(test_sets[v].assign(pred=[PAIRS[k] for k in p], mode=mode, seed=seed))
        print(f"== {mode} seed={seed} xong trong {time.time() - t0:.0f}s")
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

res = pd.DataFrame(rows)
pred_df = pd.concat(preds, ignore_index=True)
""")

md("## 9. Kết quả\nBảng chính: macro-F1 nhãn đầy đủ (trung bình 3 seed) theo biến thể. Cột `drop` = mức giảm so với câu chuẩn.")
code("""
pd.set_option("display.precision", 3)
main = res.groupby(["mode", "variant"]).f1.agg(["mean", "std"]).unstack(0)
main = main.reindex(VARIANTS)
for m in CFG["modes"]:
    main[("drop", m)] = main[("mean", m)] - main.loc["clean", ("mean", m)]
main
""")
code("""
# Chi tiết: service, issue, accuracy
res.groupby(["mode", "variant"])[["acc", "f1", "f1_service", "f1_issue"]].mean().reindex(VARIANTS, level=1)
""")

md("## 10. Phân tích lỗi\nCác cặp hay nhầm nhất (gộp mọi seed, câu chuẩn), và đoán service đúng bao nhiêu khi câu **không nêu rõ dịch vụ** (`explicit = 0`).")
code("""
clean = pred_df[pred_df.variant == "clean"]
wrong = clean[clean.label != clean.pred]
print("Cặp nhầm nhiều nhất (nhãn đúng -> dự đoán):")
print(wrong.groupby(["mode", "label", "pred"]).size().sort_values(ascending=False).head(15).to_string())

clean = clean.assign(service_ok=clean.pred.str.split("/").str[0] == clean.service)
print("\\nĐoán đúng service theo explicit (0 = câu không nêu rõ dịch vụ):")
print(clean.groupby(["mode", "explicit"]).service_ok.mean().round(3).to_string())
""")

md("## 11. Lưu và tải kết quả về")
code("""
os.makedirs("results", exist_ok=True)
res.to_csv("results/B_phobert_metrics.csv", index=False)
pred_df.to_csv("results/B_phobert_predictions.csv", index=False)
json.dump({**CFG, "device": device}, open("results/B_phobert_config.json", "w"), indent=2, ensure_ascii=False)
with zipfile.ZipFile("results_B_phobert.zip", "w") as z:
    for f in os.listdir("results"):
        if f.startswith("B_phobert"):
            z.write(f"results/{f}")
try:
    from google.colab import files
    files.download("results_B_phobert.zip")
except ImportError:
    print("Đã lưu vào results/")
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python"}, "accelerator": "GPU",
                                   "colab": {"provenance": []}},
      "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks/B_phobert.ipynb"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Đã tạo", out.relative_to(ROOT), "-", len(cells), "ô")
