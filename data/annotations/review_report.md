# Cross-Review & Data Verification Report (v4)

## 1. Summary
- **Total QA items in `qa_gold.jsonl`**: **204** (`dev`: 44, `test`: 160; `pending-answer`: 0)
- **Cross-reviewed sample size (this run, seed=42)**: **53 / 204 (25.98%)**
- **Cumulative `reviewed-agree` items in `qa_gold.jsonl`**: **57 / 204 (27.94%)** (includes 4 prior `member-1/member-2` `supplement` items outside the random subsample + 53 items verified in this run)
- **Inter-reviewer disagreements**: **0** (`agree`: 53, `disagree`: 0)

## 2. Stratified Sample Breakdown
- **By source**: `table-clean`: 30 (T1=10, T2=9, T3=9, T5=2), `vifinqa`: 12, `supplement`: 7, `dev-refusal`: 4
- **By split**: `dev`: 14, `test`: 39
- **By answer_type**: `numeric`: 25, `computation`: 19, `unanswerable`: 9

## 3. Verification Methodology & Audit Notes
1. **Corpus-wide integrity (`204/204`)**: Every `vifinqa` (35/35) and `supplement` (7/7 answerable) evidence `quote` was verified verbatim inside `data/processed/chunks.jsonl` (`source_page == chunk.page`). Legacy `v2/v3` `table-clean` summary quotes (`"metric | raw_value"`) were verified against matching pipe-delimited lines inside their cited `chunks.jsonl` chunk (`142/142` answerable `table-clean` items).
2. **Independent arithmetic recomputation (`44/44` sampled answerables)**: Raw numbers and chunk-level scales (`VND` vs `Nghìn VND`) were re-extracted directly from `chunks.jsonl` without reading `row['computation']`, recomputed to 4 decimals, and asserted equal to `row['value']`.
3. **Out-of-corpus refusal probe (`9/9` sampled refusals)**: Explicit domain phrase probes (`giá đóng cửa`, `thị giá`, `kế hoạch doanh thu`, `quý 2`, `quý ii`, `usd một tấn`, `usd/tấn`, `vốn hóa thị trường`, `doanh thu thuần quý 1`, `báo cáo quý 1`) returned **0** matching chunks across all **2407** corpus chunks.
4. **Domain nuances verified & documented in ViFinQA (`qa_gold.jsonl`)**:
   - `ViFinQA-97` (`99.988%`): Uses direct `Tỷ lệ % sở hữu` (`99,988%`) from `HPG_2023_separate#p027` (confirmed by `1/1/2024` column in `HPG_2024_separate#p025`); consolidated group effective interest (`99,999%`) differs slightly.
   - `ViFinQA-186` (`10850162726 nghìn đồng`): Exact total of Note 21(b) `Vay và phát hành trái phiếu dài hạn` in `MSR_2023_consolidated#p060`; balance-sheet code `338` (`8.760.544.403`) excludes current portion due within 12 months (`2.089.618.323`) and is documented in `computation`.
   - `ViFinQA-709` (`9.1149%`): Computed directly from `MSR_2022_consolidated` primary BCTC statements (`1.194.553.796 / 13.105.475.407 * 100`); subsequent comparative reclassification in `MSR_2023_consolidated` (`14.374.663.611`) is noted in `computation`.
   - `CLEAN-T5-HPG-2024-01` & `CLEAN-T5-HSG-2025-06`: Annual financial statements report cash/stock dividends executed for FY2023 (`HPG`) and FY2022-2023 (`HSG`), not FY2024 dividend-per-share (`đồng/cổ phiếu`).

## 4. Per-Item Cross-Review Log (Sample n=53)

| # | Question ID | Source | Split | Type | Gold Value / Status | Verification Check | Result |
|---:|---|---|---|---|---|---|---|
| 1 | `CLEAN-T1-MSR-2020-B12` | `table-clean` | `test` | `numeric` | `66.8428 tỷ đồng` | verbatim/chunk match + recomputed=66.8428 == gold=66.8428 | **agree** |
| 2 | `CLEAN-T1-HPG-2020-08` | `table-clean` | `dev` | `numeric` | `55.864 tỷ đồng` | verbatim/chunk match + recomputed=55.864 == gold=55.864 | **agree** |
| 3 | `CLEAN-T1-HSG-2020-02` | `table-clean` | `test` | `numeric` | `-3.2852 tỷ đồng` | verbatim/chunk match + recomputed=-3.2852 == gold=-3.2852 | **agree** |
| 4 | `CLEAN-T1-HPG-2021-B19` | `table-clean` | `test` | `numeric` | `73.4593 nghìn tỷ đồng` | verbatim/chunk match + recomputed=73.4593 == gold=73.4593 | **agree** |
| 5 | `CLEAN-T1-NKG-2020-18` | `table-clean` | `test` | `numeric` | `1.0704 nghìn tỷ đồng` | verbatim/chunk match + recomputed=1.0704 == gold=1.0704 | **agree** |
| 6 | `CLEAN-T1-HPG-2020-16` | `table-clean` | `test` | `numeric` | `564.297 tỷ đồng` | verbatim/chunk match + recomputed=564.297 == gold=564.297 | **agree** |
| 7 | `CLEAN-T1-NKG-2020-15` | `table-clean` | `test` | `numeric` | `900.0 triệu đồng` | verbatim/chunk match + recomputed=900.0 == gold=900.0 | **agree** |
| 8 | `CLEAN-T1-HSG-2020-09` | `table-clean` | `test` | `numeric` | `10.5553 tỷ đồng` | verbatim/chunk match + recomputed=10.5553 == gold=10.5553 | **agree** |
| 9 | `CLEAN-T1-HSG-2024-07` | `table-clean` | `test` | `numeric` | `154.8429 tỷ đồng` | verbatim/chunk match + recomputed=154.8429 == gold=154.8429 | **agree** |
| 10 | `CLEAN-T1-HSG-2020-B15` | `table-clean` | `dev` | `numeric` | `546.7341 tỷ đồng` | verbatim/chunk match + recomputed=546.7341 == gold=546.7341 | **agree** |
| 11 | `CLEAN-T2-HSG-2021-2022-B13` | `table-clean` | `test` | `computation` | `-8.3631 nghìn tỷ đồng` | verbatim/chunk match + recomputed=-8.3631 == gold=-8.3631 | **agree** |
| 12 | `CLEAN-T2-HSG-2023-2024-06` | `table-clean` | `dev` | `computation` | `19.4573 tỷ đồng` | verbatim/chunk match + recomputed=19.4573 == gold=19.4573 | **agree** |
| 13 | `CLEAN-T2-HSG-2022-2023-B16` | `table-clean` | `test` | `computation` | `559.707 tỷ đồng` | verbatim/chunk match + recomputed=559.707 == gold=559.707 | **agree** |
| 14 | `CLEAN-T2-NKG-2022-2023-B06` | `table-clean` | `dev` | `computation` | `-912.9216 tỷ đồng` | verbatim/chunk match + recomputed=-912.9216 == gold=-912.9216 | **agree** |
| 15 | `CLEAN-T2-MSR-2020-2021-03` | `table-clean` | `test` | `computation` | `156.4154 tỷ đồng` | verbatim/chunk match + recomputed=156.4154 == gold=156.4154 | **agree** |
| 16 | `CLEAN-T2-HSG-2023-2024-02` | `table-clean` | `dev` | `computation` | `-42.3713 tỷ đồng` | verbatim/chunk match + recomputed=-42.3713 == gold=-42.3713 | **agree** |
| 17 | `CLEAN-T2-NKG-2022-2023-B21` | `table-clean` | `test` | `computation` | `0.0 đồng` | verbatim/chunk match + recomputed=0.0 == gold=0.0 | **agree** |
| 18 | `CLEAN-T2-HSG-2021-2022-14` | `table-clean` | `test` | `computation` | `1.5008 tỷ đồng` | verbatim/chunk match + recomputed=1.5008 == gold=1.5008 | **agree** |
| 19 | `CLEAN-T2-MSR-2023-2024-15` | `table-clean` | `dev` | `computation` | `-62.5724 tỷ đồng` | verbatim/chunk match + recomputed=-62.5724 == gold=-62.5724 | **agree** |
| 20 | `CLEAN-T3-HSG-2023-2024-B11` | `table-clean` | `test` | `computation` | `-557.1587 tỷ đồng` | verbatim/chunk match + recomputed=-557.1587 == gold=-557.1587 | **agree** |
| 21 | `CLEAN-T3-HSG-2022-2023-B17` | `table-clean` | `test` | `computation` | `16.0978 tỷ đồng` | verbatim/chunk match + recomputed=16.0978 == gold=16.0978 | **agree** |
| 22 | `CLEAN-T3-HSG-2020-2021-02` | `table-clean` | `test` | `computation` | `1.3859 tỷ đồng` | verbatim/chunk match + recomputed=1.3859 == gold=1.3859 | **agree** |
| 23 | `CLEAN-T3-NKG-2021-2022-B14` | `table-clean` | `test` | `computation` | `-182.4218 tỷ đồng` | verbatim/chunk match + recomputed=-182.4218 == gold=-182.4218 | **agree** |
| 24 | `CLEAN-T3-HPG-2023-2024-13` | `table-clean` | `test` | `computation` | `284.5307 tỷ đồng` | verbatim/chunk match + recomputed=284.5307 == gold=284.5307 | **agree** |
| 25 | `CLEAN-T3-HSG-2020-2021-B13` | `table-clean` | `test` | `computation` | `3.1409 nghìn tỷ đồng` | verbatim/chunk match + recomputed=3.1409 == gold=3.1409 | **agree** |
| 26 | `CLEAN-T3-HSG-2020-2021-B05` | `table-clean` | `test` | `computation` | `2.8389 nghìn tỷ đồng` | verbatim/chunk match + recomputed=2.8389 == gold=2.8389 | **agree** |
| 27 | `CLEAN-T3-MSR-2020-2021-15` | `table-clean` | `test` | `computation` | `4.1807 nghìn tỷ đồng` | verbatim/chunk match + recomputed=4.1807 == gold=4.1807 | **agree** |
| 28 | `CLEAN-T3-HSG-2021-2022-B07` | `table-clean` | `dev` | `computation` | `-3.2542 nghìn tỷ đồng` | verbatim/chunk match + recomputed=-3.2542 == gold=-3.2542 | **agree** |
| 29 | `CLEAN-T5-HPG-2025-05` | `table-clean` | `test` | `unanswerable` | `Refusal` | 0 hits across 2407 chunks for ['kế hoạch doanh thu'] | **agree** |
| 30 | `CLEAN-T5-NKG-2024-07` | `table-clean` | `test` | `unanswerable` | `Refusal` | 0 hits across 2407 chunks for ['báo cáo quý 1'] | **agree** |
| 31 | `S_NEW_02` | `supplement` | `test` | `numeric` | `453008.1444 triệu đồng` | verbatim/chunk match + recomputed=453008.1444 == gold=453008.1444 | **agree** |
| 32 | `S_NEW_04` | `supplement` | `test` | `numeric` | `319.2579 tỷ đồng` | verbatim/chunk match + recomputed=319.2579 == gold=319.2579 | **agree** |
| 33 | `S_NEW_05` | `supplement` | `test` | `numeric` | `602.0718 tỷ đồng` | verbatim/chunk match + recomputed=602.0718 == gold=602.0718 | **agree** |
| 34 | `S_NEW_07` | `supplement` | `test` | `computation` | `10.8568 %` | verbatim/chunk match + recomputed=10.8568 == gold=10.8568 | **agree** |
| 35 | `S_NEW_09` | `supplement` | `test` | `unanswerable` | `Refusal` | 0 hits across 2407 chunks for ['vốn hóa thị trường'] | **agree** |
| 36 | `S_NEW_10` | `supplement` | `test` | `unanswerable` | `Refusal` | 0 hits across 2407 chunks for ['doanh thu thuần quý 1'] | **agree** |
| 37 | `S_NEW_12` | `supplement` | `test` | `unanswerable` | `Refusal` | 0 hits across 2407 chunks for ['kế hoạch doanh thu'] | **agree** |
| 38 | `ViFinQA-97` | `vifinqa` | `test` | `numeric` | `99.988 %` | verbatim/chunk match + recomputed=99.988 == gold=99.988 | **agree** |
| 39 | `ViFinQA-186` | `vifinqa` | `test` | `numeric` | `10850162726 nghìn đồng` | verbatim/chunk match + recomputed=10850162726.0 == gold=10850162726.0 | **agree** |
| 40 | `ViFinQA-311` | `vifinqa` | `test` | `numeric` | `360 triệu đồng` | verbatim/chunk match + recomputed=360.0 == gold=360.0 | **agree** |
| 41 | `ViFinQA-612` | `vifinqa` | `test` | `numeric` | `52.842 %` | verbatim/chunk match + recomputed=52.842 == gold=52.842 | **agree** |
| 42 | `ViFinQA-682` | `vifinqa` | `dev` | `numeric` | `-1899.3214 triệu đồng` | verbatim/chunk match + recomputed=-1899.3214 == gold=-1899.3214 | **agree** |
| 43 | `ViFinQA-709` | `vifinqa` | `test` | `numeric` | `9.1149 %` | verbatim/chunk match + recomputed=9.1149 == gold=9.1149 | **agree** |
| 44 | `ViFinQA-973` | `vifinqa` | `dev` | `numeric` | `1` | verbatim/chunk match + recomputed=1.0 == gold=1.0 | **agree** |
| 45 | `ViFinQA-368` | `vifinqa` | `test` | `numeric` | `0.5909 %` | verbatim/chunk match + recomputed=0.5909 == gold=0.5909 | **agree** |
| 46 | `ViFinQA-369` | `vifinqa` | `test` | `numeric` | `1.747 lần` | verbatim/chunk match + recomputed=1.747 == gold=1.747 | **agree** |
| 47 | `ViFinQA-373` | `vifinqa` | `dev` | `numeric` | `6.2269 %` | verbatim/chunk match + recomputed=6.2269 == gold=6.2269 | **agree** |
| 48 | `ViFinQA-400` | `vifinqa` | `test` | `numeric` | `17.8521 %` | verbatim/chunk match + recomputed=17.8521 == gold=17.8521 | **agree** |
| 49 | `ViFinQA-473` | `vifinqa` | `test` | `numeric` | `206.6695 nghìn tỷ đồng` | verbatim/chunk match + recomputed=206.6695 == gold=206.6695 | **agree** |
| 50 | `DEV-REF-01` | `dev-refusal` | `dev` | `unanswerable` | `Refusal` | 0 hits across 2407 chunks for ['giá đóng cửa', 'thị giá'] | **agree** |
| 51 | `DEV-REF-02` | `dev-refusal` | `dev` | `unanswerable` | `Refusal` | 0 hits across 2407 chunks for ['kế hoạch doanh thu'] | **agree** |
| 52 | `DEV-REF-03` | `dev-refusal` | `dev` | `unanswerable` | `Refusal` | 0 hits across 2407 chunks for ['quý 2', 'quý ii'] | **agree** |
| 53 | `DEV-REF-04` | `dev-refusal` | `dev` | `unanswerable` | `Refusal` | 0 hits across 2407 chunks for ['usd một tấn', 'usd/tấn'] | **agree** |
