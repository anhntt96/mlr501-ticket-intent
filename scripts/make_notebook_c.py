"""Sinh notebooks/C_qwen_lora.ipynb: fine-tune Qwen2.5-1.5B/3B-Instruct bằng LoRA (chạy trên Google Colab).
Chạy: python3 scripts/make_notebook_c.py
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
# Bước C – Qwen2.5 + LoRA cho phân loại ticket CSKH super-app

**Mục tiêu:** fine-tune **Qwen2.5-1.5B-Instruct** và **Qwen2.5-3B-Instruct** bằng LoRA trên câu **chuẩn** (clean), rồi đo trên tập test ở **6 biến thể**, giống hệt điều kiện của PhoBERT (bước B) để so sánh công bằng.

**Cách làm:** mô hình đọc ticket và *sinh ra* nhãn dạng `service/issue` (vd `food/charged_but_failed`).
- Chỉ tính loss trên phần nhãn (không tính trên câu hỏi).
- Khi dự đoán dùng **giải mã ràng buộc**: mô hình chỉ được sinh 1 trong 45 nhãn hợp lệ (tương tự kiểu `hier` của PhoBERT chỉ chọn trong 45 cặp).
- Chọn epoch tốt nhất theo macro-F1 trên val (câu chuẩn); chạy **3 seed** → trung bình ± độ lệch.

**Cách chạy trên Colab**
1. Runtime → Change runtime type → **T4 GPU** (bản miễn phí là đủ; có L4/A100 thì nhanh hơn).
2. Chạy từng ô từ trên xuống. Ô 2 hỏi tải **`mlr501_data.zip`** lên.
3. Chạy lần 1 với `Qwen/Qwen2.5-1.5B-Instruct` (~15–25 phút cho 3 seed trên T4). Tải `results_C_qwen1.5b.zip` về.
4. Ở ô **Cấu hình** đổi `model_name` thành `Qwen/Qwen2.5-3B-Instruct`, chạy lại từ ô đó trở xuống (~30–50 phút). Tải `results_C_qwen3b.zip` về.
5. Giải nén cả hai vào thư mục `results/` của dự án.

> Colab miễn phí có thể ngắt kết nối giữa chừng. Bật `USE_DRIVE = True` ở ô 3 để lưu kết quả thẳng vào Google Drive: kết quả lưu sau **từng seed**, chạy lại notebook sẽ bỏ qua seed đã xong.
""")

md("""## 1. Cài thư viện
Colab có sẵn PyTorch, Transformers, scikit-learn. Thêm `peft` (LoRA) và `bitsandbytes` (chỉ cần nếu bật 4-bit).
Gỡ `torchao`: Colab cài sẵn bản cũ, `peft` mới gặp nó sẽ báo `ImportError: incompatible version of torchao` (notebook không dùng `torchao`).""")
code("""
!pip -q install -U peft bitsandbytes
!pip -q uninstall -y torchao
""")

md("## 2. Tải dữ liệu lên\nCần `data/superapp/dataset_all.csv` (hoặc train/val/test.csv) và `labels/label_schema.json`, đều có trong `mlr501_data.zip`.")
code("""
import os, zipfile
if os.path.basename(os.getcwd()) == "notebooks":   # chạy trên máy: về thư mục gốc dự án
    os.chdir("..")
if not os.path.exists("labels/label_schema.json"):
    try:
        from google.colab import files
        up = files.upload()                      # chọn mlr501_data.zip
        zipfile.ZipFile(next(iter(up))).extractall(".")
    except ImportError:
        raise SystemExit("Không phải Colab: chạy notebook từ thư mục gốc dự án (có data/ và labels/).")
print(sorted(os.listdir("data/superapp")))
""")

md("## 3. Nơi lưu kết quả\n`USE_DRIVE = True` → lưu vào Google Drive (`MyDrive/mlr501_results`), không mất khi Colab ngắt.")
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

md("## 4. Cấu hình\nChạy 1.5B trước, xong đổi `model_name` sang 3B rồi chạy lại từ ô này.")
code("""
import gc, json, math, random, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import accuracy_score, f1_score
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, get_linear_schedule_with_warmup
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

MODELS = {  # tên trên Hugging Face -> (tên trong bảng kết quả, tiền tố file kết quả)
    "Qwen/Qwen2.5-1.5B-Instruct": ("Qwen2.5-1.5B+LoRA", "C_qwen1.5b"),
    "Qwen/Qwen2.5-3B-Instruct": ("Qwen2.5-3B+LoRA", "C_qwen3b"),
}
CFG = dict(
    model_name="Qwen/Qwen2.5-1.5B-Instruct",   # lần 2: "Qwen/Qwen2.5-3B-Instruct"
    dtype="auto",        # auto = bf16 nếu GPU hỗ trợ (L4/A100), không thì fp16 (T4). Báo loss = nan → thử "float32" (chỉ vừa 1.5B trên T4)
    load_4bit=False,     # True = QLoRA 4-bit: ít bộ nhớ hơn, chậm hơn. Bật nếu 3B báo hết bộ nhớ (CUDA out of memory)
    grad_ckpt=False,     # True = tiết kiệm bộ nhớ, chậm hơn ~30%
    lora_r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lr=2e-4,
    epochs=5,
    batch_size=8,
    grad_accum=2,        # batch hiệu dụng = 16, bằng PhoBERT
    warmup_ratio=0.1,
    eval_batch_size=32,
    constrained=True,    # giải mã ràng buộc: chỉ sinh được 1 trong 45 nhãn
    seeds=[42, 43, 44],
    train_variants=["clean"],  # giống PhoBERT: chỉ học câu chuẩn
)
MODEL_LABEL, TAG = MODELS.get(CFG["model_name"], (CFG["model_name"].split("/")[-1] + "+LoRA",
                                                    "C_" + CFG["model_name"].split("/")[-1].lower()))
VARIANTS = ["clean", "no_diacritics", "teencode", "telex", "code_switch", "mixed"]

assert torch.cuda.is_available(), "Cần GPU: Runtime → Change runtime type → T4 GPU"
device = "cuda"
if CFG["dtype"] == "auto":
    DTYPE = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
else:
    DTYPE = getattr(torch, CFG["dtype"])
print(torch.cuda.get_device_name(0), "|", DTYPE, "|", MODEL_LABEL, "->", TAG)
""")

md("## 5. Đọc dữ liệu và bảng nhãn\nĐọc `dataset_all.csv` (1 dòng/câu, 6 cột biến thể, cột `split`) rồi chuyển sang dạng dài: 1 dòng/biến thể.")
code("""
schema = json.load(open("labels/label_schema.json", encoding="utf-8"))
SERVICES = list(schema["services"])
ISSUES = list(schema["issues"])
PAIRS = sorted(f"{s}/{i}" for i, v in schema["issues"].items() for s in v["services"])
P_SET = set(PAIRS)


def load_long():
    p = "data/superapp/dataset_all.csv"
    if os.path.exists(p):
        wide = pd.read_csv(p)
        return wide.melt(id_vars=["id", "split", "service", "issue", "label", "explicit"],
                         value_vars=VARIANTS, var_name="variant", value_name="text")
    return pd.concat([pd.read_csv(f"data/superapp/{s}.csv").assign(split=s) for s in ("train", "val", "test")],
                     ignore_index=True)


data = load_long()
assert set(data.label) <= P_SET, "Có nhãn không nằm trong label_schema.json"
train_df = data[(data.split == "train") & data.variant.isin(CFG["train_variants"])].reset_index(drop=True)
val_df = data[(data.split == "val") & (data.variant == "clean")].reset_index(drop=True)
test_df = data[data.split == "test"].reset_index(drop=True)
print(f"{len(SERVICES)} service, {len(ISSUES)} issue, {len(PAIRS)} cặp")
print("train", len(train_df), "| val", len(val_df), "| test", len(test_df), "(=", len(test_df) // 6, "câu x 6 biến thể)")
""")

md("""
## 6. Prompt, mã hoá và giải mã ràng buộc
Mỗi mẫu = prompt dạng chat của Qwen + nhãn + `<|im_end|>`. Loss chỉ tính trên nhãn.

Giải mã ràng buộc: dựng cây tiền tố (trie) từ token của 45 nhãn; ở mỗi bước chỉ cho phép các token còn đi tiếp được trên cây → đầu ra luôn là nhãn hợp lệ.
""")
code("""
SYSTEM = ("Bạn phân loại ticket chăm sóc khách hàng của một super-app Việt Nam "
          "(gọi xe, đồ ăn, đi chợ, giao hàng, ví/tài chính, doanh nghiệp, gói hội viên, đặt bàn nhà hàng, tài khoản). "
          "Trả lời đúng một nhãn dạng service/issue.")

tok = AutoTokenizer.from_pretrained(CFG["model_name"])
IM_END = tok.convert_tokens_to_ids("<|im_end|>")
PAD = tok.pad_token_id if tok.pad_token_id is not None else IM_END


def prompt_ids(text):
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"Ticket: {text}"}]
    s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    return tok(s, add_special_tokens=False).input_ids


LABEL_IDS = {p: tok(p, add_special_tokens=False).input_ids + [IM_END] for p in PAIRS}
MAX_NEW = max(len(v) for v in LABEL_IDS.values())
TRIE = {}
for ids in LABEL_IDS.values():
    node = TRIE
    for t in ids:
        node = node.setdefault(t, {})


def allowed(gen):
    node = TRIE
    for t in gen:
        node = node.get(t)
        if node is None:
            return [IM_END]
    return list(node) or [IM_END]


def encode_train(df):
    out = []
    for t, l in zip(df.text, df.label):
        p, y = prompt_ids(t), LABEL_IDS[l]
        out.append((p + y, [-100] * len(p) + y))
    return out


train_data = encode_train(train_df)
print("Ví dụ prompt:\\n" + tok.decode(train_data[0][0]))
print("Độ dài chuỗi dài nhất:", max(len(x) for x, _ in train_data), "token | nhãn dài nhất:", MAX_NEW, "token")
""")

md("## 7. Hàm dự đoán và chỉ số\nCâu trả lời không phải nhãn hợp lệ (chỉ xảy ra khi `constrained=False`) được ghi `INVALID` và tính là sai.")
code("""
def collate(batch):
    L = max(len(x) for x, _ in batch)
    ids = torch.full((len(batch), L), PAD)
    lab = torch.full((len(batch), L), -100)
    att = torch.zeros((len(batch), L), dtype=torch.long)
    for k, (x, y) in enumerate(batch):        # đệm bên phải khi huấn luyện
        ids[k, :len(x)] = torch.tensor(x)
        lab[k, :len(y)] = torch.tensor(y)
        att[k, :len(x)] = 1
    return ids, att, lab


@torch.no_grad()
def predict(model, texts):
    model.eval()
    encs = [prompt_ids(t) for t in texts]
    preds = []
    for b in range(0, len(encs), CFG["eval_batch_size"]):
        chunk = encs[b:b + CFG["eval_batch_size"]]
        L = max(map(len, chunk))
        ids = torch.full((len(chunk), L), PAD)
        att = torch.zeros((len(chunk), L), dtype=torch.long)
        for k, x in enumerate(chunk):          # đệm bên trái khi sinh
            ids[k, L - len(x):] = torch.tensor(x)
            att[k, L - len(x):] = 1
        kw = dict(max_new_tokens=MAX_NEW, do_sample=False, repetition_penalty=1.0, use_cache=True,
                  eos_token_id=IM_END, pad_token_id=PAD)
        if CFG["constrained"]:
            kw["prefix_allowed_tokens_fn"] = lambda _, seq, L=L: allowed(seq[L:].tolist())
        out = model.generate(input_ids=ids.to(device), attention_mask=att.to(device), **kw)
        for row in out[:, L:].tolist():
            s = tok.decode([t for t in row if t not in (IM_END, PAD)]).strip()
            preds.append(s if s in P_SET else "INVALID")
    return preds


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
""")

md("## 8. Huấn luyện\nNạp mô hình gốc → gắn LoRA → huấn luyện; sau mỗi epoch đo val, giữ trọng số LoRA của epoch tốt nhất.")
code("""
def set_seed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)


def load_model(seed):
    set_seed(seed)
    kw = dict(torch_dtype=DTYPE, attn_implementation="sdpa")
    if CFG["load_4bit"]:
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16 if DTYPE == torch.float32 else DTYPE)
    model = AutoModelForCausalLM.from_pretrained(CFG["model_name"], device_map={"": 0}, **kw)
    model.config.use_cache = False
    if CFG["load_4bit"]:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=CFG["grad_ckpt"])
    elif CFG["grad_ckpt"]:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(
        r=CFG["lora_r"], lora_alpha=CFG["lora_alpha"], lora_dropout=CFG["lora_dropout"],
        target_modules=CFG["target_modules"], bias="none", task_type="CAUSAL_LM"))
    for p in model.parameters():           # tham số LoRA giữ ở fp32 cho ổn định
        if p.requires_grad:
            p.data = p.data.float()
    return model


def train_one(seed):
    model = load_model(seed)
    model.print_trainable_parameters()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=CFG["lr"], weight_decay=0.0)
    bs, acc = CFG["batch_size"], CFG["grad_accum"]
    n_batches = math.ceil(len(train_data) / bs)
    total = math.ceil(n_batches / acc) * CFG["epochs"]
    sch = get_linear_schedule_with_warmup(opt, int(total * CFG["warmup_ratio"]), total)
    use_amp = DTYPE != torch.float32
    scaler = torch.amp.GradScaler("cuda", enabled=DTYPE == torch.float16)
    rng = random.Random(seed)
    best_f1, best_state, best_ep = -1, None, 0
    for ep in range(1, CFG["epochs"] + 1):
        model.train()
        idx = list(range(len(train_data)))
        rng.shuffle(idx)
        batches = [idx[i:i + bs] for i in range(0, len(idx), bs)]
        total_loss = 0.0
        opt.zero_grad()
        for b, bi in enumerate(batches):
            ids, att, lab = collate([train_data[i] for i in bi])
            with torch.autocast("cuda", dtype=DTYPE, enabled=use_amp):
                loss = model(input_ids=ids.to(device), attention_mask=att.to(device), labels=lab.to(device)).loss
            if not torch.isfinite(loss):
                raise RuntimeError("loss = nan/inf: đổi CFG['dtype'] = 'float32' (1.5B) hoặc bật load_4bit (3B)")
            scaler.scale(loss / acc).backward()
            total_loss += loss.item()
            if (b + 1) % acc == 0 or b + 1 == len(batches):
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                scaler.step(opt); scaler.update(); opt.zero_grad(); sch.step()
        vm = metrics(val_df, predict(model, list(val_df.text)))
        print(f"  [seed={seed}] epoch {ep} loss={total_loss / len(batches):.3f} val_f1={vm['f1']:.3f}")
        if vm["f1"] > best_f1:
            best_f1, best_ep = vm["f1"], ep
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items() if "lora_" in k}
    model.load_state_dict(best_state, strict=False)
    print(f"  -> chọn epoch {best_ep} (val_f1={best_f1:.3f})")
    return model, best_ep
""")

md("## 9. Chạy thực nghiệm (3 seed)\nKết quả ghi vào file sau **mỗi seed**. Chạy lại ô này sẽ bỏ qua seed đã có trong file.")
code("""
MET = f"{RESULTS_DIR}/{TAG}_metrics.csv"
PRED = f"{RESULTS_DIR}/{TAG}_predictions.csv"
done = set(pd.read_csv(MET).seed) if os.path.exists(MET) else set()
test_sets = {v: test_df[test_df.variant == v].reset_index(drop=True) for v in VARIANTS}

for seed in CFG["seeds"]:
    if seed in done:
        print(f"seed={seed} đã có kết quả, bỏ qua")
        continue
    t0 = time.time()
    model, best_ep = train_one(seed)
    rows, preds = [], []
    for v in VARIANTS:
        p = predict(model, list(test_sets[v].text))
        rows.append(dict(model=MODEL_LABEL, mode="lora", seed=seed, variant=v, best_epoch=best_ep,
                         **metrics(test_sets[v], p)))
        preds.append(test_sets[v].assign(pred=p, model=MODEL_LABEL, mode="lora", seed=seed))
    pd.DataFrame(rows).to_csv(MET, mode="a", header=not os.path.exists(MET), index=False)
    pd.concat(preds).to_csv(PRED, mode="a", header=not os.path.exists(PRED), index=False)
    print(f"== seed={seed} xong trong {time.time() - t0:.0f}s:",
          {r["variant"]: round(r["f1"], 3) for r in rows})
    del model
    gc.collect(); torch.cuda.empty_cache()

res = pd.read_csv(MET)
pred_df = pd.read_csv(PRED)
""")

md("## 10. Kết quả\nmacro-F1 nhãn đầy đủ (trung bình 3 seed) theo biến thể; `drop` = mức giảm so với câu chuẩn.")
code("""
pd.set_option("display.precision", 3)
main = res.groupby("variant").f1.agg(["mean", "std"]).reindex(VARIANTS)
main["drop"] = main["mean"] - main.loc["clean", "mean"]
main
""")
code("""
# Chi tiết: accuracy, service, issue, tỉ lệ đầu ra không hợp lệ
res.groupby("variant")[["acc", "f1", "f1_service", "f1_issue", "invalid"]].mean().reindex(VARIANTS)
""")

md("## 11. Phân tích lỗi\nCặp hay nhầm nhất (gộp mọi seed, câu chuẩn) và độ chính xác service theo `explicit`.")
code("""
clean = pred_df[pred_df.variant == "clean"]
wrong = clean[clean.label != clean.pred]
print("Cặp nhầm nhiều nhất (nhãn đúng -> dự đoán):")
print(wrong.groupby(["label", "pred"]).size().sort_values(ascending=False).head(15).to_string())

clean = clean.assign(service_ok=clean.pred.str.split("/").str[0] == clean.service)
print("\\nĐoán đúng service theo explicit (0 = câu không nêu rõ dịch vụ):")
print(clean.groupby("explicit").service_ok.mean().round(3).to_string())
""")

md("## 12. Lưu cấu hình và tải kết quả về")
code("""
json.dump({**CFG, "dtype_used": str(DTYPE), "gpu": torch.cuda.get_device_name(0), "system_prompt": SYSTEM},
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
out = ROOT / "notebooks/C_qwen_lora.ipynb"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Đã tạo", out.relative_to(ROOT), "-", len(cells), "ô")
