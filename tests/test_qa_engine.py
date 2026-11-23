"""Unit tests for app/qa_engine.py parity, alias retrieval bonus, and refusals."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import qa_engine  # noqa: E402
from src.preprocess.normalize import normalize_query, tokenize_vi  # noqa: E402
from src.retrieval.bm25 import BM25Retriever  # noqa: E402
from src.retrieval.table_lookup import REFUSAL_TEXT_DEFAULT, synthesize_answer  # noqa: E402


def _build_fixture():
    chunks = [
        {
            "chunk_id": "HPG_2024_consolidated_p007_t01",
            "company_id": "HPG",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "page": 7,
            "document_id": "HPG_2024_consolidated",
            "local_path": "data/raw/HPG_2024_consolidated.pdf",
            "unit": "đồng",
            "n_tables": 1,
            "text": "Báo cáo kết quả hoạt động kinh doanh hợp nhất năm 2024. Doanh thu thuần về bán hàng và cung cấp dịch vụ 138855 tỷ đồng.",
        },
        {
            "chunk_id": "HPG_2024_consolidated_p007_t02",
            "company_id": "HPG",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "page": 7,
            "document_id": "HPG_2024_consolidated",
            "local_path": "data/raw/HPG_2024_consolidated.pdf",
            "unit": "đồng",
            "n_tables": 1,
            "text": "Báo cáo kết quả hoạt động kinh doanh hợp nhất năm 2024. Lợi nhuận gộp về bán hàng và cung cấp dịch vụ 18500 tỷ đồng.",
        },
        {
            "chunk_id": "HPG_2023_consolidated_p007_t01",
            "company_id": "HPG",
            "fiscal_year": "2023",
            "report_version": "consolidated",
            "page": 7,
            "document_id": "HPG_2023_consolidated",
            "local_path": "data/raw/HPG_2023_consolidated.pdf",
            "unit": "đồng",
            "n_tables": 1,
            "text": "Báo cáo kết quả hoạt động kinh doanh hợp nhất năm 2023. Doanh thu thuần về bán hàng và cung cấp dịch vụ 118953 tỷ đồng.",
        },
        {
            "chunk_id": "HSG_2024_consolidated_p007_t01",
            "company_id": "HSG",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "page": 7,
            "document_id": "HSG_2024_consolidated",
            "local_path": "data/raw/HSG_2024_consolidated.pdf",
            "unit": "đồng",
            "n_tables": 1,
            "text": "Báo cáo kết quả hoạt động kinh doanh hợp nhất năm 2024. Doanh thu thuần về bán hàng và cung cấp dịch vụ 39271 tỷ đồng.",
        },
        {
            "chunk_id": "HSG_2024_consolidated_p007_t02",
            "company_id": "HSG",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "page": 7,
            "document_id": "HSG_2024_consolidated",
            "local_path": "data/raw/HSG_2024_consolidated.pdf",
            "unit": "đồng",
            "n_tables": 1,
            "text": "Báo cáo kết quả hoạt động kinh doanh hợp nhất năm 2024. Lợi nhuận gộp về bán hàng và cung cấp dịch vụ 4200 tỷ đồng.",
        },
        {
            "chunk_id": "NKG_2024_consolidated_p006_t01",
            "company_id": "NKG",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "page": 6,
            "document_id": "NKG_2024_consolidated",
            "local_path": "data/raw/NKG_2024_consolidated.pdf",
            "unit": "đồng",
            "n_tables": 1,
            "text": "Báo cáo kết quả hoạt động kinh doanh hợp nhất năm 2024. Doanh thu thuần về bán hàng và cung cấp dịch vụ 20600 tỷ đồng.",
        },
        {
            "chunk_id": "MSR_2024_consolidated_p009_t01",
            "company_id": "MSR",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "page": 9,
            "document_id": "MSR_2024_consolidated",
            "local_path": "data/raw/MSR_2024_consolidated.pdf",
            "unit": "đồng",
            "n_tables": 1,
            "text": "Báo cáo kết quả hoạt động kinh doanh hợp nhất năm 2024. Doanh thu thuần về bán hàng và cung cấp dịch vụ 14300 tỷ đồng.",
        },
        {
            "chunk_id": "HPG_2022_consolidated_p020_n01",
            "company_id": "HPG",
            "fiscal_year": "2022",
            "report_version": "consolidated",
            "page": 20,
            "document_id": "HPG_2022_consolidated",
            "local_path": "data/raw/HPG_2022_consolidated.pdf",
            "unit": "",
            "n_tables": 0,
            "text": "Thuyết minh chính sách kế toán hàng tồn kho và tài sản cố định năm 2022.",
        },
    ]

    records = [
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
            "confidence": 0.98,
        },
        {
            "company": "HSG",
            "year": "2024",
            "fiscal_year": "2024",
            "report_version": "consolidated",
            "statement": "income_statement",
            "metric": "Doanh thu thuần về bán hàng và cung cấp dịch vụ",
            "metric_code": "10",
            "value": 39_271_000_000_000.0,
            "unit": "đồng",
            "period_label": "Năm 2024",
            "source_chunk_id": "HSG_2024_consolidated_p007_t01",
            "page": 7,
            "confidence": 0.98,
        },
    ]

    stopwords = {"của", "và", "là", "năm", "bao", "nhiêu"}

    def tokenize(text: str) -> list[str]:
        return [t for t in tokenize_vi(normalize_query(text)) if t not in stopwords and len(t) > 1]

    retriever = BM25Retriever(k1=1.5, b=0.75).fit([tokenize(c["text"]) for c in chunks])
    patterns = ["quý", "giá đóng cửa", "vốn hóa", "kế hoạch", "2025", "usd"]
    gold_by_q: dict = {}
    gold_list: list = []
    engine_tuple = (chunks, tokenize, retriever, patterns, gold_by_q, gold_list)
    return engine_tuple, records


class TestQAEngine(unittest.TestCase):
    def setUp(self):
        self.engine_tuple, self.records = _build_fixture()
        self.p_engine = patch("app.qa_engine.load_engine", return_value=self.engine_tuple)
        self.p_records = patch("app.qa_engine.load_table_records", return_value=self.records)
        self.p_engine.start()
        self.p_records.start()

    def tearDown(self):
        self.p_engine.stop()
        self.p_records.stop()

    def test_parity_with_shared_synthesize_answer(self):
        patterns = self.engine_tuple[3]
        queries = [
            ("Doanh thu thuần của HPG năm 2024 là bao nhiêu tỷ đồng?", "rag-table-lookup"),
            ("Biên lợi nhuận gộp của HPG năm 2024 là bao nhiêu phần trăm?", "rag-margin"),
            ("Doanh thu thuần của HPG năm 2024 chênh lệch bao nhiêu tỷ đồng so với năm 2023?", "rag-table-diff"),
        ]
        for query, expected_src in queries:
            with self.subTest(query=query):
                hits = qa_engine.retrieve(query, top_k=5)
                gen = qa_engine.generate_from_context(query, hits)
                synth = synthesize_answer(
                    query,
                    self.records,
                    min_score=0.4,
                    extra_refusal_patterns=patterns,
                    refusal_text=REFUSAL_TEXT_DEFAULT,
                )
                self.assertEqual(gen["answer"], synth["answer"])
                self.assertEqual(gen["computation"], synth["computation"])
                self.assertEqual(gen["evidence"], synth["evidence_chunk_ids"])
                self.assertEqual(gen["answer_source"], expected_src)

                out = qa_engine.answer(query, top_k=5)
                self.assertFalse(out["refused"])
                self.assertEqual(out["answer"], synth["answer"])
                self.assertEqual(out["answer_status"], "answered")
                for h in out["hits"]:
                    self.assertGreaterEqual(h["score"], 0.0)
                    self.assertLessEqual(h["score"], 1.0)

    def test_vietnamese_company_alias_retrieval_bonus(self):
        alias_queries = [
            ("Doanh thu thuần của Tập đoàn Hoa Sen năm 2024", "Doanh thu thuần của HSG năm 2024", "HSG"),
            ("Doanh thu thuần của Thép Nam Kim năm 2024", "Doanh thu thuần của NKG năm 2024", "NKG"),
            ("Doanh thu thuần của Masan High-Tech Materials năm 2024", "Doanh thu thuần của MSR năm 2024", "MSR"),
            ("Doanh thu thuần của Tập đoàn Hòa Phát năm 2024", "Doanh thu thuần của HPG năm 2024", "HPG"),
        ]
        for alias_q, ticker_q, expected_company in alias_queries:
            with self.subTest(query=alias_q):
                hits = qa_engine.retrieve(alias_q, top_k=5)
                ticker_hits = qa_engine.retrieve(ticker_q, top_k=5)
                self.assertTrue(hits)
                self.assertEqual(hits[0]["company_id"], expected_company)
                self.assertEqual(hits[0]["fiscal_year"], "2024")
                # Alias resolution must yield identical top chunk and clamped scores as explicit ticker
                self.assertEqual(
                    [(h["chunk_id"], h["score"]) for h in hits],
                    [(h["chunk_id"], h["score"]) for h in ticker_hits],
                )
                for h in hits:
                    self.assertGreaterEqual(h["score"], 0.0)
                    self.assertLessEqual(h["score"], 1.0)
        # Below the 1.0 clamp ceiling, alias match gets +0.15 vs +0.075 for year-only match
        hsg_hits = qa_engine.retrieve("Doanh thu thuần của Tập đoàn Hoa Sen năm 2024", top_k=8)
        hsg_t02 = next(h for h in hsg_hits if h["chunk_id"] == "HSG_2024_consolidated_p007_t02")
        hpg_t02 = next(h for h in hsg_hits if h["chunk_id"] == "HPG_2024_consolidated_p007_t02")
        self.assertGreater(hsg_t02["score"], hpg_t02["score"])
        self.assertAlmostEqual(hsg_t02["score"] - hpg_t02["score"], 0.075, places=3)

    def test_refusal_on_out_of_corpus_prompts(self):
        rule_refusals = [
            "Giá đóng cửa cổ phiếu HPG ngày 31/12/2024 là bao nhiêu đồng?",
            "Doanh thu thuần quý 2 năm 2024 của HSG là bao nhiêu tỷ đồng?",
            "Dự báo lợi nhuận năm 2025 của HPG là bao nhiêu tỷ đồng?",
            "Giá bán sản phẩm năm 2024 của MSR là bao nhiêu USD một tấn?",
        ]
        for q in rule_refusals:
            with self.subTest(query=q):
                out = qa_engine.answer(q, top_k=5)
                self.assertTrue(out["refused"])
                self.assertEqual(out["answer"], REFUSAL_TEXT_DEFAULT)
                self.assertEqual(out["answer_source"], "refusal-rule")
                self.assertEqual(out["answer_status"], "refused")

        unmatched_refusals = [
            "Doanh thu thuần của VNM năm 2024 là bao nhiêu tỷ đồng?",
            "Thời tiết Hà Nội hôm nay như thế nào?",
        ]
        for q in unmatched_refusals:
            with self.subTest(query=q):
                out = qa_engine.answer(q, top_k=5)
                self.assertTrue(out["refused"])
                self.assertEqual(out["answer"], REFUSAL_TEXT_DEFAULT)
                self.assertEqual(out["answer_source"], "refusal-no-evidence")
                self.assertEqual(out["answer_status"], "refused")

    def test_attach_status_multi_year_partial_vs_answered(self):
        q = "Doanh thu thuần của HPG năm 2024 so với năm 2023 chênh lệch bao nhiêu tỷ đồng?"
        only_2024 = [
            {
                "chunk_id": "HPG_2024_consolidated_p007_t01",
                "page": 7,
                "company_id": "HPG",
                "fiscal_year": "2024",
            }
        ]
        st_partial = qa_engine.attach_status(q, "19902 tỷ đồng", only_2024)
        self.assertEqual(st_partial["answer_status"], "partial_answer")
        self.assertEqual(st_partial["status_reason"], "missing_multi_entity_evidence")

        both_years = only_2024 + [
            {
                "chunk_id": "HPG_2023_consolidated_p007_t01",
                "page": 7,
                "company_id": "HPG",
                "fiscal_year": "2023",
            }
        ]
        st_answered = qa_engine.attach_status(q, "19902 tỷ đồng", both_years)
        self.assertEqual(st_answered["answer_status"], "answered")


if __name__ == "__main__":
    unittest.main()
