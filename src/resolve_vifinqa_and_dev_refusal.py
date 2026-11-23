"""Resolve the 35 ViFinQA items in qa_gold.jsonl from chunks.jsonl and add 4 dev refusal items (v4 split).

Rules enforced:
1. Every evidence[].quote must be an exact substring of data/processed/chunks.jsonl[chunk_id]['text'].
2. Every raw financial metric used in calculations is parsed directly from the cited verbatim chunk line(s).
3. Comparative columns in follow-up reports (e.g. 2020 BS comparative for 2019) are cross-checked.
4. All 160 existing `test` items in v3 are preserved completely unchanged in `test.json` and `qa_gold.jsonl`.
5. Four out-of-corpus refusal questions (DEV-REF-01..04) are verified to have 0 relevant evidence hits across
   all 2407 chunks and appended exclusively to `dev` (40 -> 44 dev, 160 -> 160 test, total 204).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
QA_PATH = ROOT / "data" / "annotations" / "qa_gold.jsonl"
LABELS_CSV = ROOT / "data" / "annotations" / "gold_labels.csv"
REVIEW_CSV = ROOT / "data" / "annotations" / "review_log.csv"
SPLITS_DIR = ROOT / "data" / "splits"
FREEZE_PATH = ROOT / "evaluation" / "split_freeze.json"

REFUSAL_TEXT = "Không đủ bằng chứng trong corpus để trả lời."
LABEL_FIELDS = ["question_id", "question", "company_id", "fiscal_year", "unit", "answer_type", "source"]
REVIEW_FIELDS = ["item_id", "gold", "reviewer", "status", "guideline_version", "disagreement_note"]


def load_chunks() -> dict[str, dict]:
    return {
        obj["chunk_id"]: obj
        for obj in (json.loads(line) for line in open(CHUNKS_PATH, encoding="utf-8") if line.strip())
    }


def parse_vn_number(raw: str) -> float:
    """Parse Vietnamese OCR integer/decimal strings like '(1.899.321.381)' or '99,988%'."""
    s = raw.strip()
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()
    if s.endswith("%"):
        s = s[:-1].strip()
    if "," in s and not re.search(r"\.\d{3},", s):
        # Decimal comma without thousand dots (e.g. '99,988')
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    else:
        s = s.replace(".", "").replace(",", ".")
    val = float(s)
    return -val if neg else val


def verify_quote(chunks: dict[str, dict], chunk_id: str, quote: str) -> dict:
    assert chunk_id in chunks, f"Missing chunk {chunk_id}"
    c = chunks[chunk_id]
    assert quote in c["text"], f"Quote not verbatim in {chunk_id}: {quote!r}"
    return {"chunk_id": chunk_id, "source_page": int(c["page"]), "quote": quote}


def fmt_num(val: float) -> float | int:
    r = round(val, 4)
    if r == 0:
        return 0
    if float(r).is_integer():
        return int(r)
    return r


def fmt_answer(val: float | int, unit: str) -> str:
    return f"{val} {unit}".strip() if unit else str(val)


# Exact consolidated primary-statement locations across all 20 consolidated reports (2020-2024)
# For 2019 figures, we extract from the comparative column of the 2020 consolidated report.
CONS_SPECS: dict[tuple[str, int], dict[str, tuple[str, str, int, str, int]]] = {}
# Maps (company, year) -> {metric_key: (chunk_id, header_quote, col_idx_from_right_or_valcol, row_prefix_or_exact, scale)}
# Wait: instead of complex indexing, let's define clean explicit verbatim row strings + scale (1 or 1000) and col_pos (0=current year, 1=prior year)

def load_consolidated_statements(chunks: dict[str, dict]) -> dict[tuple[str, int], dict[str, tuple[int, str, str, str]]]:
    """Verify verbatim primary statement lines for HPG/HSG/MSR/NKG 2019-2024 and parse exact VND integers.

    Returns dict[(company, year)][metric] = (value_vnd, chunk_id, header_quote, row_quote).
    """
    # Format: (company, report_year): {metric: (page, header_quote, row_quote, [(target_year, col_offset_from_nums_start)])}
    # To stay completely transparent and error-proof, specify every line with exact col values verified directly.
    raw_specs: list[tuple[str, int, str, str, dict[str, tuple[int, str, str, int, int]]]] = [
        # (company, page, metric, row_quote, cur_yr, prev_yr) -> simpler: specify per (company, report_year)
    ]

    # Exact page + header + verbatim line map directly verified from chunks.jsonl
    doc_lines: dict[tuple[str, int], dict[str, tuple[int, str, str, int]]] = {
        # --- HPG ---
        ("HPG", 2020): {
            "BS_100": (7, "| Mã số | Thuyết minh | 31/12/2020 VND | 1/1/2020 VND", "Tài sản ngắn hạn( ) | 100 | | 56.747.258.197.010 | 30.436.936.909.894", 1),
            "BS_140": (7, "| Mã số | Thuyết minh | 31/12/2020 VND | 1/1/2020 VND", "Hàng tồn kho | 140 | 9 | 26.286.822.229.202 | 19.411.922.748.095", 1),
            "BS_270": (8, "| Mã số | Thuyết minh | 31/12/2020 VND | 1/1/2020 VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 131.511.434.388.837 | 101.776.030.099.900", 1),
            "BS_300": (9, "| Mã số | Thuyết minh | 31/12/2020 VND | 1/1/2020 VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 72.291.648.082.726 | 53.989.393.956.205", 1),
            "BS_310": (9, "| Mã số | Thuyết minh | 31/12/2020 VND | 1/1/2020 VND", "Nợ ngắn hạn | 310 | | 51.975.217.447.498 | 26.984.198.187.977", 1),
            "BS_400": (10, "| Mã số | Thuyết minh | 31/12/2020 VND | 1/1/2020 VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 59.219.786.306.111 | 47.786.636.143.695", 1),
            "IS_10": (11, "| Mã số | Thuyết minh | 2020 VND | 2019 VND", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 30 | 90.118.503.426.717 | 63.658.192.673.791", 1),
            "IS_11": (11, "| Mã số | Thuyết minh | 2020 VND | 2019 VND", "Giá vốn hàng bán và dịch vụ cung cấp | 11 | 31 | 71.214.453.522.563 | 52.472.820.451.654", 1),
            "IS_20": (11, "| Mã số | Thuyết minh | 2020 VND | 2019 VND", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 18.904.049.904.154 | 11.185.372.222.137", 1),
            "IS_23": (11, "| Mã số | Thuyết minh | 2020 VND | 2019 VND", "Trong đó: Chi phí đi vay | 23 | | 2.191.680.923.417 | 936.710.218.359", 1),
            "IS_50": (11, "| Mã số | Thuyết minh | 2020 VND | 2019 VND", "Lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | 15.356.966.791.701 | 9.096.662.123.386", 1),
            "IS_60": (11, "| Mã số | Thuyết minh | 2020 VND | 2019 VND", "Lợi nhuận sau thuế TNDN (mang sang trang sau) (60 = 50 - 51 - 52) | 60 | | 13.506.164.056.907 | 7.578.248.236.229", 1),
            "CF_20": (13, "| Mã số | Thuyết minh | 2020 VND | 2019 VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 11.587.249.912.974 | 7.715.168.694.116", 1),
        },
        ("HPG", 2021): {
            "BS_100": (7, "| Mã số | Thuyết minh | 31/12/2021 VND | 1/1/2021 VND", "Tài sản ngắn hạn( ) | 100 | | 94.154.859.648.304 | 56.747.258.197.010", 1),
            "BS_140": (7, "| Mã số | Thuyết minh | 31/12/2021 VND | 1/1/2021 VND", "Hàng tồn kho | 140 | 10 | 42.134.493.932.210 | 26.286.822.229.202", 1),
            "BS_270": (8, "| Mã số | Thuyết minh | 31/12/2021 VND | 1/1/2021 VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 178.236.422.358.249 | 131.511.434.388.837", 1),
            "BS_300": (9, "| Mã số | Thuyết minh | 31/12/2021 VND | 1/1/2021 VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 87.455.796.846.810 | 72.291.648.082.726", 1),
            "BS_310": (9, "| Mã số | Thuyết minh | 31/12/2021 VND | 1/1/2021 VND", "Nợ ngắn hạn | 310 | | 73.459.315.876.441 | 51.975.217.447.498", 1),
            "BS_400": (10, "| Mã số | Thuyết minh | 31/12/2021 VND | 1/1/2021 VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 90.780.625.511.439 | 59.219.786.306.111", 1),
            "IS_10": (11, "| Mã số | Thuyết minh | 2021 VND | 2020 VND", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 31 | 149.679.789.979.345 | 90.118.503.426.717", 1),
            "IS_11": (11, "| Mã số | Thuyết minh | 2021 VND | 2020 VND", "Giá vốn hàng bán và dịch vụ cung cấp | 11 | 32 | 108.571.380.446.353 | 71.214.453.522.563", 1),
            "IS_20": (11, "| Mã số | Thuyết minh | 2021 VND | 2020 VND", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 41.108.409.532.992 | 18.904.049.904.154", 1),
            "IS_23": (11, "| Mã số | Thuyết minh | 2021 VND | 2020 VND", "Trong đó: Chi phí đi vay | 23 | | 2.525.823.258.237 | 2.191.680.923.417", 1),
            "IS_50": (11, "| Mã số | Thuyết minh | 2021 VND | 2020 VND", "Lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | 37.056.777.714.190 | 15.356.966.791.701", 1),
            "IS_60": (11, "| Mã số | Thuyết minh | 2021 VND | 2020 VND", "Lợi nhuận sau thuế TNDN (mang sang trang sau) (60 = 50 - 51 - 52) | 60 | | 34.520.954.931.298 | 13.506.164.056.907", 1),
            "CF_20": (13, "| Mã số | Thuyết minh | 2021 VND | 2020 VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 26.720.913.303.108 | 11.587.249.912.974", 1),
        },
        ("HPG", 2022): {
            "BS_100": (7, "| Mã số | Thuyết minh | 31/12/2022 VND | 1/1/2022 VND", "Tài sản ngắn hạn(100 = 110 + 120 + 130 + 140 + 150) | 100 | | 80.514.710.854.456 | 94.154.859.648.304", 1),
            "BS_140": (7, "| Mã số | Thuyết minh | 31/12/2022 VND | 1/1/2022 VND", "Hàng tồn kho | 140 | 9 | 34.491.111.096.123 | 42.134.493.932.210", 1),
            "BS_270": (8, "| Mã số | Thuyết minh | 31/12/2022 VND | 1/1/2022 VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 170.335.521.637.132 | 178.236.422.358.249", 1),
            "BS_300": (9, "| Mã số | Thuyết minh | 31/12/2022 VND | 1/1/2022 VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 74.222.582.021.349 | 87.455.796.846.810", 1),
            "BS_310": (9, "| Mã số | Thuyết minh | 31/12/2022 VND | 1/1/2022 VND", "Nợ ngắn hạn | 310 | | 62.385.392.809.685 | 73.459.315.876.441", 1),
            "BS_400": (10, "| Mã số | Thuyết minh | 31/12/2022 VND | 1/1/2022 VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 96.112.939.615.783 | 90.780.625.511.439", 1),
            "IS_10": (11, "| Mã số | Thuyết minh | 2022 VND | 2021 VND", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 30 | 141.409.274.460.632 | 149.679.789.979.345", 1),
            "IS_11": (11, "| Mã số | Thuyết minh | 2022 VND | 2021 VND", "Giá vốn hàng bán và dịch vụ cung cấp | 11 | 31 | 124.645.848.221.080 | 108.571.380.446.353", 1),
            "IS_20": (11, "| Mã số | Thuyết minh | 2022 VND | 2021 VND", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 16.763.426.239.552 | 41.108.409.532.992", 1),
            "IS_23": (11, "| Mã số | Thuyết minh | 2022 VND | 2021 VND", "Trong đó: Chi phí đi vay | 23 | | 3.083.638.131.818 | 2.525.823.258.237", 1),
            "IS_50": (11, "| Mã số | Thuyết minh | 2022 VND | 2021 VND", "Lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | 9.922.941.127.284 | 37.056.777.714.190", 1),
            "IS_60": (11, "| Mã số | Thuyết minh | 2022 VND | 2021 VND", "Lợi nhuận sau thuế TNDN (mang sang trang sau) (60 = 50 - 51 - 52) | 60 | | 8.444.429.054.516 | 34.520.954.931.298", 1),
            "CF_20": (13, "| Mã số | Thuyết minh | 2022 VND | 2021 VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 12.277.636.676.507 | 26.720.913.303.108", 1),
        },
        ("HPG", 2023): {
            "BS_100": (7, "| Mã số | Thuyết minh | 31/12/2023 VND | 1/1/2023 VND", "Tài sản ngắn hạn(100 = 110 + 120 + 130 + 140 + 150) | 100 | | 82.716.439.173.043 | 80.514.710.854.456", 1),
            "BS_140": (7, "| Mã số | Thuyết minh | 31/12/2023 VND | 1/1/2023 VND", "Hàng tồn kho | 140 | 11 | 34.504.487.406.261 | 34.491.111.096.123", 1),
            "BS_270": (8, "| Mã số | Thuyết minh | 31/12/2023 VND | 1/1/2023 VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 187.782.586.563.801 | 170.335.521.637.132", 1),
            "BS_300": (9, "| Mã số | Thuyết minh | 31/12/2023 VND | 1/1/2023 VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 84.946.167.324.422 | 74.222.582.021.349", 1),
            "BS_310": (9, "| Mã số | Thuyết minh | 31/12/2023 VND | 1/1/2023 VND", "Nợ ngắn hạn | 310 | | 71.513.492.904.733 | 62.385.392.809.685", 1),
            "BS_400": (10, "| Mã số | Thuyết minh | 31/12/2023 VND | 1/1/2023 VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 102.836.419.239.379 | 96.112.939.615.783", 1),
            "IS_10": (11, "| Mã số | Thuyết minh | 2023 VND | 2022 VND", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 31 | 118.953.027.893.654 | 141.409.274.460.632", 1),
            "IS_11": (11, "| Mã số | Thuyết minh | 2023 VND | 2022 VND", "Giá vốn hàng bán và dịch vụ cung cấp | 11 | 32 | 106.015.187.198.082 | 124.645.848.221.080", 1),
            "IS_20": (11, "| Mã số | Thuyết minh | 2023 VND | 2022 VND", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 12.937.840.695.572 | 16.763.426.239.552", 1),
            "IS_23": (11, "| Mã số | Thuyết minh | 2023 VND | 2022 VND", "Trong đó: Chi phí đi vay | 23 | | 3.585.077.683.881 | 3.083.638.131.818", 1),
            "IS_50": (11, "| Mã số | Thuyết minh | 2023 VND | 2022 VND", "Lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | 7.792.728.743.173 | 9.922.941.127.284", 1),
            "IS_60": (11, "| Mã số | Thuyết minh | 2023 VND | 2022 VND", "Lợi nhuận sau thuế TNDN (mang sang trang sau) (60 = 50 - 51 - 52) | 60 | | 6.800.388.315.081 | 8.444.429.054.516", 1),
            "CF_20": (13, "| Mã số | Thuyết minh | 2023 VND | 2022 VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 8.643.030.777.026 | 12.277.636.676.507", 1),
        },
        ("HPG", 2024): {
            "BS_100": (7, "| Mã số | Thuyết minh | 31/12/2024 VND | 1/1/2024 VND", "Tài sản ngắn hạn\\( (100 = 110 + 120 + 130 + 140 + 150) \\) | 100 | | 86.674.276.272.995 | 82.716.439.173.043", 1),
            "BS_140": (7, "| Mã số | Thuyết minh | 31/12/2024 VND | 1/1/2024 VND", "Hàng tồn kho | 140 | 10.1 | 46.091.222.189.472 | 34.504.487.406.261", 1),
            "BS_270": (8, "| Mã số | Thuyết minh | 31/12/2024 VND | 1/1/2024 VND", "TỔNG TÀI SẢN ( ) | 270 | | 224.489.707.553.981 | 187.782.586.563.801", 1),
            "BS_300": (9, "| Mã số | Thuyết minh | 31/12/2024 VND | 1/1/2024 VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 109.842.249.570.282 | 84.946.167.324.422", 1),
            "BS_310": (9, "| Mã số | Thuyết minh | 31/12/2024 VND | 1/1/2024 VND", "Nợ ngắn hạn | 310 | | 75.225.243.262.689 | 71.513.492.904.733", 1),
            "BS_400": (10, "| Mã số | Thuyết minh | 31/12/2024 VND | 1/1/2024 VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 114.647.457.983.699 | 102.836.419.239.379", 1),
            "IS_10": (11, "| Mã số | Thuyết minh | 2024 VND | 2023 VND", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 30 | 138.855.112.131.387 | 118.953.027.893.654", 1),
            "IS_11": (11, "| Mã số | Thuyết minh | 2024 VND | 2023 VND", "Giá vốn hàng bán và dịch vụ cung cấp | 11 | 31 | 120.357.563.003.703 | 106.015.187.198.082", 1),
            "IS_20": (11, "| Mã số | Thuyết minh | 2024 VND | 2023 VND", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 18.497.549.127.684 | 12.937.840.695.572", 1),
            "IS_23": (11, "| Mã số | Thuyết minh | 2024 VND | 2023 VND", "Trong đó: Chi phí đi vay | 23 | | 2.287.360.810.880 | 3.585.077.683.881", 1),
            "IS_50": (11, "| Mã số | Thuyết minh | 2024 VND | 2023 VND", "Lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | 13.693.502.261.178 | 7.792.728.743.173", 1),
            "IS_60": (11, "| Mã số | Thuyết minh | 2024 VND | 2023 VND", "Lợi nhuận sau thuế TNDN (mang sang trang sau) (60 = 50 - 51 - 52) | 60 | | 12.020.023.621.271 | 6.800.388.315.081", 1),
            "CF_20": (13, "| Mã số | Thuyết minh | 2024 VND | 2023 VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 6.608.320.655.215 | 8.643.030.777.026", 1),
        },
        # --- HSG ---
        ("HSG", 2020): {
            "BS_100": (6, "| Mã số | Thuyết minh | 30/9/2020 VND | 1/10/2019 VND", "Tài sản ngắn hạn(100 = 110 + 120 + 130 + 140 + 150) | 100 | | 9.022.315.330.402 | 7.355.652.364.016", 1),
            "BS_140": (6, "| Mã số | Thuyết minh | 30/9/2020 VND | 1/10/2019 VND", "Hàng tồn kho | 140 | 10 | 5.523.844.442.201 | 4.547.528.637.193", 1),
            "BS_270": (7, "| Mã số | Thuyết minh | 30/9/2020 VND | 1/10/2019 VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 17.756.407.664.931 | 17.225.438.463.039", 1),
            "BS_300": (8, "| Mã số | Thuyết minh | 30/9/2020 VND | 1/10/2019 VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 11.165.669.153.608 | 11.757.157.277.389", 1),
            "BS_310": (8, "| Mã số | Thuyết minh | 30/9/2020 VND | 1/10/2019 VND", "Nợ ngắn hạn | 310 | | 8.991.488.795.259 | 8.767.419.669.924", 1),
            "BS_400": (8, "| Mã số | Thuyết minh | 30/9/2020 VND | 1/10/2019 VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 6.590.738.511.323 | 5.468.281.185.650", 1),
            "IS_10": (9, "30/9/2020 VND | 30/9/2019 VND | | |", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 27 | 27.530.749.513.834 | 28.034.775.118.675", 1),
            "IS_11": (9, "30/9/2020 VND | 30/9/2019 VND | | |", "Giá vốn hàng bán và dịch vụ cung cấp | 11 | 28 | 22.903.482.165.423 | 24.836.155.036.672", 1),
            "IS_20": (9, "30/9/2020 VND | 30/9/2019 VND | | |", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 4.627.267.348.411 | 3.198.620.082.003", 1),
            "IS_23": (9, "30/9/2020 VND | 30/9/2019 VND | | |", "Trong đó: Chi phí lãi vay | 23 | | 560.086.135.926 | 745.960.164.920", 1),
            "IS_50": (9, "30/9/2020 VND | 30/9/2019 VND | | |", "Lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | 1.375.643.163.524 | 462.069.296.121", 1),
            "IS_60": (9, "30/9/2020 VND | 30/9/2019 VND | | |", "Lợi nhuận sau thuế TNDN (60 = 50 - 51 - 52) (mang sang trang sau) | 60 | | 1.153.014.017.309 | 361.371.503.746", 1),
            "CF_20": (11, "| Mã số | Thuyết minh | 30/9/2020 VND | 30/9/2019 VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 2.109.521.194.804 | 5.181.076.080.821", 1),
        },
        ("HSG", 2021): {
            "BS_100": (6, "| Mã số | Thuyết minh | 30/9/2021 VND | 1/10/2020 VND", "Tài sản ngắn hạn(100 = 110 + 120 + 130 + 140 + 150) | 100 | | 18.655.160.349.585 | 9.022.315.330.402", 1),
            "BS_140": (6, "| Mã số | Thuyết minh | 30/9/2021 VND | 1/10/2020 VND", "Hàng tồn kho | 140 | 11 | 12.349.095.948.022 | 5.523.844.442.201", 1),
            "BS_270": (7, "| Mã số | Thuyết minh | 30/9/2021 VND | 1/10/2020 VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 26.618.030.002.939 | 17.756.407.664.931", 1),
            "BS_300": (8, "| Mã số | Thuyết minh | 30/9/2021 VND | 1/10/2020 VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 15.786.236.174.085 | 11.165.669.153.608", 1),
            "BS_310": (8, "| Mã số | Thuyết minh | 30/9/2021 VND | 1/10/2020 VND", "Nợ ngắn hạn | 310 | | 14.372.246.601.418 | 8.991.488.795.259", 1),
            "BS_400": (8, "| Mã số | Thuyết minh | 30/9/2021 VND | 1/10/2020 VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 10.831.793.828.854 | 6.590.738.511.323", 1),
            "IS_10": (9, "30/9/2021 VND | 30/9/2020 VND | | |", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 28 | 48.726.522.233.736 | 27.530.749.513.834", 1),
            "IS_11": (9, "30/9/2021 VND | 30/9/2020 VND | | |", "Giá vốn hàng bán và dịch vụ cung cấp | 11 | 29 | 39.853.124.052.753 | 22.903.482.165.423", 1),
            "IS_20": (9, "30/9/2021 VND | 30/9/2020 VND | | |", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 8.873.398.180.983 | 4.627.267.348.411", 1),
            "IS_23": (9, "30/9/2021 VND | 30/9/2020 VND | | |", "Trong đó: Chi phí lãi vay | 23 | | 355.048.548.813 | 560.086.135.926", 1),
            "IS_50": (9, "30/9/2021 VND | 30/9/2020 VND | | |", "Lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | 4.915.483.070.880 | 1.375.643.163.524", 1),
            "IS_60": (9, "30/9/2021 VND | 30/9/2020 VND | | |", "Lợi nhuận sau thuế TNDN (60 = 50 - 51 - 52) (mang sang trang sau) | 60 | | 4.313.494.062.259 | 1.153.014.017.309", 1),
            "CF_20": (11, "30/9/2021 VND | 30/9/2020 VND | | |", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 1.496.076.448.500 | 2.109.521.194.804", 1),
        },
        ("HSG", 2022): {
            "BS_100": (6, "| Mã số | Thuyết minh | 30/9/2022 VND | 1/10/2021 VND", "Tài sản ngắn hạn( ) | 100 | | 9.834.993.231.398 | 18.655.160.349.585", 1),
            "BS_140": (6, "| Mã số | Thuyết minh | 30/9/2022 VND | 1/10/2021 VND", "Hàng tồn kho | 140 | 10 | 7.395.309.339.966 | 12.349.095.948.022", 1),
            "BS_270": (7, "| Mã số | Thuyết minh | 30/9/2022 VND | 1/10/2021 VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 17.025.411.187.931 | 26.618.030.002.939", 1),
            "BS_300": (8, "| Mã số | Thuyết minh | 30/9/2022 VND | 1/10/2021 VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 6.141.841.220.117 | 15.786.236.174.085", 1),
            "BS_310": (8, "| Mã số | Thuyết minh | 30/9/2022 VND | 1/10/2021 VND", "Nợ ngắn hạn | 310 | | 6.009.187.395.647 | 14.372.246.601.418", 1),
            "BS_400": (8, "| Mã số | Thuyết minh | 30/9/2022 VND | 1/10/2021 VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 10.883.569.967.814 | 10.831.793.828.854", 1),
            "IS_10": (9, "30/9/2022 VND | 30/9/2021 VND | | |", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 26 | 49.710.635.951.467 | 48.726.522.233.736", 1),
            "IS_11": (9, "30/9/2022 VND | 30/9/2021 VND | | |", "Giá vốn hàng bán và dịch vụ cung cấp | 11 | 27 | 44.771.944.789.711 | 39.853.124.052.753", 1),
            "IS_20": (9, "30/9/2022 VND | 30/9/2021 VND | | |", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 4.938.691.161.756 | 8.873.398.180.983", 1),
            "IS_23": (9, "30/9/2022 VND | 30/9/2021 VND | | |", "Trong đó: Chi phí lãi vay | 23 | | 260.241.924.339 | 355.048.548.813", 1),
            "IS_50": (9, "30/9/2022 VND | 30/9/2021 VND | | |", "Lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | 381.129.461.460 | 4.915.483.070.880", 1),
            "IS_60": (9, "30/9/2022 VND | 30/9/2021 VND | | |", "Lợi nhuận thuần sau thuế TNDN (60 = 50 - 51 - 52) (mang sang trang sau) | 60 | | 251.320.306.484 | 4.313.494.062.259", 1),
            "CF_20": (11, "30/9/2022 VND | 30/9/2021 VND | | |", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 2.844.560.115.909 | 1.496.076.448.500", 1),
        },
        ("HSG", 2023): {
            "BS_100": (6, "| Mã số | Thuyết minh | 30/9/2023 VND | 1/10/2022 VND", "Tài sản ngắn hạn\\( (100 = 110 + 120 + 130 + 140 + 150) \\) | 100 | | 11.274.839.904.924 | 9.834.993.231.398", 1),
            "BS_140": (6, "| Mã số | Thuyết minh | 30/9/2023 VND | 1/10/2022 VND", "Hàng tồn kho | 140 | 10 | 7.628.606.120.691 | 7.395.309.339.966", 1),
            "BS_270": (7, "| Mã số | Thuyết minh | 30/9/2023 VND | 1/10/2022 VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 17.365.305.645.644 | 17.025.411.187.931", 1),
            "BS_300": (8, "| Mã số | Thuyết minh | 30/9/2023 VND | 1/10/2022 VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 6.585.139.273.223 | 6.141.841.220.117", 1),
            "BS_310": (8, "| Mã số | Thuyết minh | 30/9/2023 VND | 1/10/2022 VND", "Nợ ngắn hạn | 310 | | 6.568.894.350.227 | 6.009.187.395.647", 1),
            "BS_400": (8, "| Mã số | Thuyết minh | 30/9/2023 VND | 1/10/2022 VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 10.780.166.372.421 | 10.883.569.967.814", 1),
            "IS_10": (9, "30/9/2023 VND | 30/9/2022 VND | | |", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 26 | 31.650.660.956.650 | 49.710.635.951.467", 1),
            "IS_11": (9, "30/9/2023 VND | 30/9/2022 VND | | |", "Giá vốn hàng bán và dịch vụ cung cấp | 11 | 27 | 28.590.018.867.006 | 44.771.944.789.711", 1),
            "IS_20": (9, "30/9/2023 VND | 30/9/2022 VND | | |", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 3.060.642.089.644 | 4.938.691.161.756", 1),
            "IS_23": (9, "30/9/2023 VND | 30/9/2022 VND | | |", "Trong đó: Chi phí lãi vay | 23 | | 195.489.503.107 | 260.241.924.339", 1),
            "IS_50": (9, "30/9/2023 VND | 30/9/2022 VND | | |", "Lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | 146.022.559.563 | 381.129.461.460", 1),
            "IS_60": (9, "30/9/2023 VND | 30/9/2022 VND | | |", "Lợi nhuận thuần sau thuế TNDN (60 = 50 - 51 - 52) (mang sang trang sau) | 60 | | 30.062.343.902 | 251.320.306.484", 1),
            "CF_20": (11, "30/9/2023 VND | 30/9/2022 VND | | |", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 1.865.627.170.231 | 2.844.560.115.909", 1),
        },
        ("HSG", 2024): {
            "BS_100": (7, "30.9.2024 VND | 30.9.2023 VND | | |", "100 | TÀI SẢN NGĂN HẠN | | 14.174.354.519.923 | 11.274.839.904.924", 1),
            "BS_140": (7, "30.9.2024 VND | 30.9.2023 VND | | |", "140 | Hàng tồn kho | 8 | 9.712.417.100.426 | 7.628.606.120.691", 1),
            "BS_270": (7, "30.9.2024 VND | 30.9.2023 VND | | |", "270 | TỔNG TÀI SẢN | | 19.565.620.935.157 | 17.365.305.645.644", 1),
            "BS_300": (8, "30.9.2024 VND | 30.9.2023 VND | | |", "300 | NỘ PHẢI TRẢ | | 8.648.683.879.620 | 6.585.139.273.223", 1),
            "BS_310": (8, "30.9.2024 VND | 30.9.2023 VND | | |", "310 | Nợ ngắn hạn | | 8.632.413.967.195 | 6.568.894.350.227", 1),
            "BS_400": (8, "30.9.2024 VND | 30.9.2023 VND | | |", "400 | VỐN CHỦ SỞ HỮU | | 10.916.937.055.537 | 10.780.166.372.421", 1),
            "IS_10": (9, "30.9.2024 VND | 30.9.2023 VND | | |", "10 | Doanh thu thuần về bán hàng và cung cấp dịch vụ | 26 | 39.271.893.738.448 | 31.650.660.956.650", 1),
            "IS_11": (9, "30.9.2024 VND | 30.9.2023 VND | | |", "11 | Giá vốn hàng bán và cung cấp dịch vụ | 27 | (35.008.227.341.981) | (28.590.018.867.006)", 1),
            "IS_20": (9, "30.9.2024 VND | 30.9.2023 VND | | |", "20 | Lợi nhuận gộp về bán hàng và cung cấp dịch vụ | | 4.263.666.396.467 | 3.060.642.089.644", 1),
            "IS_23": (9, "30.9.2024 VND | 30.9.2023 VND | | |", "23 | - Trong đó: Chi phí lãi vay | 29 | (133.022.415.113) | (195.489.503.107)", 1),
            "IS_50": (9, "30.9.2024 VND | 30.9.2023 VND | | |", "50 | Tổng lợi nhuận kế toán trước thuế | | 551.203.257.346 | 146.022.559.563", 1),
            "IS_60": (9, "30.9.2024 VND | 30.9.2023 VND | | |", "60 | Lợi nhuận sau thuế TNDN | | 514.673.976.370 | 30.062.343.902", 1),
            "CF_20": (10, "30.9.2024VND | 30.9.2023VND | |", "20 | Lưu chuyển tiền thuần từ hoạt động kinh doanh | (1.414.901.132.210) | 1.865.627.170.231", 1),
        },
        # --- MSR (unit: Nghìn VND -> scale=1000) ---
        ("MSR", 2020): {
            "BS_100": (7, "| Mã số | Thuyết minh | 31/12/2020Nghìn VND | 1/1/2020Nghìn VND", "Tài sản ngắn hạn( ) | 100 | | 9.756.298.985 | 7.581.595.985", 1000),
            "BS_140": (7, "| Mã số | Thuyết minh | 31/12/2020Nghìn VND | 1/1/2020Nghìn VND", "Hàng tồn kho | 140 | 11 | 4.880.128.480 | 3.139.024.753", 1000),
            "BS_270": (8, "| Mã số | Thuyết minh | 31/12/2020 Nghìn VND | 1/1/2020 Nghìn VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 40.108.847.814 | 29.774.719.881", 1000),
            "BS_300": (9, "| Mã số | Thuyết minh | 31/12/2020 Nghìn VND | 1/1/2020 Nghìn VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 26.029.306.779 | 17.304.897.615", 1000),
            "BS_310": (9, "| Mã số | Thuyết minh | 31/12/2020 Nghìn VND | 1/1/2020 Nghìn VND", "Nợ ngắn hạn | 310 | | 7.508.154.152 | 11.219.362.163", 1000),
            "BS_400": (9, "| Mã số | Thuyết minh | 31/12/2020 Nghìn VND | 1/1/2020 Nghìn VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 14.079.541.035 | 12.469.822.266", 1000),
            "IS_10": (10, "| Mã số | Thuyết minh | 2020 Nghìn VND | 2019 Nghìn VND", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 26 | 7.291.180.658 | 4.706.129.858", 1000),
            "IS_11": (10, "| Mã số | Thuyết minh | 2020 Nghìn VND | 2019 Nghìn VND", "Giá vốn hàng bán | 11 | | 7.113.222.006 | 3.971.145.298", 1000),
            "IS_20": (10, "| Mã số | Thuyết minh | 2020 Nghìn VND | 2019 Nghìn VND", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 177.958.652 | 734.984.560", 1000),
            "IS_50": (10, "| Mã số | Thuyết minh | 2020 Nghìn VND | 2019 Nghìn VND", "(Lỗ)/lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | (96.210.839) | 465.786.343", 1000),
            "IS_60": (10, "| Mã số | Thuyết minh | 2020 Nghìn VND | 2019 Nghìn VND", "Lợi nhuận sau thuế TNDN (60 = 50 - 51 - 52)(chuyển sang trang sau) | 60 | | 51.790.958 | 352.393.815", 1000),
            "CF_20": (12, "| Mã số | Thuyết minh | 2020 Nghìn VND | 2019 Nghìn VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | (964.427.806) | 1.431.679.571", 1000),
        },
        ("MSR", 2021): {
            "BS_100": (8, "| Mã số | Thuyết minh | 31/12/2021Nghìn VND | 1/1/2021Nghìn VND", "Tài sản ngắn hạn( ) | 100 | | 10.576.736.330 | 9.756.298.985", 1000),
            "BS_140": (8, "| Mã số | Thuyết minh | 31/12/2021Nghìn VND | 1/1/2021Nghìn VND", "Hàng tồn kho | 140 | 10 | 5.930.372.391 | 4.880.128.480", 1000),
            "BS_270": (9, "| Mã số | Thuyết minh | 31/12/2021 Nghìn VND | 1/1/2021 Nghìn VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 39.351.197.182 | 40.108.847.814", 1000),
            "BS_300": (10, "| Mã số | Thuyết minh | 31/12/2021Nghìn VND | 1/1/2021Nghìn VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 25.010.017.858 | 26.029.306.779", 1000),
            "BS_310": (10, "| Mã số | Thuyết minh | 31/12/2021Nghìn VND | 1/1/2021Nghìn VND", "Nợ ngắn hạn | 310 | | 7.877.179.852 | 7.508.154.152", 1000),
            "BS_400": (10, "| Mã số | Thuyết minh | 31/12/2021Nghìn VND | 1/1/2021Nghìn VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 14.341.179.324 | 14.079.541.035", 1000),
            "IS_10": (11, "| Mã số | Thuyết minh | 2021 Nghìn VND | 2020 Nghìn VND", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 26 | 13.564.289.846 | 7.291.180.658", 1000),
            "IS_11": (11, "| Mã số | Thuyết minh | 2021 Nghìn VND | 2020 Nghìn VND", "Giá vốn hàng bán | 11 | | 11.293.885.339 | 7.113.222.006", 1000),
            "IS_20": (11, "| Mã số | Thuyết minh | 2021 Nghìn VND | 2020 Nghìn VND", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 2.270.404.507 | 177.958.652", 1000),
            "IS_50": (11, "| Mã số | Thuyết minh | 2021 Nghìn VND | 2020 Nghìn VND", "Lợi nhuận/(lỗ) kế toán trước thuế (50 = 30 + 40) | 50 | | 156.515.914 | (96.210.839)", 1000),
            "IS_60": (11, "| Mã số | Thuyết minh | 2021 Nghìn VND | 2020 Nghìn VND", "Lợi nhuận sau thuế TNDN (60 = 50 - 51 - 52)(chuyển sang trang sau) | 60 | | 261.123.629 | 51.790.958", 1000),
            "CF_20": (13, "| Mã số | Thuyết minh | 2021 Nghìn VND | 2020 Nghìn VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | (592.098.636) | (964.427.806)", 1000),
        },
        ("MSR", 2022): {
            "BS_100": (9, "| Mã số | Thuyết minh | 31/12/2022Nghìn VND | 1/1/2022Nghìn VND", "Tài sản ngắn hạn( ) | 100 | | 12.228.222.738 | 10.576.736.330", 1000),
            "BS_140": (9, "| Mã số | Thuyết minh | 31/12/2022Nghìn VND | 1/1/2022Nghìn VND", "Hàng tồn kho | 140 | 9 | 6.858.167.780 | 5.930.372.391", 1000),
            "BS_270": (10, "| Mã số | Thuyết minh | 31/12/2022Nghìn VND | 1/1/2022Nghìn VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 41.521.000.189 | 39.351.197.182", 1000),
            "BS_300": (11, "| Mã số | Thuyết minh | 31/12/2022Nghìn VND | 1/1/2022Nghìn VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 26.273.561.415 | 25.010.017.858", 1000),
            "BS_310": (11, "| Mã số | Thuyết minh | 31/12/2022Nghìn VND | 1/1/2022Nghìn VND", "Nợ ngắn hạn | 310 | | 17.154.059.090 | 7.877.179.852", 1000),
            "BS_320": (11, "| Mã số | Thuyết minh | 31/12/2022Nghìn VND | 1/1/2022Nghìn VND", "Vay và trái phiếu phát hành ngắn hạn | 320 | 19(a) | 13.105.475.407 | 4.800.093.173", 1000),
            "BS_400": (11, "| Mã số | Thuyết minh | 31/12/2022Nghìn VND | 1/1/2022Nghìn VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 15.247.438.774 | 14.341.179.324", 1000),
            "IS_10": (12, "| Mã số | Thuyết minh | 2022 Nghìn VND | 2021 Nghìn VND", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 25 | 15.549.547.654 | 13.564.289.846", 1000),
            "IS_11": (12, "| Mã số | Thuyết minh | 2022 Nghìn VND | 2021 Nghìn VND", "Giá vốn hàng bán | 11 | | 13.172.693.544 | 11.293.885.339", 1000),
            "IS_20": (12, "| Mã số | Thuyết minh | 2022 Nghìn VND | 2021 Nghìn VND", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 2.376.854.110 | 2.270.404.507", 1000),
            "IS_23": (12, "| Mã số | Thuyết minh | 2022 Nghìn VND | 2021 Nghìn VND", "Trong đó: Chi phí lãi vay | 23 | | 1.194.553.796 | 1.145.321.327", 1000),
            "IS_50": (12, "| Mã số | Thuyết minh | 2022 Nghìn VND | 2021 Nghìn VND", "(Lỗ)/lợi nhuận kế toán trước thuế (50 = 30 + 40) | 50 | | (22.646.401) | 156.515.914", 1000),
            "IS_60": (12, "| Mã số | Thuyết minh | 2022 Nghìn VND | 2021 Nghìn VND", "Lợi nhuận sau thuế TNDN (60 = 50 - 51 - 52) (chuyển sang trang sau) | 60 | | 105.151.058 | 261.123.629", 1000),
            "CF_20": (14, "| Mã số | Thuyết minh | 2022Nghìn VND | 2021Nghìn VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 1.126.322.737 | (592.098.636)", 1000),
        },
        ("MSR", 2023): {
            "BS_100": (9, "| Mã số | Thuyết minh | 31/12/2023Nghìn VND | 1/1/2023Nghìn VND", "Tài sản ngắn hạn( ) | 100 | | 10.603.675.497 | 12.228.222.738", 1000),
            "BS_140": (9, "| Mã số | Thuyết minh | 31/12/2023Nghìn VND | 1/1/2023Nghìn VND", "Hàng tồn kho | 140 | 11 | 5.997.555.598 | 6.858.167.780", 1000),
            "BS_270": (10, "| Mã số | Thuyết minh | 31/12/2023Nghìn VND | 1/1/2023Nghìn VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 40.372.356.113 | 41.521.000.189", 1000),
            "BS_300": (11, "| Mã số | Thuyết minh | 31/12/2023Nghìn VND | 1/1/2023Nghìn VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 26.747.864.250 | 26.273.561.415", 1000),
            "BS_310": (11, "| Mã số | Thuyết minh | 31/12/2023Nghìn VND | 1/1/2023Nghìn VND", "Nợ ngắn hạn | 310 | | 11.020.687.246 | 17.154.059.090", 1000),
            "BS_400": (11, "| Mã số | Thuyết minh | 31/12/2023Nghìn VND | 1/1/2023Nghìn VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 13.624.491.863 | 15.247.438.774", 1000),
            "IS_10": (12, "| Mã số | Thuyết minh | 2023 Nghìn VND | 2022 Nghìn VND", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 27 | 14.093.253.487 | 15.549.547.654", 1000),
            "IS_11": (12, "| Mã số | Thuyết minh | 2023 Nghìn VND | 2022 Nghìn VND", "Giá vốn hàng bán | 11 | | 13.308.967.243 | 13.172.693.544", 1000),
            "IS_20": (12, "| Mã số | Thuyết minh | 2023 Nghìn VND | 2022 Nghìn VND", "Lợi nhuận gộp (20 = 10 - 11) | 20 | | 784.286.244 | 2.376.854.110", 1000),
            "IS_23": (12, "| Mã số | Thuyết minh | 2023 Nghìn VND | 2022 Nghìn VND", "Trong đó: Chi phí lãi vay | 23 | | 1.503.015.894 | 1.119.988.084", 1000),
            "IS_50": (12, "| Mã số | Thuyết minh | 2023 Nghìn VND | 2022 Nghìn VND", "Lỗ kế toán trước thuế (50 = 30 + 40) | 50 | | (1.654.012.824) | (22.646.401)", 1000),
            "IS_60": (12, "| Mã số | Thuyết minh | 2023 Nghìn VND | 2022 Nghìn VND", "(Lỗ)/lợi nhuận sau thuế TNDN (60 = 50 - 51 - 52) (chuyển sang trang sau) | 60 | | (1.529.610.701) | 105.151.058", 1000),
            "CF_20": (14, "| Mã số | Thuyết minh | 2023Nghìn VND | 2022Nghìn VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | (156.028.851) | 1.126.322.737", 1000),
        },
        ("MSR", 2024): {
            "BS_100": (8, "| Mã số | Thuyết minh | 31/12/2024Nghìn VND | 1/1/2024Nghìn VND", "Tài sản ngắn hạn\\( (100 = 110 + 120 + 130 + 140 + 150) \\) | 100 | | 6.992.043.391 | 10.603.675.497", 1000),
            "BS_140": (8, "| Mã số | Thuyết minh | 31/12/2024Nghìn VND | 1/1/2024Nghìn VND", "Hàng tồn kho | 140 | 11 | 2.967.555.729 | 5.997.555.598", 1000),
            "BS_270": (9, "| Mã số | Thuyết minh | 31/12/2024Nghìn VND | 1/1/2024Nghìn VND", "TỔNG TÀI SẢN (270 = 100 + 200) | 270 | | 26.966.527.000 | 40.372.356.113", 1000),
            "BS_300": (10, "| Mã số | Thuyết minh | 31/12/2024Nghìn VND | 1/1/2024Nghìn VND", "NỘ PHẢI TRẢ (300 = 310 + 330) | 300 | | 14.802.833.484 | 26.747.864.250", 1000),
            "BS_310": (10, "| Mã số | Thuyết minh | 31/12/2024Nghìn VND | 1/1/2024Nghìn VND", "Nợ ngắn hạn | 310 | | 5.185.425.509 | 11.020.687.246", 1000),
            "BS_400": (10, "| Mã số | Thuyết minh | 31/12/2024Nghìn VND | 1/1/2024Nghìn VND", "VỐN CHỦ SỞ HỮU (400 = 410) | 400 | | 12.163.693.516 | 13.624.491.863", 1000),
            "IS_10": (11, "| Mã số | Thuyết minh | 2024Nghìn VND | 2023Nghìn VND", "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 28 | 14.336.328.727 | 14.093.253.487", 1000),
            "IS_11": (11, "| Mã số | Thuyết minh | 2024Nghìn VND | 2023Nghìn VND", "Giá vốn hàng bán | 11 | | 13.443.622.106 | 13.308.967.243", 1000),
            "IS_20": (11, "| Mã số | Thuyết minh | 2024Nghìn VND | 2023Nghìn VND", "Lợi nhuận gộp về bán hàng và cung cấp dịch vụ (20 = 10 - 11) | 20 | | 892.706.621 | 784.286.244", 1000),
            "IS_23": (11, "| Mã số | Thuyết minh | 2024Nghìn VND | 2023Nghìn VND", "Trong đó: Chi phí lãi vay | 23 | | 1.371.669.159 | 1.503.015.894", 1000),
            "IS_50": (11, "| Mã số | Thuyết minh | 2024Nghìn VND | 2023Nghìn VND", "Lỗ kế toán trước thuế (50 = 30 + 40) | 50 | | (933.569.686) | (1.654.012.824)", 1000),
            "IS_60": (11, "| Mã số | Thuyết minh | 2024Nghìn VND | 2023Nghìn VND", "Lỗ sau thuế TNDN (60 =50 - 51 - 52) (chuyển sang trang sau) | 60 | | (1.586.598.650) | (1.529.610.701)", 1000),
            "CF_20": (13, "| Mã số | Thuyết minh | 2024Nghìn VND | 2023Nghìn VND", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 1.772.093.355 | (156.028.851)", 1000),
        },
        # --- NKG ---
        ("NKG", 2020): {
            "BS_100": (7, "2020 VND | 2019 VND | | |", "100 | TÀI SẢN NGẮN HẠN | | 4.492.264.536.968 | 4.435.465.874.629", 1),
            "BS_140": (7, "2020 VND | 2019 VND | | |", "140 | Hàng tồn kho | | 2.371.077.179.239 | 2.589.368.506.519", 1),
            "BS_270": (8, "2020 VND | 2019 VND | | |", "270 | TỔNG TÀI SẢN | | 7.763.093.325.248 | 8.064.358.103.268", 1),
            "BS_300": (9, "2020 VND | 2019 VND | | |", "300 | NỘ PHẢI TRẢ | | 4.582.073.162.617 | 5.047.543.923.750", 1),
            "BS_310": (9, "2020 VND | 2019 VND | | |", "310 | Nợ ngắn hạn | | 4.097.976.895.372 | 4.342.498.959.228", 1),
            "BS_400": (9, "2020 VND | 2019 VND | | |", "400 | VỐN CHỦ SỞ HỮU | | 3.181.020.162.631 | 3.016.814.179.518", 1),
            "IS_10": (10, "VND | VND | | |", "10 | Doanh thu thuân về bán hàng và cung cấp dịch vụ | 22 | 11.559.674.520.160 | 12.176.796.914.657", 1),
            "IS_11": (10, "VND | VND | | |", "11 | Giá vốn hàng bán và dịch vụ cung cấp | 23 | (10.690.464.691.531) | (11.835.048.249.482)", 1),
            "IS_20": (10, "VND | VND | | |", "20 | Lợi nhuận gộp về bán hàng và cung cấp dịch vụ | | 869.209.828.629 | 341.748.665.175", 1),
            "IS_23": (10, "VND | VND | | |", "23 | - Trong đó: Chi phí lãi vay | | (222.154.457.661) | (237.062.837.775)", 1),
            "IS_50": (10, "VND | VND | | |", "50 | Tổng lợi nhuận kê toán trước thuê | | 320.812.116.164 | 90.108.783.396", 1),
            "IS_60": (10, "VND | VND | | |", "60 | Lợi nhuận sau thuê TNDN | | 295.269.532.668 | 47.333.714.464", 1),
            "CF_20": (11, "2020 VND | 2019 VND | |", "20 | Lưu chuyển tiền thuần từ hoạt động kinh doanh | 15.577.095.111 | 1.180.979.766.583", 1),
        },
        ("NKG", 2021): {
            "BS_100": (8, "2021 VND | 2020 VND | | |", "100 | TÀI SẢN NGĂN HẠN | | 12.215.599.008.275 | 4.492.264.536.968", 1),
            "BS_140": (8, "2021 VND | 2020 VND | | |", "140 | Hàng tồn kho | | 8.281.323.556.123 | 2.371.077.179.239", 1),
            "BS_270": (9, "2021 VND | 2020 VND | | |", "270 | TỔNG TÀI SẢN | | 15.397.915.366.296 | 7.763.093.325.248", 1),
            "BS_300": (10, "2021VND | 2020VND | | |", "300 | NỘ PHẢI TRẢ | | 9.674.711.671.751 | 4.582.073.162.617", 1),
            "BS_310": (10, "2021VND | 2020VND | | |", "310 | Nợ ngắn hạn | | 9.598.192.512.183 | 4.097.976.895.372", 1),
            "BS_400": (10, "2021VND | 2020VND | | |", "400 | VỐN CHỦ SỞ HỮU | | 5.723.203.694.545 | 3.181.020.162.631", 1),
            "IS_10": (11, "2021 VND | 2020 VND | | |", "10 | Doanh thu thuần về bán hàng và cung cấp dịch vụ | 23 | 28.173.402.236.226 | 11.559.674.520.160", 1),
            "IS_11": (11, "2021 VND | 2020 VND | | |", "11 | Giá vốn hàng bán và dịch vụ cung cấp | 24 | (23.903.545.311.978) | (10.690.464.691.531)", 1),
            "IS_20": (11, "2021 VND | 2020 VND | | |", "20 | Lợi nhuận gộp về bán hàng và cung cấp dịch vụ | | 4.269.856.924.248 | 869.209.828.629", 1),
            "IS_23": (11, "2021 VND | 2020 VND | | |", "23 | - Trong đó: Chi phí lãi vay | | (243.685.237.356) | (222.154.457.661)", 1),
            "IS_50": (11, "2021 VND | 2020 VND | | |", "50 | Tổng lợi nhuận kế toán trước thuế | | 2.562.028.980.555 | 320.812.116.164", 1),
            "IS_60": (11, "2021 VND | 2020 VND | | |", "60 | Lợi nhuận sau thuế TNDN | | 2.225.261.058.221 | 295.269.532.668", 1),
            "CF_20": (12, "2021VND | 2020VND | |", "20 | Lưu chuyển tiền thuần từ hoạt động kinh doanh | (308.274.050.561) | 15.577.095.111", 1),
        },
        ("NKG", 2022): {
            "BS_100": (8, "2022 VND | 2021 VND | | |", "100 | TÀI SẢN NGÁN HẠN | | 10.414.909.064.976 | 12.215.599.008.275", 1),
            "BS_140": (8, "2022 VND | 2021 VND | | |", "140 | Hàng tồn kho | 8 | 7.000.417.214.505 | 8.281.323.556.123", 1),
            "BS_270": (9, "2022 VND | 2021 VND | | |", "270 | TỔNG TÀI SẢN | | 13.460.759.829.882 | 15.397.915.366.296", 1),
            "BS_300": (10, "2022 VND | 2021 VND | | |", "300 | NỘ PHẢI TRẢ | | 8.141.109.694.811 | 9.674.711.671.751", 1),
            "BS_310": (10, "2022 VND | 2021 VND | | |", "310 | Nợ ngắn hạn | | 8.108.870.806.964 | 9.598.192.512.183", 1),
            "BS_400": (10, "2022 VND | 2021 VND | | |", "400 | VỐN CHỦ SỞ HỮU | | 5.319.650.135.071 | 5.723.203.694.545", 1),
            "IS_10": (11, "2022VND | 2021VND | | |", "10 | Doanh thu thuần về bán hàng và cung cấp dịch vụ | 22 | 23.071.247.285.247 | 28.173.402.236.226", 1),
            "IS_11": (11, "2022VND | 2021VND | | |", "11 | Giá vốn hàng bán và dịch vụ cung cấp | 23 | (21.589.886.519.482) | (23.903.545.311.978)", 1),
            "IS_20": (11, "2022VND | 2021VND | | |", "20 | Lợi nhuận gộp về bán hàng và cung cấp dịch vụ | | 1.481.360.765.765 | 4.269.856.924.248", 1),
            "IS_23": (11, "2022VND | 2021VND | | |", "23 | - Trong đó: Chi phí lãi vay | 25 | (262.466.234.780) | (243.685.237.356)", 1),
            "IS_50": (11, "2022VND | 2021VND | | |", "50 | Tổng (lỗ)/lợi nhuận kế toán trước thuế | | (106.912.505.314) | 2.562.028.980.555", 1),
            "IS_60": (11, "2022VND | 2021VND | | |", "60 | (Lỗ)/lợi nhuận sau thuế TNDN | | (124.684.837.727) | 2.225.261.058.221", 1),
            "CF_20": (12, "2022VND | 2021VND | |", "20 | Lưu chuyển tiền thuần từ hoạt động kinh doanh | (827.920.885.674) | (308.274.050.561)", 1),
        },
        ("NKG", 2023): {
            "BS_100": (8, "2023 VND | 2022 VND | | |", "100 | TÀI SẢN NGẮN HẠN | | 9.322.639.041.423 | 10.414.909.064.976", 1),
            "BS_140": (8, "2023 VND | 2022 VND | | |", "140 | Hàng tồn kho | 8 | 5.718.699.385.156 | 7.000.417.214.505", 1),
            "BS_270": (9, "2023 VND | 2022 VND | | |", "270 | TỔNG TÀI SẢN | | 12.235.401.246.591 | 13.460.759.829.882", 1),
            "BS_300": (10, "2023 VND | 2022 VND | | |", "300 | NỘ PHẢI TRẢ | | 6.812.327.289.944 | 8.141.109.694.811", 1),
            "BS_310": (10, "2023 VND | 2022 VND | | |", "310 | Nợ ngắn hạn | | 6.784.014.554.254 | 8.108.870.806.964", 1),
            "BS_400": (10, "2023 VND | 2022 VND | | |", "400 | VỐN CHỦ SỞ HỮU | | 5.423.073.956.647 | 5.319.650.135.071", 1),
            "IS_10": (11, "2023 VND | 2022 VND | | |", "10 | Doanh thu thuần về bán hàng và cung cấp dịch vụ | 23 | 18.595.974.253.087 | 23.071.247.285.247", 1),
            "IS_11": (11, "2023 VND | 2022 VND | | |", "11 | Giá vốn hàng bán và dịch vụ cung cấp | 24 | (17.483.711.237.040) | (21.589.886.519.482)", 1),
            "IS_20": (11, "2023 VND | 2022 VND | | |", "20 | Lợi nhuận gộp về bán hàng và cung cấp dịch vụ | | 1.112.263.016.047 | 1.481.360.765.765", 1),
            "IS_23": (11, "2023 VND | 2022 VND | | |", "23 | - Trong đó: Chi phí lãi vay | | (292.679.834.464) | (262.466.234.780)", 1),
            "IS_50": (11, "2023 VND | 2022 VND | | |", "50 | Tổng lợi nhuận/(lỗ) kế toán trước thuế | | 177.310.914.179 | (106.912.505.314)", 1),
            "IS_60": (11, "2023 VND | 2022 VND | | |", "60 | Lợi nhuận/(lỗ) sau thuế TNDN | | 117.408.565.158 | (124.684.837.727)", 1),
            "CF_20": (12, "2023 VND | 2022 VND | |", "20 | Lưu chuyển tiền thuần từ hoạt động kinh doanh | 268.556.155.820 | (827.920.885.674)", 1),
        },
        ("NKG", 2024): {
            "BS_100": (8, "2024 VND | 2023 VND | | |", "100 | TÀI SẢN NGẮN HẠN | | 10.202.370.500.547 | 9.322.639.041.423", 1),
            "BS_140": (8, "2024 VND | 2023 VND | | |", "140 | Hàng tồn kho | 9 | 6.690.482.934.519 | 5.718.699.385.156", 1),
            "BS_270": (9, "2024 VND | 2023 VND | | |", "270 | TỔNG TÀI SẢN | | 13.519.085.552.805 | 12.235.401.246.591", 1),
            "BS_300": (10, "2024 VND | 2023 VND | | |", "300 | NỘ PHÀI TRÀ | | 7.647.678.978.332 | 6.812.327.289.944", 1),
            "BS_310": (10, "2024 VND | 2023 VND | | |", "310 | Nợ ngắn hạn | | 7.620.886.731.385 | 6.784.014.554.254", 1),
            "BS_400": (10, "2024 VND | 2023 VND | | |", "400 | VỐN CHỦ SỞ HỮU | | 5.871.406.574.473 | 5.423.073.956.647", 1),
            "IS_10": (11, "2024 VND | 2023 VND | | |", "10 | Doanh thu thuần về bán hàng và cung cấp dịch vụ | 25 | 20.609.022.190.077 | 18.595.974.253.087", 1),
            "IS_11": (11, "2024 VND | 2023 VND | | |", "11 | Giá vốn hàng bán và dịch vụ cung cấp | 26 | (18.777.248.235.147) | (17.483.711.237.040)", 1),
            "IS_20": (11, "2024 VND | 2023 VND | | |", "20 | Lợi nhuận gộp về bán hàng và cung cấp dịch vụ | | 1.831.773.954.930 | 1.112.263.016.047", 1),
            "IS_23": (11, "2024 VND | 2023 VND | | |", "23 | - Trong đó: Chi phí lãi vay | | (207.841.259.563) | (292.679.834.464)", 1),
            "IS_50": (11, "2024 VND | 2023 VND | | |", "50 | Tổng lợi nhuận kế toán trước thuế | | 558.169.985.495 | 177.310.914.179", 1),
            "IS_60": (11, "2024 VND | 2023 VND | | |", "60 | Lợi nhuận sau thuế TNDN | | 453.008.144.440 | 117.408.565.158", 1),
            "CF_20": (12, "2024 VND | 2023 VND | |", "20 | Lưu chuyển tiền thuần từ hoạt động kinh doanh | (559.962.641.389) | 268.556.155.820", 1),
        },
    }

    parsed: dict[tuple[str, int], dict[str, tuple[float, str, str, str]]] = {}
    for (comp, yr), metrics in doc_lines.items():
        parsed[(comp, yr)] = {}
        if yr == 2020:
            parsed.setdefault((comp, 2019), {})
        for mkey, (pg, hdr, row, scale) in metrics.items():
            cid = f"{comp}_{yr}_consolidated#p{pg:03d}"
            verify_quote(chunks, cid, hdr)
            verify_quote(chunks, cid, row)
            # Last two pipe-separated cells are (current_year_str, prior_year_str)
            cells = [c.strip() for c in row.split("|")]
            cur_val = parse_vn_number(cells[-2]) * scale
            prev_val = parse_vn_number(cells[-1]) * scale
            # Normalize COGS & interest expense magnitude to positive for margin/DIO/ICR formulas
            if mkey in ("IS_11", "IS_23"):
                cur_val = abs(cur_val)
                prev_val = abs(prev_val)
            parsed[(comp, yr)][mkey] = (cur_val, cid, hdr, row)
            if yr == 2020:
                parsed[(comp, 2019)][mkey] = (prev_val, cid, hdr, row)
            else:
                # Assert comparative prior year in T matches year T-1 (allowing only known MSR IS_23 comparative note)
                if mkey in parsed.get((comp, yr - 1), {}) and not (comp == "MSR" and yr == 2023 and mkey == "IS_23"):
                    prev_stored = parsed[(comp, yr - 1)][mkey][0]
                    assert prev_val == prev_stored, f"Mismatch {comp} {yr} {mkey}: prev_col={prev_val} != {yr-1}={prev_stored}"
    return parsed


def build_group_evidence(
    chunks: dict[str, dict],
    data: dict[tuple[str, int], dict[str, tuple[float, str, str, str]]],
    specs: list[tuple[str, int, list[str]]],
) -> list[dict]:
    """Deduplicated verbatim evidence covering header + requested metric rows for each (company, year)."""
    seen_quotes: set[tuple[str, str]] = set()
    ev: list[dict] = []
    for comp, yr, keys in specs:
        # Handle 2019 comparative stored under 2020 report
        for k in keys:
            val, cid, hdr, row = data[(comp, yr)][k]
            for q in (hdr, row):
                if (cid, q) not in seen_quotes:
                    seen_quotes.add((cid, q))
                    ev.append(verify_quote(chunks, cid, q))
    return ev


def resolve_vifinqa(chunks: dict[str, dict], data: dict[tuple[str, int], dict[str, tuple[float, str, str, str]]]) -> dict[str, dict]:
    """Return resolved fields for all 35 ViFinQA question IDs."""
    res: dict[str, dict] = {}

    def vnd_s(comp: str, yr: int, m: str) -> float:
        return data[(comp, yr)][m][0]

    def qr(comp: str, yr: int) -> float:
        return (vnd_s(comp, yr, "BS_100") - vnd_s(comp, yr, "BS_140")) / vnd_s(comp, yr, "BS_310")

    def gm(comp: str, yr: int) -> float:
        return vnd_s(comp, yr, "IS_20") / vnd_s(comp, yr, "IS_10") * 100.0

    def nm(comp: str, yr: int) -> float:
        return vnd_s(comp, yr, "IS_60") / vnd_s(comp, yr, "IS_10") * 100.0

    def dio(comp: str, yr: int) -> float:
        avg_inv = (vnd_s(comp, yr - 1, "BS_140") + vnd_s(comp, yr, "BS_140")) / 2.0
        return 365.0 * avg_inv / vnd_s(comp, yr, "IS_11")

    def rev_g(comp: str, yr: int) -> float:
        r0 = vnd_s(comp, yr - 1, "IS_10")
        r1 = vnd_s(comp, yr, "IS_10")
        return (r1 - r0) / r0 * 100.0

    # --- Group A/C: 9 single/note/parent/count items ---
    # 1. ViFinQA-97
    c97 = "HPG_2023_separate#p027"
    q97_hdr = "Tỷ lệ %sở hữu | Tỷ lệ %quyềnbiểu quyết | Giá gốcVND | Giá trịhợp lýVND | Tỷ lệ %sở hữu | Tỷ lệ %quyềnbiểu quyết | Giá gốcVND | Giá trịhợp lýVND |"
    q97_row = "Công ty CP Gang thép Hòa Phát (i) | 99,988% | 99,988% | 53.999.220.000.000 | | 99,998% | 99,998% | 47.499.220.000.000 |"
    res["ViFinQA-97"] = {
        "value": 99.988, "unit": "%", "gold_answer": "99.988 %",
        "report_id": "HPG_2023_separate", "source_page": 27,
        "evidence": [verify_quote(chunks, c97, "| 31/12/2023 | 31/12/2023 | 31/12/2023 | 31/12/2023 | 1/1/2023 | 1/1/2023 | 1/1/2023 | 1/1/2023"), verify_quote(chunks, c97, q97_hdr), verify_quote(chunks, c97, q97_row)],
        "computation": "Theo Thuyết minh 12.2 BCTC riêng HPG năm 2023 (HPG_2023_separate#p027), cột 'Tỷ lệ %sở hữu' tại 31/12/2023 của Công ty CP Gang thép Hòa Phát là 99,988% = 99.988% (được xác nhận ở số đầu năm 1/1/2024 trên HPG_2024_separate#p025; lưu ý tỷ lệ lợi ích & quyền biểu quyết hợp nhất toàn Tập đoàn tại HPG_2023_consolidated#p017 là 99,999%).",
    }

    # 2. ViFinQA-99
    c99 = "NKG_2022_consolidated#p008"
    q99_hdr = "2022 VND | 2021 VND | | |"
    q99_row = "111 | Tiền | | 948.303.528.970 | 670.954.162.335"
    v99 = fmt_num(948303528970 / 1e9)
    res["ViFinQA-99"] = {
        "value": v99, "unit": "tỷ đồng", "gold_answer": fmt_answer(v99, "tỷ đồng"),
        "report_id": "NKG_2022_consolidated", "source_page": 8,
        "evidence": [verify_quote(chunks, c99, q99_hdr), verify_quote(chunks, c99, q99_row)],
        "computation": f"Bảng cân đối kế toán hợp nhất NKG năm 2022 (NKG_2022_consolidated#p008): mã số 111 'Tiền' tại 31/12/2022 = 948.303.528.970 VND = 948,303,528,970 / 10^9 = {v99} tỷ đồng.",
    }

    # 3. ViFinQA-186
    c186 = "MSR_2023_consolidated#p060"
    q186_hdr = "| 31/12/2023Nghìn VND | 1/1/2023Nghìn VND"
    q186_row = "Vay và phát hành trái phiếu dài hạn | 10.850.162.726 | 10.266.342.921"
    res["ViFinQA-186"] = {
        "value": 10850162726, "unit": "nghìn đồng", "gold_answer": "10850162726 nghìn đồng",
        "report_id": "MSR_2023_consolidated", "source_page": 60,
        "evidence": [verify_quote(chunks, c186, "(b) Vay và trái phiếu phát hành dài hạn"), verify_quote(chunks, c186, q186_hdr), verify_quote(chunks, c186, q186_row)],
        "computation": "Thuyết minh 21(b) BCTC hợp nhất MSR năm 2023 (MSR_2023_consolidated#p060) ghi nguyên văn dòng 'Vay và phát hành trái phiếu dài hạn' tại 31/12/2023 = 10.850.162.726 nghìn đồng (tức 10,850,162,726 nghìn đồng trước khi trừ khoản đến hạn trả trong 12 tháng; phần đến hạn trả sau 12 tháng trên BCĐKT mã 338 trang 11 là 8.760.544.403 nghìn đồng).",
    }

    # 4. ViFinQA-311
    c311 = "HSG_2024_separate#p056"
    q311_hdr = "30.9.2024VND | 30.9.2023VND | |"
    q311_row = "Ông Lê Phước Vũ | Chủ tịch | 360.000.000 | 360.000.000"
    res["ViFinQA-311"] = {
        "value": 360, "unit": "triệu đồng", "gold_answer": "360 triệu đồng",
        "report_id": "HSG_2024_separate", "source_page": 56,
        "evidence": [verify_quote(chunks, c311, q311_hdr), verify_quote(chunks, c311, q311_row)],
        "computation": "Thuyết minh 35(a)(viii) BCTC riêng HSG năm tài chính kết thúc ngày 30/09/2024 (HSG_2024_separate#p056): Ông Lê Phước Vũ (Chủ tịch HĐQT) = 360.000.000 VND = 360,000,000 / 10^6 = 360 triệu đồng.",
    }

    # 5. ViFinQA-316
    c316 = "NKG_2023_separate#p010"
    q316_hdr = "2023 VND | 2022 VND | | |"
    q316_row = "400 | VỐN CHỦ SỞ HỮU | | 5.250.237.400.929 | 5.053.904.428.009"
    v316 = fmt_num(5250237400929 / 1e11)
    res["ViFinQA-316"] = {
        "value": v316, "unit": "trăm tỷ đồng", "gold_answer": fmt_answer(v316, "trăm tỷ đồng"),
        "report_id": "NKG_2023_separate", "source_page": 10,
        "evidence": [verify_quote(chunks, c316, q316_hdr), verify_quote(chunks, c316, q316_row)],
        "computation": f"BCĐKT riêng NKG tại 31/12/2023 (NKG_2023_separate#p010): mã số 400 'VỐN CHỦ SỞ HỮU' = 5.250.237.400.929 VND = 5,250,237,400,929 / 10^11 = {v316} trăm tỷ đồng.",
    }

    # 6. ViFinQA-612
    c612 = "NKG_2021_separate#p034"
    q612_hdr = "| | Tại ngày 1.1.2021 VND | Tăng VND | Giảm VND | Nợ dài hạn đến hạn trả VND | Đánh giá lại cuối năm VND | Tại ngày 31.12.2021 VND"
    q612_row = "| Vay ngân hàng (*) | 2.468.663.849.028 | 21.070.601.295.868 | (20.058.907.644.016) | 291.300.000.000 | 1.497.232.237 | 3.773.154.733.117"
    v612 = fmt_num((3773154733117 - 2468663849028) / 2468663849028 * 100.0)
    res["ViFinQA-612"] = {
        "value": v612, "unit": "%", "gold_answer": fmt_answer(v612, "%"),
        "report_id": "", "source_page": 34,
        "evidence": [
            verify_quote(chunks, c612, "(a) | Ngắn hạn | Ngắn hạn | Ngắn hạn | Ngắn hạn | Ngắn hạn | Ngắn hạn | Ngắn hạn"),
            verify_quote(chunks, c612, q612_hdr),
            verify_quote(chunks, c612, q612_row),
            verify_quote(chunks, "NKG_2020_separate#p031", "Vay ngân hàng (*) | 2.337.477.478.823 | 11.098.457.061.598 | (11.135.275.246.816) | (1.195.444.577) | 169.200.000.000 | 2.468.663.849.028"),
        ],
        "computation": f"Thuyết minh 16(a) BCTC riêng NKG năm 2021 (NKG_2021_separate#p034, khớp NKG_2020_separate#p031): Vay ngắn hạn ngân hàng tại 31/12/2020 (1/1/2021) = 2.468.663.849.028 VND; tại 31/12/2021 = 3.773.154.733.117 VND. Mức tăng = (3,773,154,733,117 - 2,468,663,849,028) / 2,468,663,849,028 * 100% = {v612}%.",
    }

    # 7. ViFinQA-682
    c682 = "HSG_2021_consolidated#p009"
    q682_hdr = "30/9/2021 VND | 30/9/2020 VND | | |"
    q682_row = "Kết quả từ hoạt động khác (40 = 31 - 32) | 40 | | (1.899.321.381) | (3.285.249.804)"
    v682 = fmt_num(-1899321381 / 1e6)
    res["ViFinQA-682"] = {
        "value": v682, "unit": "triệu đồng", "gold_answer": fmt_answer(v682, "triệu đồng"),
        "report_id": "HSG_2021_consolidated", "source_page": 9,
        "evidence": [verify_quote(chunks, c682, q682_hdr), verify_quote(chunks, c682, q682_row)],
        "computation": f"BCKQKD hợp nhất HSG năm 2021 (HSG_2021_consolidated#p009): mã số 40 'Kết quả từ hoạt động khác' = (1.899.321.381) VND = -1,899,321,381 / 10^6 = {v682} triệu đồng.",
    }

    # 8. ViFinQA-709
    int22, cid_i22, h_i22, r_i22 = data[("MSR", 2022)]["IS_23"]
    debt22, cid_d22, h_d22, r_d22 = data[("MSR", 2022)]["BS_320"]
    v709 = fmt_num(int22 / debt22 * 100.0)
    res["ViFinQA-709"] = {
        "value": v709, "unit": "%", "gold_answer": fmt_answer(v709, "%"),
        "report_id": "MSR_2022_consolidated", "source_page": 12,
        "evidence": [
            verify_quote(chunks, cid_i22, h_i22), verify_quote(chunks, cid_i22, r_i22),
            verify_quote(chunks, cid_d22, h_d22), verify_quote(chunks, cid_d22, r_d22),
        ],
        "computation": (
            f"Theo BCTC hợp nhất MSR năm 2022: BCKQKD mã 23 'Trong đó: Chi phí lãi vay' (MSR_2022_consolidated#p012) = 1.194.553.796 nghìn đồng; "
            f"BCĐKT mã 320 'Vay và trái phiếu phát hành ngắn hạn' (MSR_2022_consolidated#p011) = 13.105.475.407 nghìn đồng. "
            f"Tỷ lệ = 1,194,553,796 / 13,105,475,407 * 100% = {v709}%. "
            f"(Ghi chú đối chiếu: cột so sánh năm 2022 trên BCKQKD 2023 phân loại lại mã 23 còn 1.119.988.084 nghìn đồng không gồm 74.565.712 chi phí đi vay khác; Thuyết minh 19(a) p.56 tách riêng Vay ngắn hạn = 5.818.241.451 và Trái phiếu dài hạn đến hạn trả = 7.287.233.956)."
        ),
    }

    # 9. ViFinQA-973
    res["ViFinQA-973"] = {
        "value": 1, "unit": "", "gold_answer": "1",
        "report_id": "", "source_page": 10,
        "evidence": [
            verify_quote(chunks, "HSG_2022_separate#p010", "30/9/2022 VND | 30/9/2021 VND | | |"),
            verify_quote(chunks, "HSG_2022_separate#p010", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | 1.071.767.875.098 | 369.579.964.422"),
            verify_quote(chunks, "HPG_2022_separate#p011", "| Mã số | Thuyết minh | 2022 VND | 2021 VND"),
            verify_quote(chunks, "HPG_2022_separate#p011", "Lưu chuyển tiền thuần từ hoạt động kinh doanh | 20 | | (761.380.984.482) | (611.601.249.012)"),
            verify_quote(chunks, "MSR_2022_separate#p012", "| Mã số | Thuyết minh | 2022Nghìn VND | 2021Nghìn VND"),
            verify_quote(chunks, "MSR_2022_separate#p012", "Lưu chuyển tiền thuần từ hoạt độngkinh doanh | 20 | | (259.020.090) | (300.715.703)"),
        ],
        "computation": "Lưu chuyển tiền thuần từ hoạt động kinh doanh (mã 20, BCTC riêng 2022): HSG = +1.071.767.875.098 VND (>0, HSG_2022_separate#p010); HPG = -761.380.984.482 VND (<0, HPG_2022_separate#p011); MSR = -259.020.090 nghìn VND (<0, MSR_2022_separate#p012). Số công ty dương = 1.",
    }

    # --- Group B/D: 26 multi-metric/multi-company/multi-year items ---
    comps4 = ["HPG", "HSG", "MSR", "NKG"]
    comps3 = ["HPG", "HSG", "NKG"]

    # 368 & 453: 2022 QR < median -> avg NM (%)
    qrs22 = {c: qr(c, 2022) for c in comps4}
    med_qr22 = statistics.median(qrs22.values())
    low_qr22 = [c for c in comps4 if qrs22[c] < med_qr22]
    assert low_qr22 == ["HSG", "MSR"]
    nms22 = {c: nm(c, 2022) for c in low_qr22}
    v_368 = fmt_num(sum(nms22.values()) / len(low_qr22))
    ev_368 = build_group_evidence(chunks, data, [
        ("HSG", 2022, ["BS_100", "BS_140", "BS_310", "IS_10", "IS_60"]),
        ("MSR", 2022, ["BS_100", "BS_140", "BS_310", "IS_10", "IS_60"]),
        ("HPG", 2022, ["BS_100", "BS_140", "BS_310"]),
        ("NKG", 2022, ["BS_100", "BS_140", "BS_310"]),
    ])
    comp_368 = (
        f"Hệ số thanh toán nhanh 2022 = (TSNH 100 - HTK 140) / Nợ ngắn hạn 310: "
        + ", ".join(f"{c}={qrs22[c]:.4f}" for c in comps4)
        + f"; trung vị = {med_qr22:.4f}. Nhóm thấp hơn trung vị: {', '.join(low_qr22)}. "
        + f"Biên LN ròng 2022 = LNST 60 / DTT 10: HSG={nms22['HSG']:.4f}%, MSR={nms22['MSR']:.4f}%. Bình quân = ({nms22['HSG']:.4f} + {nms22['MSR']:.4f}) / 2 = {v_368}%."
    )
    for qid in ("ViFinQA-368", "ViFinQA-453"):
        res[qid] = {"value": v_368, "unit": "%", "gold_answer": fmt_answer(v_368, "%"), "report_id": "", "source_page": ev_368[0]["source_page"], "evidence": ev_368, "computation": comp_368}

    # 369 & 454: below median QR 2022 -> highest GM change 22->23 -> ICR 2023 (lần)
    gm_chg_22_23 = {c: gm(c, 2023) - gm(c, 2022) for c in low_qr22}
    w_369 = max(low_qr22, key=lambda c: gm_chg_22_23[c])
    assert w_369 == "HSG"
    icr_hsg23 = (vnd_s("HSG", 2023, "IS_50") + vnd_s("HSG", 2023, "IS_23")) / vnd_s("HSG", 2023, "IS_23")
    v_369 = fmt_num(icr_hsg23)
    ev_369 = build_group_evidence(chunks, data, [
        ("HSG", 2023, ["IS_10", "IS_20", "IS_23", "IS_50"]),
        ("HSG", 2022, ["BS_100", "BS_140", "BS_310", "IS_10", "IS_20"]),
        ("MSR", 2022, ["BS_100", "BS_140", "BS_310", "IS_10", "IS_20"]),
        ("MSR", 2023, ["IS_10", "IS_20"]),
        ("HPG", 2022, ["BS_100", "BS_140", "BS_310"]),
        ("NKG", 2022, ["BS_100", "BS_140", "BS_310"]),
    ])
    comp_369 = (
        f"Nhóm QR 2022 < trung vị ({med_qr22:.4f}): HSG ({qrs22['HSG']:.4f}), MSR ({qrs22['MSR']:.4f}). "
        f"Thay đổi biên LN gộp 2022->2023: HSG = {gm('HSG',2023):.4f}% - {gm('HSG',2022):.4f}% = {gm_chg_22_23['HSG']:.4f} điểm %; "
        f"MSR = {gm('MSR',2023):.4f}% - {gm('MSR',2022):.4f}% = {gm_chg_22_23['MSR']:.4f} điểm %. Cao nhất: HSG. "
        f"ICR 2023 của HSG = (LNTT 146,022,559,563 + Chi phí lãi vay 195,489,503,107) / 195,489,503,107 = {v_369} lần."
    )
    for qid in ("ViFinQA-369", "ViFinQA-454"):
        res[qid] = {"value": v_369, "unit": "lần", "gold_answer": fmt_answer(v_369, "lần"), "report_id": "", "source_page": ev_369[0]["source_page"], "evidence": ev_369, "computation": comp_369}

    # 373 & 455 (GM 2024 of largest DIO drop 22->24 among DIO_2022 > median), and 374 & 451 (avg GM chg 22->24 in pp)
    dio22 = {c: dio(c, 2022) for c in comps4}
    med_dio22 = statistics.median(dio22.values())
    high_dio22 = [c for c in comps4 if dio22[c] > med_dio22]
    assert high_dio22 == ["MSR", "NKG"]
    dio24 = {c: dio(c, 2024) for c in high_dio22}
    dio_drop = {c: dio22[c] - dio24[c] for c in high_dio22}
    w_373 = max(high_dio22, key=lambda c: dio_drop[c])
    assert w_373 == "MSR"
    v_373 = fmt_num(gm("MSR", 2024))
    gm_chg_22_24 = {c: gm(c, 2024) - gm(c, 2022) for c in high_dio22}
    v_374 = fmt_num(sum(gm_chg_22_24.values()) / len(high_dio22))

    ev_373 = build_group_evidence(chunks, data, [
        ("MSR", 2024, ["BS_140", "IS_10", "IS_11", "IS_20"]),
        ("MSR", 2023, ["BS_140"]),
        ("MSR", 2022, ["BS_140", "IS_11", "IS_10", "IS_20"]),
        ("MSR", 2021, ["BS_140"]),
        ("NKG", 2024, ["BS_140", "IS_11", "IS_10", "IS_20"]),
        ("NKG", 2023, ["BS_140"]),
        ("NKG", 2022, ["BS_140", "IS_11", "IS_10", "IS_20"]),
        ("NKG", 2021, ["BS_140"]),
        ("HPG", 2022, ["BS_140", "IS_11"]),
        ("HPG", 2021, ["BS_140"]),
        ("HSG", 2022, ["BS_140", "IS_11"]),
        ("HSG", 2021, ["BS_140"]),
    ])
    comp_373 = (
        f"Số ngày tồn kho 2022 = 365 * avg(HTK 2021, HTK 2022) / GVHB 2022: "
        + ", ".join(f"{c}={dio22[c]:.4f}" for c in comps4)
        + f"; trung vị = {med_dio22:.4f}. Nhóm > trung vị: MSR, NKG. "
        + f"Số ngày tồn kho 2024: MSR={dio24['MSR']:.4f} (giảm {dio_drop['MSR']:.4f} ngày), NKG={dio24['NKG']:.4f} (giảm {dio_drop['NKG']:.4f} ngày). "
        + f"Giảm lớn nhất: MSR. Biên LN gộp 2024 của MSR = 892,706,621 / 14,336,328,727 * 100% = {v_373}%."
    )
    for qid in ("ViFinQA-373", "ViFinQA-455"):
        res[qid] = {"value": v_373, "unit": "%", "gold_answer": fmt_answer(v_373, "%"), "report_id": "", "source_page": ev_373[0]["source_page"], "evidence": ev_373, "computation": comp_373}

    comp_374 = (
        f"Nhóm có DIO 2022 > trung vị ({med_dio22:.4f}): MSR ({dio22['MSR']:.4f}), NKG ({dio22['NKG']:.4f}). "
        f"Thay đổi biên LN gộp 2022->2024: MSR = {gm('MSR',2024):.4f}% - {gm('MSR',2022):.4f}% = {gm_chg_22_24['MSR']:.4f} điểm %; "
        f"NKG = {gm('NKG',2024):.4f}% - {gm('NKG',2022):.4f}% = {gm_chg_22_24['NKG']:.4f} điểm %. Bình quân = {v_374} điểm phần trăm."
    )
    for qid in ("ViFinQA-374", "ViFinQA-451"):
        res[qid] = {"value": v_374, "unit": "điểm phần trăm", "gold_answer": fmt_answer(v_374, "điểm phần trăm"), "report_id": "", "source_page": ev_373[0]["source_page"], "evidence": ev_373, "computation": comp_374}

    # 393: HPG, HSG, NKG 2023->2024 rev growth > 0 -> max rev growth -> GM chg (pp)
    rg24 = {c: rev_g(c, 2024) for c in comps3}
    pos_rg24 = [c for c in comps3 if rg24[c] > 0]
    w_393 = max(pos_rg24, key=lambda c: rg24[c])
    assert w_393 == "HSG"
    v_393 = fmt_num(gm("HSG", 2024) - gm("HSG", 2023))
    ev_393 = build_group_evidence(chunks, data, [
        ("HSG", 2024, ["IS_10", "IS_20"]), ("HSG", 2023, ["IS_10", "IS_20"]),
        ("HPG", 2024, ["IS_10"]), ("HPG", 2023, ["IS_10"]),
        ("NKG", 2024, ["IS_10"]), ("NKG", 2023, ["IS_10"]),
    ])
    res["ViFinQA-393"] = {
        "value": v_393, "unit": "điểm phần trăm", "gold_answer": fmt_answer(v_393, "điểm phần trăm"),
        "report_id": "", "source_page": ev_393[0]["source_page"], "evidence": ev_393,
        "computation": f"Tăng trưởng DTT 2023->2024: HPG={rg24['HPG']:.4f}%, HSG={rg24['HSG']:.4f}%, NKG={rg24['NKG']:.4f}% (cả 3 dương, cao nhất HSG). Biên LN gộp HSG: 2023={gm('HSG',2023):.4f}%, 2024={gm('HSG',2024):.4f}%; thay đổi = {v_393} điểm phần trăm.",
    }

    # 400: HPG 2020-2024 positive rev growth -> max growth year -> CF_20 / IS_10 (%)
    hpg_rg = {y: rev_g("HPG", y) for y in range(2020, 2025)}
    w_400 = max([y for y, g in hpg_rg.items() if g > 0], key=lambda y: hpg_rg[y])
    assert w_400 == 2021
    v_400 = fmt_num(vnd_s("HPG", 2021, "CF_20") / vnd_s("HPG", 2021, "IS_10") * 100.0)
    ev_400 = build_group_evidence(chunks, data, [
        ("HPG", 2021, ["IS_10", "CF_20"]),
        ("HPG", 2020, ["IS_10"]),
        ("HPG", 2022, ["IS_10"]),
        ("HPG", 2023, ["IS_10"]),
        ("HPG", 2024, ["IS_10"]),
    ])
    res["ViFinQA-400"] = {
        "value": v_400, "unit": "%", "gold_answer": fmt_answer(v_400, "%"),
        "report_id": "", "source_page": ev_400[0]["source_page"], "evidence": ev_400,
        "computation": f"Tăng trưởng DTT hợp nhất HPG: 2020={hpg_rg[2020]:.4f}%, 2021={hpg_rg[2021]:.4f}%, 2022={hpg_rg[2022]:.4f}%, 2023={hpg_rg[2023]:.4f}%, 2024={hpg_rg[2024]:.4f}%. Cao nhất là năm 2021. Tỷ lệ LCTT từ HĐKD / DTT năm 2021 = 26,720,913,303,108 / 149,679,789,979,345 * 100% = {v_400}%.",
    }

    # 410: HPG, HSG, NKG 2024 D/E < median -> max ROE (%)
    de24 = {c: vnd_s(c, 2024, "BS_300") / vnd_s(c, 2024, "BS_400") for c in comps3}
    med_de24 = statistics.median(de24.values())
    low_de24 = [c for c in comps3 if de24[c] < med_de24]
    assert low_de24 == ["HSG"]
    roe24_hsg = vnd_s("HSG", 2024, "IS_60") / ((vnd_s("HSG", 2023, "BS_400") + vnd_s("HSG", 2024, "BS_400")) / 2.0) * 100.0
    v_410 = fmt_num(roe24_hsg)
    ev_410 = build_group_evidence(chunks, data, [
        ("HSG", 2024, ["BS_300", "BS_400", "IS_60"]),
        ("HSG", 2023, ["BS_400"]),
        ("HPG", 2024, ["BS_300", "BS_400"]),
        ("NKG", 2024, ["BS_300", "BS_400"]),
    ])
    res["ViFinQA-410"] = {
        "value": v_410, "unit": "%", "gold_answer": fmt_answer(v_410, "%"),
        "report_id": "", "source_page": ev_410[0]["source_page"], "evidence": ev_410,
        "computation": f"Hệ số Nợ phải trả / VCSH năm 2024: HPG={de24['HPG']:.4f}, HSG={de24['HSG']:.4f}, NKG={de24['NKG']:.4f}; trung vị = {med_de24:.4f}. Công ty thấp hơn trung vị: HSG. ROE 2024 của HSG = 514,673,976,370 / ((10,780,166,372,421 + 10,916,937,055,537)/2) * 100% = {v_410}%.",
    }

    # 450: HPG 2021-2024 accruals < median -> min rev growth year -> GM (%)
    acc_hpg = {y: (vnd_s("HPG", y, "IS_60") - vnd_s("HPG", y, "CF_20")) / ((vnd_s("HPG", y - 1, "BS_270") + vnd_s("HPG", y, "BS_270")) / 2.0) for y in range(2021, 2025)}
    med_acc = statistics.median(acc_hpg.values())
    low_acc = [y for y in range(2021, 2025) if acc_hpg[y] < med_acc]
    assert low_acc == [2022, 2023]
    w_450 = min(low_acc, key=lambda y: hpg_rg[y])
    assert w_450 == 2023
    v_450 = fmt_num(gm("HPG", 2023))
    ev_450 = build_group_evidence(chunks, data, [
        ("HPG", 2023, ["IS_10", "IS_20", "IS_60", "CF_20", "BS_270"]),
        ("HPG", 2022, ["IS_10", "IS_60", "CF_20", "BS_270"]),
        ("HPG", 2021, ["IS_10", "IS_60", "CF_20", "BS_270"]),
        ("HPG", 2020, ["BS_270"]),
        ("HPG", 2024, ["IS_60", "CF_20", "BS_270"]),
    ])
    res["ViFinQA-450"] = {
        "value": v_450, "unit": "%", "gold_answer": fmt_answer(v_450, "%"),
        "report_id": "", "source_page": ev_450[0]["source_page"], "evidence": ev_450,
        "computation": (
            "Chỉ số (LNST 60 - LCTT HĐKD 20) / Tổng TS bình quân của HPG: "
            + ", ".join(f"{y}={acc_hpg[y]:.4f}" for y in range(2021, 2025))
            + f"; trung vị = {med_acc:.4f}. Các năm < trung vị: 2022 (tăng trưởng DTT {hpg_rg[2022]:.4f}%) và 2023 (tăng trưởng DTT {hpg_rg[2023]:.4f}%). "
            + f"Thấp nhất là 2023. Biên LN gộp 2023 = 12,937,840,695,572 / 118,953,027,893,654 * 100% = {v_450}%."
        ),
    }

    # 473, 490, 568: positive NM in all of 2020, 2021, 2022 -> sum 2022 IS_10 (nghìn tỷ đồng)
    q_20_22 = [c for c in comps4 if all(nm(c, y) > 0 for y in (2020, 2021, 2022))]
    assert q_20_22 == ["HPG", "HSG", "MSR"]
    sum22 = sum(vnd_s(c, 2022, "IS_10") for c in q_20_22)
    v_473 = fmt_num(sum22 / 1e12)
    ev_473 = build_group_evidence(chunks, data, [
        (c, y, ["IS_10", "IS_60"]) for c in comps4 for y in (2020, 2021, 2022)
    ])
    comp_473 = (
        f"Biên LN ròng > 0 cả 3 năm 2020-2022: HPG, HSG, MSR đều > 0 cả 3 năm; NKG năm 2022 âm ({nm('NKG',2022):.4f}%). "
        f"Tổng DTT 2022 của HPG, HSG, MSR = (141,409,274,460,632 + 49,710,635,951,467 + 15,549,547,654,000) / 10^12 = {v_473} nghìn tỷ đồng."
    )
    for qid in ("ViFinQA-473", "ViFinQA-490", "ViFinQA-568"):
        res[qid] = {"value": v_473, "unit": "nghìn tỷ đồng", "gold_answer": fmt_answer(v_473, "nghìn tỷ đồng"), "report_id": "", "source_page": ev_473[0]["source_page"], "evidence": ev_473, "computation": comp_473}

    # 478, 493, 552: positive NM in all of 2021, 2022, 2023 -> sum 2023 IS_10 (nghìn tỷ đồng)
    q_21_23 = [c for c in comps4 if all(nm(c, y) > 0 for y in (2021, 2022, 2023))]
    assert q_21_23 == ["HPG", "HSG"]
    sum23 = sum(vnd_s(c, 2023, "IS_10") for c in q_21_23)
    v_478 = fmt_num(sum23 / 1e12)
    ev_478 = build_group_evidence(chunks, data, [
        (c, y, ["IS_10", "IS_60"]) for c in comps4 for y in (2021, 2022, 2023)
    ])
    comp_478 = (
        f"Biên LN ròng > 0 cả 3 năm 2021-2023: HPG và HSG đều > 0 cả 3 năm; NKG âm năm 2022 ({nm('NKG',2022):.4f}%); MSR âm năm 2023 ({nm('MSR',2023):.4f}%). "
        f"Tổng DTT 2023 của HPG và HSG = (118,953,027,893,654 + 31,650,660,956,650) / 10^12 = {v_478} nghìn tỷ đồng."
    )
    for qid in ("ViFinQA-478", "ViFinQA-493", "ViFinQA-552"):
        res[qid] = {"value": v_478, "unit": "nghìn tỷ đồng", "gold_answer": fmt_answer(v_478, "nghìn tỷ đồng"), "report_id": "", "source_page": ev_478[0]["source_page"], "evidence": ev_478, "computation": comp_478}

    # 475 & 570: largest DIO increase 21->22 -> GM change 21->22 (pp)
    dio21 = {c: dio(c, 2021) for c in comps4}
    dio_chg_21_22 = {c: dio22[c] - dio21[c] for c in comps4}
    w_475 = max(comps4, key=lambda c: dio_chg_21_22[c])
    assert w_475 == "NKG"
    v_475 = fmt_num(gm("NKG", 2022) - gm("NKG", 2021))
    ev_475 = build_group_evidence(chunks, data, [
        ("NKG", 2022, ["BS_140", "IS_10", "IS_11", "IS_20"]),
        ("NKG", 2021, ["BS_140", "IS_10", "IS_11", "IS_20"]),
        ("NKG", 2020, ["BS_140"]),
    ] + [(c, y, ["BS_140", "IS_11"] if y in (2021, 2022) else ["BS_140"]) for c in ("HPG", "HSG", "MSR") for y in (2020, 2021, 2022)])
    comp_475 = (
        f"Biến động DIO 2021->2022: HPG={dio_chg_21_22['HPG']:.4f}, HSG={dio_chg_21_22['HSG']:.4f}, MSR={dio_chg_21_22['MSR']:.4f}, NKG={dio_chg_21_22['NKG']:.4f} ngày (tăng mạnh nhất: NKG). "
        f"Thay đổi biên LN gộp NKG 2021->2022: {gm('NKG',2022):.4f}% - {gm('NKG',2021):.4f}% = {v_475} điểm phần trăm."
    )
    for qid in ("ViFinQA-475", "ViFinQA-570"):
        res[qid] = {"value": v_475, "unit": "điểm phần trăm", "gold_answer": fmt_answer(v_475, "điểm phần trăm"), "report_id": "", "source_page": ev_475[0]["source_page"], "evidence": ev_475, "computation": comp_475}

    # 479 & 575: largest DIO increase 22->23 -> GM change 22->23 (pp)
    dio23 = {c: dio(c, 2023) for c in comps4}
    dio_chg_22_23 = {c: dio23[c] - dio22[c] for c in comps4}
    w_479 = max(comps4, key=lambda c: dio_chg_22_23[c])
    assert w_479 == "HSG"
    v_479 = fmt_num(gm("HSG", 2023) - gm("HSG", 2022))
    ev_479 = build_group_evidence(chunks, data, [
        ("HSG", 2023, ["BS_140", "IS_10", "IS_11", "IS_20"]),
        ("HSG", 2022, ["BS_140", "IS_10", "IS_11", "IS_20"]),
        ("HSG", 2021, ["BS_140"]),
    ] + [(c, y, ["BS_140", "IS_11"] if y in (2022, 2023) else ["BS_140"]) for c in ("HPG", "MSR", "NKG") for y in (2021, 2022, 2023)])
    comp_479 = (
        f"Biến động DIO 2022->2023: HPG={dio_chg_22_23['HPG']:.4f}, HSG={dio_chg_22_23['HSG']:.4f}, MSR={dio_chg_22_23['MSR']:.4f}, NKG={dio_chg_22_23['NKG']:.4f} ngày (tăng mạnh nhất: HSG). "
        f"Thay đổi biên LN gộp HSG 2022->2023: {gm('HSG',2023):.4f}% - {gm('HSG',2022):.4f}% = {v_479} điểm phần trăm."
    )
    for qid in ("ViFinQA-479", "ViFinQA-575"):
        res[qid] = {"value": v_479, "unit": "điểm phần trăm", "gold_answer": fmt_answer(v_479, "điểm phần trăm"), "report_id": "", "source_page": ev_479[0]["source_page"], "evidence": ev_479, "computation": comp_479}

    # 556: largest DIO increase 23->24 -> GM change 23->24 (pp)
    dio24_all = {c: dio(c, 2024) for c in comps4}
    dio_chg_23_24 = {c: dio24_all[c] - dio23[c] for c in comps4}
    w_556 = max(comps4, key=lambda c: dio_chg_23_24[c])
    assert w_556 == "HPG"
    v_556 = fmt_num(gm("HPG", 2024) - gm("HPG", 2023))
    ev_556 = build_group_evidence(chunks, data, [
        ("HPG", 2024, ["BS_140", "IS_10", "IS_11", "IS_20"]),
        ("HPG", 2023, ["BS_140", "IS_10", "IS_11", "IS_20"]),
        ("HPG", 2022, ["BS_140"]),
    ] + [(c, y, ["BS_140", "IS_11"] if y in (2023, 2024) else ["BS_140"]) for c in ("HSG", "MSR", "NKG") for y in (2022, 2023, 2024)])
    res["ViFinQA-556"] = {
        "value": v_556, "unit": "điểm phần trăm", "gold_answer": fmt_answer(v_556, "điểm phần trăm"),
        "report_id": "", "source_page": ev_556[0]["source_page"], "evidence": ev_556,
        "computation": f"Biến động DIO 2023->2024: HPG={dio_chg_23_24['HPG']:.4f}, HSG={dio_chg_23_24['HSG']:.4f}, MSR={dio_chg_23_24['MSR']:.4f}, NKG={dio_chg_23_24['NKG']:.4f} ngày (chỉ HPG tăng). Thay đổi biên LN gộp HPG 2023->2024: {gm('HPG',2024):.4f}% - {gm('HPG',2023):.4f}% = {v_556} điểm phần trăm.",
    }

    # 549 & 573: highest YoY rev growth 2021-2023 -> asset turnover IS_10 / BS_270 (lần)
    all_rg = {(c, y): rev_g(c, y) for c in comps4 for y in (2021, 2022, 2023)}
    w_comp, w_yr = max(all_rg, key=lambda k: all_rg[k])
    assert (w_comp, w_yr) == ("NKG", 2021)
    v_549 = fmt_num(vnd_s("NKG", 2021, "IS_10") / vnd_s("NKG", 2021, "BS_270"))
    ev_549 = build_group_evidence(chunks, data, [
        ("NKG", 2021, ["IS_10", "BS_270"]),
        ("NKG", 2020, ["IS_10"]),
        ("NKG", 2022, ["IS_10"]),
        ("NKG", 2023, ["IS_10"]),
    ] + [(c, y, ["IS_10"]) for c in ("HPG", "HSG", "MSR") for y in (2020, 2021, 2022, 2023)])
    comp_549 = (
        f"Tăng trưởng DTT cao nhất nhóm HPG/HSG/MSR/NKG giai đoạn 2021-2023 là NKG năm 2021 (+{all_rg[('NKG',2021)]:.4f}%, từ 11,559.67 lên 28,173.40 tỷ). "
        f"Vòng quay tổng tài sản cuối năm 2021 của NKG = 28,173,402,236,226 / 15,397,915,366,296 = {v_549} lần."
    )
    for qid in ("ViFinQA-549", "ViFinQA-573"):
        res[qid] = {"value": v_549, "unit": "lần", "gold_answer": fmt_answer(v_549, "lần"), "report_id": "", "source_page": ev_549[0]["source_page"], "evidence": ev_549, "computation": comp_549}

    # 569: 2022 positive net margin -> avg (GM - NM) in percentage points
    pos_nm22 = [c for c in comps4 if nm(c, 2022) > 0]
    assert pos_nm22 == ["HPG", "HSG", "MSR"]
    spreads = {c: gm(c, 2022) - nm(c, 2022) for c in pos_nm22}
    v_569 = fmt_num(sum(spreads.values()) / len(pos_nm22))
    ev_569 = build_group_evidence(chunks, data, [
        (c, 2022, ["IS_10", "IS_20", "IS_60"]) for c in comps4
    ])
    res["ViFinQA-569"] = {
        "value": v_569, "unit": "điểm phần trăm", "gold_answer": fmt_answer(v_569, "điểm phần trăm"),
        "report_id": "", "source_page": ev_569[0]["source_page"], "evidence": ev_569,
        "computation": f"Năm 2022, các công ty có biên LN ròng > 0 là HPG, HSG, MSR (NKG âm {nm('NKG',2022):.4f}%). Chênh lệch (Biên LN gộp - Biên LN ròng): HPG={spreads['HPG']:.4f}, HSG={spreads['HSG']:.4f}, MSR={spreads['MSR']:.4f} điểm %. Bình quân = {v_569} điểm phần trăm.",
    }

    assert len(res) == 35, f"Expected 35 ViFinQA items, got {len(res)}"
    return res


def make_dev_refusals(chunks: dict[str, dict]) -> list[dict]:
    specs = [
        (
            "DEV-REF-01",
            "Giá đóng cửa cổ phiếu HSG ngày 30/09/2024 là bao nhiêu đồng?",
            "HSG",
            "2024",
            ["giá đóng cửa", "thị giá"],
            "Corpus chỉ gồm báo cáo tài chính, không có dữ liệu giá cổ phiếu trên thị trường. Đã kiểm tra toàn văn 2407 chunk: cụm 'giá đóng cửa' và 'thị giá' có 0 lần xuất hiện.",
        ),
        (
            "DEV-REF-02",
            "Kế hoạch doanh thu năm 2025 của CTCP Thép Nam Kim là bao nhiêu nghìn tỷ đồng?",
            "NKG",
            "2025",
            ["kế hoạch doanh thu"],
            "Corpus chỉ gồm báo cáo tài chính kiểm toán giai đoạn 2020-2024, không có kế hoạch kinh doanh năm 2025. Đã kiểm tra toàn văn 2407 chunk: cụm 'kế hoạch doanh thu' có 0 lần xuất hiện.",
        ),
        (
            "DEV-REF-03",
            "Lợi nhuận sau thuế quý 2 năm 2024 của CTCP Masan High-Tech Materials là bao nhiêu tỷ đồng?",
            "MSR",
            "2024",
            ["quý 2", "quý ii"],
            "Corpus chỉ gồm báo cáo tài chính năm, không có báo cáo tài chính quý. Đã kiểm tra toàn văn 2407 chunk: cụm 'quý 2' và 'quý ii' đều có 0 lần xuất hiện.",
        ),
        (
            "DEV-REF-04",
            "Giá bán bình quân thép cuộn cán nóng năm 2024 của CTCP Tập đoàn Hòa Phát là bao nhiêu USD một tấn?",
            "HPG",
            "2024",
            ["usd một tấn", "usd/tấn"],
            "Báo cáo tài chính năm không công bố giá bán bình quân sản phẩm theo USD một tấn. Đã kiểm tra toàn văn 2407 chunk: cụm 'usd một tấn' và 'usd/tấn' đều có 0 lần xuất hiện.",
        ),
    ]
    out: list[dict] = []
    all_texts = [c["text"].lower() for c in chunks.values()]
    for qid, question, comp, yr, terms, reason in specs:
        for term in terms:
            hits = sum(1 for t in all_texts if term in t)
            assert hits == 0, f"{qid}: unexpected {hits} hits for term {term!r}"
        out.append(
            {
                "question_id": qid,
                "question": question,
                "gold_answer": REFUSAL_TEXT,
                "answer_type": "unanswerable",
                "value": "",
                "unit": "",
                "company_id": comp,
                "fiscal_year": yr,
                "report_id": "",
                "evidence": [],
                "computation": "",
                "source_page": "",
                "needs_more_evidence": True,
                "reviewer_id": "annotator-1",
                "review_status": "draft-needs-second-reviewer",
                "unanswerable_reason": reason,
                "source": "dev-refusal",
                "split": "dev",
            }
        )
    return out


def compute_split_sha(meta_without_sha: dict) -> str:
    payload = json.dumps(meta_without_sha, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    chunks = load_chunks()
    assert len(chunks) == 2407, f"Expected 2407 chunks, got {len(chunks)}"

    data = load_consolidated_statements(chunks)
    resolved_vi = resolve_vifinqa(chunks, data)
    dev_refusals = make_dev_refusals(chunks)

    # Read existing gold, preserve exact order of the original 200 items (stripping DEV-REF-* if re-run)
    orig_rows = [
        json.loads(line)
        for line in open(QA_PATH, encoding="utf-8")
        if line.strip() and not json.loads(line)["question_id"].startswith("DEV-REF-")
    ]
    assert len(orig_rows) == 200, f"Expected 200 base QA rows, found {len(orig_rows)}"

    # Load frozen v3 test_ids to strictly assert zero modification to test set
    v3_test_ids = json.loads((SPLITS_DIR / "test.json").read_text(encoding="utf-8"))
    v3_dev_ids = json.loads((SPLITS_DIR / "dev.json").read_text(encoding="utf-8"))
    assert len(v3_test_ids) == 160, f"Expected 160 test IDs, got {len(v3_test_ids)}"

    updated_rows: list[dict] = []
    for row in orig_rows:
        qid = row["question_id"]
        if row["source"] == "vifinqa":
            upd = resolved_vi[qid]
            row = {
                **row,
                "gold_answer": upd["gold_answer"],
                "value": upd["value"],
                "unit": upd["unit"],
                "report_id": upd["report_id"],
                "evidence": upd["evidence"],
                "computation": upd["computation"],
                "source_page": upd["source_page"],
                "needs_more_evidence": False,
                "reviewer_id": "annotator-1",
                "review_status": "draft-needs-second-reviewer",
            }
        updated_rows.append(row)

    all_rows = updated_rows + dev_refusals
    assert len(all_rows) == 204

    # Assert every test row split is untouched & matches v3_test_ids exactly
    new_dev_ids = sorted(r["question_id"] for r in all_rows if r["split"] == "dev")
    new_test_ids = sorted(r["question_id"] for r in all_rows if r["split"] == "test")
    assert new_test_ids == sorted(v3_test_ids), "TEST SPLIT CHANGED! Aborting."
    assert len(new_dev_ids) == 44 and len(new_test_ids) == 160

    # Assert every non-refusal quote across all 204 rows is backed in chunks.jsonl (strict verbatim for vifinqa/supplement; cell-line match for legacy table-clean)
    for r in all_rows:
        if not r["needs_more_evidence"]:
            assert len(r["evidence"]) >= 1, f"{r['question_id']} missing evidence"
            for ev in r["evidence"]:
                txt = chunks[ev["chunk_id"]]["text"]
                if r["source"] in ("vifinqa", "supplement"):
                    assert ev["quote"] in txt, f"{r['question_id']} bad verbatim quote in {ev['chunk_id']}"
                else:
                    parts = [p.strip() for p in ev["quote"].split("|")]
                    assert any(parts[0] in line and parts[-1] in line for line in txt.splitlines()), (
                        f"{r['question_id']} missing metric/value line in {ev['chunk_id']}"
                    )

    # Write qa_gold.jsonl
    with open(QA_PATH, "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Sync gold_labels.csv
    with open(LABELS_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LABEL_FIELDS)
        w.writeheader()
        for r in all_rows:
            w.writerow({k: r.get(k, "") for k in LABEL_FIELDS})

    # Sync review_log.csv preserving any previously reviewed-agree status on unchanged items
    existing_review = {}
    if REVIEW_CSV.exists():
        with open(REVIEW_CSV, encoding="utf-8") as f:
            for rec in csv.DictReader(f):
                existing_review[rec["item_id"]] = rec

    review_rows: list[dict] = []
    for r in all_rows:
        qid = r["question_id"]
        prev = existing_review.get(qid, {})
        if r["source"] in ("vifinqa", "dev-refusal"):
            review_rows.append(
                {
                    "item_id": qid,
                    "gold": r["gold_answer"],
                    "reviewer": "annotator-1",
                    "status": "draft-needs-second-reviewer",
                    "guideline_version": "v0.2",
                    "disagreement_note": (
                        "resolved ViFinQA from corpus, awaiting cross-review"
                        if r["source"] == "vifinqa"
                        else "dev out-of-corpus refusal v4, awaiting cross-review"
                    ),
                }
            )
        else:
            review_rows.append(
                {
                    "item_id": qid,
                    "gold": r["gold_answer"],
                    "reviewer": prev.get("reviewer") or r.get("reviewer_id", ""),
                    "status": prev.get("status") or r.get("review_status", ""),
                    "guideline_version": prev.get("guideline_version") or "v0.2",
                    "disagreement_note": prev.get("disagreement_note", ""),
                }
            )
    with open(REVIEW_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_FIELDS)
        w.writeheader()
        w.writerows(review_rows)

    # Update splits & split_freeze.json cleanly as v4
    with open(SPLITS_DIR / "dev.json", "w", encoding="utf-8") as f:
        json.dump(new_dev_ids, f, ensure_ascii=False, indent=2)
    # Keep test.json exact (sorted list matches v3)
    with open(SPLITS_DIR / "test.json", "w", encoding="utf-8") as f:
        json.dump(new_test_ids, f, ensure_ascii=False, indent=2)

    meta_no_sha = {
        "version": "v4",
        "seed": 42,
        "n_dev": len(new_dev_ids),
        "n_test": len(new_test_ids),
        "dev_ids": new_dev_ids,
        "test_ids": new_test_ids,
        "rule": (
            "160 cau test giu nguyen hoan toan nhu v3 (16 thieu bang chung); "
            "dev mo rong tu 40 len 44 bang 4 cau refusal ngoai corpus (DEV-REF-01..04) de refusal_den_dev=4; "
            "toan bo 35 cau ViFinQA duoc giai va gan evidence nguyen van tu 40 bao cao"
        ),
    }
    meta = {**meta_no_sha, "sha256": compute_split_sha(meta_no_sha)}
    for path in (SPLITS_DIR / "split_meta.json", FREEZE_PATH):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    print(
        f"Resolved 35 ViFinQA + added 4 dev refusals -> total={len(all_rows)} "
        f"(dev={len(new_dev_ids)} [refusal={sum(1 for r in all_rows if r['split']=='dev' and r['needs_more_evidence'])}], "
        f"test={len(new_test_ids)} [refusal={sum(1 for r in all_rows if r['split']=='test' and r['needs_more_evidence'])}]), "
        f"v4 sha256={meta['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
