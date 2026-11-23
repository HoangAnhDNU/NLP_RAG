"""Unit tests for src/retrieval/table_lookup.py."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.retrieval.table_lookup import (  # noqa: E402
    REFUSAL_TEXT_DEFAULT,
    UNIT_FACTORS,
    check_refusal,
    convert_value,
    detect_report_version,
    is_unit_compatible,
    lookup_comparison_pair,
    lookup_records,
    metric_score,
    parse_target_unit,
    pick_readable_vnd_unit,
    resolve_tickers,
    synthesize_answer,
)


def _sample_records() -> list[dict]:
    return [
        {
            "company": "HPG",
            "year": "2024",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "statement": "income_statement",
            "metric": "Doanh thu thuần về bán hàng và cung cấp dịch vụ",
            "metric_code": "10",
            "value": 138_855_000_000_000.0,
            "unit": "đồng",
            "period_label": "Năm 2024",
            "source_chunk_id": "HPG_2024_consolidated_p007_t01",
            "page": 7,
            "confidence": 0.98,
        },
        {
            "company": "HPG",
            "year": "2023",
            "fiscal_year": "2023",
            "report_version": "consolidated",
            "statement": "income_statement",
            "metric": "Doanh thu thuần về bán hàng và cung cấp dịch vụ",
            "metric_code": "10",
            "value": 118_953_000_000_000.0,
            "unit": "đồng",
            "period_label": "Năm 2023",
            "source_chunk_id": "HPG_2023_consolidated_p007_t01",
            "page": 7,
            "confidence": 0.98,
        },
        {
            "company": "HPG",
            "year": "2024",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "statement": "income_statement",
            "metric": "Lợi nhuận gộp về bán hàng và cung cấp dịch vụ",
            "metric_code": "20",
            "value": 18_500_000_000_000.0,
            "unit": "đồng",
            "period_label": "Năm 2024",
            "source_chunk_id": "HPG_2024_consolidated_p007_t02",
            "page": 7,
            "confidence": 0.97,
        },
        {
            "company": "HPG",
            "year": "2023",
            "fiscal_year": "2023",
            "report_version": "consolidated",
            "statement": "income_statement",
            "metric": "Lợi nhuận gộp về bán hàng và cung cấp dịch vụ",
            "metric_code": "20",
            "value": 13_000_000_000_000.0,
            "unit": "đồng",
            "period_label": "Năm 2023",
            "source_chunk_id": "HPG_2023_consolidated_p007_t02",
            "page": 7,
            "confidence": 0.97,
        },
        {
            "company": "HPG",
            "year": "2024",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "statement": "income_statement",
            "metric": "Lợi nhuận sau thuế của cổ đông của công ty mẹ",
            "metric_code": "61",
            "value": 12_020_000_000_000.0,
            "unit": "đồng",
            "period_label": "Năm 2024",
            "source_chunk_id": "HPG_2024_consolidated_p008_t01",
            "page": 8,
            "confidence": 0.96,
        },
        {
            "company": "HPG",
            "year": "2024",
            "fiscal_year": "2024",
            "report_version": "separate",
            "statement": "income_statement",
            "metric": "Lợi nhuận sau thuế thu nhập doanh nghiệp",
            "metric_code": "60",
            "value": 5_000_000_000_000.0,
            "unit": "đồng",
            "period_label": "Năm 2024",
            "source_chunk_id": "HPG_2024_separate_p008_t01",
            "page": 8,
            "confidence": 0.96,
        },
        {
            "company": "HSG",
            "year": "2024",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "statement": "notes",
            "metric": "Tỷ lệ lãi suất vay ngân hàng bình quân",
            "metric_code": "",
            "value": 6.5,
            "unit": "%",
            "period_label": "30/09/2024",
            "source_chunk_id": "HSG_2024_consolidated_p030_t01",
            "page": 30,
            "confidence": 0.92,
        },
        {
            "company": "HSG",
            "year": "2024",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "statement": "notes",
            "metric": "Tỷ lệ lãi suất vay ngân hàng bình quân",
            "metric_code": "",
            "value": 1_200_000_000.0,
            "unit": "đồng",
            "period_label": "30/09/2024",
            "source_chunk_id": "HSG_2024_consolidated_p031_t01",
            "page": 31,
            "confidence": 0.99,
        },
        {
            "company": "HSG",
            "year": "2024",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "statement": "notes",
            "metric": "Doanh thu thuần về bán hàng",
            "metric_code": "",
            "value": 18.0,
            "unit": "",
            "period_label": "Thuyết minh 18",
            "source_chunk_id": "HSG_2024_consolidated_p012_t01",
            "page": 12,
            "confidence": 0.90,
        },
        {
            "company": "HSG",
            "year": "2024",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "statement": "balance_sheet",
            "metric": "Nợ ngắn hạn",
            "metric_code": "310",
            "value": 10_500_000_000_000.0,
            "unit": "đồng",
            "period_label": "30/09/2024",
            "source_chunk_id": "HSG_2024_consolidated_p005_t01",
            "page": 5,
            "confidence": 0.98,
        },
        {
            "company": "HSG",
            "year": "2024",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "statement": "balance_sheet",
            "metric": "Nợ dài hạn",
            "metric_code": "330",
            "value": 500_000_000_000.0,
            "unit": "đồng",
            "period_label": "30/09/2024",
            "source_chunk_id": "HSG_2024_consolidated_p005_t02",
            "page": 5,
            "confidence": 0.98,
        },
    ]


class TestUnitParsingAndConversion(unittest.TestCase):
    def test_unit_factors_and_convert_value(self):
        self.assertEqual(UNIT_FACTORS["nghìn tỷ đồng"], 1e12)
        self.assertAlmostEqual(convert_value(1.5e12, "đồng", "tỷ đồng"), 1500.0)
        self.assertAlmostEqual(convert_value(2500.0, "triệu đồng", "tỷ đồng"), 2.5)
        self.assertAlmostEqual(convert_value(3.0, "nghìn tỷ đồng", "trăm tỷ đồng"), 30.0)
        self.assertAlmostEqual(convert_value(12.34, "%", "%"), 12.34)
        self.assertIsNone(convert_value(12.34, "%", "tỷ đồng"))
        self.assertIsNone(convert_value(12.34, "đồng", "%"))

    def test_parse_target_unit_scales_and_false_positive_guards(self):
        self.assertEqual(parse_target_unit("Biên lợi nhuận gộp là bao nhiêu phần trăm?"), "%")
        self.assertEqual(parse_target_unit("Đạt bao nhiêu nghìn tỷ đồng?"), "nghìn tỷ đồng")
        self.assertEqual(parse_target_unit("Đạt bao nhiêu trăm tỷ đồng?"), "trăm tỷ đồng")
        self.assertEqual(parse_target_unit("Doanh thu là bao nhiêu tỷ đồng?"), "tỷ đồng")
        self.assertEqual(parse_target_unit("Lợi nhuận tính theo triệu đồng là bao nhiêu?"), "triệu đồng")
        self.assertEqual(parse_target_unit("Chi phí bao nhiêu nghìn đồng?"), "nghìn đồng")
        self.assertEqual(parse_target_unit("Tỷ số nợ gấp bao nhiêu lần?"), "lần")
        self.assertEqual(parse_target_unit("Lãi cơ bản trên cổ phiếu là bao nhiêu đồng?"), "đồng")
        # Words containing "tỷ" or "đồng" must not trigger currency unit matching
        self.assertEqual(parse_target_unit("Tỷ lệ chi phí của Hội đồng quản trị đồng thời tăng?"), "")
        self.assertEqual(parse_target_unit("Số lượng 50 triệu cổ phiếu lưu hành là bao nhiêu?"), "")
        self.assertEqual(parse_target_unit("Giá bán tính bằng USD là bao nhiêu?"), "USD")
        self.assertEqual(parse_target_unit("Doanh thu theo EUR là bao nhiêu?"), "EUR")
        self.assertEqual(parse_target_unit("Mức cổ tức bao nhiêu đồng/cổ phiếu?"), "đồng/cổ phiếu")

    def test_is_unit_compatible_and_pick_readable(self):
        self.assertTrue(is_unit_compatible("đồng", "tỷ đồng"))
        self.assertTrue(is_unit_compatible("%", "%"))
        self.assertFalse(is_unit_compatible("đồng", "%"))
        self.assertFalse(is_unit_compatible("%", "tỷ đồng"))
        self.assertEqual(pick_readable_vnd_unit(2.5e12), "nghìn tỷ đồng")
        self.assertEqual(pick_readable_vnd_unit(2.5e9), "tỷ đồng")
        self.assertEqual(pick_readable_vnd_unit(2.5e6), "triệu đồng")
        self.assertEqual(pick_readable_vnd_unit(2500.0), "đồng")


class TestEntityAndMetadataExtraction(unittest.TestCase):
    def test_resolve_tickers_codes_and_vietnamese_aliases(self):
        self.assertEqual(resolve_tickers("Doanh thu của HPG năm 2024"), ["HPG"])
        self.assertEqual(resolve_tickers("Tập đoàn Hòa Phát đạt lợi nhuận bao nhiêu?"), ["HPG"])
        self.assertEqual(resolve_tickers("So sánh Hoa Sen và Thép Nam Kim năm 2023"), ["HSG", "NKG"])
        self.assertEqual(resolve_tickers("Masan High-Tech Materials báo lỗ bao nhiêu?"), ["MSR"])
        # Substring inside non-ticker token must not trigger false ticker match
        self.assertEqual(resolve_tickers("Mã XHPGR không thuộc danh sách"), [])

    def test_detect_report_version_handles_consolidated_parent_shareholder_idiom(self):
        self.assertEqual(detect_report_version("Báo cáo tài chính hợp nhất HPG 2024"), "consolidated")
        self.assertEqual(detect_report_version("Báo cáo tài chính riêng công ty mẹ HPG 2024"), "separate")
        self.assertEqual(
            detect_report_version("Lợi nhuận sau thuế của cổ đông của công ty mẹ HPG năm 2024 là bao nhiêu?"),
            "",
        )


class TestRefusalRules(unittest.TestCase):
    def test_out_of_corpus_queries_are_refused(self):
        cases = [
            ("Doanh thu quý 1 năm 2024 của HPG là bao nhiêu?", "subannual_period"),
            ("Kết quả bán niên 2023 của HSG?", "subannual_period"),
            ("Dự phóng doanh thu năm 2025 của NKG?", "out_of_range_year_future"),
            ("Lợi nhuận năm 2019 của HPG là bao nhiêu?", "out_of_range_year_past"),
            ("Kế hoạch lợi nhuận sau thuế của HPG là bao nhiêu?", "forward_looking"),
            ("Giá đóng cửa cổ phiếu HPG ngày 31/12/2024?", "market_or_nonstatement_metric"),
            ("Xếp hạng tín nhiệm của HSG năm 2024?", "market_or_nonstatement_metric"),
            ("Mức cổ tức bằng cổ phiếu của HSG năm 2023?", "dividend_per_share"),
            ("Giá trị hợp đồng năm 2024 là bao nhiêu USD?", "foreign_currency_unit"),
            ("Chi phí quản lý bình quân năm 2024 là bao nhiêu đồng một cổ phiếu?", "per_unit_non_statement"),
        ]
        for query, expected_reason in cases:
            with self.subTest(query=query):
                refused, reason = check_refusal(query)
                self.assertTrue(refused)
                self.assertEqual(reason, expected_reason)

    def test_in_corpus_queries_not_falsely_refused(self):
        valid_queries = [
            "Quỹ đầu tư phát triển của HPG năm 2024 là bao nhiêu tỷ đồng?",
            "Lãi cơ bản trên cổ phiếu của HSG năm 2023 là bao nhiêu đồng?",
            "Tiền trả cổ tức cho chủ sở hữu của HPG năm 2022 là bao nhiêu tỷ đồng?",
        ]
        for query in valid_queries:
            with self.subTest(query=query):
                refused, reason = check_refusal(query, extra_patterns=["quý"])
                self.assertFalse(refused, msg=f"Unexpected refusal {reason} for: {query}")


class TestLookupAndScoring(unittest.TestCase):
    def test_lookup_records_unit_priority_and_unitless_footnote_filter(self):
        recs = _sample_records()
        pct_hits = lookup_records(
            recs,
            tickers=["HSG"],
            years=["2024"],
            version="consolidated",
            question="Tỷ lệ lãi suất vay ngân hàng bình quân của HSG năm 2024 là bao nhiêu phần trăm?",
            target_unit="%",
        )
        self.assertTrue(pct_hits)
        self.assertEqual(pct_hits[0][1]["unit"], "%")
        self.assertEqual(pct_hits[0][1]["value"], 6.5)

        vnd_hits = lookup_records(
            recs,
            tickers=["HSG"],
            years=["2024"],
            version="consolidated",
            question="Doanh thu thuần của HSG năm 2024 đạt bao nhiêu tỷ đồng?",
            target_unit="tỷ đồng",
        )
        # Tiny unitless footnote number (18.0) must be filtered out on VND target unit
        self.assertEqual(vnd_hits, [])

    def test_metric_score_semantic_guards(self):
        self.assertEqual(metric_score("Cổ tức tiền mặt năm 2024", "Tiền"), 0.0)
        self.assertEqual(metric_score("Tổng tài sản năm 2024", "Tổng cộng"), 0.0)
        s_short = metric_score("Nợ ngắn hạn của HSG năm 2024", "Nợ ngắn hạn")
        s_long = metric_score("Nợ ngắn hạn của HSG năm 2024", "Nợ dài hạn")
        self.assertGreater(s_short, s_long)
        self.assertGreater(s_short, 0.7)

    def test_lookup_comparison_pair_matches_both_years(self):
        recs = _sample_records()
        pair = lookup_comparison_pair(
            recs,
            ticker="HPG",
            y1="2023",
            y2="2024",
            version="consolidated",
            question="Doanh thu thuần của HPG năm 2024 so với năm 2023?",
            target_unit="tỷ đồng",
        )
        self.assertIsNotNone(pair)
        score, r1, r2 = pair
        self.assertGreater(score, 0.5)
        self.assertEqual(r1["year"], "2023")
        self.assertEqual(r2["year"], "2024")


class TestSynthesizeAnswer(unittest.TestCase):
    def setUp(self):
        self.records = _sample_records()

    def test_single_metric_unit_conversion(self):
        res = synthesize_answer(
            "Doanh thu thuần của Tập đoàn Hòa Phát năm 2024 là bao nhiêu tỷ đồng?",
            self.records,
        )
        self.assertFalse(res["refused"])
        self.assertEqual(res["answer_source"], "table_lookup")
        self.assertEqual(res["answer"], "138855 tỷ đồng")
        self.assertEqual(res["predicted_company"], "HPG")
        self.assertEqual(res["predicted_year"], "2024")
        self.assertEqual(res["evidence_chunk_ids"], ["HPG_2024_consolidated_p007_t01"])
        self.assertGreaterEqual(res["lookup_score"], 0.0)
        self.assertLessEqual(res["lookup_score"], 1.0)

    def test_gross_margin_calculation(self):
        res = synthesize_answer(
            "Biên lợi nhuận gộp của HPG năm 2024 đạt bao nhiêu phần trăm?",
            self.records,
        )
        self.assertFalse(res["refused"])
        self.assertEqual(res["answer_source"], "computed_margin")
        expected_margin = round((18_500_000_000_000.0 / 138_855_000_000_000.0) * 100.0, 4)
        self.assertEqual(res["answer"], f"{expected_margin} %")
        self.assertEqual(
            res["evidence_chunk_ids"],
            ["HPG_2024_consolidated_p007_t02", "HPG_2024_consolidated_p007_t01"],
        )

    def test_t2_t3_comparison_difference_synthesis(self):
        res = synthesize_answer(
            "Doanh thu thuần của HPG năm 2024 tăng thêm bao nhiêu tỷ đồng so với năm 2023?",
            self.records,
        )
        self.assertFalse(res["refused"])
        self.assertEqual(res["answer_source"], "computed_diff")
        self.assertEqual(res["predicted_year"], "2023|2024")
        self.assertEqual(res["answer"], "19902 tỷ đồng")
        self.assertEqual(
            set(res["evidence_chunk_ids"]),
            {"HPG_2023_consolidated_p007_t01", "HPG_2024_consolidated_p007_t01"},
        )
        self.assertIn("2024:", res["computation"])
        self.assertIn("2023:", res["computation"])

    def test_refusal_output_and_multi_company_skip(self):
        ref = synthesize_answer(
            "Giá đóng cửa cổ phiếu HPG ngày 31/12/2024 là bao nhiêu?",
            self.records,
        )
        self.assertTrue(ref["refused"])
        self.assertEqual(ref["answer"], REFUSAL_TEXT_DEFAULT)
        self.assertEqual(ref["answer_source"], "refusal_rule")
        self.assertEqual(ref["lookup_score"], 0.0)

        multi = synthesize_answer(
            "So sánh doanh thu thuần của HPG và HSG năm 2024?",
            self.records,
        )
        self.assertFalse(multi["refused"])
        self.assertEqual(multi["answer"], "")
        self.assertEqual(multi["answer_source"], "none")


if __name__ == "__main__":
    unittest.main()
