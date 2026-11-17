"""Bộ dữ liệu super-app (nhãn 2 tầng service/issue).

Đầu vào:
  labels/label_schema.json      (danh mục nhãn v1)
  data/generated/*.tsv          (câu sinh bằng LLM: service, issue, explicit, text)
Đầu ra (data/superapp/):
  dataset_all.csv               (1 dòng / câu, đủ 6 biến thể, cột split)
  train.csv, val.csv, test.csv  (dạng dài: id, service, issue, label, explicit, variant, text)
  stats.txt                     (thống kê)

Hàm tạo biến thể ở scripts/noise.py.
Chạy: python3 scripts/03_build_superapp.py
"""
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "data/generated"
OUT = ROOT / "data/superapp"
SEED = 42
VAL_RATIO = TEST_RATIO = 0.15

import noise as b  # noqa: E402  (cùng thư mục scripts/)
VARIANTS = b.VARIANTS


def load():
    schema = json.load((ROOT / "labels/label_schema.json").open(encoding="utf-8"))
    valid = {(s, i) for i, v in schema["issues"].items() for s in v["services"]}
    rows, errors, seen, dups = [], [], set(), 0
    for f in sorted(GEN.glob("*.tsv")):
        for n, r in enumerate(csv.DictReader(f.open(encoding="utf-8"), delimiter="\t"), 2):
            pair = (r["service"], r["issue"])
            if pair not in valid:
                errors.append(f"{f.name}:{n} cặp không hợp lệ {pair}")
                continue
            text = " ".join(r["text"].split())
            key = b.group_key(text)
            if key in seen:
                dups += 1
                continue
            seen.add(key)
            rows.append({"service": r["service"], "issue": r["issue"],
                         "label": f"{r['service']}/{r['issue']}",
                         "explicit": r["explicit"], "clean": text})
    assert not errors, "\n".join(errors)
    missing = valid - {(r["service"], r["issue"]) for r in rows}
    assert not missing, f"Thiếu dữ liệu cho: {sorted(missing)}"
    return schema, rows, dups


def split(rows, rng):
    by_label = defaultdict(list)
    for r in rows:
        by_label[r["label"]].append(r)
    for items in by_label.values():
        rng.shuffle(items)
        n = len(items)
        n_test, n_val = round(n * TEST_RATIO), round(n * VAL_RATIO)
        for k, r in enumerate(items):
            r["split"] = "test" if k < n_test else "val" if k < n_test + n_val else "train"


def main():
    schema, rows, dups = load()
    rng = random.Random(SEED)
    rng.shuffle(rows)
    for k, r in enumerate(rows, 1):
        r["id"] = f"t{k:04d}"
        c = r["clean"]
        r["no_diacritics"] = b.strip_diacritics(c)
        r["teencode"] = b.teencode(c, rng)
        r["telex"] = b.telex_typo(c, rng)
        r["code_switch"] = b.code_switch(c, rng)
        r["mixed"] = b.mixed(c, rng)
    split(rows, rng)
    rows.sort(key=lambda r: r["id"])

    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["id", "split", "service", "issue", "label", "explicit"] + VARIANTS
    with (OUT / "dataset_all.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    for sp in ("train", "val", "test"):
        with (OUT / f"{sp}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "service", "issue", "label", "explicit", "variant", "text"])
            for r in rows:
                if r["split"] == sp:
                    for v in VARIANTS:
                        w.writerow([r["id"], r["service"], r["issue"], r["label"], r["explicit"], v, r[v]])

    lines = [f"Tổng câu: {len(rows)} (bỏ {dups} câu trùng)",
             f"Service: {len({r['service'] for r in rows})} · Issue: {len({r['issue'] for r in rows})} · Nhãn đầy đủ: {len({r['label'] for r in rows})}",
             f"Theo tập: {dict(Counter(r['split'] for r in rows))}",
             f"Không nêu rõ dịch vụ (explicit=0): {sum(r['explicit'] == '0' for r in rows)}",
             f"Độ dài TB: {sum(len(r['clean'].split()) for r in rows) / len(rows):.1f} từ",
             "", "Số câu theo service:"]
    lines += [f"  {k:<11} {v}" for k, v in sorted(Counter(r["service"] for r in rows).items())]
    lines += ["", "Số câu theo nhãn (ít nhất / nhiều nhất):"]
    lc = Counter(r["label"] for r in rows)
    lines += [f"  min {min(lc.values())} · max {max(lc.values())}"]
    text = "\n".join(lines)
    (OUT / "stats.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
