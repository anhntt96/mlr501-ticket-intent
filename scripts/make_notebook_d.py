"""Sinh notebooks/D_gpt4o.ipynb: GPT-4o zero-shot và few-shot qua OpenAI API (chạy trên Colab hoặc máy bất kỳ).
Chạy: python3 scripts/make_notebook_d.py
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
# Bước D – GPT-4o zero-shot và few-shot

**Mục tiêu:** đo GPT-4o (không huấn luyện) trên **cùng tập test** (135 câu × 6 biến thể = 810 lượt) để so với PhoBERT và Qwen + LoRA.

- **zero-shot:** prompt = hướng dẫn nhãn (lấy từ `docs/SUPERAPP_INTENTS.md`) + danh sách 45 nhãn hợp lệ.
- **few-shot:** như trên + `shots_per_label` câu ví dụ mỗi nhãn, **lấy từ tập train** (câu chuẩn).
- `temperature = 0`; đầu ra ép về 1 trong 45 nhãn bằng Structured Outputs (`constrained=True`).

> **Chống lộ đề:** tài liệu nhãn có 52 câu "Ví dụ", trong đó **6 câu trùng nguyên văn câu test** (và vài câu gần giống).
> Vì vậy mặc định `guide_examples=False`: bỏ các dòng ví dụ khỏi prompt, chỉ giữ định nghĩa và quy tắc "Không phải".

**Cách chạy**
1. Cần **OpenAI API key** có tiền trong tài khoản. Trên Colab: biểu tượng 🔑 (Secrets) bên trái → thêm `OPENAI_API_KEY` → bật quyền cho notebook. Không có Secrets thì ô 4 sẽ hỏi nhập key (không lưu vào notebook).
2. Không cần GPU (Runtime CPU là đủ).
3. **Chạy thử trước** với `limit=10` (10 câu test × 6 biến thể × 2 kiểu = 120 lượt) → ô 9 in chi phí thực tế và **ước tính chi phí chạy đủ**. Thấy ổn thì đặt `limit=None` và chạy lại từ ô Cấu hình. Câu đã gọi được lưu lại, không gọi lại (không tốn tiền 2 lần).
4. Ô cuối tải về `results_D_gpt4o.zip` → giải nén vào `results/`.
""")

md("## 1. Cài thư viện")
code("""
!pip -q install -U openai
""")

md("## 2. Tải dữ liệu lên\nCần `data/superapp/dataset_all.csv`, `labels/label_schema.json`, `docs/SUPERAPP_INTENTS.md` (đều có trong `mlr501_data.zip`).")
code("""
import os, zipfile
if os.path.basename(os.getcwd()) == "notebooks":   # chạy trên máy: về thư mục gốc dự án
    os.chdir("..")
if not os.path.exists("docs/SUPERAPP_INTENTS.md"):
    try:
        from google.colab import files
        up = files.upload()                      # chọn mlr501_data.zip
        zipfile.ZipFile(next(iter(up))).extractall(".")
    except ImportError:
        raise SystemExit("Không phải Colab: chạy notebook từ thư mục gốc dự án (có data/, labels/, docs/).")
print(sorted(os.listdir("data/superapp")))
""")

md("## 3. Nơi lưu kết quả\n`USE_DRIVE = True` → lưu vào Google Drive (`MyDrive/mlr501_results`).")
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

md("## 4. API key\nĐọc từ Colab Secrets (`OPENAI_API_KEY`) hoặc biến môi trường; không có thì hỏi nhập. **Đừng dán key thẳng vào notebook.**")
code("""
import getpass
if not os.environ.get("OPENAI_API_KEY"):
    try:
        from google.colab import userdata
        os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
    except Exception:
        os.environ["OPENAI_API_KEY"] = getpass.getpass("OPENAI_API_KEY: ")
print("Đã có key:", bool(os.environ.get("OPENAI_API_KEY")))
""")

md("## 5. Cấu hình")
code("""
import difflib, hashlib, json, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, pandas as pd
from sklearn.metrics import accuracy_score, f1_score

CFG = dict(
    model="gpt-4o",           # nên ghim bản cụ thể để tái lập được, vd "gpt-4o-2024-08-06"; tên thật được ghi lại vào config
    settings=["zero_shot", "few_shot"],
    shots_per_label=2,        # few-shot: số câu ví dụ / nhãn (45 nhãn x 2 = 90 câu), lấy từ train
    shot_seed=42,
    runs=[0],                 # mỗi phần tử = 1 lần chạy (truyền làm seed của API). [0, 1, 2] để đo dao động (tốn x3)
    temperature=0.0,
    constrained=True,         # Structured Outputs: buộc trả về 1 trong 45 nhãn
    guide_examples=False,     # KHÔNG đưa câu "Ví dụ" của tài liệu nhãn vào prompt (6 câu trùng câu test)
    limit=10,                 # chạy thử N câu test đầu tiên; đặt None để chạy đủ 135 câu
    max_workers=8,            # số lượt gọi song song; gặp lỗi rate limit thì giảm xuống
    price_per_1m=dict(input=2.50, cached_input=1.25, output=10.00),  # USD / 1 triệu token – KIỂM TRA LẠI giá hiện tại
)
VARIANTS = ["clean", "no_diacritics", "teencode", "telex", "code_switch", "mixed"]
TAG = "D_gpt4o" if CFG["limit"] is None else "D_gpt4o_trial"
NAME = {"zero_shot": "GPT-4o zero-shot", "few_shot": "GPT-4o few-shot"}
""")

md("## 6. Đọc dữ liệu và bảng nhãn")
code("""
schema = json.load(open("labels/label_schema.json", encoding="utf-8"))
SERVICES = list(schema["services"])
ISSUES = list(schema["issues"])
PAIRS = sorted(f"{s}/{i}" for i, v in schema["issues"].items() for s in v["services"])
P_SET = set(PAIRS)

wide = pd.read_csv("data/superapp/dataset_all.csv")
data = wide.melt(id_vars=["id", "split", "service", "issue", "label", "explicit"],
                 value_vars=VARIANTS, var_name="variant", value_name="text")
test_ids = list(wide[wide.split == "test"].id)
if CFG["limit"]:
    test_ids = test_ids[:CFG["limit"]]
test_df = data[data.id.isin(test_ids)].reset_index(drop=True)
print(f"{len(PAIRS)} nhãn | test: {len(test_ids)} câu x 6 biến thể = {len(test_df)} lượt / kiểu / lần chạy")
""")

md("""
## 7. Dựng prompt
- Hướng dẫn nhãn = phần **2. Service** và **3. Issue** của `docs/SUPERAPP_INTENTS.md` (bỏ ma trận và bảng danh mục gốc).
- Few-shot: chọn ngẫu nhiên (seed cố định) `shots_per_label` câu chuẩn / nhãn từ **train**, xáo thứ tự.
- Ví dụ và hướng dẫn nằm ở system prompt (giống nhau cho mọi lượt) → OpenAI tự cache phần đầu prompt, giảm chi phí.
""")
code("""
doc = open("docs/SUPERAPP_INTENTS.md", encoding="utf-8").read()
guide = doc[doc.index("## 2. Service"):doc.index("## 4.")]
if not CFG["guide_examples"]:
    guide = "\\n".join(l for l in guide.splitlines() if not l.startswith("- **Ví dụ:**"))
guide = re.sub(r"\\n{3,}", "\\n\\n", guide).strip()

BASE = f\"\"\"Bạn là hệ thống phân loại ticket chăm sóc khách hàng (CSKH) của một super-app Việt Nam.
Đọc 1 ticket và gán đúng 1 nhãn dạng service/issue trong danh sách 45 nhãn hợp lệ ở cuối.
- Ticket có thể viết không dấu, viết tắt (teencode), gõ Telex lỗi hoặc trộn tiếng Anh.
- Ticket không nêu rõ dịch vụ: chọn dịch vụ hợp lý nhất theo ngữ cảnh.
- Ticket nêu nhiều vấn đề: chọn vấn đề chính (điều khách muốn được giải quyết nhất).
Chỉ trả lời bằng nhãn.

# Hướng dẫn nhãn
{guide}

# 45 nhãn hợp lệ
\"\"\" + "\\n".join(PAIRS)

train_clean = data[(data.split == "train") & (data.variant == "clean")]
shots = pd.concat([g.sample(min(CFG["shots_per_label"], len(g)), random_state=CFG["shot_seed"])
                   for _, g in train_clean.groupby("label")]).sample(frac=1, random_state=CFG["shot_seed"])
FEW = BASE + "\\n\\n# Ví dụ đã gán nhãn\\n" + "\\n\\n".join(f"Ticket: {t}\\nNhãn: {l}" for t, l in zip(shots.text, shots.label))
SYSTEM = {"zero_shot": BASE, "few_shot": FEW}
for k, v in SYSTEM.items():
    print(f"{k}: {len(v):,} ký tự")
print("\\n--- 1500 ký tự đầu của prompt zero-shot ---\\n" + BASE[:1500])
""")

md("## 8. Kiểm tra lộ đề\nCâu test nào giống ≥ 85% một câu có trong prompt (ví dụ của tài liệu nhãn hoặc ví dụ few-shot)? Kết quả mong đợi: không có.")
code("""
def norm(t):
    return re.sub(r"\\W+", " ", str(t).lower()).strip()

in_prompt = re.findall(r"“([^”]+)”", guide) + list(shots.text)
test_clean = [norm(t) for t in wide[wide.split == "test"].clean]
leaks = [(e, t) for e in in_prompt for t in test_clean
         if difflib.SequenceMatcher(None, norm(e), t).ratio() >= 0.85]
print(f"{len(in_prompt)} câu trong prompt | {len(leaks)} câu giống câu test")
for e, t in leaks[:10]:
    print(" -", e, "|", t)
""")

md("""
## 9. Gọi API
Kết quả thô lưu vào `D_gpt4o_raw_<mã cấu hình>.jsonl` ngay khi có. Chạy lại ô này chỉ gọi những lượt **chưa có** (vd sau lỗi mạng).
Mã cấu hình đổi khi đổi model/prompt/temperature → không lẫn kết quả cũ.
""")
code("""
from openai import OpenAI
client = OpenAI(max_retries=8, timeout=60)
SCHEMA = {"type": "json_schema", "json_schema": {"name": "ticket_label", "strict": True, "schema": {
    "type": "object", "properties": {"label": {"type": "string", "enum": PAIRS}},
    "required": ["label"], "additionalProperties": False}}}
cfg_key = hashlib.md5(json.dumps([CFG["model"], CFG["temperature"], CFG["constrained"], SYSTEM],
                                 ensure_ascii=False).encode()).hexdigest()[:8]
CACHE = f"{RESULTS_DIR}/D_gpt4o_raw_{cfg_key}.jsonl"


def call(setting, run, text):
    kw = dict(model=CFG["model"], temperature=CFG["temperature"], seed=run, max_completion_tokens=40,
              messages=[{"role": "system", "content": SYSTEM[setting]}, {"role": "user", "content": f"Ticket: {text}"}])
    if CFG["constrained"]:
        kw["response_format"] = SCHEMA
    r = client.chat.completions.create(**kw)
    u = r.usage
    cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
    return dict(raw=r.choices[0].message.content or "", model_used=r.model, prompt_tokens=u.prompt_tokens,
                cached_tokens=cached, completion_tokens=u.completion_tokens)


cache = {}
if os.path.exists(CACHE):
    for line in open(CACHE, encoding="utf-8"):
        d = json.loads(line)
        cache[(d["setting"], d["run"], d["id"], d["variant"])] = d
jobs = [(s, r, row) for s in CFG["settings"] for r in CFG["runs"] for row in test_df.itertuples()
        if (s, r, row.id, row.variant) not in cache]
print(f"Đã có {len(cache)} lượt | cần gọi {len(jobs)} lượt")

t0, errors = time.time(), 0
with ThreadPoolExecutor(CFG["max_workers"]) as ex, open(CACHE, "a", encoding="utf-8") as f:
    futs = {ex.submit(call, s, r, row.text): (s, r, row) for s, r, row in jobs}
    for k, fut in enumerate(as_completed(futs), 1):
        s, r, row = futs[fut]
        try:
            d = fut.result()
        except Exception as e:
            errors += 1
            print("Lỗi", s, row.id, row.variant, "-", str(e)[:200])
            continue
        d.update(setting=s, run=r, id=row.id, variant=row.variant)
        cache[(s, r, row.id, row.variant)] = d
        f.write(json.dumps(d, ensure_ascii=False) + "\\n"); f.flush()
        if k % 100 == 0:
            print(f"  {k}/{len(jobs)} ({time.time() - t0:.0f}s)")
print(f"Xong trong {time.time() - t0:.0f}s, {errors} lỗi" + (" → chạy lại ô này để gọi lại các lượt lỗi" if errors else ""))
""")

md("## 10. Chi phí\nChi phí thực tế của các lượt đã gọi, và ước tính khi chạy đủ 135 câu.")
code("""
raw = pd.DataFrame([d for k, d in cache.items() if k[0] in CFG["settings"] and k[1] in CFG["runs"]
                    and k[2] in set(test_ids)])
P = CFG["price_per_1m"]
def cost(df):
    return ((df.prompt_tokens - df.cached_tokens).sum() * P["input"] + df.cached_tokens.sum() * P["cached_input"]
            + df.completion_tokens.sum() * P["output"]) / 1e6
for s, g in raw.groupby("setting"):
    full = len(wide[wide.split == "test"]) * 6 * len(CFG["runs"])
    print(f"{s}: {len(g)} lượt, TB {g.prompt_tokens.mean():,.0f} token prompt (cache {g.cached_tokens.mean():,.0f}) "
          f"→ ${cost(g):.2f}; chạy đủ {full} lượt ≈ ${cost(g) / len(g) * full:.2f}")
print("Model thật sự trả lời:", raw.model_used.unique())
""")

md("## 11. Chấm điểm\nĐầu ra không đọc được thành nhãn hợp lệ → `INVALID` (tính là sai).")
code("""
def parse(raw):
    s = raw.strip()
    try:
        s = json.loads(s)["label"]
    except Exception:
        pass
    s = str(s).strip().strip("`'\\" .").lower()
    if s in P_SET:
        return s
    found = [p for p in PAIRS if p in s]          # câu trả lời dài: tìm nhãn nằm bên trong
    return found[0] if len(found) == 1 else "INVALID"


def metrics(df, pred):
    ps = [p.split("/")[0] for p in pred]
    pi = [p.split("/")[-1] for p in pred]
    return dict(
        acc=accuracy_score(df.label, pred),
        f1=f1_score(df.label, pred, labels=PAIRS, average="macro", zero_division=0),
        f1_service=f1_score(df.service, ps, labels=SERVICES, average="macro", zero_division=0),
        f1_issue=f1_score(df.issue, pi, labels=ISSUES, average="macro", zero_division=0),
        invalid=float(np.mean([p == "INVALID" for p in pred])),
    )


rows, preds = [], []
for s in CFG["settings"]:
    for r in CFG["runs"]:
        for v in VARIANTS:
            d = test_df[test_df.variant == v].reset_index(drop=True)
            keys = [(s, r, i, v) for i in d.id]
            if not all(k in cache for k in keys):
                print(f"Thiếu lượt gọi cho {s} run={r} {v} → chạy lại ô 9"); continue
            p = [parse(cache[k]["raw"]) for k in keys]
            rows.append(dict(model="GPT-4o", mode=s, seed=r, variant=v, best_epoch=np.nan, **metrics(d, p)))
            preds.append(d.assign(pred=p, model="GPT-4o", mode=s, seed=r, raw=[cache[k]["raw"] for k in keys]))
res = pd.DataFrame(rows)
pred_df = pd.concat(preds, ignore_index=True)
""")

md("## 12. Kết quả\nmacro-F1 nhãn đầy đủ theo biến thể; `drop` = mức giảm so với câu chuẩn. (Với `limit` nhỏ, con số chỉ để kiểm tra, chưa có ý nghĩa.)")
code("""
pd.set_option("display.precision", 3)
main = res.groupby(["mode", "variant"]).f1.mean().unstack(0).reindex(VARIANTS)
for m in main.columns:
    main[f"drop_{m}"] = main[m] - main.loc["clean", m]
main
""")
code("""
res.groupby(["mode", "variant"])[["acc", "f1", "f1_service", "f1_issue", "invalid"]].mean().reindex(VARIANTS, level=1)
""")

md("## 13. Phân tích lỗi")
code("""
clean = pred_df[pred_df.variant == "clean"]
wrong = clean[clean.label != clean.pred]
print("Cặp nhầm nhiều nhất (nhãn đúng -> dự đoán):")
print(wrong.groupby(["mode", "label", "pred"]).size().sort_values(ascending=False).head(15).to_string())

clean = clean.assign(service_ok=clean.pred.str.split("/").str[0] == clean.service)
print("\\nĐoán đúng service theo explicit (0 = câu không nêu rõ dịch vụ):")
print(clean.groupby(["mode", "explicit"]).service_ok.mean().round(3).to_string())
""")

md("## 14. Lưu và tải kết quả về\nLưu cả prompt đã dùng (`D_gpt4o_prompts.json`) để đưa vào phụ lục paper.")
code("""
res.to_csv(f"{RESULTS_DIR}/{TAG}_metrics.csv", index=False)
pred_df.to_csv(f"{RESULTS_DIR}/{TAG}_predictions.csv", index=False)
json.dump({**CFG, "model_used": sorted(raw.model_used.unique()), "cfg_key": cfg_key, "n_calls": len(raw),
           "cost_usd_estimate": round(cost(raw), 4)},
          open(f"{RESULTS_DIR}/{TAG}_config.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
json.dump({**SYSTEM, "few_shot_ids": list(shots.id)}, open(f"{RESULTS_DIR}/{TAG}_prompts.json", "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)
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
                                   "language_info": {"name": "python"}, "colab": {"provenance": []}},
      "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks/D_gpt4o.ipynb"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Đã tạo", out.relative_to(ROOT), "-", len(cells), "ô")
