"""Unit tests for src/retrieval/answer_policy.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.retrieval.answer_policy import (  # noqa: E402
    REFUSAL_TEXT,
    REFUSAL_TEXT_ALT,
    build_evidence_block,
    build_generation_prompt,
    citation_complete,
    decide_status,
    detect_conflicts,
    detect_retrieval_conflict,
    is_refusal,
    refusal_label,
)


def _chunk(cid: str, company: str = "HPG", year: int | str = 2024, page: int | str = 10) -> dict:
    return {
        "chunk_id": cid,
        "company_id": company,
        "fiscal_year": year,
        "page": page,
        "report_version": "consolidated",
        "text": f"Noi dung {cid}",
    }


class TestAnswerPolicy(unittest.TestCase):
    def test_single_entity_answered(self) -> None:
        chunks = [_chunk("HPG_2024_consolidated#p010", "HPG", 2024, 10)]
        res = decide_status(
            "Doanh thu thuần của HPG năm 2024?",
            "100 tỷ đồng",
            chunks,
            tickers=["HPG"],
            years=["2024"],
        )
        self.assertEqual(res, {"status": "answered", "reason": "evidence_sufficient"})

    def test_refusal_branches(self) -> None:
        chunks = [_chunk("HPG_2024_consolidated#p010")]
        self.assertTrue(is_refusal(REFUSAL_TEXT))
        self.assertTrue(is_refusal(REFUSAL_TEXT_ALT))
        self.assertFalse(is_refusal("100 tỷ đồng"))

        self.assertEqual(
            decide_status("q", "100 tỷ", chunks, refused_by_rule=True),
            {"status": "refused", "reason": "rule_or_empty_evidence"},
        )
        self.assertEqual(
            decide_status("q", REFUSAL_TEXT, chunks),
            {"status": "refused", "reason": "rule_or_empty_evidence"},
        )
        self.assertEqual(
            decide_status("q", REFUSAL_TEXT_ALT, chunks),
            {"status": "refused", "reason": "rule_or_empty_evidence"},
        )
        self.assertEqual(
            decide_status("q", "100 tỷ", []),
            {"status": "refused", "reason": "no_chunks"},
        )

    def test_ambiguous_and_partial_single_entity(self) -> None:
        chunks = [_chunk("HSG_2024_consolidated#p009", "HSG", 2024, 9)]
        self.assertEqual(
            decide_status("q", "100 tỷ", chunks, conflict=True),
            {"status": "ambiguous", "reason": "conflicting_values"},
        )
        self.assertEqual(
            decide_status("q", "   ", chunks),
            {"status": "partial_answer", "reason": "missing_answer"},
        )
        self.assertEqual(
            decide_status("q", "100 tỷ", chunks, tickers=["HPG"], years=["2024"]),
            {"status": "partial_answer", "reason": "company_mismatch"},
        )
        self.assertEqual(
            decide_status("q", "100 tỷ", chunks, tickers=["HSG"], years=["2023"]),
            {"status": "partial_answer", "reason": "year_mismatch"},
        )
        no_page = [_chunk("HSG_2024_consolidated#p009", "HSG", 2024, "")]
        self.assertEqual(
            decide_status("q", "100 tỷ", no_page, tickers=["HSG"], years=["2024"]),
            {"status": "partial_answer", "reason": "missing_page"},
        )

    def test_multi_year_coverage_top5(self) -> None:
        only_2021 = [_chunk("HPG_2021_consolidated#p012", "HPG", 2021, 12)]
        res_missing = decide_status(
            "So sánh lợi nhuận sau thuế HPG năm 2020 và 2021",
            "21.0278 nghìn tỷ đồng",
            only_2021,
            tickers=["HPG"],
            years=["2020", "2021"],
        )
        self.assertEqual(
            res_missing,
            {"status": "partial_answer", "reason": "missing_multi_entity_evidence"},
        )

        # Year 2020 appears only at index 5 (outside top-5) -> still missing in top-5
        beyond_top5 = [_chunk(f"c{i}", "HPG", 2021, i + 1) for i in range(5)] + [
            _chunk("c5", "HPG", 2020, 11)
        ]
        res_beyond = decide_status(
            "So sánh HPG 2020 và 2021",
            "21.0278 nghìn tỷ đồng",
            beyond_top5,
            tickers=["HPG"],
            years=["2020", "2021"],
        )
        self.assertEqual(
            res_beyond,
            {"status": "partial_answer", "reason": "missing_multi_entity_evidence"},
        )

        both_in_top5 = [
            _chunk("HPG_2021_consolidated#p012", "HPG", 2021, 12),
            _chunk("HPG_2020_consolidated#p011", "HPG", 2020, 11),
        ]
        res_ok = decide_status(
            "So sánh HPG 2020 và 2021",
            "21.0278 nghìn tỷ đồng",
            both_in_top5,
            tickers=["HPG"],
            years=["2020", "2021"],
        )
        self.assertEqual(res_ok, {"status": "answered", "reason": "evidence_sufficient"})

    def test_multi_company_coverage_top5(self) -> None:
        only_hpg = [_chunk("HPG_2024#p010", "HPG", 2024, 10)]
        self.assertEqual(
            decide_status(
                "So sánh doanh thu HPG và HSG năm 2024",
                "50 nghìn tỷ đồng",
                only_hpg,
                tickers=["HPG", "HSG"],
                years=["2024"],
            ),
            {"status": "partial_answer", "reason": "missing_multi_entity_evidence"},
        )

        both_companies = [
            _chunk("HPG_2024#p010", "HPG", 2024, 10),
            _chunk("HSG_2024#p009", "HSG", 2024, 9),
        ]
        self.assertEqual(
            decide_status(
                "So sánh doanh thu HPG và HSG năm 2024",
                "50 nghìn tỷ đồng",
                both_companies,
                tickers=["hpg", "hsg"],
                years=[2024],
            ),
            {"status": "answered", "reason": "evidence_sufficient"},
        )

        # Multi-company AND multi-year where one year is missing
        missing_year_multi_comp = [
            _chunk("HPG_2024#p010", "HPG", 2024, 10),
            _chunk("HSG_2024#p009", "HSG", 2024, 9),
        ]
        self.assertEqual(
            decide_status(
                "So sánh HPG và HSG 2023 và 2024",
                "10 nghìn tỷ đồng",
                missing_year_multi_comp,
                tickers=["HPG", "HSG"],
                years=["2023", "2024"],
            ),
            {"status": "partial_answer", "reason": "missing_multi_entity_evidence"},
        )

    def test_detect_retrieval_conflict(self) -> None:
        # Single entity: top1 wrong company, asked company present later in top-5 -> conflict
        chunks_comp = [
            _chunk("HSG_2024#p009", "HSG", 2024, 9),
            _chunk("HPG_2024#p010", "HPG", 2024, 10),
        ]
        self.assertTrue(detect_retrieval_conflict(["HPG"], ["2024"], chunks_comp))

        # Single entity: top1 matches asked entity -> no conflict
        self.assertFalse(detect_retrieval_conflict(["HSG"], ["2024"], chunks_comp))

        # Single entity: top1 wrong year, asked year present later in top-5 -> conflict
        chunks_year = [
            _chunk("HPG_2023#p010", "HPG", 2023, 10),
            _chunk("HPG_2024#p010", "HPG", 2024, 10),
        ]
        self.assertTrue(detect_retrieval_conflict(["HPG"], ["2024"], chunks_year))

        # Multi-company or multi-year comparison queries -> NEVER conflict
        self.assertFalse(detect_retrieval_conflict(["HPG", "HSG"], ["2024"], chunks_comp))
        self.assertFalse(detect_retrieval_conflict(["HPG"], ["2023", "2024"], chunks_year))
        self.assertFalse(detect_retrieval_conflict([], ["2024"], chunks_comp))
        self.assertFalse(detect_retrieval_conflict(["HPG"], ["2024"], []))

    def test_detect_conflicts_table_records(self) -> None:
        self.assertFalse(detect_conflicts([]))
        self.assertFalse(detect_conflicts([{"value": 100}, {"value": 100}]))
        self.assertTrue(detect_conflicts([{"value": 100}, {"value": 200}]))

    def test_citation_complete(self) -> None:
        self.assertFalse(citation_complete([]))
        self.assertTrue(citation_complete([_chunk("c1", "HPG", 2024, 7)]))
        for missing_key in ("chunk_id", "page", "company_id", "fiscal_year"):
            c = _chunk("c1", "HPG", 2024, 7)
            c[missing_key] = ""
            self.assertFalse(citation_complete([c]))

    def test_refusal_label_and_prompt_helpers(self) -> None:
        self.assertEqual(refusal_label(REFUSAL_TEXT, True), "true_refusal")
        self.assertEqual(refusal_label("100 tỷ đồng", True), "missed_refusal")
        self.assertEqual(refusal_label(REFUSAL_TEXT, False), "false_refusal")
        self.assertEqual(refusal_label("100 tỷ đồng", False), "true_answer")

        block = build_evidence_block([_chunk("HPG_2024#p007", "HPG", 2024, 7)])
        self.assertIn("chunk_id=HPG_2024#p007", block)
        prompt = build_generation_prompt("Doanh thu HPG 2024?", [_chunk("HPG_2024#p007")])
        self.assertIn("Doanh thu HPG 2024?", prompt)
        self.assertIn("HPG_2024#p007", prompt)


if __name__ == "__main__":
    unittest.main()
