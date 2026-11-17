"""Sinh docs/SUPERAPP_INTENTS.md từ labels/label_schema.json và labels/original_intents.json.
Sửa nhãn ở file JSON rồi chạy lại: python3 scripts/make_intents_doc.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
schema = json.load((ROOT / "labels/label_schema.json").open(encoding="utf-8"))
orig = json.load((ROOT / "labels/original_intents.json").open(encoding="utf-8"))
S, I = schema["services"], schema["issues"]
pairs = [(s, i) for i, v in I.items() for s in v["services"]]
n_orig = sum(len(c["intents"]) for c in orig["categories"])

L = [
    "# Danh mục intent – ticket CSKH super-app",
    "",
    "> File sinh tự động bởi `scripts/make_intents_doc.py`. **Đừng sửa tay**: sửa `labels/*.json` rồi chạy lại script.",
    "",
    f"- Nhãn 2 tầng **{schema['version']}** ({schema['date']}): **{len(S)} service × {len(I)} issue = {len(pairs)} cặp hợp lệ**. Nhãn đầy đủ = `service/issue`, vd `food/charged_but_failed`.",
    f"- Danh mục gốc **{orig['version']}** ({orig['date']}): **{len(orig['categories'])} category, {n_orig} intent**, mỗi intent gốc ánh xạ sang 1 nhãn 2 tầng.",
    f"- {schema['note']}",
    "",
    "## 1. Ma trận service × issue",
    "",
    "✓ = cặp hợp lệ (có dữ liệu).",
    "",
    "| Issue | " + " | ".join(f"`{s}`" for s in S) + " |",
    "| --- | " + " | ".join(":-:" for _ in S) + " |",
]
for i, v in I.items():
    L.append(f"| `{i}` | " + " | ".join("✓" if s in v["services"] else "" for s in S) + " |")
L.append("| **Số cặp** | " + " | ".join(str(sum(s in v["services"] for v in I.values())) for s in S) + " |")

L += ["", "## 2. Service", "", "| Code | Tên | Định nghĩa |", "| --- | --- | --- |"]
L += [f"| `{k}` | {v['vi']} | {v['definition']} |" for k, v in S.items()]

L += ["", "## 3. Issue (hướng dẫn gán nhãn)", ""]
for k, v in I.items():
    L += [f"### `{k}` – {v['vi']}", "",
          f"- **Định nghĩa:** {v['definition']}"]
    if v["not"]:
        L.append(f"- **Không phải:** {v['not']}")
    L += [f"- **Dịch vụ:** {', '.join(f'`{s}`' for s in v['services'])}",
          "- **Ví dụ:** " + " · ".join(f"“{e}”" for e in v["examples"]), ""]
L += ["### Quy tắc chung", "",
      "- Ticket nêu nhiều vấn đề → chọn vấn đề **chính** (khách muốn được giải quyết nhất).",
      "- Ticket không nói rõ dịch vụ → vẫn gán service theo ngữ cảnh; đây là nguồn nhầm lẫn cần phân tích.", ""]

L += ["## 4. Danh mục gốc → nhãn 2 tầng", "", f"Nguồn: {orig['source']}", "",
      "| Category | Nhóm vấn đề | Intent gốc | Nhãn 2 tầng |", "| --- | --- | --- | --- |"]
for c in orig["categories"]:
    first = True
    for x in c["intents"]:
        L.append(f"| {c['category'] if first else ''} | {x['group'] or '–'} | {x['intent']} | `{x['label']}` |")
        first = False

merged = {}
for c in orig["categories"]:
    for x in c["intents"]:
        merged.setdefault(x["label"], []).append(x["intent"])
multi = {k: v for k, v in merged.items() if len(v) > 1}
L += ["", f"Các nhãn gộp nhiều intent gốc ({len(multi)} nhãn):", ""]
L += [f"- `{k}` ← " + " · ".join(v) for k, v in sorted(multi.items())]

out = ROOT / "docs/SUPERAPP_INTENTS.md"
out.parent.mkdir(exist_ok=True)
out.write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"Đã tạo {out.relative_to(ROOT)}: {len(S)} service, {len(I)} issue, {len(pairs)} cặp, {n_orig} intent gốc")
