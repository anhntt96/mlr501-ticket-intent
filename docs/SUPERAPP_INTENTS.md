# Danh mục intent – ticket CSKH super-app

> File sinh tự động bởi `scripts/make_intents_doc.py`. **Đừng sửa tay**: sửa `labels/*.json` rồi chạy lại script.

- Nhãn 2 tầng **v1** (2026-11-16): **9 service × 26 issue = 45 cặp hợp lệ**. Nhãn đầy đủ = `service/issue`, vd `food/charged_but_failed`.
- Danh mục gốc **v0** (2026-11-16): **9 category, 54 intent**, mỗi intent gốc ánh xạ sang 1 nhãn 2 tầng.
- Nhãn 2 tầng: service (dịch vụ) + issue (loại vấn đề). Nhãn đầy đủ = service/issue. Dựa trên danh mục tự lập theo trang trợ giúp công khai của các super-app; không dùng tài liệu nội bộ.

## 1. Ma trận service × issue

✓ = cặp hợp lệ (có dữ liệu).

| Issue | `transport` | `food` | `mart` | `express` | `finance` | `business` | `membership` | `dine_out` | `account` |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| `overcharged` | ✓ | ✓ | ✓ | ✓ |  |  |  |  |  |
| `payment_method_failed` | ✓ | ✓ | ✓ | ✓ |  |  |  |  |  |
| `charged_but_failed` | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  |
| `safety_incident` | ✓ |  |  |  |  |  |  |  |  |
| `driver_no_show` | ✓ |  |  |  |  |  |  |  |  |
| `cannot_book` | ✓ |  |  |  |  |  |  |  |  |
| `lost_item` | ✓ |  |  |  |  |  |  |  |  |
| `trip_howto` | ✓ |  |  |  |  |  |  |  |  |
| `food_safety` |  | ✓ |  |  |  |  |  |  |  |
| `order_cancelled` |  | ✓ | ✓ |  |  |  |  |  |  |
| `order_not_received` |  | ✓ | ✓ | ✓ |  |  |  |  |  |
| `order_missing_wrong` |  | ✓ | ✓ | ✓ |  |  |  |  |  |
| `order_damaged` |  | ✓ | ✓ | ✓ |  |  |  |  |  |
| `fraud_report` |  |  |  |  | ✓ |  |  |  |  |
| `link_card_failed` |  |  |  |  | ✓ | ✓ |  |  |  |
| `business_profile` |  |  |  |  |  | ✓ |  |  |  |
| `refund_request` |  |  |  |  |  | ✓ |  |  |  |
| `membership_cancel` |  |  |  |  |  |  | ✓ |  |  |
| `membership_subscribe` |  |  |  |  |  |  | ✓ |  |  |
| `reservation_issue` |  |  |  |  |  |  |  | ✓ |  |
| `voucher_issue` |  |  |  |  |  |  |  | ✓ |  |
| `update_contact` |  |  |  |  |  | ✓ |  |  | ✓ |
| `login_failed` |  |  |  |  |  |  |  |  | ✓ |
| `forgot_credential` |  |  |  |  |  |  |  |  | ✓ |
| `delete_history` |  |  |  |  |  |  |  |  | ✓ |
| `delete_account` |  |  |  |  |  |  |  |  | ✓ |
| **Số cặp** | 8 | 8 | 7 | 6 | 3 | 4 | 2 | 2 | 5 |

## 2. Service

| Code | Tên | Định nghĩa |
| --- | --- | --- |
| `transport` | Di chuyển | Gọi xe máy, ô tô: chuyến xe, tài xế chở khách, điểm đón, điểm đến. |
| `food` | Đồ ăn | Đặt đồ ăn, đồ uống từ quán/nhà hàng giao tận nơi. |
| `mart` | Đi chợ | Đặt hàng tạp hoá, siêu thị, thực phẩm tươi, đồ gia dụng giao tận nơi. |
| `express` | Giao hàng | Gửi bưu kiện, hàng hoá từ người gửi đến người nhận. |
| `finance` | Tài chính | Ví điện tử, nạp/rút/chuyển tiền, liên kết thẻ ngân hàng, giao dịch không gắn với chuyến xe hay đơn hàng cụ thể. |
| `business` | Doanh nghiệp | Hồ sơ doanh nghiệp, chuyến xe/đơn hàng công tác, thẻ và thanh toán của doanh nghiệp. |
| `membership` | Gói hội viên | Gói hội viên trả phí theo tháng/năm. |
| `dine_out` | Đi ăn nhà hàng | Đặt bàn và dùng voucher khi ăn tại nhà hàng (không giao đồ ăn). |
| `account` | Tài khoản | Đăng nhập, thông tin cá nhân, bảo mật, xoá dữ liệu, xoá tài khoản. |

## 3. Issue (hướng dẫn gán nhãn)

### `overcharged` – Bị tính phí cao hơn giá hiển thị

- **Định nghĩa:** Số tiền bị trừ hoặc phải trả cao hơn giá đã hiển thị khi đặt.
- **Không phải:** Bị trừ tiền khi giao dịch thất bại -> charged_but_failed.
- **Dịch vụ:** `transport`, `food`, `mart`, `express`
- **Ví dụ:** “Lúc đặt xe báo 45k mà xuống xe bị trừ 68k là sao vậy” · “Đơn đồ ăn hiện 120.000đ nhưng ví bị trừ 155.000đ”

### `payment_method_failed` – Không thanh toán được bằng ví điện tử/ngân hàng

- **Định nghĩa:** Không chọn được hoặc thanh toán bị từ chối bằng ví, thẻ, ngân hàng; tiền chưa bị trừ.
- **Không phải:** Tiền đã bị trừ mà giao dịch không thành công -> charged_but_failed. Không thêm/liên kết được thẻ -> link_card_failed.
- **Dịch vụ:** `transport`, `food`, `mart`, `express`
- **Ví dụ:** “Mình chọn thanh toán bằng ví mà cứ báo lỗi, không đặt xe được” · “Thẻ ngân hàng bị từ chối khi đặt đơn đi chợ”

### `charged_but_failed` – Bị trừ tiền dù giao dịch không thành công

- **Định nghĩa:** Tiền đã bị trừ nhưng chuyến xe/đơn hàng/giao dịch báo thất bại hoặc không được tạo.
- **Không phải:** Giao dịch thành công nhưng tính sai số tiền -> overcharged.
- **Dịch vụ:** `transport`, `food`, `mart`, `express`, `finance`
- **Ví dụ:** “Đặt đơn báo thất bại mà tài khoản ngân hàng vẫn bị trừ 230.000đ” · “Nạp tiền vào ví không thành công nhưng ngân hàng đã trừ tiền”

### `safety_incident` – Báo cáo tai nạn, sự cố an toàn

- **Định nghĩa:** Tai nạn giao thông, va chạm, tài xế lái ẩu, quấy rối, đe doạ, hoặc tình huống nguy hiểm trong chuyến xe.
- **Không phải:** Tài xế không đến -> driver_no_show.
- **Dịch vụ:** `transport`
- **Ví dụ:** “Tài xế chạy quá nhanh rồi va vào xe khác, tôi bị trầy chân” · “Tài xế nói năng thô tục và có hành vi quấy rối tôi”

### `driver_no_show` – Tài xế không đến điểm đón

- **Định nghĩa:** Đã có tài xế nhận chuyến nhưng không đến, đến sai chỗ, hoặc bắt khách tự huỷ.
- **Không phải:** Không tìm được tài xế/không đặt được -> cannot_book.
- **Dịch vụ:** `transport`
- **Ví dụ:** “Tài xế nhận chuyến rồi đứng im một chỗ 20 phút không tới” · “Chờ mãi tài xế không đến điểm đón, gọi không nghe máy”

### `cannot_book` – Không đặt được xe

- **Định nghĩa:** Không tạo được chuyến: không có tài xế nhận, ứng dụng báo lỗi khi đặt, không bấm đặt được.
- **Không phải:** Lỗi do phương thức thanh toán -> payment_method_failed.
- **Dịch vụ:** `transport`
- **Ví dụ:** “Bấm đặt xe hoài mà không có tài xế nào nhận” · “App báo lỗi hệ thống mỗi lần tôi đặt xe”

### `lost_item` – Để quên đồ/điện thoại trên xe

- **Định nghĩa:** Khách để quên đồ vật trên xe sau chuyến đi, muốn liên hệ tài xế lấy lại.
- **Dịch vụ:** `transport`
- **Ví dụ:** “Em để quên điện thoại trên xe lúc 8h sáng nay, giúp em liên hệ tài xế” · “Tôi bỏ quên túi xách trên xe, làm sao lấy lại”

### `trip_howto` – Hỏi cách dùng tính năng chuyến xe

- **Định nghĩa:** Câu hỏi cách làm: theo dõi tài xế, đổi điểm đến, chọn hồ sơ thanh toán, quản lý địa điểm đã lưu, thêm điểm dừng. Không phải khiếu nại.
- **Dịch vụ:** `transport`
- **Ví dụ:** “Làm sao thêm điểm dừng giữa đường khi đang đi?” · “Đổi điểm đến khi tài xế đã nhận chuyến được không”

### `food_safety` – Vệ sinh an toàn thực phẩm

- **Định nghĩa:** Dị vật trong món ăn, mất vệ sinh, nghi ngộ độc, đau bụng sau khi ăn.
- **Không phải:** Món bị đổ, nguội, ôi, hỏng nhưng không có dị vật/ngộ độc -> order_damaged.
- **Dịch vụ:** `food`
- **Ví dụ:** “Trong tô phở có con gián, quá kinh khủng” · “Ăn xong cả nhà bị đau bụng, nghi ngộ độc thức ăn”

### `order_cancelled` – Đơn hàng bị huỷ

- **Định nghĩa:** Đơn bị quán/cửa hàng/tài xế/hệ thống huỷ mà khách không muốn, hoặc khách hỏi vì sao đơn bị huỷ.
- **Không phải:** Khách muốn tự huỷ đơn: hiện chưa có nhãn riêng.
- **Dịch vụ:** `food`, `mart`
- **Ví dụ:** “Đơn đồ ăn của tôi tự nhiên bị huỷ dù đã chờ 30 phút” · “Sao đơn đi chợ bị huỷ mà không báo lý do”

### `order_not_received` – Chưa nhận được đơn / giao không thành công

- **Định nghĩa:** App báo đã giao hoặc đang giao quá lâu nhưng người nhận chưa nhận được; tài xế giao không thành công.
- **Không phải:** Nhận được nhưng thiếu/sai -> order_missing_wrong.
- **Dịch vụ:** `food`, `mart`, `express`
- **Ví dụ:** “App báo đã giao mà tôi chưa nhận được gì” · “Người nhận chưa nhận được bưu kiện dù đã 3 ngày”

### `order_missing_wrong` – Thiếu hoặc sai món/sản phẩm, nhận nhầm đơn

- **Định nghĩa:** Nhận được đơn nhưng thiếu món, sai món, sai sản phẩm, hoặc nhận nhầm đơn của người khác.
- **Không phải:** Hàng đúng nhưng hư/đổ -> order_damaged.
- **Dịch vụ:** `food`, `mart`, `express`
- **Ví dụ:** “Đặt 2 ly trà sữa mà chỉ nhận 1 ly” · “Đơn đi chợ giao nhầm sữa tươi thành sữa chua”

### `order_damaged` – Hàng/món bị đổ, hư hỏng, kém chất lượng, thất lạc

- **Định nghĩa:** Thức ăn bị đổ, ôi, hỏng; sản phẩm kém chất lượng, hết hạn; bưu gửi hư hại hoặc thất lạc.
- **Không phải:** Dị vật, ngộ độc -> food_safety.
- **Dịch vụ:** `food`, `mart`, `express`
- **Ví dụ:** “Canh bị đổ hết ra túi, không ăn được” · “Bưu kiện tới nơi bị móp méo, đồ bên trong vỡ”

### `fraud_report` – Báo cáo bất thường, gian lận, lừa đảo

- **Định nghĩa:** Giao dịch lạ không phải mình làm, tài khoản bị chiếm, bị lừa chuyển tiền, tin nhắn giả mạo.
- **Dịch vụ:** `finance`
- **Ví dụ:** “Ví bị trừ 2 triệu mà tôi không hề giao dịch” · “Có người giả nhân viên gọi xin mã OTP, tôi lỡ đưa rồi”

### `link_card_failed` – Không liên kết/thêm được thẻ, ví

- **Định nghĩa:** Không thêm hoặc liên kết được thẻ ngân hàng, thẻ tín dụng (kể cả thẻ doanh nghiệp), ví điện tử vào tài khoản.
- **Không phải:** Thẻ đã liên kết nhưng thanh toán bị lỗi -> payment_method_failed.
- **Dịch vụ:** `finance`, `business`
- **Ví dụ:** “Liên kết thẻ Vietcombank báo lỗi hoài” · “Không thêm được thẻ tín dụng công ty vào hồ sơ doanh nghiệp”

### `business_profile` – Vấn đề hồ sơ doanh nghiệp

- **Định nghĩa:** Không tạo được hồ sơ doanh nghiệp, chuyến/đơn công tác bị tính vào hồ sơ cá nhân.
- **Không phải:** Đổi email/SĐT -> update_contact.
- **Dịch vụ:** `business`
- **Ví dụ:** “Tạo hồ sơ doanh nghiệp mãi không được” · “Chuyến đi công tác sáng nay bị tính vào hồ sơ cá nhân”

### `refund_request` – Yêu cầu hoàn tiền chuyến xe/đơn hàng

- **Định nghĩa:** Yêu cầu hoàn tiền cho chuyến xe hoặc đơn hàng đã thanh toán bằng hồ sơ/thẻ doanh nghiệp, không kèm lỗi cụ thể khác.
- **Không phải:** Có lỗi cụ thể (thiếu món, bị trừ tiền khi thất bại...) -> dùng issue của lỗi đó.
- **Dịch vụ:** `business`
- **Ví dụ:** “Công ty cần hoàn tiền chuyến xe ngày 12/11 đã trả bằng thẻ doanh nghiệp” · “Làm sao yêu cầu hoàn tiền cho đơn công tác”

### `membership_cancel` – Không huỷ được gói hội viên

- **Định nghĩa:** Muốn huỷ gói hội viên nhưng không tìm thấy chỗ huỷ hoặc huỷ bị lỗi, vẫn bị gia hạn.
- **Dịch vụ:** `membership`
- **Ví dụ:** “Tôi đã huỷ gói hội viên mà tháng này vẫn bị trừ tiền” · “Tìm mãi không thấy chỗ huỷ gói hội viên”

### `membership_subscribe` – Không đăng ký được gói hội viên

- **Định nghĩa:** Muốn đăng ký hoặc nâng cấp gói hội viên nhưng không được.
- **Dịch vụ:** `membership`
- **Ví dụ:** “Bấm đăng ký gói hội viên báo lỗi” · “Sao tài khoản tôi không đăng ký được gói tiết kiệm”

### `reservation_issue` – Vấn đề đặt bàn nhà hàng

- **Định nghĩa:** Không đặt được bàn, đến nơi nhà hàng không có bàn đã đặt, đổi/huỷ đặt bàn.
- **Dịch vụ:** `dine_out`
- **Ví dụ:** “Tôi đặt bàn 7h tối qua app mà tới nơi quán nói không có” · “Muốn đổi giờ đặt bàn thì làm sao”

### `voucher_issue` – Vấn đề voucher nhà hàng

- **Định nghĩa:** Không áp dụng được voucher ăn tại nhà hàng, voucher bị từ chối, mua voucher không nhận được.
- **Dịch vụ:** `dine_out`
- **Ví dụ:** “Nhà hàng không chịu nhận voucher tôi mua trên app” · “Mua voucher buffet rồi mà không thấy trong tài khoản”

### `update_contact` – Đổi số điện thoại/email

- **Định nghĩa:** Cập nhật số điện thoại, email của tài khoản cá nhân hoặc hồ sơ doanh nghiệp; xác minh số mới.
- **Dịch vụ:** `account`, `business`
- **Ví dụ:** “Tôi đổi sim mới, muốn cập nhật số điện thoại” · “Cần đổi email nhận hoá đơn của hồ sơ doanh nghiệp”

### `login_failed` – Không đăng nhập được

- **Định nghĩa:** Không vào được tài khoản: không nhận OTP, tài khoản bị khoá, báo lỗi khi đăng nhập.
- **Không phải:** Quên mật khẩu/PIN -> forgot_credential.
- **Dịch vụ:** `account`
- **Ví dụ:** “Đăng nhập không nhận được mã OTP” · “Tài khoản bị khoá, không vào được app”

### `forgot_credential` – Quên mật khẩu / mã PIN

- **Định nghĩa:** Quên mật khẩu hoặc mã PIN, muốn đặt lại.
- **Dịch vụ:** `account`
- **Ví dụ:** “Em quên mã PIN ví, đặt lại sao ạ” · “Quên mật khẩu tài khoản rồi”

### `delete_history` – Xoá lịch sử chuyến xe

- **Định nghĩa:** Muốn xoá lịch sử chuyến xe, đơn hàng khỏi tài khoản.
- **Không phải:** Xoá cả tài khoản -> delete_account.
- **Dịch vụ:** `account`
- **Ví dụ:** “Làm sao xoá lịch sử các chuyến xe cũ” · “Tôi muốn xoá lịch sử đi lại trong app”

### `delete_account` – Xoá vĩnh viễn tài khoản

- **Định nghĩa:** Muốn xoá vĩnh viễn tài khoản và dữ liệu.
- **Dịch vụ:** `account`
- **Ví dụ:** “Tôi muốn xoá vĩnh viễn tài khoản” · “Không dùng nữa, xoá tài khoản giúp tôi”

### Quy tắc chung

- Ticket nêu nhiều vấn đề → chọn vấn đề **chính** (khách muốn được giải quyết nhất).
- Ticket không nói rõ dịch vụ → vẫn gán service theo ngữ cảnh; đây là nguồn nhầm lẫn cần phân tích.

## 4. Danh mục gốc → nhãn 2 tầng

Nguồn: Danh mục do Tuấn Anh lập (tham khảo trang trợ giúp công khai của các super-app), trước khi gộp thành nhãn 2 tầng.

| Category | Nhóm vấn đề | Intent gốc | Nhãn 2 tầng |
| --- | --- | --- | --- |
| Di chuyển (Transportation) | Vấn đề liên quan đến an toàn | Báo cáo tai nạn | `transport/safety_incident` |
|  | Vấn đề liên quan đến an toàn | Báo cáo sự cố | `transport/safety_incident` |
|  | Vấn đề về thanh toán | Bị tính phí cao hơn giá hiển thị | `transport/overcharged` |
|  | Vấn đề về thanh toán | Không thể thanh toán bằng ví điện tử hoặc ngân hàng | `transport/payment_method_failed` |
|  | Vấn đề về thanh toán | Bị trừ tiền dù giao dịch không thành công | `transport/charged_but_failed` |
|  | Vấn đề về chuyến xe | Tài xế không đến điểm đón | `transport/driver_no_show` |
|  | Vấn đề về chuyến xe | Không đặt được xe | `transport/cannot_book` |
|  | Vấn đề về chuyến xe | Để quên đồ hoặc điện thoại trên xe | `transport/lost_item` |
|  | Câu hỏi thường gặp | Theo dõi tài xế | `transport/trip_howto` |
|  | Câu hỏi thường gặp | Thay đổi điểm đến | `transport/trip_howto` |
|  | Câu hỏi thường gặp | Chọn hồ sơ thanh toán | `transport/trip_howto` |
|  | Câu hỏi thường gặp | Quản lý địa điểm đã lưu | `transport/trip_howto` |
|  | Câu hỏi thường gặp | Thêm điểm dừng | `transport/trip_howto` |
| Đồ ăn (Food) | Vấn đề vệ sinh an toàn thực phẩm | Vấn đề vệ sinh an toàn thực phẩm | `food/food_safety` |
|  | Vấn đề về thanh toán | Bị tính phí cao hơn giá hiển thị | `food/overcharged` |
|  | Vấn đề về thanh toán | Không thể thanh toán bằng ví điện tử hoặc ngân hàng | `food/payment_method_failed` |
|  | Vấn đề về thanh toán | Bị trừ tiền dù giao dịch không thành công | `food/charged_but_failed` |
|  | Vấn đề về đơn hàng | Đơn hàng bị huỷ | `food/order_cancelled` |
|  | Vấn đề về đơn hàng | Đơn hàng không được giao | `food/order_not_received` |
|  | Vấn đề về đơn hàng | Đơn hàng bị thiếu hoặc sai món ăn | `food/order_missing_wrong` |
|  | Vấn đề về đơn hàng | Thức ăn bị đổ | `food/order_damaged` |
|  | Vấn đề về đơn hàng | Thức ăn bị hư hỏng | `food/order_damaged` |
| Đi chợ (Mart) | Vấn đề về đơn hàng | Đơn hàng bị huỷ | `mart/order_cancelled` |
|  | Vấn đề về đơn hàng | Đơn hàng không được giao | `mart/order_not_received` |
|  | Vấn đề về đơn hàng | Đơn hàng bị thiếu hoặc sai sản phẩm | `mart/order_missing_wrong` |
|  | Vấn đề về đơn hàng | Đơn hàng kém chất lượng | `mart/order_damaged` |
|  | Vấn đề về thanh toán | Bị tính phí cao hơn giá hiển thị | `mart/overcharged` |
|  | Vấn đề về thanh toán | Không thể thanh toán bằng ví điện tử hoặc ngân hàng | `mart/payment_method_failed` |
|  | Vấn đề về thanh toán | Bị trừ tiền dù giao dịch không thành công | `mart/charged_but_failed` |
| Giao hàng (Express) | Vấn đề về hàng hoá và giao nhận | Bưu gửi bị thất lạc hoặc hư hại | `express/order_damaged` |
|  | Vấn đề về hàng hoá và giao nhận | Nhận sai đơn hàng | `express/order_missing_wrong` |
|  | Vấn đề về hàng hoá và giao nhận | Người nhận chưa nhận được đơn hàng | `express/order_not_received` |
|  | Vấn đề về hàng hoá và giao nhận | Tài xế giao hàng không thành công | `express/order_not_received` |
|  | Vấn đề về thanh toán | Bị tính phí cao hơn giá hiển thị | `express/overcharged` |
|  | Vấn đề về thanh toán | Không thể thanh toán bằng ví điện tử hoặc ngân hàng | `express/payment_method_failed` |
|  | Vấn đề về thanh toán | Bị trừ tiền dù giao dịch không thành công | `express/charged_but_failed` |
| Tài chính | – | Báo cáo hoạt động bất thường, gian lận, hoặc lừa đảo trong tài khoản | `finance/fraud_report` |
|  | – | Bị trừ tiền cho giao dịch không thành công | `finance/charged_but_failed` |
|  | – | Không thể liên kết thẻ ngân hàng, ví điện tử vào tài khoản | `finance/link_card_failed` |
| Doanh nghiệp | Vấn đề về hồ sơ doanh nghiệp | Không thể tạo hồ sơ doanh nghiệp | `business/business_profile` |
|  | Vấn đề về hồ sơ doanh nghiệp | Thay đổi thông tin liên lạc như email hoặc số điện thoại | `business/update_contact` |
|  | Vấn đề về hồ sơ doanh nghiệp | Chuyến xe công việc bị tính vào hồ sơ cá nhân | `business/business_profile` |
|  | Vấn đề về thanh toán | Không thêm được thẻ tín dụng doanh nghiệp | `business/link_card_failed` |
|  | Vấn đề về thanh toán | Yêu cầu hoàn tiền cho chuyến xe hoặc đơn hàng | `business/refund_request` |
| Gói hội viên | Vấn đề về gói hội viên | Không thể huỷ gói hội viên | `membership/membership_cancel` |
|  | Vấn đề về gói hội viên | Không thể đăng kí gói hội viên | `membership/membership_subscribe` |
| Đi ăn nhà hàng | – | Vấn đề với dịch vụ đặt bàn nhà hàng | `dine_out/reservation_issue` |
|  | – | Vấn đề với voucher nhà hàng | `dine_out/voucher_issue` |
| Tài khoản | Xác minh tài khoản | Cập nhật số điện thoại mới | `account/update_contact` |
|  | Vấn đề với tài khoản | Không thể đăng nhập | `account/login_failed` |
|  | Vấn đề với tài khoản | Quên mật khẩu | `account/forgot_credential` |
|  | Vấn đề với tài khoản | Quên mã PIN | `account/forgot_credential` |
|  | – | Xoá lịch sử chuyến xe | `account/delete_history` |
|  | – | Xoá vĩnh viễn tài khoản của tôi | `account/delete_account` |

Các nhãn gộp nhiều intent gốc (6 nhãn):

- `account/forgot_credential` ← Quên mật khẩu · Quên mã PIN
- `business/business_profile` ← Không thể tạo hồ sơ doanh nghiệp · Chuyến xe công việc bị tính vào hồ sơ cá nhân
- `express/order_not_received` ← Người nhận chưa nhận được đơn hàng · Tài xế giao hàng không thành công
- `food/order_damaged` ← Thức ăn bị đổ · Thức ăn bị hư hỏng
- `transport/safety_incident` ← Báo cáo tai nạn · Báo cáo sự cố
- `transport/trip_howto` ← Theo dõi tài xế · Thay đổi điểm đến · Chọn hồ sơ thanh toán · Quản lý địa điểm đã lưu · Thêm điểm dừng
