"""Lọc tập câu hỏi ViFinQA cho khớp với corpus đã chọn.

ViFinQA công khai chỉ có câu hỏi, không kèm gold answer. Script này gắn mỗi câu
hỏi với doanh nghiệp (company_id) và các năm được nhắc tới, rồi giữ lại những câu
hỏi có thể trả lời được từ corpus đang dùng.

Nhận diện doanh nghiệp và năm dùng src/preprocess/company_match.py:
- mã CK trong ngoặc, ví dụ "CTCP Tập đoàn Hòa Phát (HPG)"
- mã CK viết tắt đứng riêng, ví dụ "công ty mẹ SCR năm 2017"
- tên công ty trong câu hỏi, so khớp theo chuỗi từ liên tiếp

Kết quả ghi ra data/processed/questions_matched.csv và questions_dropped.csv,
kèm lý do loại bỏ để phục vụ data_quality_report.md.

Ví dụ:
    python src/filter_questions.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.preprocess.company_match import (  # noqa: E402
    build_signatures,
    common_tokens_in_questions,
    detect_companies,
    detect_years,
    load_companies,
)

RAW = ROOT / "data" / "raw" / "vifinqa"
OUT_DIR = ROOT / "data" / "processed"

UNIT_PRIORITY = ["nghìn tỷ đồng", "trăm tỷ đồng", "tỷ đồng", "triệu đồng", "lần", "%"]

CALC_KEYWORDS = ["tính", "trung bình", "chênh lệch", "năm nào", "tổng ", "so sánh", "lớn hơn", "thấp hơn"]


def detect_unit(question: str) -> str:
    """Trích xuất đơn vị được hỏi, ưu tiên đơn vị dài hơn."""
    lowered = question.lower()
    for unit in UNIT_PRIORITY:
        if unit in lowered:
            return unit
    return ""


def detect_answer_type(question: str) -> str:
    """Phân loại dạng câu hỏi: tính toán, số, hay văn bản."""
    lowered = question.lower()
    if any(k in lowered for k in ["tính", "trung bình", "chênh lệch", "năm nào", "so sánh"]):
        return "computation"
    if any(k in lowered for k in ["bao nhiêu", "giá trị", "số dư", "tỷ lệ", "chi phí", "lợi nhuận"]):
        return "numeric"
    return "text"


def detect_scope(question: str) -> str:
    """Phạm vi báo cáo: công ty mẹ, công ty con, hay không rõ."""
    if "công ty mẹ" in question:
        return "parent"
    if "công ty con" in question:
        return "subsidiary"
    return "unspecified"


def main() -> int:
    p = argparse.ArgumentParser(description="Loc cau hoi ViFinQA theo corpus da chon.")
    p.add_argument("--tickers", nargs="+", required=True)
    p.add_argument("--years", nargs="+", required=True, type=int)
    p.add_argument("--out", default=str(OUT_DIR / "questions_matched.csv"))
    p.add_argument("--drop-out", default=str(OUT_DIR / "questions_dropped.csv"))
    args = p.parse_args()

    corpus_tickers = {t.upper() for t in args.tickers}
    corpus_years = set(args.years)

    companies = load_companies()
    questions_path = RAW / "questions" / "questions.jsonl"
    questions = [json.loads(line) for line in open(questions_path, encoding="utf-8")]

    signatures = build_signatures(companies, common_tokens_in_questions([q["question"] for q in questions]))

    kept: list[dict] = []
    dropped: list[dict] = []

    for item in questions:
        q = item["question"]
        qid = item["id"]
        codes = detect_companies(q, companies, signatures)
        years = detect_years(q)

        base = {
            "id": qid,
            "question": q,
            "codes": "|".join(codes),
            "years": "|".join(map(str, years)),
        }

        if not codes:
            dropped.append({**base, "reason": "khong xac dinh duoc doanh nghiep"})
            continue
        if not years:
            dropped.append({**base, "reason": "khong co nam trong cau hoi"})
            continue

        outside = [c for c in codes if c not in corpus_tickers]
        if outside:
            dropped.append({**base, "reason": f"doanh nghiep ngoai corpus: {'|'.join(outside)}"})
            continue

        year_outside = [y for y in years if y not in corpus_years]
        if year_outside:
            dropped.append({**base, "reason": f"nam ngoai corpus: {'|'.join(map(str, year_outside))}"})
            continue

        matched_years = [y for y in years if y in corpus_years]
        lowered = q.lower()

        kept.append(
            {
                "question_id": qid,
                "question": q,
                "company_id": "|".join(codes),
                "company_name": " | ".join(companies[c] for c in codes),
                "n_companies": len(codes),
                "years_in_question": "|".join(map(str, years)),
                "years_in_corpus": "|".join(map(str, matched_years)),
                "unit": detect_unit(q),
                "answer_type": detect_answer_type(q),
                "scope": detect_scope(q),
                "has_calculation": int(any(k in lowered for k in CALC_KEYWORDS)),
                "is_multi_company": int(len(codes) > 1),
                "evidence_required": 1,
                "source_question_id": f"ViFinQA-{qid}",
            }
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(kept[0].keys()) if kept else ["question_id"]
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(kept)

    drop_path = Path(args.drop_out)
    with open(drop_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "question", "reason", "codes", "years"])
        writer.writeheader()
        writer.writerows(dropped)

    print(f"Tong cau hoi goc: {len(questions)}")
    print(f"Giu lai (khop corpus): {len(kept)}")
    print(f"Loai bo: {len(dropped)}")

    print("\nLy do loai bo (gom nhom):")
    groups = Counter()
    for d in dropped:
        reason = d["reason"]
        if reason.startswith("doanh nghiep ngoai corpus"):
            groups["doanh nghiep ngoai corpus"] += 1
        elif reason.startswith("nam ngoai corpus"):
            groups["nam ngoai corpus"] += 1
        else:
            groups[reason] += 1
    for reason, count in groups.most_common():
        print(f"  {count:>4}  {reason}")

    print("\nPhan bo theo doanh nghiep (giai lai):")
    per_company = Counter()
    for r in kept:
        for c in r["company_id"].split("|"):
            per_company[c] += 1
    for c, count in per_company.most_common():
        print(f"  {c:<6} {count}")

    print("\nPhan bo theo nam (giai lai):")
    per_year: Counter = Counter()
    for r in kept:
        for y in r["years_in_corpus"].split("|"):
            if y:
                per_year[int(y)] += 1
    for y, count in sorted(per_year.items()):
        print(f"  {y}  {count}")

    print("\nPhan bo theo don vi:")
    for u, count in Counter(r["unit"] or "(khong ro)" for r in kept).most_common():
        print(f"  {u:<16} {count}")

    print("\nPhan bo theo dang cau hoi:")
    for t, count in Counter(r["answer_type"] for r in kept).most_common():
        print(f"  {t:<14} {count}")

    multi = sum(1 for r in kept if r["is_multi_company"])
    calc = sum(1 for r in kept if r["has_calculation"])
    print(f"\nCau hoi nhieu doanh nghiep: {multi}")
    print(f"Cau hoi co phép tinh: {calc}")

    print(f"\nGhi: {out}\n     {drop_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
