# Data Card: ViFinQA-Steel-4Co RAG Corpus & Gold QA Benchmark (v4)

## 1. Dataset Summary & Intended Use

`ViFinQA-Steel-4Co (v4)` is a Vietnamese financial question-answering and retrieval-augmented generation (RAG) benchmark constructed for CSC4007 Topic 6 (Vietnamese Financial Statement Retrieval-Augmented Generation with Citation & Evidence-Grounded Refusal).

Given a Vietnamese financial query and a fixed corpus of audited annual financial statements, a model retrieves page-level source chunks (`company_id`, `fiscal_year`, `report_version`, `page`, `chunk_id`), computes or extracts the normalized numeric answer with unit conversion, attaches verifiable evidence citations, or outputs the exact refusal string `"Không đủ bằng chứng trong corpus để trả lời."` when corpus evidence is absent.

All processed chunks, table records, and gold items preserve Vietnamese (`vi`) in Unicode NFC across four listed companies and fiscal years `2020-2024`, covering both `consolidated` (hợp nhất) and `separate` (riêng / công ty mẹ) audited statements:

| Ticker | Company Name | Fiscal Year End | Primary Statement Unit | Versions |
|---|---|---|---|---|
| `HPG` | CTCP Tập đoàn Hòa Phát | `31/12` | `VND` | `consolidated`, `separate` |
| `HSG` | CTCP Tập đoàn Hoa Sen | `30/09` | `VND` | `consolidated`, `separate` |
| `NKG` | CTCP Thép Nam Kim | `31/12` | `VND` | `consolidated`, `separate` |
| `MSR` | CTCP Masan High-Tech Materials | `31/12` | `Nghìn VND` (1,000x to VND) | `consolidated`, `separate` |

The intended use is academic benchmarking and reproducible offline RAG experiments (`E0-E8`), retrieval/citation/refusal evaluation, and interactive demonstration (`app/streamlit_app.py`) within the 4-company `2020-2024` scope. Data and split version is `v4` (`data/splits/split_meta.json` and `evaluation/split_freeze.json`).

## 2. Dataset Sources & Versions

The primary upstream source is Hugging Face [`AIGuruTinix/ViFinQA`](https://huggingface.co/datasets/AIGuruTinix/ViFinQA/blob/0450088ab22ec946f04f097586967ca405955b3b/), pinned at revision `0450088ab22ec946f04f097586967ca405955b3b` and downloaded locally via `src/download_vifinqa.py` into `data/raw/vifinqa/`. Upstream `ViFinQA` draws 1,973 OCR reports from [`tinixai/ocr_annual_financials`](https://huggingface.co/datasets/tinixai/ocr_annual_financials) (`TiniX Vietnam OCR Annual Financial Statements`), stored as UTF-8 text files with `===== PAGE n =====` page delimiters and inline HTML `<table>` markup.

Initial corpus selection and manifest generation occurred on `2026-11-10`, and the corpus manifest was refreshed during the `v4` pipeline build on `2026-11-15` (`retrieved_at` in `data/processed/corpus_manifest.csv` is `2026-11-15`; gold rows in `data/data_manifest.csv` record `2026-11-10`; `published_at` remains empty `""` because upstream does not publish original filing release dates).

The `204` Gold QA items originate from four sources:

- `vifinqa` (`35` items): Question prompts filtered from `data/raw/vifinqa/questions/questions.jsonl` (`1,012` prompt-only rows -> `35` matched to the 4-company `2020-2024` scope; `977` dropped). Because upstream `ViFinQA` contains only `id` and `question` with no answers, evidence, or splits, all 35 answers, normalized values, step-by-step computations, and verbatim chunk quotes were authored and verified against the 40-report corpus (`src/resolve_vifinqa_and_dev_refusal.py`).
- `table-clean` (`150` items): Template-generated single-period lookup (`T1`, 55), comparative year-over-year directional (`T2`, 44), comparative difference (`T3`, 43), and out-of-corpus refusal (`T5`, 8) questions built over clean `consolidated` income-statement and balance-sheet table records (`src/build_expanded_gold_v2.py`, `src/build_expanded_gold_v3.py`).
- `supplement` (`15` items): Manually authored domain QA (`S_NEW_01..07`) and out-of-corpus refusal probes (`S_NEW_08..15`) (`src/build_supplement_gold.py`).
- `dev-refusal` (`4` items): Out-of-corpus refusal items (`DEV-REF-01..04`) added exclusively to `dev` in `v4` (`src/resolve_vifinqa_and_dev_refusal.py`) so `dev` refusal evaluation has a non-zero denominator (`refusal_den = 4`) without altering the frozen `test` split.

A legacy `v1` snapshot (`50` items) is retained at `data/annotations/qa_gold_v1_50.jsonl` for historical reference.

## 3. License & Access

All `40` rows of `data/processed/corpus_manifest.csv` and all `244` rows of `data/data_manifest.csv` record `license_status` as `unknown_verify_with_teacher`. The upstream `data/raw/vifinqa/README.md` states that the underlying `tinixai/ocr_annual_financials` OCR filings carry the Creative Commons Attribution-NonCommercial 4.0 International license (`CC BY-NC 4.0`), while the `ViFinQA` question annotations include no separate license file. Redistribution rights must be confirmed with course instructors before any public release.

Raw source files under `data/raw/` are excluded from Git via `.gitignore` and are not redistributed inside the repository. Processed artifacts (`chunks.jsonl`, `table_records.jsonl`), manifests, annotations, evaluation outputs, and reproducible build scripts are versioned for academic verification.

## 4. Data Structure

All structured files use UTF-8 encoding (`encoding="utf-8"`). Full column definitions appear in `data/data_schema.md`.

### Core Artifacts

| Artifact | Path | Records | Key Fields |
|---|---|---:|---|
| Master manifest | `data/data_manifest.csv` | 244 | `item_id`, `document_id`, `source_name`, `source_url`, `source_version`, `retrieved_at`, `published_at`, `language`, `original_category`, `task_label`, `license_status`, `split`, `notes` |
| Corpus manifest | `data/processed/corpus_manifest.csv` | 40 | `document_id`, `company_id`, `fiscal_year`, `report_version`, `n_pages`, `n_chars`, `sha256`, `local_path`, `license_status` |
| Page chunks | `data/processed/chunks.jsonl` | 2,407 | `chunk_id`, `document_id`, `company_id`, `fiscal_year`, `report_version`, `page`, `n_tables`, `unit`, `text`, `text_chars`, `local_path` |
| Table records | `data/processed/table_records.jsonl` | 29,615 | `company`, `year`, `period_label`, `statement`, `metric`, `metric_code`, `value`, `unit`, `value_raw`, `page`, `table_index`, `source_chunk_id`, `document_id`, `report_version`, `fiscal_year`, `confidence` |
| Gold QA (`v4`) | `data/annotations/qa_gold.jsonl` | 204 | `question_id`, `question`, `gold_answer`, `answer_type`, `value`, `unit`, `company_id`, `fiscal_year`, `report_id`, `evidence`, `computation`, `source_page`, `needs_more_evidence`, `reviewer_id`, `review_status`, `source`, `split`, `unanswerable_reason` |
| Review log | `data/annotations/review_log.csv` | 204 | `item_id`, `gold`, `reviewer`, `status`, `guideline_version`, `disagreement_note` |

### Redacted Schema Examples

Example chunk record (`data/processed/chunks.jsonl`, long `text` truncated):

```json
{
  "chunk_id": "HPG_2020_consolidated#p001",
  "document_id": "HPG_2020_consolidated",
  "company_id": "HPG",
  "fiscal_year": 2020,
  "report_version": "consolidated",
  "page": 1,
  "n_tables": 0,
  "unit": "",
  "text": "KPMG\n\nCông ty Cổ phần Tập đoàn Hòa Phát\n\nBáo cáo tài chính hợp nhất cho năm kết thúc ngày 31 tháng 12 năm 2020...",
  "text_chars": 110,
  "local_path": "data/raw/vifinqa/financial_statements/HPG/2020/HPG_financial_statements_2020_consolidated/HPG_financial_statements_2020_consolidated_extracted.txt"
}
```

Example table record (`data/processed/table_records.jsonl`):

```json
{
  "company": "HPG",
  "year": 2020,
  "period_label": "31/12/2020 VND",
  "statement": "balance_sheet",
  "metric": "Tài sản ngắn hạn(\\( 100 = 110 + 120 + 130 + 140 + 150 \\))",
  "metric_code": "100",
  "value": 56747258197010.0,
  "unit": "đồng",
  "value_raw": "56.747.258.197.010",
  "page": 7,
  "table_index": 1,
  "source_chunk_id": "HPG_2020_consolidated#p007",
  "document_id": "HPG_2020_consolidated",
  "report_version": "consolidated",
  "fiscal_year": 2020,
  "confidence": 0.93
}
```

Example gold record (`data/annotations/qa_gold.jsonl`):

```json
{
  "question_id": "S_NEW_01",
  "question": "Doanh thu thuần về bán hàng và cung cấp dịch vụ hợp nhất của CTCP Tập đoàn Hoa Sen trong năm tài chính kết thúc ngày 30/09/2024 là bao nhiêu nghìn tỷ đồng?",
  "gold_answer": "39.2719 nghìn tỷ đồng",
  "answer_type": "numeric",
  "value": 39.2719,
  "unit": "nghìn tỷ đồng",
  "company_id": "HSG",
  "fiscal_year": 2024,
  "report_id": "HSG_2024_consolidated",
  "evidence": [{"chunk_id": "HSG_2024_consolidated#p009", "source_page": 9, "quote": "10 | Doanh thu thuần về bán hàng và cung cấp dịch vụ | 26 | 39.271.893.738.448 | 31.650.660.956.650"}],
  "computation": "39271893738448 VND / 1e12 = 39.2719 nghìn tỷ đồng (làm tròn 4 chữ số thập phân).",
  "source_page": 9,
  "needs_more_evidence": false,
  "reviewer_id": "member-1/member-2",
  "review_status": "reviewed-agree",
  "source": "supplement",
  "split": "test"
}
```

Private personal identifiers and API credentials do not appear in any data or manifest field; named individuals inside raw OCR texts are statutory company officers and auditors named in public financial disclosures.

## 5. Composition & Distributions

### Corpus Summary

| Metric | Verified Count | Path / Notes |
|---|---:|---|
| Audited reports | 40 | 4 companies × 5 years (2020-2024) × 2 versions (`consolidated`, `separate`) |
| Raw OCR pages | 2,437 | `5,422,578` total characters across 40 `.txt` files (`report/ocr_audit.md`) |
| Empty OCR pages excluded | 30 | `1.23%` of raw pages (`data/processed/ocr_audit_pages.csv`) |
| Retrieval chunks | 2,407 | `data/processed/chunks.jsonl` (1 chunk = 1 non-empty page; `1,634` contain tables) |
| OCR HTML tables parsed | 2,585 | Extracted from non-empty chunks |
| Structured table records | 29,615 | `data/processed/table_records.jsonl` |
| Master manifest rows | 244 | `40` corpus + `44` dev + `160` test in `data/data_manifest.csv` |

Table records (`n = 29,615`) break down by statement type into `other` (19,904), `balance_sheet` (5,391), `cash_flow` (2,263), and `income_statement` (2,057). By parsed unit, they break down into `đồng` (22,634), `nghìn đồng` (4,912), `%` (1,530), empty `""` (292), `triệu đồng` (234), and `tỷ đồng` (13).

At the page chunk level (`n = 2,407`), `unit` is `""` on `1,680` chunks (pages without a table unit header), `đồng` on `478`, `triệu đồng` on `142`, and `tỷ đồng` on `107`. Downstream lookup resolves units from table column headers or page text rather than guessing missing headers.
At the page chunk level (`n = 2,407`), `unit` is `""` on `1,680` chunks (pages without a table unit header), `đồng` on `478`, `triệu đồng` on `142`, and `tỷ đồng` on `107`. Downstream lookup resolves units from table column headers or page text and does not guess missing headers.

### Gold QA Breakdown (`n = 204`)

- Source: `table-clean` **150** (`T1`: 55, `T2`: 44, `T3`: 43, `T5`: 8), `vifinqa` **35**, `supplement` **15** (7 answerable, 8 unanswerable), `dev-refusal` **4** (`DEV-REF-01..04`).
- Answer type and split: `computation` **94** (`dev`: 21, `test`: 73), `numeric` **90** (`dev`: 19, `test`: 71), and `unanswerable` **20** (`dev`: 4, `test`: 16).
- Evidence status: `needs_more_evidence=false` **184** (non-empty `evidence`), `needs_more_evidence=true` **20** (empty `evidence` and canonical refusal string).
- Review status: `reviewed-agree` **57** (`27.94%`), `draft-needs-second-reviewer` **147** (`72.06%`), `pending-answer` **0**.
- Company ID: single-company `HSG` (**57**), `NKG` (**52**), `MSR` (**36**), `HPG` (**34**); cross-company `HPG|HSG|MSR|NKG` (**22**), `HPG|HSG|NKG` (**2**), `HPG|MSR|HSG` (**1**).
- Normalized `unit`: `tỷ đồng` (89), `nghìn tỷ đồng` (46), `""` for counts/refusals (21), `triệu đồng` (12), `%` (11), `đồng` (10), `điểm phần trăm` (9), `lần` (4), `nghìn đồng` (1), `trăm tỷ đồng` (1).

### Missing Data Summary

In `data/data_manifest.csv` and `data/processed/corpus_manifest.csv`, `published_at` is `""` on every row because upstream `ViFinQA` does not provide original publication dates. In `qa_gold.jsonl`, `report_id` and `source_page` are `""` on the `20` refusal items and multi-company/multi-period synthesis items where no single filing or page holds the aggregated answer (all evidence references remain recorded inside `evidence[]` for answerable items). On `HPG_2022_consolidated`, `24` trailing note pages (`42`, `44-54`, `57-68`) are blank in the upstream OCR snapshot.

## 6. Collection & Sampling

Candidate tickers in `ViFinQA` were ranked via `src/select_corpus.py` by matched question density, accounting-template comparability (non-financial firms following Circular `202/2014/TT-BTC`), and OCR table parseability. Selecting `HPG`, `HSG`, `NKG`, and `MSR` across `2020-2024` (excluding banks such as `VCB` and `ACB` whose statement line items differ substantially) yielded **20** company-year pairs and **40** OCR report files (`consolidated` and `separate`). Both statement versions are retained because 4 matched `ViFinQA` questions ask specifically for parent-company (`công ty mẹ`, `separate`) figures while others ask for `consolidated` figures.

Using `src/filter_questions.py` and `src/preprocess/company_match.py`, all `1,012` raw questions in `data/raw/vifinqa/questions/questions.jsonl` were matched by parenthesized ticker codes, standalone ticker symbols, and contiguous Vietnamese company-name sequences. Exactly **35** questions matched `{HPG, HSG, NKG, MSR} × {2020..2024}` (`data/processed/questions_matched.csv`: `10` single-company, `25` multi-company; `29` numeric, `6` computation). The other **977** questions are logged with drop reasons in `data/processed/questions_dropped.csv` (`951` out-of-corpus company, `21` out-of-corpus year, `4` unknown company, `1` missing year).

Controlled expansion proceeded across four versions:
- `v1` (`50` items): `35` `vifinqa` + `15` `supplement` (`S_NEW_01..15`, authored via `src/build_supplement_gold.py`).
- `v2` (`127` items): added `77` clean consolidated table QA (`T1`, `T2`, `T3`, `T5`) via `src/build_expanded_gold_v2.py` (filtering `confidence >= 0.9`, valid `metric_code`, years `2020-2024`, deduplicating `(company, norm_name, year, source_chunk_id)`).
- `v3` (`200` items): added `73` additional `table-clean` items (`T1 +26`, `T2 +22`, `T3 +21`, `T5 +4`) via `src/build_expanded_gold_v3.py`.
- `v4` (`204` items): resolved all `35` `vifinqa` items against the 40-report corpus and appended `4` `dev-refusal` items (`DEV-REF-01..04`) exclusively to `dev` via `src/resolve_vifinqa_and_dev_refusal.py`.

## 7. Preprocessing

All preprocessing scripts read from `data/raw/` without altering upstream files and write deterministic UTF-8 outputs to `data/processed/`.

First, `src/preprocess/vifinqa_parser.py` and `src/build_chunks.py` split each report on `===== PAGE n =====`, parse inline HTML `<table>` elements, normalize text to Unicode `NFC` while preserving all Vietnamese diacritics, strip `1,317` decorative symbols (`○ ● ◎ ...`) across `116` pages, `486` LaTeX expressions across `295` pages, and control characters (`CONTROL_RE`), and exclude **30** empty pages (`1.23%` of `2,437`). Each remaining non-empty page forms one retrieval chunk (`2,407` chunks in `chunks.jsonl`) keyed by `<document_id>#p<NNN>`.

Second, `corpus_manifest.csv` records per-file `sha256` hashes, confirming 40 distinct reports (`consolidated` and `separate` versions differ in hash and content) with `0` duplicate `document_id` or `chunk_id` identifiers. Question expansion scripts normalize questions with lowercasing and whitespace collapse (`norm_question`) to reject exact or near-duplicate questions.

Third, `normalize_number()`, `src/build_table_records.py`, and `src/preprocess/table_extract.py` preserve raw numeric strings in `value_raw` and chunk texts while normalizing Vietnamese thousands separators (`91.279.041.771.826` -> `91279041771826`), comma decimals (`3,2` -> `3.2`, never multiplied by 100), and parenthetical negatives (`(983.237)` -> `-983237`). Units are inferred from table column headers (`Nghìn VND`, `Triệu VND`, `Tỷ VND`, `VND`, `%`) or page fallback, yielding `29,615` structured table records with `confidence` `0.93` (when `metric_code` exists) or `0.85` (minus `0.1` when the unit is absent).

## 8. Annotation Process

Annotations follow `data/annotations/annotation_guideline.md` (`v0.2`), executed by team annotators (`member-1`, `member-2`, `annotator-1`, `reviewer-2`) alongside deterministic script builders (`auto-builder`). Breakdown by `reviewer_id` across the `204` items: `auto-builder` (120), `auto-builder/reviewer-2` (30), `annotator-1` (23), `annotator-1/reviewer-2` (16), `member-1/reviewer-2` (6), `member-1/member-2` (5), and `member-1` (4).

Four rules govern all gold labels in `v0.2`:

1. Queries specifying `"công ty mẹ"` or `"riêng"` use `separate` statements; group or unspecified queries use `consolidated`.
2. Numeric answers come from the target fiscal year column (`2020-2024`, or comparative `"Số đầu năm"`/`"1/1/2020"` in `2020` filings when querying `2019` bases), never from adjacent columns or notes unless the question asks for a note disclosure (`ViFinQA-97`, `ViFinQA-186`, `ViFinQA-311`, `ViFinQA-612`).
3. Report scales (`VND` vs `Nghìn VND`) are converted to the exact unit requested by the question (`đồng`, `nghìn đồng`, `triệu đồng`, `tỷ đồng`, `trăm tỷ đồng`, `nghìn tỷ đồng`, `%`, `điểm phần trăm`, `lần`) and rounded to at most `4` decimal places (`round(x, 4)`).
4. Questions whose topic or period has zero coverage across all `2,407` chunks receive `needs_more_evidence: true`, `answer_type: "unanswerable"`, `evidence: []`, the canonical string `"Không đủ bằng chứng trong corpus để trả lời."`, and an explicit `unanswerable_reason` listing the searched phrases that returned `0` hits. Borderline accounting cases (`ViFinQA-97`, `ViFinQA-186`, `ViFinQA-709`) are documented inside `computation` and resolved against the primary statement or specified note per guideline Section 7.

## 9. Quality Checks

Across all `40` reports, `2,437` pages, and `2,585` HTML tables, `src/audit_ocr.py` (`report/ocr_audit.md`) measured `0.0000` `avg_ragged_row_ratio` on every report (zero column-misaligned HTML table rows) and `0` occurrences of the Unicode replacement character (`U+FFFD`). All `30` empty OCR pages are logged in `data/processed/ocr_audit_pages.csv` and excluded from retrieval chunks.

Running `src/data_quality_report.py` (`report/data_quality_report.md`) verified `0` duplicate or empty IDs across `corpus_manifest.csv` (40), `ocr_audit.csv` (40), `questions_matched.csv` (35), `questions_dropped.csv` (977), `data_manifest.csv` (244), `chunks.jsonl` (2,407), and `qa_gold.jsonl` (204), `0` out-of-vocabulary `answer_type` or `review_status` labels, and `0` `pending-answer` items.

`src/cross_review.py` runs two layers of verification:

1. Corpus-wide quote integrity (`204/204`): Every `vifinqa` (`35/35`) and answerable `supplement` (`7/7`) `evidence[].quote` matches verbatim inside `chunks.jsonl[chunk_id]["text"]` with `source_page == chunk["page"]`. For all `142` answerable `table-clean` items, both `metric` and `raw_value` tokens from `"metric | raw_value"` co-occur on an actual pipe-delimited line of the cited chunk.
2. Stratified independent audit (`53/204 = 25.98%`, `seed = 42`, `data/annotations/review_report.md`): Covers `table-clean` (`30`: T1=10, T2=9, T3=9, T5=2), `vifinqa` (`12`), `supplement` (`7`), and `dev-refusal` (`4`) across `dev` (`14`) and `test` (`39`), spanning `25` numeric, `19` computation, and `9` unanswerable items. Re-extracting raw numbers directly from `chunks.jsonl` (without reading `row['computation']`) and running zero-hit phrase probes across all `2,407` chunks produced **0 disagreements** (`agree: 53`, `disagree: 0`), bringing cumulative `reviewed-agree` in `qa_gold.jsonl` and `review_log.csv` to **57 / 204 (27.94%)** (including 4 previously verified `member-1/member-2` `supplement` items outside the random subsample).

## 10. Splits & Leakage Prevention

Split assignments live in `data/splits/dev.json`, `data/splits/test.json`, and `data/splits/split_meta.json`, mirrored identically at `evaluation/split_freeze.json`.

| Property | Value |
|---|---|
| `version` | `v4` |
| `seed` | `42` |
| `n_dev` | `44` (`table-clean`: 30, `vifinqa`: 9, `dev-refusal`: 4, `supplement`: 1; `40` answerable + `4` refusal; `refusal_den = 4`) |
| `n_test` | `160` (`table-clean`: 120, `vifinqa`: 26, `supplement`: 14; `144` answerable + `16` refusal; `refusal_den = 16`) |
| `sha256` | `0012ebccd6712b44cdd1faf18f020c547c82973db09d37ab2b9e96b0a94a34b4` |

Full sorted ID lists are stored in `data/splits/dev.json` (`44` IDs, covering `CLEAN-T1-HPG-2020-08` through `CLEAN-T3-NKG-2023-2024-B18`, `DEV-REF-01..04`, `S_NEW_03`, `ViFinQA-99`, and `ViFinQA-373`..`ViFinQA-973`) and `data/splits/test.json` (`160` IDs, covering `CLEAN-T1-HPG-2020-01` through `CLEAN-T5-NKG-2024-07`, `S_NEW_01..02`, `S_NEW_04..15`, and `ViFinQA-97`..`ViFinQA-709`).

Four safeguards prevent evaluation leakage:

1. All `160` `test` IDs and ground-truth assignments from `v3` remain untouched in `v4`; previously `pending-answer` `vifinqa` rows were populated from corpus evidence without changing split membership, and `DEV-REF-01..04` were added only to `dev`.
2. All `204` questions are unique after lowercasing and whitespace normalization, preventing duplicate or paraphrased test queries from entering `dev`.
3. Both `dev` and `test` query the same `40`-report corpus (`2,407` chunks), which is standard for fixed-corpus financial QA and explicitly disclosed in `evaluation/evaluation_protocol.md`. Results do not support generalization claims to unseen companies or years without a company-held-out evaluation.
4. Prompt rules, retrieval weights, and lookup aliases were tuned on `dev` only, with `test` reserved for final reporting. `src/build_gold.py` exits with status `1` if `qa_gold.jsonl` already has `> 50` non-empty rows unless `--force-v1` is passed.

## 11. Gold & Evaluation Protocol

Every answerable gold item stores `gold_answer`, `value` (normalized to `unit`, rounded to 4 decimals), `unit`, `evidence[]` (`chunk_id`, `source_page`, `quote`), and `computation` (arithmetic trace for `94` computation items and unit conversions). Every unanswerable gold item stores `"Không đủ bằng chứng trong corpus để trả lời."`, `needs_more_evidence: true`, and `unanswerable_reason`.

`src/evaluate/evaluate.py` (`evaluation/evaluation_protocol.md` v9) computes four metric groups offline over saved top-10 `predicted_chunk_ids`:

- Retrieval (`evidence_den`: 144 test, 40 dev): `recall_at_3`, `recall_at_5`, `recall_at_10`, `mrr_at_3`, `mrr_at_5`, `mrr_at_10`, `context_precision_at_5`, `context_recall_at_5`.
- Citation: `citation_precision_top1`, `citation_recall_at_5`, `citation_complete_rate` (`chunk_id`, `page`, `company_id`, `fiscal_year` per `config/answer_policy.yaml`), `page_accuracy`.
- Answer and financial period: `numeric_match` (tolerance `max(1e-4, |gv| × 1e-6)`), `exact_match`, `company_accuracy`, `year_accuracy`, `version_accuracy`, `period_accuracy` (matching multi-entity `|` sets via `parse_pipe_set()`), `unsupported_claim_rate` (chunk-isolated via `CHUNK_SEP`, unit factors bounded to `1e3..1e12` at `1e-3` relative tolerance, year headers `2020-2025` excluded), `faithfulness_heuristic` (`1 - unsupported_claim_rate`), and `answer_relevancy_heuristic`.
- Refusal and status (`refusal_den`: 16 test, 4 dev): `decide_status()` assigns `answered`, `partial_answer`, `refused`, or `ambiguous`; `refusal_precision`, `refusal_recall`, `false_answer_rate`, and per-item labels (`true_refusal`, `missed_refusal`, `false_refusal`, `true_answer`) are exported to `evaluation/refusal_labels/refusal_labels_E*.csv`.

Two portions remain unannotated by design or for future review: `147 / 204` (`72.06%`) items remain `draft-needs-second-reviewer` for a second human reviewer (while passing automated chunk-quote verification with `0` `pending-answer` items), and multi-hop `ViFinQA` questions (such as `ViFinQA-368`, spanning 4 companies and 10 chunks) have verified final gold values and evidence chunks without intermediate sub-step gold labels (`needs_decomposition` noted in `evaluation/pilot_advanced.md`).

## 12. Biases, Ethics & Risks

The `40` filings cover only 4 industrial, steel, and materials firms (`HPG`, `HSG`, `NKG`, `MSR`) across `2020-2024`, a period marked by post-2021 steel margin compression and `MSR` net losses in `2023-2024`. Models or rules tuned on these Circular `202/2014/TT-BTC` line items will not transfer directly to banks, insurers, or other accounting standards.

Upstream OCR texts preserve genuine auditor formatting differences, including `HSG` 2024 (PwC) printing expenses in parentheses `(35.008.227.341.981)` versus `HSG` 2020-2023 (KPMG) printing positive expense lines, and `MSR` reporting in `Nghìn VND` while `HPG`, `HSG`, and `NKG` report in `VND`. Occasional Vietnamese diacritic OCR typos (`"doanh thu thuân"`, `"NỢ PHÀI TRẢ"`) remain verbatim in chunks.

The filings contain only statutory corporate disclosures (including names of corporate executives, board chairs, and signing auditors already published by listed companies). Automated scans confirm `0` private consumer PII entries and `0` API keys or credentials inside `src/`, `app/`, `config/`, and `tests/`. Because `license_status` is `unknown_verify_with_teacher`, raw OCR filings under `data/raw/` must remain excluded from public Git commits until instructor confirmation.

## 13. Limitations & Inappropriate Uses

1. `HPG_2022_consolidated` has `24` blank trailing pages (`42`, `44-54`, `57-68`) in the upstream OCR snapshot, so note-level queries outside pages `1-41` cannot be answered from those missing notes (primary statements on earlier pages remain intact).
2. The `150` `table-clean` items inherited from `v2/v3` format `evidence[].quote` as two-column `"metric | raw_value"` pipe summaries rather than contiguous substrings; `src/cross_review.py` verifies both tokens on an actual pipe-delimited line of the cited chunk, whereas `vifinqa` (`35`) and answerable `supplement` (`7`) items store strict verbatim chunk substrings.
2. The `150` `table-clean` items inherited from `v2/v3` store `evidence[].quote` as two-column `"metric | raw_value"` pipe summaries instead of contiguous substrings; `src/cross_review.py` verifies both tokens on an actual pipe-delimited line of the cited chunk, whereas `vifinqa` (`35`) and answerable `supplement` (`7`) items store strict verbatim chunk substrings.
3. Multi-year comparisons can reflect inter-year note reclassifications (documented in `computation` and `data/annotations/review_report.md` for `ViFinQA-97`, `ViFinQA-186`, and `ViFinQA-709`).
4. On `dev`, `refusal_den = 4` (`test` holds `16`), so each individual refusal prediction shifts `dev` refusal precision/recall by `25` percentage points.
5. Do not use this benchmark or demo for live financial or investment decisions, do not extrapolate answers beyond `2020-2024` or outside `{HPG, HSG, NKG, MSR}`, and do not claim generalization to unseen companies or banking filings without an out-of-company test split.

## 14. Reproducibility & Access Instructions

The pipeline runs offline on CPU using Python `3.10.22` (`.venv`) and dependencies pinned in `requirements.txt` (`scikit-learn==1.7.2`, `pandas==2.3.3`, `numpy==2.2.6`, `scipy==1.15.3`, `PyYAML==6.0.3`, `streamlit==1.65.0`, `huggingface_hub==1.30.0`, `matplotlib==3.10.9`, `Pillow==12.3.0`).

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Download upstream data locally (`data/raw/` is excluded from Git):

```powershell
.\.venv\Scripts\python.exe src\download_vifinqa.py --mode questions --revision 0450088ab22ec946f04f097586967ca405955b3b
.\.venv\Scripts\python.exe src\download_vifinqa.py --mode corpus --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024 --revision 0450088ab22ec946f04f097586967ca405955b3b
```

Rebuild processed chunks, table records, `v4` gold (`seed = 42`), stratified cross-review, and data documentation:

```powershell
.\.venv\Scripts\python.exe src\select_corpus.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024 --versions consolidated separate
.\.venv\Scripts\python.exe src\filter_questions.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
.\.venv\Scripts\python.exe src\audit_ocr.py
.\.venv\Scripts\python.exe src\build_chunks.py
.\.venv\Scripts\python.exe src\build_table_records.py
.\.venv\Scripts\python.exe src\build_supplement_gold.py
.\.venv\Scripts\python.exe src\build_gold.py --force-v1
.\.venv\Scripts\python.exe src\build_expanded_gold_v2.py
.\.venv\Scripts\python.exe src\build_expanded_gold_v3.py
.\.venv\Scripts\python.exe src\resolve_vifinqa_and_dev_refusal.py
.\.venv\Scripts\python.exe src\cross_review.py
.\.venv\Scripts\python.exe src\build_data_docs.py
.\.venv\Scripts\python.exe src\data_quality_report.py
```

Run evaluation (`E0-E8`), `35` unit tests, and `4` demo verification checks:

```powershell
foreach ($r in "E0","E1","E2","E3","E4","E5","E6","E7","E8") { .\.venv\Scripts\python.exe src\evaluate\evaluate.py --run $r }
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe app\check_demo.py
```
