"""Công cụ cho tập test do người viết (chỉ cần Python 3, thư viện chuẩn).

  python scripts/human_test.py template [--per-label 4] [--writers 4]
      -> data/human_test/assignment.csv : bảng phân công (mỗi dòng = 1 ticket cần viết)
  python scripts/human_test.py blind
      -> data/human_test/review_blind.csv : ticket đã viết, KHÔNG kèm nhãn, để người thứ 2 gán nhãn độc lập
  python scripts/human_test.py check
      -> kiểm tra assignment.csv đã điền; nếu review_blind.csv đã điền thì tính độ đồng thuận (Cohen's kappa)
         và ghi disagreements.csv; cuối cùng ghi data/human_test/human_test.csv (file notebook F, G đọc)
  python scripts/human_test.py pack
      -> đóng gói lại dist/mlr501_data.zip (thêm human_test.csv nếu có)

CSV ghi bằng UTF-8 có BOM để Excel mở đúng tiếng Việt. Khi lưu từ Excel, chọn "CSV UTF-8".
"""
import argparse
import csv
import difflib
import json
import random
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HT = ROOT / "data/human_test"
ASSIGN = HT / "assignment.csv"
BLIND = HT / "review_blind.csv"
DISAGREE = HT / "disagreements.csv"
FINAL = HT / "human_test.csv"
SEED = 42

sys.stdout.reconfigure(encoding="utf-8")


def load_schema():
    s = json.load((ROOT / "labels/label_schema.json").open(encoding="utf-8"))
    pairs = sorted(f"{sv}/{i}" for i, v in s["issues"].items() for sv in v["services"])
    return s, pairs


def read_csv(p):
    try:
        with p.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except UnicodeDecodeError:
        sys.exit(f"{p.name} không phải UTF-8. Trong Excel hãy chọn Save As -> 'CSV UTF-8 (Comma delimited)'.")


def write_csv(p, rows, cols):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def strip_diacritics(text):
    """Giống scripts/noise.py: 'Hủy đơn' -> 'Huy don'."""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    return unicodedata.normalize("NFC", "".join(c for c in nfd if unicodedata.category(c) != "Mn"))


def norm(t):
    return re.sub(r"\W+", " ", strip_diacritics(t).lower()).strip()


# ---------------------------------------------------------------- template
def cmd_template(a):
    if ASSIGN.exists() and not a.force:
        sys.exit(f"{ASSIGN} đã có. Thêm --force nếu muốn tạo lại (sẽ GHI ĐÈ phần đã viết).")
    s, pairs = load_schema()
    writers = [f"W{k + 1}" for k in range(a.writers)]
    rows, n = [], 0
    for li, p in enumerate(pairs):
        sv, iss = p.split("/")
        for k in range(a.per_label):
            n += 1
            # mỗi nhãn: 1 ticket không nêu tên dịch vụ (nếu per_label >= 4), còn lại có nêu
            explicit = 0 if (a.per_label >= 4 and k == a.per_label - 1) else 1
            rows.append(dict(
                hid=f"h{n:04d}", writer=writers[(li + k) % len(writers)], label=p,
                dich_vu=s["services"][sv]["vi"], van_de=s["issues"][iss]["vi"],
                dinh_nghia=s["issues"][iss]["definition"],
                yeu_cau="NÊU RÕ dịch vụ" if explicit else "KHÔNG nêu tên dịch vụ",
                explicit=explicit, text="", text_nodiac="", label_final="", ghi_chu=""))
    random.Random(SEED).shuffle(rows)                    # trộn để người viết không viết theo từng nhãn liền nhau
    rows.sort(key=lambda r: r["writer"])
    write_csv(ASSIGN, rows, list(rows[0]))
    print(f"Đã tạo {ASSIGN.relative_to(ROOT)}: {len(rows)} ticket "
          f"({len(pairs)} nhãn x {a.per_label}), {len(writers)} người viết:",
          dict(Counter(r["writer"] for r in rows)))


# ---------------------------------------------------------------- blind
def cmd_blind(a):
    rows = [r for r in read_csv(ASSIGN) if r["text"].strip()]
    if not rows:
        sys.exit("assignment.csv chưa có ticket nào được viết (cột text trống).")
    random.Random(SEED + 1).shuffle(rows)
    # duyệt chéo: ticket của người viết thứ k giao cho người viết thứ k+1 (không ai duyệt bài của mình)
    writers = sorted({r["writer"] for r in rows})
    nxt = {w: writers[(k + 1) % len(writers)] for k, w in enumerate(writers)}
    out = [dict(reviewer=nxt[r["writer"]] if len(writers) > 1 else "", hid=r["hid"], text=r["text"].strip(),
                label_reviewer="") for r in rows]
    out.sort(key=lambda r: r["reviewer"])
    write_csv(BLIND, out, ["reviewer", "hid", "text", "label_reviewer"])
    print(f"Đã tạo {BLIND.relative_to(ROOT)} ({len(out)} ticket), duyệt chéo:",
          {f"{nxt[w]} duyệt bài của {w}": sum(r['writer'] == w for r in rows) for w in writers})
    print("Mỗi người lọc cột reviewer = mã của mình, điền label_reviewer bằng 1 trong 45 nhãn "
          "(xem docs/SUPERAPP_INTENTS.md), KHÔNG xem assignment.csv.")


# ---------------------------------------------------------------- check
def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


def cmd_check(a):
    _, pairs = load_schema()
    P = set(pairs)
    rows = read_csv(ASSIGN)
    errs, warns = [], []
    done = [r for r in rows if r["text"].strip()]
    for r in done:
        h = r["hid"]
        lab = (r.get("label_final") or "").strip() or r["label"]
        if lab not in P:
            errs.append(f"{h}: nhãn '{lab}' không hợp lệ")
        if not r["text_nodiac"].strip():
            errs.append(f"{h}: thiếu text_nodiac (bản gõ không dấu)")
        elif strip_diacritics(r["text_nodiac"]) != r["text_nodiac"]:
            warns.append(f"{h}: text_nodiac vẫn còn chữ có dấu")
        if strip_diacritics(r["text"]) == r["text"]:
            warns.append(f"{h}: text (bản có dấu) không có dấu nào")
    print(f"Đã viết {len(done)}/{len(rows)} ticket.", dict(Counter(r["writer"] for r in done)))

    # trùng hoặc gần trùng với dữ liệu tổng hợp (người viết chép câu có sẵn)
    syn = []
    with (ROOT / "data/superapp/dataset_all.csv").open(encoding="utf-8") as f:
        syn = [norm(r["clean"]) for r in csv.DictReader(f)]
    for r in done:
        t = norm(r["text"])
        best = max((difflib.SequenceMatcher(None, t, s).ratio() for s in syn), default=0)
        if best >= 0.85:
            warns.append(f"{r['hid']}: giống {best:.0%} một câu trong dữ liệu tổng hợp -> viết lại")
    seen = Counter(norm(r["text"]) for r in done)
    warns += [f"trùng nội dung: '{t[:50]}' xuất hiện {c} lần" for t, c in seen.items() if c > 1]

    # đồng thuận giữa người viết (nhãn được giao) và người duyệt (gán mù)
    if BLIND.exists():
        rev = {r["hid"]: r["label_reviewer"].strip() for r in read_csv(BLIND) if r["label_reviewer"].strip()}
        both = [r for r in done if r["hid"] in rev]
        if both:
            bad = [rev[r["hid"]] for r in both if rev[r["hid"]] not in P]
            if bad:
                errs.append(f"review_blind.csv có nhãn không hợp lệ: {sorted(set(bad))[:5]}")
            A = [r["label"] for r in both]
            B = [rev[r["hid"]] for r in both]
            po, k = kappa(A, B)
            po_s, k_s = kappa([x.split("/")[0] for x in A], [x.split("/")[0] for x in B])
            print(f"Đồng thuận trên {len(both)} ticket: nhãn đầy đủ {po:.1%} (kappa {k:.3f}); "
                  f"service {po_s:.1%} (kappa {k_s:.3f})")
            dis = [dict(hid=r["hid"], text=r["text"], label_assigned=r["label"], label_reviewer=rev[r["hid"]],
                        label_final=r.get("label_final", "")) for r in both if r["label"] != rev[r["hid"]]]
            write_csv(DISAGREE, dis, ["hid", "text", "label_assigned", "label_reviewer", "label_final"])
            print(f"{len(dis)} ticket bất đồng -> {DISAGREE.relative_to(ROOT)}. Cả nhóm thống nhất nhãn đúng "
                  f"rồi ghi vào cột label_final của assignment.csv (để trống = giữ nhãn được giao).")

    for w in warns:
        print("  CẢNH BÁO:", w)
    for e in errs:
        print("  LỖI:", e)
    if errs:
        sys.exit(f"{len(errs)} lỗi, chưa ghi human_test.csv.")
    out = []
    for r in done:
        lab = (r.get("label_final") or "").strip() or r["label"]
        out.append(dict(id=r["hid"], writer=r["writer"], service=lab.split("/")[0], issue=lab.split("/")[1],
                        label=lab, explicit=r["explicit"], text=r["text"].strip(),
                        text_nodiac=r["text_nodiac"].strip(), text_nodiac_rule=strip_diacritics(r["text"].strip())))
    with FINAL.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"Đã ghi {FINAL.relative_to(ROOT)}: {len(out)} ticket, {len({r['label'] for r in out})} nhãn.")


# ---------------------------------------------------------------- pack
def cmd_pack(a):
    files = ["data/superapp/train.csv", "data/superapp/val.csv", "data/superapp/test.csv",
             "data/superapp/dataset_all.csv", "labels/label_schema.json", "docs/SUPERAPP_INTENTS.md"]
    if FINAL.exists():
        files.append("data/human_test/human_test.csv")
    out = ROOT / "dist/mlr501_data.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(ROOT / f, f)
    print(f"Đã đóng gói {out.relative_to(ROOT)}:", ", ".join(files))
    if not FINAL.exists():
        print("  (chưa có human_test.csv: notebook sẽ chỉ đo trên tập test tổng hợp)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("template")
    t.add_argument("--per-label", type=int, default=4)
    t.add_argument("--writers", type=int, default=4)
    t.add_argument("--force", action="store_true")
    sp.add_parser("blind")
    sp.add_parser("check")
    sp.add_parser("pack")
    a = ap.parse_args()
    {"template": cmd_template, "blind": cmd_blind, "check": cmd_check, "pack": cmd_pack}[a.cmd](a)
