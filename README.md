# MLR501 – Phân loại intent ticket CSKH super-app tiếng Việt (bản thử)

## Cấu trúc

```
labels/label_schema.json        # nhãn 2 tầng: 9 service, 26 issue, 45 cặp hợp lệ, định nghĩa + ví dụ
labels/original_intents.json    # danh mục gốc 9 category, 54 intent → ánh xạ sang nhãn 2 tầng
docs/SUPERAPP_INTENTS.md                 # tài liệu intent đọc được (sinh từ 2 file JSON trên)
scripts/make_intents_doc.py     # sinh lại docs/SUPERAPP_INTENTS.md
data/generated/*.tsv            # câu sinh bằng LLM (Claude): service, issue, explicit, text
data/superapp/dataset_all.csv   # 1 dòng/câu, 6 biến thể, cột split
data/superapp/{train,val,test}.csv  # dạng dài: id, service, issue, label, explicit, variant, text
data/superapp/stats.txt
scripts/noise.py                # hàm tạo biến thể không chuẩn + khoá phát hiện câu trùng
scripts/03_build_superapp.py    # dựng bộ dữ liệu
scripts/make_notebook_{b,c,d,e}.py  # sinh các notebook bên dưới
notebooks/B_phobert.ipynb       # bước B: PhoBERT (chạy trên Colab)
notebooks/C_qwen_lora.ipynb     # bước C: Qwen2.5-1.5B / 3B + LoRA (Colab T4)
notebooks/D_gpt4o.ipynb         # bước D: GPT-4o zero-shot / few-shot (OpenAI API)
notebooks/E_compare.ipynb       # bước E: gộp kết quả, bảng, biểu đồ, bootstrap
dist/mlr501_data.zip            # dữ liệu để tải lên Colab (dùng chung cho B, C, D)
```

Chạy lại (chỉ cần Python 3, thư viện chuẩn; seed = 42 nên ra đúng kết quả cũ):

```bash
python3 scripts/03_build_superapp.py
```

## Bước A – Dữ liệu (xong 16/11/2026)

- **900 câu = 45 nhãn × 20 câu**, độ dài TB 12,2 từ, 0 câu trùng.
- Chia 70/15/15 theo từng nhãn: **train 630 · val 135 · test 135** (mỗi nhãn 14/3/3).
- Cột `explicit`: 1 = câu nêu rõ dịch vụ, 0 = không (vd "bị trừ tiền dù giao dịch không thành công"). Hiện chỉ **36/900 câu (4%)** là 0.
- Sinh dữ liệu theo `label_schema.json`, cố ý đa dạng xưng hô (tôi/em/mình), có chi tiết (mã đơn, số tiền, giờ, ngân hàng), giọng lịch sự/bực bội. **Chưa có người đọc kiểm tra.**

### 6 biến thể

| Biến thể | Cách tạo | Ví dụ |
| --- | --- | --- |
| clean | Câu chuẩn | Quán huỷ đơn rồi mà tiền đồ ăn chưa được hoàn |
| no_diacritics | Bỏ dấu | Quan huy don roi ma tien do an chua duoc hoan |
| teencode | Viết tắt (ko, dc, vs, j, tk, tt, nv…), viết thường | quán huỷ đơn r mà tiền đồ ăn chưa dc hoàn |
| telex | 1–2 từ gõ Telex quên bật bộ gõ | Quán huỷ đơn rooif mà tiền đồ ăn chưa được hoanf |
| code_switch | Thay thuật ngữ bằng tiếng Anh (cancel, order, refund…) | Quán huỷ order rồi mà tiền đồ ăn chưa được hoàn |
| mixed | code_switch + teencode + bỏ dấu | quan huy order r ma tien do an chua dc hoan |

`code_switch` chỉ đổi được 345/900 câu (câu không chứa thuật ngữ trong danh sách thì giữ nguyên).

### Hạn chế cần ghi trong paper
- Dữ liệu tổng hợp do một LLM viết → văn phong đồng đều, không phải ticket thật.
- Biến thể không chuẩn sinh bằng quy tắc, có thể chưa giống hết cách khách viết thật.
- Ít câu mơ hồ về dịch vụ (4%) so với thực tế.
- Mỗi nhãn chỉ 3 câu test → điểm theo từng nhãn dao động lớn; chỉ nên đọc macro-F1 tổng và theo nhóm.

## Bước B – PhoBERT (đã chạy trên máy M4 Pro/MPS, 16/11/2026)

- Mô hình `vinai/phobert-base-v2`, tách từ bằng `underthesea`, max_len 64, batch 16, lr 2e-5, 10 epoch (chọn epoch tốt nhất theo macro-F1 val), warmup 10%.
- 2 kiểu: **flat** (45 nhãn) và **hier** (2 đầu ra service 9 + issue 26, giải mã chỉ trong 45 cặp hợp lệ).
- Huấn luyện trên câu chuẩn (`train_variants=["clean"]`), đánh giá test trên 6 biến thể; 3 seed (42, 43, 44).
- Chỉ số: accuracy, macro-F1 nhãn đầy đủ, macro-F1 service, macro-F1 issue; phân tích cặp nhầm và độ chính xác service theo `explicit`.
- Chạy: mở notebook trên Colab (T4 GPU) → tải `dist/mlr501_data.zip` lên → chạy hết → tải `results_B_phobert.zip` về, giải nén vào `results/`.
- Đóng gói lại dữ liệu sau khi sửa: `rm -f dist/mlr501_data.zip && zip -q dist/mlr501_data.zip data/superapp/{train,val,test,dataset_all}.csv labels/label_schema.json docs/SUPERAPP_INTENTS.md`

### Kết quả B (macro-F1 nhãn đầy đủ, trung bình ± độ lệch 3 seed; test 135 câu/biến thể)

| Biến thể | flat | hier | Giảm (flat / hier) |
| --- | --- | --- | --- |
| clean | 0,791 ± 0,011 | **0,810 ± 0,014** | – |
| no_diacritics | 0,160 | 0,161 | −0,63 / −0,65 |
| teencode | 0,782 | 0,786 | −0,01 / −0,02 |
| telex | 0,632 | 0,642 | −0,16 / −0,17 |
| code_switch | 0,742 | 0,746 | −0,05 / −0,06 |
| mixed | 0,193 | 0,166 | −0,60 / −0,64 |

- Câu chuẩn: hier nhỉnh hơn flat (0,810 vs 0,791); hier đoán service tốt hơn (F1 0,915 vs 0,889) nhưng issue kém hơn (0,844 vs 0,876).
- **Bỏ dấu là "sát thủ":** F1 rơi từ ~0,8 xuống ~0,16; `mixed` thấp vì có bỏ dấu. Teencode gần như không ảnh hưởng (vẫn giữ dấu).
- Câu không nêu rõ dịch vụ (`explicit=0`, chỉ 5 câu test): đoán đúng service 0%; câu có nêu rõ: 90–93%.
- Nhầm nhiều nhất: food ↔ mart (đơn thiếu/sai, chưa nhận, bị huỷ) và các nhãn thanh toán của dịch vụ khác → `finance/charged_but_failed`.
- **Chưa hội tụ:** val F1 vẫn tăng ở epoch 9–10, loss còn ~2,1 → nên tăng epoch (20) hoặc lr (3e-5–5e-5).
- Mỗi lần chạy ~52 s trên MPS; tổng ~6 phút. Kết quả: `results/B_phobert_*` và notebook đã chạy `results/B_phobert.executed.ipynb`.
- Môi trường máy: `.venv/` (Python 3.9, torch 2.8, transformers 4.57, underthesea 9.0); kernel Jupyter "MLR501 (.venv)".

## Bước C, D, E – So sánh với LLM (notebook viết 18/11/2026; C đã chạy, D chưa chạy)

Cùng điều kiện với B: train chỉ câu chuẩn, test 135 câu × 6 biến thể, cùng chỉ số (cách tính đã đối chiếu: ra đúng số của B).

| Bước | Notebook | Hệ thống | Chạy ở đâu | Thời gian ước tính |
| --- | --- | --- | --- | --- |
| C | `C_qwen_lora.ipynb` | Qwen2.5-1.5B-Instruct + LoRA, Qwen2.5-3B-Instruct + LoRA | Colab T4 | ~15–25 / ~30–50 phút (3 seed) |
| D | `D_gpt4o.ipynb` | GPT-4o zero-shot, few-shot (2 câu/nhãn từ train) | Colab CPU + OpenAI API key | vài phút; chi phí: chạy thử `limit=10` để xem |
| E | `E_compare.ipynb` | gộp tất cả | Colab CPU hoặc máy | < 1 phút |

- **C:** sinh nhãn `service/issue`, LoRA r=16 trên mọi lớp tuyến tính, lr 2e-4, 5 epoch (chọn theo val), giải mã ràng buộc trong 45 nhãn. Chạy 1.5B xong đổi `model_name` sang 3B. Kết quả lưu sau từng seed; `USE_DRIVE=True` để không mất khi Colab ngắt.
- **D:** prompt = phần 2–3 của `docs/SUPERAPP_INTENTS.md` + 45 nhãn; `temperature=0`; Structured Outputs ép đầu ra về 45 nhãn. **Bỏ các dòng "Ví dụ" của tài liệu nhãn** vì 6/52 câu ví dụ trùng nguyên văn câu test (lộ đề). Key đọc từ Colab Secrets `OPENAI_API_KEY`.
- **E:** bảng F1 (TB ± độ lệch), mức giảm, cơ cấu lỗi (sai service / sai issue), `explicit`, cặp nhầm, câu mọi hệ thống đều sai, bootstrap 95% so với PhoBERT hier → `results/E_summary.md`, `E_fig1_*.png`, `E_fig2_*.png`.
- Trình tự: chạy C (2 lần) và D → giải nén các `results_*.zip` vào `results/` → chạy E.

### Kết quả C (Colab T4, bf16, 18–19/11/2026) so với B

macro-F1 nhãn đầy đủ, TB ± độ lệch 3 seed (42, 43, 44); test 135 câu/biến thể. Bảng đầy đủ: `results/E_summary.md`.

| Biến thể | PhoBERT flat | PhoBERT hier | Qwen2.5-1.5B + LoRA | Qwen2.5-3B + LoRA |
| --- | --- | --- | --- | --- |
| clean | 0,791 ± 0,011 | 0,810 ± 0,014 | 0,870 ± 0,010 | **0,901 ± 0,011** |
| no_diacritics | 0,160 | 0,161 | 0,347 ± 0,056 | **0,563 ± 0,014** |
| teencode | 0,782 | 0,786 | 0,860 | **0,880** |
| telex | 0,632 | 0,642 | 0,733 | **0,823** |
| code_switch | 0,742 | 0,746 | 0,878 | **0,900** |
| mixed | 0,193 | 0,166 | 0,321 | **0,613** |
| TB 5 biến thể nhiễu | 0,502 | 0,500 | 0,628 | **0,756** |

- Qwen hơn PhoBERT hier ở **mọi biến thể**, bootstrap 95% không chứa 0. Câu chuẩn: +0,07 (1.5B), +0,10 (3B).
- **Bỏ dấu vẫn là điểm yếu chung** nhưng mô hình lớn chịu tốt hơn nhiều: giữ lại 20% (PhoBERT) → 40% (1.5B) → 63% (3B) điểm câu chuẩn. Telex: 79% → 84% → 91%. Teencode và trộn tiếng Anh gần như không ảnh hưởng Qwen.
- Qwen giảm cả lỗi service lẫn issue; trên câu chuẩn F1 service 0,946 / issue 0,938 (3B) so với 0,915 / 0,844 (PhoBERT hier).
- Câu không nêu rõ dịch vụ (5 câu test): đúng service 0% (PhoBERT), 7% (1.5B), 13% (3B) – gần như không đoán được. 4/6 câu mà mọi mô hình đều sai là loại này (vd "Bị trừ tiền dù giao dịch báo không thành công" → `mart/...`): **nhãn không suy ra được từ câu**, nên xem là giới hạn của dữ liệu.
- Cặp nhầm còn lại: food ↔ mart, `transport/trip_howto` → `business/business_profile` (câu nhắc "hồ sơ doanh nghiệp").
- **Lưu ý khi so sánh:** PhoBERT chưa hội tụ (epoch tốt nhất 9–10/10), Qwen 1.5B cũng chọn epoch 4–5/5; một phần khoảng cách có thể do ngân sách huấn luyện. Nên chạy lại PhoBERT 20 epoch trước khi kết luận trong paper.

## RQ2 – Tăng cường câu bỏ dấu (theo góp ý của thầy, 23/11/2026; chưa chạy)

Hướng dẫn đầy đủ (bảng lộ trình, cài đặt, cách đọc kết quả): **`docs/RQ2_GUIDE.md`**.

```
data/human_test/HUONG_DAN_VIET.md   # hướng dẫn cho người viết ticket
data/human_test/assignment.csv      # bảng phân công 180 ticket (45 nhãn x 4, 3 người viết, 60/người)
scripts/human_test.py               # template / blind / check (kappa) / pack
notebooks/F_rq2_encoders.ipynb      # PhoBERT + XLM-R, chế độ clean vs aug (50% câu bỏ dấu, cùng số bước)
notebooks/G_rq2_qwen.ipynb          # Qwen2.5-3B (1.5B) + LoRA, clean vs aug
notebooks/H_rq2_analysis.ipynb      # mức tăng trên câu không dấu, thay đổi trên câu có dấu, bootstrap
```

Kết quả RQ2 có tiền tố `R2_` trong `results/`; notebook E và `make_paper_figures.py` bỏ qua các file này.

## Lịch sử
- 16/11/2026: làm thử bước A trên Bitext (400 câu tiếng Anh dịch sang tiếng Việt) để học quy trình; sau khi đổi sang bối cảnh super-app đã bỏ toàn bộ dữ liệu và script Bitext.
