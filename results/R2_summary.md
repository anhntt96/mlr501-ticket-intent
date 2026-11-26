# RQ2 – Tăng cường câu bỏ dấu

Chế độ tăng cường: `aug50`. gain = F1(aug) − F1(clean), điểm %, TB ± độ lệch 3 seed; CI = khoảng tin cậy 95% bootstrap ghép cặp.

## Bảng 1. Mức tăng trên câu không dấu và thay đổi trên câu có dấu

| system | variant | clean | aug | gain | gain_sd | ci_low | ci_high | significant | n_ticket |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PhoBERT-base (hier) | Test tổng hợp – không dấu | 18.6 | 59.9 | 41.3 | 6.5 | 32.5 | 45.6 | True | 135 |
| PhoBERT-base (hier) | Test tổng hợp – có dấu | 86.3 | 79.5 | -6.8 | 3.6 | -12.2 | -2.4 | True | 135 |
| PhoBERT-base (hier) | Người viết – gõ không dấu | 16.4 | 50.1 | 33.7 | 3.3 | 26.2 | 37.7 | True | 180 |
| PhoBERT-base (hier) | Người viết – bỏ dấu bằng quy tắc | 17.6 | 50.9 | 33.3 | 1.1 | 26.1 | 37.4 | True | 180 |
| PhoBERT-base (hier) | Người viết – có dấu | 72.6 | 66.6 | -6.0 | 2.3 | -10.4 | -2.3 | True | 180 |
| XLM-R-base (hier) | Test tổng hợp – không dấu | 10.0 | 63.8 | 53.8 | 6.4 | 44.3 | 57.1 | True | 135 |
| XLM-R-base (hier) | Test tổng hợp – có dấu | 84.6 | 74.2 | -10.4 | 5.0 | -16.0 | -6.1 | True | 135 |
| XLM-R-base (hier) | Người viết – gõ không dấu | 8.8 | 46.7 | 37.8 | 4.1 | 30.3 | 41.1 | True | 180 |
| XLM-R-base (hier) | Người viết – bỏ dấu bằng quy tắc | 7.2 | 45.0 | 37.8 | 2.5 | 30.1 | 40.6 | True | 180 |
| XLM-R-base (hier) | Người viết – có dấu | 69.8 | 61.3 | -8.5 | 3.3 | -12.7 | -4.8 | True | 180 |
| Qwen2.5-3B+LoRA | Test tổng hợp – không dấu | 56.3 | 78.9 | 22.6 | 1.4 | 17.4 | 30.3 | True | 135 |
| Qwen2.5-3B+LoRA | Test tổng hợp – có dấu | 90.1 | 90.9 | 0.7 | 1.7 | -2.0 | 3.4 | False | 135 |
| Qwen2.5-3B+LoRA | Người viết – gõ không dấu | 60.6 | 70.6 | 10.1 | 4.6 | 6.2 | 14.9 | True | 180 |
| Qwen2.5-3B+LoRA | Người viết – bỏ dấu bằng quy tắc | 60.2 | 70.8 | 10.5 | 6.0 | 6.5 | 15.4 | True | 180 |
| Qwen2.5-3B+LoRA | Người viết – có dấu | 78.0 | 78.3 | 0.3 | 1.5 | -2.8 | 3.5 | False | 180 |

## Bảng 2. Tất cả biến thể test tổng hợp theo chế độ huấn luyện

| level_0 | level_1 | clean | no_diacritics | teencode | telex | code_switch | mixed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PhoBERT-base (hier) | clean | 86.3 | 18.6 | 86.5 | 71.7 | 82.7 | 18.6 |
| PhoBERT-base (hier) | aug50 | 79.5 | 59.9 | 77.5 | 66.7 | 74.0 | 53.0 |
| XLM-R-base (hier) | clean | 84.6 | 10.0 | 84.9 | 74.8 | 80.2 | 12.1 |
| XLM-R-base (hier) | aug50 | 74.2 | 63.8 | 73.8 | 67.9 | 72.4 | 53.9 |
| Qwen2.5-3B+LoRA | clean | 90.1 | 56.3 | 88.0 | 82.3 | 90.0 | 61.3 |
| Qwen2.5-3B+LoRA | aug50 | 90.9 | 78.9 | 87.6 | 85.2 | 91.1 | 79.6 |

## Bảng 3. Đoán đúng service theo explicit (RQ3)

| system | train | variant | explicit=0 | explicit=1 | n_ticket explicit=0 |
| --- | --- | --- | --- | --- | --- |
| PhoBERT-base (hier) | aug50 | clean | 0.0 | 93.3 | 5 |
| PhoBERT-base (hier) | aug50 | human_clean | 61.5 | 85.4 | 45 |
| PhoBERT-base (hier) | aug50 | human_nodiac | 45.9 | 81.7 | 45 |
| PhoBERT-base (hier) | clean | clean | 0.0 | 94.1 | 5 |
| PhoBERT-base (hier) | clean | human_clean | 61.5 | 85.4 | 45 |
| PhoBERT-base (hier) | clean | human_nodiac | 25.9 | 45.7 | 45 |
| Qwen2.5-3B+LoRA | aug50 | clean | 6.7 | 96.9 | 5 |
| Qwen2.5-3B+LoRA | aug50 | human_clean | 58.5 | 88.6 | 45 |
| Qwen2.5-3B+LoRA | aug50 | human_nodiac | 44.4 | 86.7 | 45 |
| Qwen2.5-3B+LoRA | clean | clean | 13.3 | 96.2 | 5 |
| Qwen2.5-3B+LoRA | clean | human_clean | 60.0 | 87.7 | 45 |
| Qwen2.5-3B+LoRA | clean | human_nodiac | 44.4 | 78.8 | 45 |
| XLM-R-base (hier) | aug50 | clean | 0.0 | 94.6 | 5 |
| XLM-R-base (hier) | aug50 | human_clean | 49.6 | 84.7 | 45 |
| XLM-R-base (hier) | aug50 | human_nodiac | 40.7 | 79.3 | 45 |
| XLM-R-base (hier) | clean | clean | 0.0 | 94.4 | 5 |
| XLM-R-base (hier) | clean | human_clean | 47.4 | 85.7 | 45 |
| XLM-R-base (hier) | clean | human_nodiac | 22.2 | 38.8 | 45 |

Số seed: system               train; PhoBERT-base (hier)  aug50    3;                      clean    3; Qwen2.5-3B+LoRA      aug50    3;                      clean    3; XLM-R-base (hier)    aug50    3;                      clean    3