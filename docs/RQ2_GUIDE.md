# Hướng dẫn làm tiếp theo góp ý của thầy (RQ2)

Cập nhật 23/11/2026. Mọi notebook và script ở đây đã được chạy thử đầu-cuối trên máy (mô hình tí hon, CPU); **chưa chạy với mô hình thật**.

## 1. Góp ý của thầy → việc nhóm làm

| Góp ý | Việc làm | File |
| --- | --- | --- |
| Làm rõ câu hỏi nghiên cứu, tập trung RQ2 | RQ2 thành câu hỏi chính; RQ1, RQ3 là phụ (bảng 2) | paper (sửa sau khi có kết quả) |
| Thêm 1 mô hình Transformer, vd XLM-R | Thêm **XLM-RoBERTa-base** (đa ngôn ngữ, không cần tách từ) | `notebooks/F_rq2_encoders.ipynb` |
| So sánh 2 chế độ: chỉ câu sạch / có một phần câu bỏ dấu | Chế độ `clean` và `aug` (50% câu train mỗi epoch được thay bằng bản bỏ dấu) | notebook F, G |
| Giữ số bước huấn luyện tương đương | Câu bỏ dấu **thay thế** câu sạch, không thêm → mỗi epoch vẫn 630 câu, cùng số epoch | notebook F, G |
| Đo mức tăng trên câu không dấu và thay đổi trên câu có dấu | `gain` = F1(aug) − F1(clean), cùng seed; kèm khoảng tin cậy 95% | `notebooks/H_rq2_analysis.ipynb` |
| Kiểm chứng trên tập độc lập do người viết | Tập 180 ticket do 3 người viết (60/người), có bản có dấu và bản **tự gõ** không dấu, duyệt nhãn mù chéo | `data/human_test/`, `scripts/human_test.py` |

## 2. Câu hỏi nghiên cứu mới

| RQ | Câu hỏi | Trả lời bằng | Vai trò |
| --- | --- | --- | --- |
| **RQ2** | Huấn luyện thêm câu bỏ dấu có giúp mô hình xử lý ticket không dấu không, và có làm giảm điểm trên ticket có dấu không? | Notebook F, G → H (bảng 1, biểu đồ) | **Chính** |
| RQ1 | Mô hình nào hiệu quả hơn khi ít dữ liệu gán nhãn (630 câu train)? | So sánh PhoBERT, XLM-R, Qwen 1.5B/3B ở chế độ `clean` (đã có kết quả B, C; F, G cho thêm XLM-R) | Phụ |
| RQ3 | Khi nào cần thêm ngữ cảnh để định tuyến? | Câu không nêu tên dịch vụ (`explicit = 0`): test tổng hợp chỉ 5 câu, test người viết 45 câu (notebook H, bảng 3) | Phụ |

## 3. Thiết kế thí nghiệm RQ2

| Thành phần | Cài đặt |
| --- | --- |
| Mô hình | PhoBERT-base (hier), XLM-R-base (hier), Qwen2.5-3B + LoRA; Qwen2.5-1.5B + LoRA nếu còn thời gian GPU |
| Chế độ `clean` | Mỗi epoch: 630 câu train có dấu |
| Chế độ `aug` | Mỗi epoch: 630 câu, mỗi câu có xác suất 50% được thay bằng bản bỏ dấu của chính nó (chọn lại mỗi epoch, theo seed) |
| Số bước | Bằng nhau giữa 2 chế độ: encoder 40 bước × 20 epoch; Qwen 40 bước × 5 epoch |
| Chọn epoch | Theo macro-F1 trên val **có dấu**, cùng quy tắc ở 2 chế độ; tập test không dùng để chọn |
| Seed | 42, 43, 44 – cùng seed ở 2 chế độ (so sánh ghép cặp) |
| Tập đánh giá | Test tổng hợp 135 câu × 6 biến thể; test người viết ~180 câu × 3 bản: có dấu, người tự gõ không dấu, bỏ dấu bằng quy tắc |
| Chỉ số chính | macro-F1 45 nhãn; `gain` trên câu không dấu; thay đổi trên câu có dấu |
| Kiểm định | Bootstrap ghép cặp 2.000 lần, khoảng tin cậy 95%; khoảng không chứa 0 → có ý nghĩa |
| Khác so với lần trước | Encoder chạy **20 epoch** (bước B 10 epoch chưa hội tụ); Qwen giữ nguyên cài đặt bước C |

## 4. Lộ trình

| # | Việc | Ai | Công cụ | Thời gian ước tính | Kết quả |
| --- | --- | --- | --- | --- | --- |
| 1 | Gửi `HUONG_DAN_VIET.md` và `assignment.csv` cho 3 người viết | Trưởng nhóm | – | 1 ngày | Mỗi người nhận 60 dòng (cột `writer` = W1, W2, W3) |
| 2 | Viết ticket: cột `text` (có dấu) và `text_nodiac` (tự gõ không dấu) | 3 người viết | Excel / Google Sheets | 90–120 phút/người | `assignment.csv` đã điền |
| 3 | Gộp file, chạy `blind` → `review_blind.csv`; mỗi người duyệt mù 60 ticket **của người khác** (cột `reviewer`) | Cả 3 người | `human_test.py blind` | 45–60 phút/người | `review_blind.csv` đã điền |
| 4 | Chạy `check`: sửa cảnh báo, thống nhất các ticket bất đồng (ghi `label_final`) | Cả nhóm | `human_test.py check` | 1 buổi | `human_test.csv`, kappa |
| 5 | Đóng gói dữ liệu | Trưởng nhóm | `human_test.py pack` | 1 phút | `dist/mlr501_data.zip` có `human_test.csv` |
| 6 | Chạy notebook F (encoder) | 1 người | Colab T4 | 30–60 phút | `results_R2_encoders.zip` |
| 7 | Chạy notebook G với Qwen 3B (và 1.5B nếu kịp) | 1 người | Colab T4 | 1–2 giờ/mô hình | `results_R2_qwen3b.zip` (…1.5b) |
| 8 | Giải nén mọi `results_R2_*.zip` vào `results/`, chạy notebook H | 1 người | Colab CPU / máy | < 2 phút | `R2_summary.md`, `R2_fig_gain.png` |
| 9 | Gửi `R2_summary.md` + hình để viết lại paper | – | – | – | Paper bản RQ2 |

**Thứ tự quan trọng:** làm tập người viết (bước 1–5) **trước** khi chạy F, G. Notebook không lưu mô hình, nên nếu chạy trước rồi mới có tập người viết thì phải chạy lại.

## 5. Lệnh cho tập test do người viết

Chạy ở thư mục gốc dự án. Máy chưa cài Python thì dùng `uv run --no-project python` thay cho `python`.

| Bước | Lệnh | Làm gì |
| --- | --- | --- |
| Tạo bảng phân công | `python scripts/human_test.py template --per-label 4 --writers 3 --force` | 180 dòng, 60/người, mỗi nhãn 4 ticket do 3 người khác nhau viết (`--force` ghi đè file cũ – chỉ chạy khi chưa ai điền) |
| Tạo file duyệt mù | `python scripts/human_test.py blind` | Lấy các ticket đã viết, xáo thứ tự, bỏ nhãn; giao chéo: W2 duyệt bài W1, W3 duyệt bài W2, W1 duyệt bài W3 |
| Kiểm tra + tính đồng thuận | `python scripts/human_test.py check` | Báo thiếu/sai, câu giống dữ liệu tổng hợp ≥ 85%, câu trùng; tính % đồng thuận và Cohen's kappa; ghi `disagreements.csv` và `human_test.csv` |
| Đóng gói | `python scripts/human_test.py pack` | Ghi lại `dist/mlr501_data.zip` kèm `human_test.csv` |

Quy tắc khi duyệt: người duyệt chỉ xem `review_blind.csv` và `docs/SUPERAPP_INTENTS.md`, **không** xem `assignment.csv`. Ghi kappa vào paper (kappa ≥ 0,8 thường được xem là đồng thuận cao).

Vì 3 người viết cũng là thành viên nhóm (đã thấy dữ liệu tổng hợp), paper cần ghi rõ điều này ở phần hạn chế; script `check` giúp phát hiện câu giống dữ liệu tổng hợp.

## 6. Các lần chạy Colab

| Lần | Notebook | Sửa gì trước khi chạy | Số lần huấn luyện | Ước tính (T4) | Tải về |
| --- | --- | --- | --- | --- | --- |
| F | `F_rq2_encoders.ipynb` | Không (mặc định PhoBERT + XLM-R, 2 chế độ, 3 seed) | 12 | 30–60 phút | `results_R2_encoders.zip` |
| G-1 | `G_rq2_qwen.ipynb` | Không (mặc định Qwen 3B) | 6 | 1–2 giờ | `results_R2_qwen3b.zip` |
| G-2 (tuỳ chọn) | `G_rq2_qwen.ipynb` | `model_name="Qwen/Qwen2.5-1.5B-Instruct"`, chạy lại từ ô Cấu hình | 6 | 40–80 phút | `results_R2_qwen1.5b.zip` |
| H | `H_rq2_analysis.ipynb` | Không | – | < 2 phút | `results_R2_analysis.zip` |

- Mỗi lần: Runtime → **T4 GPU** → Run all → tải `mlr501_data.zip` (bản đã `pack` ở bước 5). Ô 2 in "Có tập test do người viết: True" là đúng.
- Bật `USE_DRIVE = True` (ô 3): kết quả lưu vào Google Drive sau mỗi lần huấn luyện; Colab ngắt thì Run all lại, lần đã xong sẽ được bỏ qua.
- Thời gian là ước tính, chưa đo trên T4. Lỗi thường gặp xử lý như bước C (bảng trong README: `torchao`, hết bộ nhớ, `loss = nan`).

### Khi Colab hết hạn mức GPU

| Cách | Làm thế nào |
| --- | --- |
| Đổi tài khoản Google (thành viên khác) | Mở notebook bằng tài khoản mới → Run all → ở ô 2 chọn **cùng lúc** `mlr501_data.zip` và `results_R2_*.zip` của lần chạy trước. Ô 3 in "Kết quả cũ đã có: …" và ô huấn luyện in "bỏ qua (đã có)" cho các lần đã xong |
| Kaggle (khoảng 30 giờ GPU/tuần, kiểm tra lại) | kaggle.com → Create → Notebook → File → Import Notebook (chọn file `.ipynb`) → Settings: Accelerator **GPU T4**, Internet **On** (cần xác minh số điện thoại) → Add Input → Upload dataset: `mlr501_data.zip` (và `results_R2_*.zip` nếu chạy tiếp) → Run all. Kết quả tải ở mục **Output** |
| Chờ | Hạn mức Colab miễn phí hồi lại sau vài giờ đến một ngày |

Kết quả luôn lưu sau **từng lần huấn luyện**, nên chuyển máy giữa chừng chỉ mất lần đang chạy dở.

## 7. Đọc kết quả

| Kết quả trên câu không dấu (`gain`) | Kết quả trên câu có dấu | Kết luận cho RQ2 |
| --- | --- | --- |
| Tăng, khoảng tin cậy không chứa 0 | Thay đổi nhỏ, khoảng chứa 0 | Tăng cường **có ích, không gây hại** |
| Tăng, khoảng không chứa 0 | Giảm, khoảng không chứa 0 | Có ích nhưng **đánh đổi**: nêu mức giảm, cân nhắc tỉ lệ nhỏ hơn (vd 25%) |
| Khoảng chứa 0 | – | **Chưa đủ bằng chứng** tăng cường có ích với mô hình đó |
| Tăng trên test tổng hợp nhưng không tăng trên test người viết | – | Mô hình chỉ học được **quy tắc bỏ dấu** của nhóm, chưa chắc giúp với cách người thật gõ → điểm quan trọng phải nêu trong paper |

So sánh thêm 2 cột của tập người viết: `human_nodiac` (người tự gõ) và `human_nodiac_rule` (bỏ dấu bằng quy tắc từ cùng câu). Nếu điểm khác nhau nhiều, cách người thật gõ không dấu khác với quy tắc của nhóm.

## 8. Sửa paper sau khi có kết quả

| Phần | Thay đổi |
| --- | --- |
| Tiêu đề, tóm tắt | Tập trung vào ticket không dấu và tăng cường dữ liệu |
| Mở đầu | RQ2 là câu hỏi chính; RQ1, RQ3 phụ (bảng 2) |
| Dữ liệu | Thêm mục tập test do người viết: số người, số ticket, cách duyệt mù, kappa |
| Phương pháp | Thêm XLM-R; mô tả 2 chế độ, cách giữ số bước bằng nhau, công thức `gain` |
| Kết quả | Bảng chính = bảng 1 của `R2_summary.md`; hình `R2_fig_gain.png`; kết quả cũ (PhoBERT/Qwen chỉ câu sạch) thành mức cơ sở |
| Hạn chế | Bỏ ý "chưa kiểm chứng trên ticket do người viết"; giữ "train là dữ liệu tổng hợp", "test người viết nhỏ" |

## 9. Rủi ro và cách xử lý

| Rủi ro | Cách xử lý |
| --- | --- |
| Người viết chép câu từ dữ liệu hoặc nhờ AI viết | `check` cảnh báo câu giống ≥ 85%; yêu cầu viết lại |
| Excel làm hỏng tiếng Việt | Lưu "CSV UTF-8"; `check` báo lỗi nếu file không phải UTF-8 |
| Hết giờ GPU miễn phí | Ưu tiên F và G-1 (3B); bỏ G-2; dùng `USE_DRIVE` để chạy tiếp hôm sau |
| XLM-R học kém (F1 thấp bất thường trên câu có dấu) | Xem `val_f1` theo epoch trong log; thử `lr=2e-5` hoặc thêm epoch, chạy lại **cả 2 chế độ** với cùng cài đặt |
| Kết quả `aug` tăng chỉ vì test tổng hợp dùng cùng quy tắc bỏ dấu | Đây chính là lý do có test người viết; báo cáo cả hai |
