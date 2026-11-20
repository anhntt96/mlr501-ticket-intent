# Kết quả so sánh mô hình

## Bảng 1. macro-F1 nhãn đầy đủ (TB ± độ lệch giữa seed)

| Hệ thống | Chuẩn | Bỏ dấu | Teencode | Telex lỗi | Trộn tiếng Anh | Trộn cả 3 | TB nhiễu |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PhoBERT-base (flat) | 0.791 ± 0.011 | 0.160 ± 0.031 | 0.782 ± 0.031 | 0.632 ± 0.034 | 0.742 ± 0.016 | 0.193 ± 0.013 | 0.502 ± 0.012 |
| PhoBERT-base (hier) | 0.810 ± 0.014 | 0.161 ± 0.030 | 0.786 ± 0.017 | 0.642 ± 0.031 | 0.746 ± 0.016 | 0.166 ± 0.009 | 0.500 ± 0.016 |
| Qwen2.5-1.5B+LoRA | 0.870 ± 0.010 | 0.347 ± 0.056 | 0.860 ± 0.008 | 0.733 ± 0.015 | 0.878 ± 0.007 | 0.321 ± 0.022 | 0.628 ± 0.014 |
| Qwen2.5-3B+LoRA | 0.901 ± 0.011 | 0.563 ± 0.014 | 0.880 ± 0.021 | 0.823 ± 0.007 | 0.900 ± 0.012 | 0.613 ± 0.012 | 0.756 ± 0.004 |

## Bảng 2. Mức giảm F1 so với câu chuẩn

| Hệ thống | Bỏ dấu | Teencode | Telex lỗi | Trộn tiếng Anh | Trộn cả 3 |
| --- | --- | --- | --- | --- | --- |
| PhoBERT-base (flat) | -0.631 | -0.009 | -0.159 | -0.049 | -0.598 |
| PhoBERT-base (hier) | -0.649 | -0.024 | -0.168 | -0.064 | -0.644 |
| Qwen2.5-1.5B+LoRA | -0.523 | -0.01 | -0.137 | 0.007 | -0.549 |
| Qwen2.5-3B+LoRA | -0.338 | -0.021 | -0.078 | -0.001 | -0.288 |

## Bảng 3. Giữ lại % điểm câu chuẩn

| Hệ thống | Bỏ dấu | Teencode | Telex lỗi | Trộn tiếng Anh | Trộn cả 3 |
| --- | --- | --- | --- | --- | --- |
| PhoBERT-base (flat) | 20.0 | 99.0 | 80.0 | 94.0 | 24.0 |
| PhoBERT-base (hier) | 20.0 | 97.0 | 79.0 | 92.0 | 20.0 |
| Qwen2.5-1.5B+LoRA | 40.0 | 99.0 | 84.0 | 101.0 | 37.0 |
| Qwen2.5-3B+LoRA | 63.0 | 98.0 | 91.0 | 100.0 | 68.0 |

## Bảng 4. Chi tiết (câu chuẩn, bỏ dấu)

| Biến thể | Hệ thống | acc | f1 | f1_service | f1_issue | invalid |
| --- | --- | --- | --- | --- | --- | --- |
| clean | PhoBERT-base (flat) | 0.8 | 0.791 | 0.889 | 0.876 | 0.0 |
| clean | PhoBERT-base (hier) | 0.822 | 0.81 | 0.915 | 0.844 | 0.0 |
| clean | Qwen2.5-1.5B+LoRA | 0.881 | 0.87 | 0.934 | 0.91 | 0.0 |
| clean | Qwen2.5-3B+LoRA | 0.906 | 0.901 | 0.946 | 0.938 | 0.0 |
| no_diacritics | PhoBERT-base (flat) | 0.215 | 0.16 | 0.414 | 0.264 | 0.0 |
| no_diacritics | PhoBERT-base (hier) | 0.207 | 0.161 | 0.418 | 0.248 | 0.0 |
| no_diacritics | Qwen2.5-1.5B+LoRA | 0.395 | 0.347 | 0.584 | 0.449 | 0.0 |
| no_diacritics | Qwen2.5-3B+LoRA | 0.593 | 0.563 | 0.775 | 0.681 | 0.0 |

## Bảng 5. Cơ cấu lỗi

| Biến thể | Hệ thống | Đúng | Sai issue | Sai service | Sai cả hai |
| --- | --- | --- | --- | --- | --- |
| clean | PhoBERT-base (flat) | 0.8 | 0.064 | 0.081 | 0.054 |
| clean | PhoBERT-base (hier) | 0.822 | 0.077 | 0.074 | 0.027 |
| clean | Qwen2.5-1.5B+LoRA | 0.881 | 0.035 | 0.049 | 0.035 |
| clean | Qwen2.5-3B+LoRA | 0.906 | 0.025 | 0.044 | 0.025 |
| code_switch | PhoBERT-base (flat) | 0.76 | 0.094 | 0.086 | 0.059 |
| code_switch | PhoBERT-base (hier) | 0.768 | 0.133 | 0.057 | 0.042 |
| code_switch | Qwen2.5-1.5B+LoRA | 0.889 | 0.032 | 0.04 | 0.04 |
| code_switch | Qwen2.5-3B+LoRA | 0.906 | 0.022 | 0.042 | 0.03 |
| mixed | PhoBERT-base (flat) | 0.249 | 0.198 | 0.077 | 0.477 |
| mixed | PhoBERT-base (hier) | 0.217 | 0.267 | 0.126 | 0.39 |
| mixed | Qwen2.5-1.5B+LoRA | 0.373 | 0.2 | 0.126 | 0.301 |
| mixed | Qwen2.5-3B+LoRA | 0.635 | 0.123 | 0.123 | 0.119 |
| no_diacritics | PhoBERT-base (flat) | 0.215 | 0.215 | 0.079 | 0.491 |
| no_diacritics | PhoBERT-base (hier) | 0.207 | 0.267 | 0.114 | 0.412 |
| no_diacritics | Qwen2.5-1.5B+LoRA | 0.395 | 0.232 | 0.121 | 0.252 |
| no_diacritics | Qwen2.5-3B+LoRA | 0.593 | 0.156 | 0.123 | 0.128 |
| teencode | PhoBERT-base (flat) | 0.79 | 0.089 | 0.064 | 0.057 |
| teencode | PhoBERT-base (hier) | 0.807 | 0.101 | 0.059 | 0.032 |
| teencode | Qwen2.5-1.5B+LoRA | 0.872 | 0.035 | 0.044 | 0.049 |
| teencode | Qwen2.5-3B+LoRA | 0.884 | 0.032 | 0.054 | 0.03 |
| telex | PhoBERT-base (flat) | 0.652 | 0.114 | 0.116 | 0.119 |
| telex | PhoBERT-base (hier) | 0.657 | 0.168 | 0.111 | 0.064 |
| telex | Qwen2.5-1.5B+LoRA | 0.743 | 0.079 | 0.101 | 0.077 |
| telex | Qwen2.5-3B+LoRA | 0.83 | 0.059 | 0.072 | 0.04 |

## Bảng 6. Đoán đúng service theo explicit (câu chuẩn)

| Hệ thống | explicit=0 | explicit=1 | n_câu explicit=0 |
| --- | --- | --- | --- |
| PhoBERT-base (flat) | 0.0 | 0.897 | 5 |
| PhoBERT-base (hier) | 0.0 | 0.933 | 5 |
| Qwen2.5-1.5B+LoRA | 0.067 | 0.949 | 5 |
| Qwen2.5-3B+LoRA | 0.133 | 0.962 | 5 |

## Bảng 7. Cặp nhầm nhiều nhất (câu chuẩn)

| system | label | pred | lần |
| --- | --- | --- | --- |
| PhoBERT-base (flat) | food/order_missing_wrong | mart/order_missing_wrong | 4 |
| PhoBERT-base (flat) | mart/order_not_received | food/order_not_received | 4 |
| PhoBERT-base (flat) | food/order_cancelled | mart/order_cancelled | 3 |
| PhoBERT-base (flat) | food/overcharged | transport/overcharged | 3 |
| PhoBERT-base (flat) | food/payment_method_failed | finance/charged_but_failed | 3 |
| PhoBERT-base (hier) | food/order_missing_wrong | mart/order_missing_wrong | 4 |
| PhoBERT-base (hier) | account/delete_account | account/login_failed | 3 |
| PhoBERT-base (hier) | business/business_profile | business/link_card_failed | 3 |
| PhoBERT-base (hier) | food/food_safety | food/order_damaged | 3 |
| PhoBERT-base (hier) | food/food_safety | food/order_missing_wrong | 3 |
| Qwen2.5-1.5B+LoRA | account/delete_history | mart/order_cancelled | 3 |
| Qwen2.5-1.5B+LoRA | express/overcharged | express/order_not_received | 3 |
| Qwen2.5-1.5B+LoRA | food/charged_but_failed | transport/charged_but_failed | 3 |
| Qwen2.5-1.5B+LoRA | mart/charged_but_failed | food/charged_but_failed | 3 |
| Qwen2.5-1.5B+LoRA | transport/trip_howto | business/business_profile | 3 |
| Qwen2.5-3B+LoRA | finance/fraud_report | mart/charged_but_failed | 3 |
| Qwen2.5-3B+LoRA | transport/trip_howto | business/business_profile | 3 |
| Qwen2.5-3B+LoRA | express/overcharged | express/order_not_received | 2 |
| Qwen2.5-3B+LoRA | food/order_missing_wrong | mart/order_missing_wrong | 2 |
| Qwen2.5-3B+LoRA | food/payment_method_failed | business/link_card_failed | 2 |

## Bảng 8. Câu mọi hệ thống đều sai (6 câu)

| id | text | label | explicit | PhoBERT-base (flat) | PhoBERT-base (hier) | Qwen2.5-1.5B+LoRA | Qwen2.5-3B+LoRA |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t0129 | Hướng dẫn mình chuyển từ hồ sơ cá nhân sang hồ sơ doanh nghiệp khi đặt xe | transport/trip_howto | 1 | business/business_profile | business/update_contact | business/business_profile | business/business_profile |
| t0200 | Tôi bị tính tiền cao hơn giá hiển thị trên app, cần hoàn phần chênh lệch | mart/overcharged | 0 | transport/overcharged | transport/overcharged | express/overcharged | transport/overcharged |
| t0242 | Không thanh toán được bằng thẻ ngân hàng, tiền chưa bị trừ | mart/payment_method_failed | 0 | finance/charged_but_failed | express/payment_method_failed | transport/payment_method_failed | food/payment_method_failed |
| t0594 | Thanh toán thất bại mà tài khoản ngân hàng vẫn bị trừ, giải quyết giúp tôi | transport/charged_but_failed | 0 | finance/charged_but_failed | finance/charged_but_failed | finance/charged_but_failed | food/charged_but_failed |
| t0797 | Bị trừ tiền dù giao dịch báo không thành công | mart/charged_but_failed | 0 | transport/charged_but_failed | food/charged_but_failed | food/charged_but_failed | food/charged_but_failed |
| t0852 | Sao tôi không thấy tài xế di chuyển trên bản đồ, xem ở đâu vậy | transport/trip_howto | 1 | transport/driver_no_show | transport/safety_incident | transport/driver_no_show | transport/driver_no_show |

## Bảng 9. Bootstrap: chênh lệch F1 so với PhoBERT-base (hier) (CI 95%)

| variant | system | delta | ci_low | ci_high | significant |
| --- | --- | --- | --- | --- | --- |
| Chuẩn | PhoBERT-base (flat) | -0.02 | -0.076 | 0.032 | False |
| Chuẩn | Qwen2.5-1.5B+LoRA | 0.07 | 0.012 | 0.13 | True |
| Chuẩn | Qwen2.5-3B+LoRA | 0.105 | 0.046 | 0.161 | True |
| Bỏ dấu | PhoBERT-base (flat) | 0.001 | -0.031 | 0.033 | False |
| Bỏ dấu | Qwen2.5-1.5B+LoRA | 0.17 | 0.12 | 0.224 | True |
| Bỏ dấu | Qwen2.5-3B+LoRA | 0.375 | 0.309 | 0.441 | True |
| Teencode | PhoBERT-base (flat) | -0.01 | -0.07 | 0.045 | False |
| Teencode | Qwen2.5-1.5B+LoRA | 0.08 | 0.023 | 0.138 | True |
| Teencode | Qwen2.5-3B+LoRA | 0.1 | 0.043 | 0.157 | True |
| Telex lỗi | PhoBERT-base (flat) | -0.011 | -0.074 | 0.048 | False |
| Telex lỗi | Qwen2.5-1.5B+LoRA | 0.098 | 0.022 | 0.173 | True |
| Telex lỗi | Qwen2.5-3B+LoRA | 0.192 | 0.124 | 0.255 | True |
| Trộn tiếng Anh | PhoBERT-base (flat) | -0.002 | -0.063 | 0.055 | False |
| Trộn tiếng Anh | Qwen2.5-1.5B+LoRA | 0.145 | 0.082 | 0.204 | True |
| Trộn tiếng Anh | Qwen2.5-3B+LoRA | 0.169 | 0.11 | 0.227 | True |
| Trộn cả 3 | PhoBERT-base (flat) | 0.026 | -0.01 | 0.06 | False |
| Trộn cả 3 | Qwen2.5-1.5B+LoRA | 0.144 | 0.088 | 0.197 | True |
| Trộn cả 3 | Qwen2.5-3B+LoRA | 0.422 | 0.358 | 0.482 | True |

Số seed / lần chạy: PhoBERT-base (flat): 3, PhoBERT-base (hier): 3, Qwen2.5-1.5B+LoRA: 3, Qwen2.5-3B+LoRA: 3