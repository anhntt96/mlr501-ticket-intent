# MLR501 – Phân loại intent ticket CSKH super-app tiếng Việt (bản thử)

Bản thu nhỏ (mini pipeline) để tự đi hết quy trình nghiên cứu trước khi chia việc cho nhóm.

## Cấu trúc

```
labels/label_schema.json        # nhãn 2 tầng: 9 service, 26 issue, 45 cặp hợp lệ, định nghĩa + ví dụ
data/generated/*.tsv            # câu sinh bằng LLM (Claude): service, issue, explicit, text
data/superapp/dataset_all.csv   # 1 dòng/câu, 6 biến thể, cột split
data/superapp/{train,val,test}.csv  # dạng dài: id, service, issue, label, explicit, variant, text
data/superapp/stats.txt
scripts/noise.py                # hàm tạo biến thể không chuẩn + khoá phát hiện câu trùng
scripts/03_build_superapp.py    # dựng bộ dữ liệu
scripts/make_notebook_b.py      # sinh notebooks/B_phobert.ipynb
notebooks/B_phobert.ipynb       # bước B: PhoBERT (chạy trên Colab)
dist/mlr501_data.zip            # dữ liệu để tải lên Colab
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
- Đóng gói lại dữ liệu sau khi sửa: `rm -f dist/mlr501_data.zip && zip -q dist/mlr501_data.zip data/superapp/{train,val,test}.csv labels/label_schema.json`

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

## Lịch sử
- 16/11/2026: làm thử bước A trên Bitext (400 câu tiếng Anh dịch sang tiếng Việt) để học quy trình; sau khi đổi sang bối cảnh super-app đã bỏ toàn bộ dữ liệu và script Bitext.
