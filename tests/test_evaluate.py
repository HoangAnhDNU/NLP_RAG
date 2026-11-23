"""Unit tests for src/evaluate/evaluate.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluate.evaluate import (  # noqa: E402
    CHUNK_SEP,
    evaluate_split,
    norm_num_token,
    numbers_in_context,
    numeric_match_pred,
    parse_pipe_set,
    recall_mrr_at,
)
from src.retrieval.answer_policy import REFUSAL_TEXT  # noqa: E402


HSG_REAL_TABLE_CTX = """
CÔNG TY CỔ PHẦN TẬP ĐOÀN HOA SEN
Mẫu số B 02 - DN/HN
Ngày 25 tháng 12 năm 2024
Các thuyết minh từ trang 9 đến trang 56 là một phần cấu thành báo cáo tài chính hợp nhất này.
7
[Bang 1]
Mã số | | Thuyết minh | Năm tài chính kết thúc ngày | Năm tài chính kết thúc ngày
30.9.2024 VND | 30.9.2023 VND | | |
01 | Doanh thu bán hàng và cung cấp dịch vụ | | 39.882.804.917.399 | 32.084.297.693.056
02 | Các khoản giảm trừ doanh thu | | (610.911.178.951) | (433.636.736.406)
10 | Doanh thu thuần về bán hàng và cung cấp dịch vụ | 26 | 39.271.893.738.448 | 31.650.660.956.650
11 | Giá vốn hàng bán và cung cấp dịch vụ | 27 | (35.008.227.341.981) | (28.590.018.867.006)
20 | Lợi nhuận gộp về bán hàng và cung cấp dịch vụ | | 4.263.666.396.467 | 3.060.642.089.644
21 | Doanh thu hoạt động tài chính | 28 | 341.714.489.440 | 233.474.915.968
50 | Tổng lợi nhuận kế toán trước thuế | | 551.203.257.346 | 146.022.559.563
60 | Lợi nhuận sau thuế TNDN | | 514.673.976.370 | 30.062.343.902
70 | Lãi cơ bản trên cổ phiếu | 24(a) | 802 | 47
"""


class TestNumbersInContext(unittest.TestCase):
    def test_empty_and_no_number_answers(self) -> None:
        self.assertTrue(numbers_in_context("Không có số liệu", ""))
        self.assertFalse(numbers_in_context("100 tỷ đồng", ""))
        self.assertFalse(numbers_in_context("5 %", "Doanh thu 100 đồng"))

    def test_direct_and_unit_scaling(self) -> None:
        # 1e12 nghìn tỷ đồng
        self.assertTrue(numbers_in_context("39.2719 nghìn tỷ đồng", HSG_REAL_TABLE_CTX))
        # 1e9 tỷ đồng
        self.assertTrue(numbers_in_context("514.674 tỷ đồng", HSG_REAL_TABLE_CTX))
        # Negative parenthesized context -> negative answer scaled by 1e9
        self.assertTrue(numbers_in_context("-610.9112 tỷ đồng", HSG_REAL_TABLE_CTX))
        # 1e6 (nghìn đồng table -> tỷ đồng answer, MSR pattern)
        self.assertTrue(numbers_in_context("39.196 tỷ đồng", "Cổ đông của Công ty | 39.195.963 | Nghìn VND"))
        # 1e3 and 1e11 scaling (and reverse scaling)
        self.assertTrue(numbers_in_context("1434 đồng", "Lãi cơ bản trên cổ phiếu | 1.434"))
        self.assertTrue(numbers_in_context("4.2637 trăm tỷ đồng", "Lợi nhuận gộp | 426.370.000.000 VND"))
        self.assertTrue(numbers_in_context("100 triệu đồng", "Tài sản | 0.1 tỷ đồng"))
        # Comma percentage
        self.assertTrue(numbers_in_context("99.988 %", "Tỷ lệ sở hữu | 99,988%"))

    def test_derived_arithmetic_operations(self) -> None:
        # a / b * 100 (gross margin %)
        self.assertTrue(numbers_in_context("10.8568 %", HSG_REAL_TABLE_CTX))
        # a - b scaled to nghìn tỷ đồng (2024 - 2023 net revenue diff)
        self.assertTrue(numbers_in_context("7.6212 nghìn tỷ đồng", HSG_REAL_TABLE_CTX))
        # Negative diff (2023 - 2024)
        self.assertTrue(numbers_in_context("-7.6212 nghìn tỷ đồng", HSG_REAL_TABLE_CTX))
        # a + b and a / b on simple numeric context
        ctx = "Doanh thu 100 tỷ đồng, chi phí 40 tỷ đồng."
        self.assertTrue(numbers_in_context("60 tỷ đồng", ctx))
        self.assertTrue(numbers_in_context("140 tỷ đồng", ctx))
        self.assertTrue(numbers_in_context("40 %", ctx))
        self.assertTrue(numbers_in_context("2.5", ctx))
        # Duplicate table value -> zero diff allowed only when value appears twice
        self.assertTrue(numbers_in_context("0.0 đồng", "2022: 900.000.000 | 2021: 900.000.000"))
        self.assertFalse(numbers_in_context("0.0 đồng", "2022: 900.000.000"))

    def test_hallucinations_rejected(self) -> None:
        for hallucinated in [
            "999.9 tỷ đồng",
            "123.45 tỷ đồng",
            "50 %",            # must NOT match line code Mã số 50
            "25.5 %",          # must NOT falsely match currency diff / 1e11
            "5 tỷ đồng",       # must NOT match 5 trăm tỷ (1e11) as 5 tỷ
            "937 tỷ đồng",     # must NOT match substring of 39.271.893.738.448
            "2024 tỷ đồng",    # must NOT treat year 2024 as currency amount
            "10 tỷ đồng",      # must NOT match line code Mã số 10
            "2000 đồng",
        ]:
            with self.subTest(answer=hallucinated):
                self.assertFalse(numbers_in_context(hallucinated, HSG_REAL_TABLE_CTX))

        # Sign mismatch rejected
        self.assertFalse(numbers_in_context("610.9112 tỷ đồng", "Giảm trừ | (610.911.178.951)"))
        # Mixed valid + hallucinated rejected
        self.assertFalse(
            numbers_in_context(
                "Năm 2024: 39.2719 nghìn tỷ đồng; Năm 2023: 99.1234 nghìn tỷ đồng",
                HSG_REAL_TABLE_CTX,
            )
        )

    def test_wrong_unit_year_header_and_cross_chunk_hallucinations_rejected(self) -> None:
        # 100x / 1,000x wrong unit factors on real VND tables must be rejected
        self.assertFalse(numbers_in_context("39.2719 tỷ đồng", HSG_REAL_TABLE_CTX))
        self.assertFalse(numbers_in_context("39271.8937 triệu đồng", HSG_REAL_TABLE_CTX))
        nkg_ctx = (
            "Mã số | TÀI SẢN | Thuyết minh | Tại ngày 31 tháng 12 năm | Tại ngày 31 tháng 12 năm\n"
            "2022 VND | 2021 VND | | |\n"
            "110 | Tiền và các khoản tương đương tiền 3 | | 948.303.528.970 | 751.445.944.000\n"
        )
        self.assertFalse(numbers_in_context("9.4830 tỷ đồng", nkg_ctx))
        # Table year column headers followed by VND/Nghin VND must not become monetary values
        self.assertFalse(numbers_in_context("2022 tỷ đồng", nkg_ctx))
        self.assertFalse(numbers_in_context("2021 tỷ đồng", nkg_ctx))
        self.assertFalse(numbers_in_context("2023 nghìn tỷ đồng", "2023 Nghìn VND | 10.850.162.726"))

        # Cross-chunk combinatorial collisions across 5-chunk boundaries must be rejected
        chunk1 = "2024 VND | Doanh thu thuần | 500.000.000.000 | 420.000.000.000"
        chunk2 = "2023 VND | Lợi nhuận gộp | 350.000.000.000 | 300.000.000.000"
        chunk3 = "2022 VND | Tổng tài sản | 800.000.000.000 | 710.000.000.000"
        chunk4 = "2021 VND | Nợ phải trả | 260.000.000.000 | 210.000.000.000"
        chunk5 = "2020 VND | Vốn chủ sở hữu | 640.000.000.000 | 590.000.000.000"
        multi_ctx = CHUNK_SEP.join([chunk1, chunk2, chunk3, chunk4, chunk5])
        # Direct within single chunk succeeds
        self.assertTrue(numbers_in_context("500 tỷ đồng", multi_ctx))
        # Cross-chunk diff (500 - 350 = 150) and cross-chunk ratio (350 / 500 = 70%) rejected
        self.assertFalse(numbers_in_context("150 tỷ đồng", multi_ctx))
        self.assertFalse(numbers_in_context("70 %", multi_ctx))
        self.assertFalse(numbers_in_context("43.75 %", multi_ctx))  # 350 / 800 * 100 cross-chunk
        self.assertFalse(numbers_in_context("333.3333 tỷ đồng", multi_ctx))
        self.assertFalse(numbers_in_context("44.4444 %", multi_ctx))


class TestEvaluateMetrics(unittest.TestCase):
    def test_norm_num_token_and_numeric_match(self) -> None:
        self.assertEqual(norm_num_token("39.271.893.738.448"), "39271893738448")
        self.assertEqual(norm_num_token("39.196"), "39.196")
        self.assertEqual(norm_num_token("(3.2852)"), "-3.2852")
        self.assertEqual(norm_num_token("10,8568%"), "10.8568%")
        self.assertTrue(numeric_match_pred("39.196 tỷ đồng", 39.196, "39.196 tỷ đồng"))
        self.assertTrue(numeric_match_pred("-3.2852 tỷ đồng", -3.2852, "-3.2852 tỷ đồng"))
        self.assertFalse(numeric_match_pred(REFUSAL_TEXT, 39.196, "39.196 tỷ đồng"))

    def test_parse_pipe_set_and_year_accuracy(self) -> None:
        self.assertEqual(parse_pipe_set("2020|2021"), {"2020", "2021"})
        self.assertEqual(parse_pipe_set(2024), {"2024"})
        self.assertEqual(parse_pipe_set("hpg | HSG", upper=True), {"HPG", "HSG"})

        gold = {
            "Q_SINGLE": {
                "question_id": "Q_SINGLE",
                "question": "Doanh thu HPG năm 2024?",
                "company_id": "HPG",
                "fiscal_year": 2024,
                "report_id": "HPG_2024_consolidated",
                "gold_answer": "100 tỷ đồng",
                "value": 100.0,
                "source_page": 10,
                "evidence": [{"chunk_id": "HPG_2024_consolidated#p010"}],
                "needs_more_evidence": False,
            },
            "Q_MULTI_OK": {
                "question_id": "Q_MULTI_OK",
                "question": "Chênh lệch HPG năm 2020 và 2021?",
                "company_id": "HPG",
                "fiscal_year": "2020|2021",
                "report_id": "",
                "gold_answer": "20 tỷ đồng",
                "value": 20.0,
                "source_page": 11,
                "evidence": [{"chunk_id": "HPG_2021_consolidated#p011"}],
                "needs_more_evidence": False,
            },
            "Q_MULTI_MISS": {
                "question_id": "Q_MULTI_MISS",
                "question": "Chênh lệch HSG năm 2022 và 2023?",
                "company_id": "HSG",
                "fiscal_year": "2022|2023",
                "report_id": "",
                "gold_answer": "10 tỷ đồng",
                "value": 10.0,
                "source_page": 9,
                "evidence": [{"chunk_id": "HSG_2023_consolidated#p009"}],
                "needs_more_evidence": False,
            },
        }
        chunks_full = {
            "HPG_2024_consolidated#p010": {
                "chunk_id": "HPG_2024_consolidated#p010",
                "company_id": "HPG",
                "fiscal_year": 2024,
                "page": 10,
                "text": "Doanh thu 100.000.000.000 VND",
            },
            "HPG_2021_consolidated#p011": {
                "chunk_id": "HPG_2021_consolidated#p011",
                "company_id": "HPG",
                "fiscal_year": 2021,
                "page": 11,
                "text": "2021: 50.000.000.000 | 2020: 30.000.000.000",
            },
            "HPG_2020_consolidated#p011": {
                "chunk_id": "HPG_2020_consolidated#p011",
                "company_id": "HPG",
                "fiscal_year": 2020,
                "page": 11,
                "text": "2020: 30.000.000.000",
            },
            "HSG_2023_consolidated#p009": {
                "chunk_id": "HSG_2023_consolidated#p009",
                "company_id": "HSG",
                "fiscal_year": 2023,
                "page": 9,
                "text": "2023: 10.000.000.000",
            },
        }
        chunks = {cid: c["text"] for cid, c in chunks_full.items()}
        items = [
            {
                "question_id": "Q_SINGLE",
                "predicted_chunk_ids": "HPG_2024_consolidated#p010",
                "predicted_top1_chunk_id": "HPG_2024_consolidated#p010",
                "predicted_company": "HPG",
                "predicted_year": "2024",
                "predicted_report_version": "consolidated",
                "predicted_page": "10",
                "predicted_answer": "100 tỷ đồng",
            },
            {
                "question_id": "Q_MULTI_OK",
                "predicted_chunk_ids": "HPG_2021_consolidated#p011;HPG_2020_consolidated#p011",
                "predicted_top1_chunk_id": "HPG_2021_consolidated#p011",
                "predicted_company": "HPG",
                # Reversed order should still match normalized set {"2020", "2021"}
                "predicted_year": "2021|2020",
                "predicted_report_version": "consolidated",
                "predicted_page": "11",
                "predicted_answer": "20 tỷ đồng",
            },
            {
                "question_id": "Q_MULTI_MISS",
                "predicted_chunk_ids": "HSG_2023_consolidated#p009",
                "predicted_top1_chunk_id": "HSG_2023_consolidated#p009",
                "predicted_company": "HSG",
                # Missing 2022
                "predicted_year": "2023",
                "predicted_report_version": "consolidated",
                "predicted_page": "9",
                "predicted_answer": "10 tỷ đồng",
            },
        ]
        summary, details = evaluate_split(items, gold, chunks, chunks_full, "TEST", "dev")
        # 2 of 3 years match cleanly (Q_SINGLE and Q_MULTI_OK)
        self.assertAlmostEqual(summary["year_accuracy"], round(2 / 3, 4))
        self.assertEqual(summary["status_answered"], 2)
        self.assertEqual(summary["status_partial"], 1)
        miss_detail = next(d for d in details if d["question_id"] == "Q_MULTI_MISS")
        self.assertEqual(miss_detail["answer_status"], "partial_answer")
        self.assertEqual(miss_detail["status_reason"], "missing_multi_entity_evidence")

    def test_recall_at_10_vs_recall_at_5(self) -> None:
        preds = [f"c{i}" for i in range(1, 11)]
        self.assertEqual(recall_mrr_at(preds, ["c8"], 5), (0.0, 0.0))
        self.assertEqual(recall_mrr_at(preds, ["c8"], 10), (1.0, 1.0 / 8.0))

        gold = {
            "Q1": {
                "question_id": "Q1",
                "question": "Doanh thu HPG năm 2024?",
                "company_id": "HPG",
                "fiscal_year": 2024,
                "report_id": "HPG_2024_consolidated",
                "gold_answer": "100 tỷ đồng",
                "value": 100.0,
                "evidence": [{"chunk_id": "c8"}],
                "needs_more_evidence": False,
            }
        }
        chunks_full = {
            f"c{i}": {
                "chunk_id": f"c{i}",
                "company_id": "HPG",
                "fiscal_year": 2024,
                "page": i,
                "text": "Doanh thu 100.000.000.000 VND",
            }
            for i in range(1, 11)
        }
        chunks = {cid: c["text"] for cid, c in chunks_full.items()}
        items = [
            {
                "question_id": "Q1",
                "gold_chunk_ids": "",  # exercises g["evidence"] fallback for recall_at_k too
                "predicted_chunk_ids": ";".join(preds),
                "predicted_top1_chunk_id": "c1",
                "predicted_company": "HPG",
                "predicted_year": "2024",
                "predicted_report_version": "consolidated",
                "predicted_page": "1",
                "predicted_answer": "100 tỷ đồng",
            }
        ]
        summary, _ = evaluate_split(items, gold, chunks, chunks_full, "TEST", "test")
        self.assertEqual(summary["k"], 10)
        self.assertEqual(summary["recall_at_k"], 1.0)
        self.assertEqual(summary["mrr_at_k"], 0.125)
        self.assertEqual(summary["recall_at_5"], 0.0)
        self.assertEqual(summary["mrr_at_5"], 0.0)
        self.assertEqual(summary["context_precision_at_5"], 0.0)
        self.assertEqual(summary["context_recall_at_5"], 0.0)
        self.assertEqual(summary["recall_at_10"], 1.0)
        self.assertEqual(summary["mrr_at_10"], 0.125)


if __name__ == "__main__":
    unittest.main()
