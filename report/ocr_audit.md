# Audit chất lượng OCR - corpus báo cáo tài chính ViFinQA

- Số báo cáo: **40**
- Tổng số trang: **2437**
- Tổng số bảng OCR: **2585**
- Script sinh báo cáo: `src/audit_ocr.py` (chạy lại được, đọc `data/processed/corpus_manifest.csv`)

## 1. Chỉ số tổng hợp theo báo cáo

| document_id | trang | bảng | trang rỗng | trang không bảng | bảng có header đơn vị | tỷ lệ ô số | tỷ lệ hàng lệch cột | tỷ lệ ký tự tiếng Việt |
|---|---|---|---|---|---|---|---|---|
| HPG_2020_consolidated | 77 | 78 | 0 | 20 | 65 | 0.3570 | 0.0000 | 0.7814 |
| HPG_2020_separate | 53 | 54 | 0 | 15 | 46 | 0.2935 | 0.0000 | 0.8065 |
| HPG_2021_consolidated | 80 | 84 | 0 | 21 | 68 | 0.3544 | 0.0000 | 0.7833 |
| HPG_2021_separate | 51 | 53 | 0 | 14 | 43 | 0.3032 | 0.0000 | 0.7988 |
| HPG_2022_consolidated | 68 | 31 | 24 | 42 | 25 | 0.1863 | 0.0000 | 0.5329 |
| HPG_2022_separate | 44 | 46 | 0 | 11 | 37 | 0.3015 | 0.0000 | 0.7988 |
| HPG_2023_consolidated | 65 | 70 | 0 | 18 | 62 | 0.3652 | 0.0000 | 0.7918 |
| HPG_2023_separate | 42 | 45 | 0 | 11 | 37 | 0.2938 | 0.0000 | 0.7973 |
| HPG_2024_consolidated | 67 | 74 | 0 | 17 | 64 | 0.3610 | 0.0000 | 0.8071 |
| HPG_2024_separate | 40 | 42 | 0 | 11 | 36 | 0.3056 | 0.0000 | 0.8056 |
| HSG_2020_consolidated | 61 | 72 | 0 | 16 | 44 | 0.3214 | 0.0000 | 0.8071 |
| HSG_2020_separate | 61 | 72 | 0 | 14 | 43 | 0.3324 | 0.0000 | 0.7862 |
| HSG_2021_consolidated | 62 | 71 | 0 | 14 | 41 | 0.3141 | 0.0000 | 0.8100 |
| HSG_2021_separate | 61 | 71 | 1 | 14 | 42 | 0.3127 | 0.0000 | 0.7886 |
| HSG_2022_consolidated | 60 | 67 | 0 | 14 | 37 | 0.3046 | 0.0000 | 0.7943 |
| HSG_2022_separate | 56 | 72 | 0 | 13 | 38 | 0.3224 | 0.0000 | 0.8184 |
| HSG_2023_consolidated | 59 | 69 | 1 | 17 | 39 | 0.2902 | 0.0000 | 0.7858 |
| HSG_2023_separate | 54 | 74 | 0 | 12 | 40 | 0.3259 | 0.0000 | 0.8074 |
| HSG_2024_consolidated | 58 | 67 | 0 | 19 | 36 | 0.2706 | 0.0000 | 0.8554 |
| HSG_2024_separate | 61 | 75 | 0 | 19 | 38 | 0.2664 | 0.0000 | 0.8528 |
| NKG_2020_consolidated | 44 | 63 | 0 | 14 | 50 | 0.2951 | 0.0000 | 0.8347 |
| NKG_2020_separate | 43 | 59 | 0 | 14 | 47 | 0.2892 | 0.0000 | 0.8071 |
| NKG_2021_consolidated | 48 | 57 | 0 | 16 | 41 | 0.2582 | 0.0000 | 0.8307 |
| NKG_2021_separate | 48 | 60 | 0 | 18 | 42 | 0.2585 | 0.0000 | 0.8270 |
| NKG_2022_consolidated | 48 | 61 | 1 | 17 | 46 | 0.2804 | 0.0000 | 0.8149 |
| NKG_2022_separate | 46 | 67 | 1 | 16 | 48 | 0.2780 | 0.0000 | 0.8284 |
| NKG_2023_consolidated | 48 | 60 | 1 | 17 | 45 | 0.2918 | 0.0000 | 0.7851 |
| NKG_2023_separate | 48 | 64 | 1 | 17 | 46 | 0.2860 | 0.0000 | 0.7950 |
| NKG_2024_consolidated | 50 | 61 | 0 | 16 | 50 | 0.2967 | 0.0000 | 0.8083 |
| NKG_2024_separate | 49 | 66 | 0 | 16 | 46 | 0.2750 | 0.0000 | 0.8052 |
| MSR_2020_consolidated | 69 | 59 | 0 | 27 | 55 | 0.2502 | 0.0000 | 0.7990 |
| MSR_2020_separate | 24 | 20 | 0 | 10 | 20 | 0.2450 | 0.0000 | 0.8228 |
| MSR_2021_consolidated | 146 | 127 | 0 | 56 | 117 | 0.2589 | 0.0000 | 0.8213 |
| MSR_2021_separate | 48 | 46 | 0 | 19 | 42 | 0.2337 | 0.0000 | 0.8216 |
| MSR_2022_consolidated | 143 | 116 | 0 | 56 | 108 | 0.2641 | 0.0000 | 0.8205 |
| MSR_2022_separate | 49 | 45 | 0 | 20 | 40 | 0.2538 | 0.0000 | 0.8307 |
| MSR_2023_consolidated | 151 | 129 | 0 | 57 | 112 | 0.2732 | 0.0000 | 0.8329 |
| MSR_2023_separate | 51 | 47 | 0 | 22 | 44 | 0.2430 | 0.0000 | 0.8253 |
| MSR_2024_consolidated | 78 | 64 | 0 | 33 | 55 | 0.2347 | 0.0000 | 0.8203 |
| MSR_2024_separate | 26 | 27 | 0 | 10 | 23 | 0.2374 | 0.0000 | 0.8205 |

## 2. Độ dài trang

| document_id | trung bình ký tự/trang | ngắn nhất | dài nhất |
|---|---|---|---|
| HPG_2020_consolidated | 843.5 | 84 | 2752 |
| HPG_2020_separate | 819.9 | 82 | 2594 |
| HPG_2021_consolidated | 825.6 | 84 | 2879 |
| HPG_2021_separate | 826.4 | 82 | 2546 |
| HPG_2022_consolidated | 596.9 | 0 | 2995 |
| HPG_2022_separate | 686.3 | 82 | 2386 |
| HPG_2023_consolidated | 806.1 | 84 | 3891 |
| HPG_2023_separate | 681.0 | 82 | 2269 |
| HPG_2024_consolidated | 749.9 | 84 | 3007 |
| HPG_2024_separate | 733.3 | 82 | 2273 |
| HSG_2020_consolidated | 727.3 | 54 | 2394 |
| HSG_2020_separate | 647.4 | 73 | 4617 |
| HSG_2021_consolidated | 695.4 | 48 | 2458 |
| HSG_2021_separate | 617.7 | 0 | 2309 |
| HSG_2022_consolidated | 710.8 | 42 | 2359 |
| HSG_2022_separate | 613.8 | 78 | 2325 |
| HSG_2023_consolidated | 705.7 | 0 | 2353 |
| HSG_2023_separate | 619.7 | 98 | 2289 |
| HSG_2024_consolidated | 875.3 | 27 | 2500 |
| HSG_2024_separate | 775.8 | 27 | 2408 |
| NKG_2020_consolidated | 825.4 | 24 | 2448 |
| NKG_2020_separate | 849.4 | 24 | 2516 |
| NKG_2021_consolidated | 751.0 | 7 | 2224 |
| NKG_2021_separate | 736.3 | 14 | 2313 |
| NKG_2022_consolidated | 923.7 | 0 | 2444 |
| NKG_2022_separate | 900.6 | 0 | 2680 |
| NKG_2023_consolidated | 887.2 | 0 | 2825 |
| NKG_2023_separate | 862.9 | 0 | 2588 |
| NKG_2024_consolidated | 876.9 | 44 | 2612 |
| NKG_2024_separate | 904.1 | 63 | 2658 |
| MSR_2020_consolidated | 1190.6 | 145 | 3226 |
| MSR_2020_separate | 1064.8 | 129 | 2435 |
| MSR_2021_consolidated | 1214.9 | 107 | 3514 |
| MSR_2021_separate | 1313.6 | 90 | 12639 |
| MSR_2022_consolidated | 1177.3 | 107 | 3729 |
| MSR_2022_separate | 1038.3 | 91 | 2486 |
| MSR_2023_consolidated | 1136.1 | 107 | 3607 |
| MSR_2023_separate | 1018.5 | 91 | 2592 |
| MSR_2024_consolidated | 1068.1 | 107 | 3126 |
| MSR_2024_separate | 911.7 | 91 | 2241 |

## 3. Chất lượng số liệu

| document_id | tổng số | có dấu phân cách nghìn | số thập phân | số âm trong ngoặc | ký hiệu % |
|---|---|---|---|---|---|
| HPG_2020_consolidated | 1376 | 39 | 20 | 0 | 31 |
| HPG_2020_separate | 894 | 13 | 1 | 0 | 14 |
| HPG_2021_consolidated | 1509 | 51 | 22 | 0 | 33 |
| HPG_2021_separate | 840 | 17 | 2 | 0 | 11 |
| HPG_2022_consolidated | 620 | 9 | 11 | 0 | 16 |
| HPG_2022_separate | 701 | 14 | 7 | 0 | 14 |
| HPG_2023_consolidated | 1285 | 29 | 20 | 0 | 24 |
| HPG_2023_separate | 648 | 10 | 4 | 0 | 7 |
| HPG_2024_consolidated | 1122 | 40 | 23 | 0 | 25 |
| HPG_2024_separate | 660 | 17 | 6 | 0 | 6 |
| HSG_2020_consolidated | 994 | 28 | 32 | 0 | 55 |
| HSG_2020_separate | 1046 | 25 | 16 | 0 | 27 |
| HSG_2021_consolidated | 945 | 25 | 13 | 0 | 27 |
| HSG_2021_separate | 927 | 26 | 10 | 0 | 20 |
| HSG_2022_consolidated | 1083 | 28 | 15 | 0 | 35 |
| HSG_2022_separate | 818 | 22 | 7 | 0 | 12 |
| HSG_2023_consolidated | 945 | 25 | 9 | 0 | 31 |
| HSG_2023_separate | 807 | 17 | 8 | 0 | 12 |
| HSG_2024_consolidated | 802 | 34 | 10 | 0 | 28 |
| HSG_2024_separate | 726 | 43 | 9 | 0 | 14 |
| NKG_2020_consolidated | 412 | 9 | 9 | 0 | 13 |
| NKG_2020_separate | 583 | 13 | 10 | 0 | 15 |
| NKG_2021_consolidated | 474 | 13 | 16 | 0 | 26 |
| NKG_2021_separate | 481 | 13 | 15 | 0 | 27 |
| NKG_2022_consolidated | 683 | 13 | 16 | 0 | 25 |
| NKG_2022_separate | 542 | 12 | 15 | 0 | 24 |
| NKG_2023_consolidated | 539 | 25 | 16 | 0 | 20 |
| NKG_2023_separate | 586 | 45 | 15 | 0 | 19 |
| NKG_2024_consolidated | 548 | 29 | 17 | 0 | 26 |
| NKG_2024_separate | 571 | 30 | 19 | 0 | 28 |
| MSR_2020_consolidated | 1588 | 27 | 72 | 0 | 97 |
| MSR_2020_separate | 513 | 10 | 7 | 0 | 12 |
| MSR_2021_consolidated | 2575 | 38 | 72 | 0 | 166 |
| MSR_2021_separate | 2318 | 14 | 10 | 0 | 30 |
| MSR_2022_consolidated | 2314 | 44 | 16 | 0 | 45 |
| MSR_2022_separate | 819 | 15 | 5 | 0 | 15 |
| MSR_2023_consolidated | 2309 | 49 | 17 | 0 | 59 |
| MSR_2023_separate | 804 | 14 | 4 | 0 | 17 |
| MSR_2024_consolidated | 1247 | 34 | 16 | 0 | 30 |
| MSR_2024_separate | 415 | 7 | 3 | 0 | 9 |

## 4. Đơn vị tiền nhận diện được trong trang

| đơn vị | số trang chứa đơn vị |
|---|---|
| đồng | 530 |
| % | 323 |
| lần | 162 |
| triệu đồng | 144 |
| tỷ đồng | 107 |

## 5. Trang có dấu hiệu lỗi OCR

| document_id | trang | ký tự | bảng | ô rỗng | hàng lệch cột | ký tự lạ | đơn vị |
|---|---|---|---|---|---|---|---|
| HPG_2020_consolidated | 10 | 339 | 1 | 0.169 | 0.000 | 0.0118 | - |
| HPG_2020_consolidated | 11 | 324 | 1 | 0.080 | 0.000 | 0.0278 | - |
| HPG_2021_consolidated | 8 | 258 | 1 | 0.126 | 0.000 | 0.0194 | - |
| HPG_2021_consolidated | 12 | 355 | 1 | 0.229 | 0.000 | 0.0113 | - |
| HPG_2021_consolidated | 18 | 140 | 1 | 0.055 | 0.000 | 0.0143 | - |
| HPG_2021_consolidated | 19 | 120 | 1 | 0.061 | 0.000 | 0.0417 | - |
| HPG_2021_consolidated | 22 | 109 | 1 | 0.059 | 0.000 | 0.0183 | - |
| HPG_2021_consolidated | 42 | 216 | 1 | 0.024 | 0.000 | 0.0185 | - |
| HPG_2021_consolidated | 48 | 575 | 1 | 0.005 | 0.000 | 0.0122 | triệu đồng |
| HPG_2021_consolidated | 52 | 401 | 1 | 0.201 | 0.000 | 0.0150 | triệu đồng |
| HPG_2021_consolidated | 63 | 221 | 1 | 0.010 | 0.000 | 0.0271 | - |
| HPG_2021_separate | 24 | 448 | 2 | 0.079 | 0.000 | 0.0179 | - |
| HPG_2021_separate | 50 | 217 | 1 | 0.024 | 0.000 | 0.0184 | - |
| HPG_2022_consolidated | 42 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 44 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 45 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 46 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 47 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 48 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 49 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 50 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 51 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 52 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 53 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 54 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 57 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 58 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 59 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 60 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 61 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 62 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 63 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 64 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 65 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 66 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 67 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2022_consolidated | 68 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HPG_2023_consolidated | 29 | 3891 | 0 | 0.000 | 0.000 | 0.0131 | đồng,% |
| HPG_2023_consolidated | 32 | 135 | 1 | 0.015 | 0.000 | 0.0148 | - |
| HPG_2023_separate | 10 | 364 | 1 | 0.138 | 0.000 | 0.0137 | - |
| HPG_2023_separate | 32 | 150 | 1 | 0.015 | 0.000 | 0.0267 | - |
| HPG_2023_separate | 41 | 263 | 1 | 0.022 | 0.000 | 0.0114 | - |
| HSG_2020_consolidated | 27 | 553 | 1 | 0.111 | 0.000 | 0.0108 | % |
| HSG_2020_consolidated | 37 | 559 | 3 | 0.098 | 0.000 | 0.2397 | - |
| HSG_2020_consolidated | 38 | 278 | 2 | 0.058 | 0.000 | 0.0180 | - |
| HSG_2020_consolidated | 42 | 318 | 1 | 0.244 | 0.000 | 0.0126 | - |
| HSG_2020_consolidated | 47 | 307 | 1 | 0.086 | 0.000 | 0.0228 | đồng |
| HSG_2020_consolidated | 53 | 267 | 3 | 0.125 | 0.000 | 0.0225 | - |
| HSG_2020_separate | 17 | 4617 | 0 | 0.000 | 0.000 | 0.0286 | đồng,% |
| HSG_2020_separate | 23 | 247 | 1 | 0.086 | 0.000 | 0.0405 | - |
| HSG_2020_separate | 34 | 159 | 1 | 0.163 | 0.000 | 0.0252 | - |
| HSG_2020_separate | 38 | 189 | 1 | 0.143 | 0.000 | 0.0159 | - |
| HSG_2020_separate | 42 | 132 | 1 | 0.033 | 0.000 | 0.0227 | - |
| HSG_2021_consolidated | 30 | 306 | 3 | 0.121 | 0.000 | 0.0163 | - |
| HSG_2021_consolidated | 31 | 346 | 2 | 0.143 | 0.000 | 0.0173 | - |
| HSG_2021_consolidated | 34 | 565 | 1 | 0.017 | 0.000 | 0.0142 | triệu đồng |
| HSG_2021_consolidated | 43 | 254 | 1 | 0.086 | 0.000 | 0.0197 | - |
| HSG_2021_consolidated | 46 | 122 | 1 | 0.056 | 0.000 | 0.0246 | - |
| HSG_2021_consolidated | 47 | 236 | 1 | 0.086 | 0.000 | 0.0254 | đồng |
| HSG_2021_separate | 23 | 138 | 1 | 0.120 | 0.000 | 0.1087 | - |
| HSG_2021_separate | 44 | 130 | 1 | 0.929 | 0.000 | 0.0154 | - |
| HSG_2021_separate | 59 | 241 | 2 | 0.036 | 0.000 | 0.0249 | - |
| HSG_2021_separate | 61 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| HSG_2022_consolidated | 14 | 327 | 1 | 0.036 | 0.000 | 0.0122 | - |
| HSG_2022_consolidated | 42 | 209 | 1 | 0.095 | 0.000 | 0.0478 | - |
| HSG_2023_consolidated | 2 | 65 | 1 | 0.125 | 0.000 | 0.0308 | - |
| HSG_2023_consolidated | 33 | 175 | 1 | 0.007 | 0.000 | 0.0171 | - |
| HSG_2023_consolidated | 38 | 126 | 1 | 0.103 | 0.000 | 0.0397 | - |
| HSG_2023_consolidated | 45 | 143 | 1 | 0.014 | 0.000 | 0.0140 | - |
| HSG_2023_consolidated | 50 | 267 | 3 | 0.120 | 0.000 | 0.0150 | - |
| HSG_2023_consolidated | 59 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| NKG_2022_consolidated | 48 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| NKG_2022_separate | 46 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| NKG_2023_consolidated | 48 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| NKG_2023_separate | 48 | 0 | 0 | 0.000 | 0.000 | 0.0000 | - |
| MSR_2020_consolidated | 38 | 385 | 1 | 0.022 | 0.000 | 0.0104 | - |
| MSR_2020_consolidated | 47 | 690 | 1 | 0.024 | 0.000 | 0.1971 | đồng |
| MSR_2020_consolidated | 51 | 359 | 1 | 0.143 | 0.000 | 0.0167 | - |
| MSR_2020_consolidated | 59 | 382 | 1 | 0.008 | 0.000 | 0.3194 | - |
| MSR_2021_consolidated | 53 | 1669 | 2 | 0.061 | 0.000 | 0.0539 | - |

Còn 16 trang có dấu hiệu lỗi, xem `data/processed/ocr_audit_pages.csv`.

## 6. Trang rỗng trong file OCR nguồn

Các trang trống hoàn toàn, nằm liền nhau, là dấu hiệu OCR bỏ sót trang trong file nguồn.
Đây là lỗi ở dữ liệu nguồn, không phải lỗi do script parse.

| document_id | số trang rỗng | danh sách trang |
|---|---|---|
| HPG_2022_consolidated | 24 | 42, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68 |
| HSG_2021_separate | 1 | 61 |
| HSG_2023_consolidated | 1 | 59 |
| NKG_2022_consolidated | 1 | 48 |
| NKG_2022_separate | 1 | 46 |
| NKG_2023_consolidated | 1 | 48 |
| NKG_2023_separate | 1 | 48 |

Tổng cộng **30 trang rỗng** trên tổng 2437 trang (1.23%).

Bước xử lý đã áp dụng: giữ nguyên trong corpus để phản ánh đúng dữ liệu thực tế, nhưng loại các trang này khỏi tập chunk dùng cho truy hồi và ghi nhận trong `data/processed/ocr_audit_pages.csv` để nhóm có thể đối chiếu.

## 7. Nhiễu OCR không mang thông tin nghiệp vụ

| loại nhiễu | tổng số lần xuất hiện | số trang bị ảnh hưởng |
|---|---|---|
| ký tự trang trí (○ ● ◎ ...) | 1317 | 116 |
| công thức LaTeX | 486 | 295 |

Ký tự trang trí xuất hiện ở tiêu đề báo cáo, ví dụ dòng `○ ○ ○ ○ ◎ ○ ○ ○` là đường kẻ trang trí bị OCR nhận thành ký tự. Công thức LaTeX lọt vào từ bản thuyết minh toán học. Cả hai loại này không mang thông tin nghiệp vụ và được loại bỏ khi sinh chunk.

## 8. Cách đọc các chỉ số

- `tỷ lệ ô số`: tỷ lệ ô trong bảng chứa giá trị số (bao gồm số âm trong ngoặc và số kèm %).
- `tỷ lệ hàng lệch cột`: tỷ lệ hàng có số ô khác số cột chuẩn của bảng, dấu hiệu bảng bị vỡ khi OCR.
- `tỷ lệ ký tự tiếng Việt`: tỷ lệ ký tự thuộc bảng chữ cái tiếng Việt, đánh giá việc giữ dấu.
- `ký tự lạ`: ký tự không hợp lệ trong văn bản tài chính, thường do OCR nhập nhầm.
- `bảng có header đơn vị`: bảng có hàng đầu chứa năm và đơn vị (triệu VND, tỷ đồng, ...), cần thiết cho việc chuẩn hóa đơn vị.
