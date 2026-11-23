# Hướng dẫn viết và duyệt ticket cho tập kiểm thử (3 người)

Mỗi người làm 2 việc: **(1) viết** 60 tin nhắn, **(2) duyệt mù** 60 tin nhắn của người khác.
Bạn đóng vai **khách hàng** của một siêu ứng dụng (gọi xe, đặt đồ ăn, đi chợ, giao hàng, ví điện tử…) và nhắn cho bộ phận chăm sóc khách hàng.

| Mã | Viết | Duyệt bài của |
| --- | --- | --- |
| W1 | 60 tin nhắn | W3 |
| W2 | 60 tin nhắn | W1 |
| W3 | 60 tin nhắn | W2 |

Thời gian: viết khoảng 90–120 phút, duyệt khoảng 45–60 phút mỗi người.

---

## Phần 1 – Viết

Mở `assignment.csv`, lọc cột `writer` = mã của bạn. Mỗi dòng là **một tin nhắn cần viết**:

| Cột | Ý nghĩa |
| --- | --- |
| `dich_vu` | Dịch vụ mà tin nhắn nói tới (vd: Đồ ăn, Đi chợ, Di chuyển) |
| `van_de` | Vấn đề khách gặp (vd: Bị tính phí cao hơn giá hiển thị) |
| `dinh_nghia` | Giải thích thêm vấn đề đó là gì |
| `yeu_cau` | **NÊU RÕ dịch vụ**: tin nhắn phải cho biết là dịch vụ nào. **KHÔNG nêu tên dịch vụ**: viết như khách không nói rõ (vd "bị trừ tiền mà giao dịch báo lỗi") |

Bạn chỉ điền 3 cột:

| Cột | Cách điền |
| --- | --- |
| `text` | Tin nhắn **có dấu**, viết như bạn nhắn thật cho tổng đài (1–2 câu, khoảng 8–25 chữ) |
| `text_nodiac` | **Cùng nội dung đó**, gõ lại **không dấu** như khi điện thoại không bật bộ gõ tiếng Việt. Gõ tự nhiên theo thói quen của bạn: có thể viết tắt, viết thường, thiếu dấu câu |
| `ghi_chu` | (Không bắt buộc) chỗ bạn thấy khó hoặc không chắc |

**Không sửa các cột khác**, kể cả `label` và `label_final` (cột này nhóm dùng ở Phần 3).

### Ví dụ

| van_de | yeu_cau | text | text_nodiac |
| --- | --- | --- | --- |
| Đồ ăn – Đơn hàng bị huỷ | NÊU RÕ dịch vụ | Mình đặt bún bò lúc 12h mà quán tự huỷ đơn, tiền vẫn chưa thấy hoàn | minh dat bun bo luc 12h ma quan tu huy don tien van chua thay hoan |
| Đi chợ – Bị trừ tiền dù giao dịch không thành công | KHÔNG nêu tên dịch vụ | Thanh toán báo lỗi mà tài khoản mình vẫn bị trừ 180k | thanh toan bao loi ma tk minh van bi tru 180k |

### Quy tắc khi viết

1. **Tự viết theo cách của bạn.** Không mở dữ liệu của nhóm (`data/superapp/`) và không nhờ AI (ChatGPT, Claude…) viết. Script kiểm tra sẽ báo câu giống dữ liệu có sẵn.
2. **Mỗi tin nhắn một vấn đề chính**, đúng với `van_de` được giao.
3. **Đa dạng**: đổi cách xưng hô (tôi/em/mình), giọng (lịch sự/bực bội), chi tiết (mã đơn, số tiền, giờ, tên ngân hàng…). Không dùng thông tin cá nhân thật.
4. Không bàn với 2 người còn lại về cách viết từng câu – mỗi người một văn phong là điều nhóm cần.

---

## Phần 2 – Duyệt mù (sau khi cả 3 đã viết xong)

Trưởng nhóm gửi file `review_blind.csv`. Lọc cột `reviewer` = mã của bạn: đó là 60 tin nhắn **của người khác**, đã xáo thứ tự và **không kèm nhãn**.

| Cột | Cách điền |
| --- | --- |
| `label_reviewer` | Đọc tin nhắn, chọn **1 trong 45 nhãn** dạng `dịch_vụ/vấn_đề` (vd `food/order_cancelled`). Danh sách nhãn và định nghĩa: `docs/SUPERAPP_INTENTS.md`, mục 1–3 |

Quy tắc khi duyệt:

1. **Không mở `assignment.csv`** trong lúc duyệt (file đó có nhãn gốc).
2. Gán theo **nội dung tin nhắn**, không đoán xem người viết "định" viết nhãn gì.
3. Tin nhắn không nói dịch vụ: chọn dịch vụ hợp lý nhất theo ngữ cảnh (quy tắc chung trong `SUPERAPP_INTENTS.md`).
4. Gõ nhãn chính xác từng ký tự (nên copy từ danh sách nhãn).

---

## Phần 3 – Thống nhất (cả nhóm, khoảng 1 buổi)

Trưởng nhóm chạy `check`, script tạo `disagreements.csv` gồm các tin nhắn mà nhãn của người duyệt khác nhãn được giao. Cả nhóm xem từng dòng:

| Kết luận | Làm gì trong `assignment.csv` |
| --- | --- |
| Người duyệt đúng (tin nhắn thực ra thuộc nhãn khác) | Ghi nhãn đúng vào cột `label_final`, ghi lý do vào `ghi_chu` |
| Nhãn được giao đúng | Để trống `label_final` |
| Tin nhắn mơ hồ, đọc kiểu nào cũng được | Người viết sửa lại `text` và `text_nodiac` cho rõ, để trống `label_final` |

---

## Lưu file

- Excel: **File → Save As → "CSV UTF-8 (Comma delimited)"** (chọn sai kiểu sẽ hỏng tiếng Việt).
- Google Sheets: **Tệp → Tải xuống → Giá trị được phân tách bằng dấu phẩy (.csv)**.
- Gửi lại file cho trưởng nhóm, **giữ nguyên tên file và các cột**.
