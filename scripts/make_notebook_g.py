"""Sinh notebooks/G_rq2_qwen.ipynb: RQ2 cho Qwen2.5 + LoRA – huấn luyện chỉ câu sạch vs có tăng cường câu bỏ dấu.
Chạy: python3 scripts/make_notebook_g.py
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
# Bước G – RQ2 với Qwen2.5 + LoRA: tăng cường câu bỏ dấu có giúp không?

Cùng thiết kế với notebook F (encoder):
- `clean`: mỗi epoch dùng 630 câu train có dấu.
- `aug`: mỗi epoch vẫn 630 câu, mỗi câu có xác suất `aug_ratio` (50%) được **thay** bằng bản bỏ dấu → **số bước huấn luyện bằng nhau**.
- Chọn epoch theo macro-F1 trên val có dấu ở cả 2 chế độ; cùng seed giữa 2 chế độ.
- Đo trên test tổng hợp (6 biến thể) và test do người viết (`data/human_test/human_test.csv`, nếu có).

Cài đặt LoRA giữ nguyên như bước C (r=16, α=32, lr 2e-4, 5 epoch, batch 8×2).

**Chạy trên Colab (T4):** chạy 3B trước (mô hình chính), xong đổi `model_name` sang 1.5B nếu còn thời gian.
Mỗi mô hình: 2 chế độ × 3 seed = 6 lần chạy. Kết quả lưu sau **mỗi lần chạy**; bật `USE_DRIVE` để chạy tiếp được khi Colab ngắt.
""")

md("## 1. Cài thư viện\nGỡ `torchao` vì bản cài sẵn trên Colab xung đột với `peft` mới.")
code("""
!pip -q install -U peft bitsandbytes
!pip -q uninstall -y torchao
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
import gc, json, math, random, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import accuracy_score, f1_score
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, get_linear_schedule_with_warmup
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

MODELS = {"Qwen/Qwen2.5-3B-Instruct": ("Qwen2.5-3B+LoRA", "R2_qwen3b"),
          "Qwen/Qwen2.5-1.5B-Instruct": ("Qwen2.5-1.5B+LoRA", "R2_qwen1.5b")}
CFG = dict(
    model_name="Qwen/Qwen2.5-3B-Instruct",   # lần 2 (nếu còn thời gian): "Qwen/Qwen2.5-1.5B-Instruct"
    train_modes=["clean", "aug"],
    aug_ratio=0.5,
    dtype="auto",          # auto = bf16 nếu GPU hỗ trợ, không thì fp16; loss = nan -> "float32" (1.5B) hoặc load_4bit
    load_4bit=False,       # True nếu 3B báo hết bộ nhớ
    grad_ckpt=False,
    lora_r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lr=2e-4, epochs=5, batch_size=8, grad_accum=2, warmup_ratio=0.1, eval_batch_size=32,
    seeds=[42, 43, 44],
)
MODEL_LABEL, TAG = MODELS.get(CFG["model_name"], (CFG["model_name"].split("/")[-1] + "+LoRA",
                                                    "R2_" + CFG["model_name"].split("/")[-1].lower()))
VARIANTS = ["clean", "no_diacritics", "teencode", "telex", "code_switch", "mixed"]
HVARIANTS = ["human_clean", "human_nodiac", "human_nodiac_rule"]
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cpu":
    print("CẢNH BÁO: không có GPU – chỉ dùng để chạy thử. Runtime → Change runtime type → T4 GPU.")
if CFG["dtype"] == "auto":
    DTYPE = (torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16) if device == "cuda" else torch.float32
else:
    DTYPE = getattr(torch, CFG["dtype"])
print(torch.cuda.get_device_name(0) if device == "cuda" else "CPU", "|", DTYPE, "|", MODEL_LABEL, "->", TAG)
""")

md("## 5. Đọc dữ liệu")
code("""
schema = json.load(open("labels/label_schema.json", encoding="utf-8"))
SERVICES = list(schema["services"])
ISSUES = list(schema["issues"])
PAIRS = sorted(f"{s}/{i}" for i, v in schema["issues"].items() for s in v["services"])
P_SET = set(PAIRS)

wide = pd.read_csv("data/superapp/dataset_all.csv")
train_w = wide[wide.split == "train"].reset_index(drop=True)
val_df = wide[wide.split == "val"].assign(variant="clean", text=lambda d: d.clean).reset_index(drop=True)
test_df = (wide[wide.split == "test"].melt(id_vars=["id", "split", "service", "issue", "label", "explicit"],
                                           value_vars=VARIANTS, var_name="variant", value_name="text"))
EVAL = {v: test_df[test_df.variant == v].reset_index(drop=True) for v in VARIANTS}
if os.path.exists(HUMAN):
    h = pd.read_csv(HUMAN)
    assert set(h.label) <= P_SET, "human_test.csv có nhãn không hợp lệ"
    for v, col in zip(HVARIANTS, ["text", "text_nodiac", "text_nodiac_rule"]):
        EVAL[v] = h.assign(variant=v, text=h[col])[["id", "service", "issue", "label", "explicit", "variant", "text"]]
print("train", len(train_w), "| val", len(val_df), "| tập đánh giá:", {k: len(v) for k, v in EVAL.items()})
""")

md("## 6. Prompt, mã hoá, giải mã ràng buộc (giống bước C)")
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


def encode_train(texts, labels):
    out = []
    for t, l in zip(texts, labels):
        p, y = prompt_ids(t), LABEL_IDS[l]
        out.append((p + y, [-100] * len(p) + y))
    return out


TR_CLEAN = encode_train(train_w.clean, train_w.label)
TR_NODIAC = encode_train(train_w.no_diacritics, train_w.label)
print("Ví dụ (bản bỏ dấu):\\n" + tok.decode(TR_NODIAC[0][0]))
""")

md("## 7. Dự đoán và chỉ số")
code("""
def collate(batch):
    L = max(len(x) for x, _ in batch)
    ids = torch.full((len(batch), L), PAD)
    lab = torch.full((len(batch), L), -100)
    att = torch.zeros((len(batch), L), dtype=torch.long)
    for k, (x, y) in enumerate(batch):
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
        for k, x in enumerate(chunk):
            ids[k, L - len(x):] = torch.tensor(x)
            att[k, L - len(x):] = 1
        out = model.generate(input_ids=ids.to(device), attention_mask=att.to(device), max_new_tokens=MAX_NEW,
                             do_sample=False, repetition_penalty=1.0, use_cache=True, eos_token_id=IM_END,
                             pad_token_id=PAD, prefix_allowed_tokens_fn=lambda _, seq, L=L: allowed(seq[L:].tolist()))
        for row in out[:, L:].tolist():
            s = tok.decode([t for t in row if t not in (IM_END, PAD)]).strip()
            preds.append(s if s in P_SET else "INVALID")
    return preds


def metrics(df, pred):
    ps = [p.split("/")[0] for p in pred]
    pi = [p.split("/")[-1] for p in pred]
    return dict(acc=accuracy_score(df.label, pred),
                f1=f1_score(df.label, pred, labels=PAIRS, average="macro", zero_division=0),
                f1_service=f1_score(df.service, ps, labels=SERVICES, average="macro", zero_division=0),
                f1_issue=f1_score(df.issue, pi, labels=ISSUES, average="macro", zero_division=0),
                invalid=float(np.mean([p == "INVALID" for p in pred])))
""")

md("""
## 8. Huấn luyện một lần chạy
Mỗi epoch chọn ngẫu nhiên (theo seed) `aug_ratio` câu để dùng bản bỏ dấu (chế độ `aug`). Số câu/epoch luôn 630 → số bước bằng nhau.
""")
code("""
def set_seed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(s)


def load_model(seed):
    set_seed(seed)
    kw = dict(torch_dtype=DTYPE)
    if device == "cuda":
        kw.update(device_map={"": 0}, attn_implementation="sdpa")
    if CFG["load_4bit"]:
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16 if DTYPE == torch.float32 else DTYPE)
    model = AutoModelForCausalLM.from_pretrained(CFG["model_name"], **kw)
    if device != "cuda":
        model = model.to(device)
    model.config.use_cache = False
    if CFG["load_4bit"]:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=CFG["grad_ckpt"])
    elif CFG["grad_ckpt"]:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(
        r=CFG["lora_r"], lora_alpha=CFG["lora_alpha"], lora_dropout=CFG["lora_dropout"],
        target_modules=CFG["target_modules"], bias="none", task_type="CAUSAL_LM"))
    for p in model.parameters():
        if p.requires_grad:
            p.data = p.data.float()
    return model


def train_one(train_mode, seed):
    model = load_model(seed)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=CFG["lr"], weight_decay=0.0)
    bs, acc, n = CFG["batch_size"], CFG["grad_accum"], len(TR_CLEAN)
    n_batches = math.ceil(n / bs)
    total = math.ceil(n_batches / acc) * CFG["epochs"]
    sch = get_linear_schedule_with_warmup(opt, int(total * CFG["warmup_ratio"]), total)
    use_amp = DTYPE != torch.float32
    scaler = torch.amp.GradScaler("cuda", enabled=DTYPE == torch.float16)
    rng = random.Random(seed)
    aug_rng = np.random.default_rng(seed)
    best = (-1, None, 0)
    for ep in range(1, CFG["epochs"] + 1):
        use_nd = aug_rng.random(n) < (CFG["aug_ratio"] if train_mode == "aug" else 0.0)
        data = [TR_NODIAC[k] if use_nd[k] else TR_CLEAN[k] for k in range(n)]
        model.train()
        idx = list(range(n))
        rng.shuffle(idx)
        batches = [idx[i:i + bs] for i in range(0, n, bs)]
        tot = 0.0
        opt.zero_grad()
        for b, bi in enumerate(batches):
            ids, att, lab = collate([data[i] for i in bi])
            with torch.autocast(device_type=device, dtype=DTYPE, enabled=use_amp):
                loss = model(input_ids=ids.to(device), attention_mask=att.to(device), labels=lab.to(device)).loss
            if not torch.isfinite(loss):
                raise RuntimeError("loss = nan/inf: đổi CFG['dtype'] = 'float32' (1.5B) hoặc bật load_4bit (3B)")
            scaler.scale(loss / acc).backward()
            tot += loss.item()
            if (b + 1) % acc == 0 or b + 1 == len(batches):
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                scaler.step(opt); scaler.update(); opt.zero_grad(); sch.step()
        vf = metrics(val_df, predict(model, list(val_df.text)))["f1"]
        print(f"    epoch {ep} loss={tot / len(batches):.3f} val_f1={vf:.3f} (câu bỏ dấu: {use_nd.mean():.0%})")
        if vf > best[0]:
            best = (vf, {k: v.detach().cpu().clone() for k, v in model.state_dict().items() if "lora_" in k}, ep)
    model.load_state_dict(best[1], strict=False)
    print(f"    -> chọn epoch {best[2]} (val_f1={best[0]:.3f})")
    return model, best[2]
""")

md("## 9. Chạy thực nghiệm\nGhi kết quả sau **mỗi lần chạy**; chạy lại ô này sẽ bỏ qua lần đã có.")
code("""
MET = f"{RESULTS_DIR}/{TAG}_metrics.csv"
PRED = f"{RESULTS_DIR}/{TAG}_predictions.csv"
done = set()
if os.path.exists(MET):
    done = set(map(tuple, pd.read_csv(MET)[["train", "seed"]].drop_duplicates().values.tolist()))
TRAIN_TAG = {"clean": "clean", "aug": f"aug{int(CFG['aug_ratio'] * 100)}"}

for tm in CFG["train_modes"]:
    for seed in CFG["seeds"]:
        if (TRAIN_TAG[tm], seed) in done:
            print("bỏ qua (đã có):", TRAIN_TAG[tm], seed); continue
        print("==", MODEL_LABEL, TRAIN_TAG[tm], "seed", seed)
        t0 = time.time()
        model, best_ep = train_one(tm, seed)
        rows, preds = [], []
        for v, d in EVAL.items():
            p = predict(model, list(d.text))
            rows.append(dict(model=MODEL_LABEL, mode="lora", train=TRAIN_TAG[tm], seed=seed, variant=v,
                             best_epoch=best_ep, **metrics(d, p)))
            preds.append(d.assign(pred=p, model=MODEL_LABEL, mode="lora", train=TRAIN_TAG[tm], seed=seed))
        pd.DataFrame(rows).to_csv(MET, mode="a", header=not os.path.exists(MET), index=False)
        pd.concat(preds).to_csv(PRED, mode="a", header=not os.path.exists(PRED), index=False)
        r = {x["variant"]: round(x["f1"], 3) for x in rows}
        print(f"   xong {time.time() - t0:.0f}s | clean {r['clean']} | no_diacritics {r['no_diacritics']}"
              + (f" | human_nodiac {r['human_nodiac']}" if "human_nodiac" in r else ""))
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
res = pd.read_csv(MET)
""")

md("## 10. Xem nhanh\nmacro-F1 (TB 3 seed); `gain` = aug − clean. Phân tích đầy đủ ở notebook H.")
code("""
pd.set_option("display.precision", 3)
show = [v for v in ["clean", "no_diacritics", "human_clean", "human_nodiac", "human_nodiac_rule"] if v in set(res.variant)]
t = res[res.variant.isin(show)].groupby(["variant", "train"]).f1.mean().unstack("train")
t["gain"] = t[TRAIN_TAG["aug"]] - t["clean"]
t
""")

md("## 11. Lưu cấu hình và tải kết quả về")
code("""
json.dump({**CFG, "dtype_used": str(DTYPE), "device": torch.cuda.get_device_name(0) if device == "cuda" else device,
           "system_prompt": SYSTEM, "human_test": os.path.exists(HUMAN)},
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
out = ROOT / "notebooks/G_rq2_qwen.ipynb"
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Đã tạo", out.relative_to(ROOT), "-", len(cells), "ô")
