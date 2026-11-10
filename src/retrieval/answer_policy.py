"""Chinh sach answered / partial_answer / refused / ambiguous cho RAG tai chinh.

Moi cau tra loi phai co trang thai ro rang, khong chi la chuoi dap an:

- answered: co bang chung du va ro, so lieu khop mot gia tri duy nhat.
- partial_answer: co bang chung nhung thieu mot phan thong tin
  (thieu ky, thieu ban bao cao, thieu don vi).
- refused: khong tim thay bang chung du tin cay, tra cau tu choi chuan.
- ambiguous: co nhieu gia tri mau thuan, can lam ro ky/cong ty/don vi.

Prompt sinh cau tra loi phai tuan thu:

- Chi dung thong tin tu cac chunk duoc cap.
- Trich chunk_id, page, company, year cho moi con so.
- Khong suy dien ngoai context.
- Thieu du lieu thi tra loi ro:
  "Khong tim thay du bang chung trong cac bao cao duoc cung cap."
"""

from __future__ import annotations

import re
import unicodedata

REFUSAL_TEXT = "Không đủ bằng chứng trong corpus để trả lời."
REFUSAL_TEXT_ALT = "Không tìm thấy đủ bằng chứng trong các báo cáo được cung cấp."

ANSWER_STATUSES = ("answered", "partial_answer", "refused", "ambiguous")

GENERATION_PROMPT = """Bạn là trợ lý RAG tài chính. Chỉ dùng thông tin từ các chunk được cấp.
Quy tắc bắt buộc:
1. Mỗi con số phải kèm trích dẫn: chunk_id, page, company, year.
2. Không suy diễn ngoài context, không dùng kiến thức ngoài các chunk.
3. Nếu thiếu dữ liệu, trả lời đúng nguyên văn:
"Không đủ bằng chứng trong corpus để trả lời."
4. Nếu có nhiều giá trị mâu thuẫn cho cùng chỉ tiêu, trả lời "ambiguous"
và nêu rõ cần làm rõ kỳ, công ty hay đơn vị nào.
Câu hỏi: {question}
Bằng chứng:
{evidence}
Trả lời:"""


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", (text or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def is_refusal(answer: str) -> bool:
    norm = normalize(answer)
    return norm in (normalize(REFUSAL_TEXT), normalize(REFUSAL_TEXT_ALT))


def build_evidence_block(chunks: list[dict], max_chars: int = 1200) -> str:
    lines: list[str] = []
    for c in chunks:
        text = (c.get("text", "") or "").replace("\n", " ")
        text = re.sub(r"\s+", " ", text).strip()[:max_chars]
        lines.append(
            f"- chunk_id={c.get('chunk_id', '')} | page={c.get('page', '')} | "
            f"company={c.get('company_id', '')} | year={c.get('fiscal_year', '')} | "
            f"report={c.get('report_version', '')} | text={text}"
        )
    return "\n".join(lines)


def build_generation_prompt(question: str, chunks: list[dict]) -> str:
    return GENERATION_PROMPT.format(
        question=question, evidence=build_evidence_block(chunks)
    )


def detect_conflicts(records: list[dict]) -> bool:
    """Phat hien ambiguous: cung chi tieu nhung nhieu gia tri khac nhau.

    records la cac ban ghi table_records trung company/year/metric sau loc.
    Neu co tu 2 gia tri rieng biet tro len thi coi la mau thuan can lam ro.
    Ghi chu: cau hoi de cap nhieu cong ty hay nhieu nam khong phai la mau
    thuan. Do la cau hoi so sanh hop le, thieu chunk se la partial_answer.
    Chi goi ham nay voi cac ban ghi da loc ve cung company/year/metric.
    """
    values = {r.get("value") for r in (records or []) if r.get("value") is not None}
    return len(values) >= 2


def detect_retrieval_conflict(
    question_tickers: list[str],
    question_years: list[str],
    top_chunks: list[dict],
) -> bool:
    """Mau thuan that: hoi 1 thuc the nhung bang chung top la nhieu thuc the.

    Chi xet cau hoi don (1 cong ty va 1 nam). Cau so sanh nhieu cong ty/nam
    la hop le, khong tinh la mo ho. Dieu kien mo ho: top-1 lech khoi thuc the
    duoc hoi ma top-5 lai chua ca thuc the duoc hoi lan thuc the khac, nghia la
    he khong quyet duoc nen tin chunk nao.
    """
    if not top_chunks:
        return False
    if len(question_tickers) != 1 or len(set(question_years)) != 1:
        return False
    asked_c = str(question_tickers[0]).strip().upper()
    asked_y = str(question_years[0]).strip()
    top1 = top_chunks[0] or {}
    top1_c = str(top1.get("company_id", "")).strip().upper()
    top1_y = str(top1.get("fiscal_year", "")).strip()
    companies = {str(c.get("company_id", "")).strip().upper() for c in top_chunks if str(c.get("company_id", "")).strip()}
    years = {str(c.get("fiscal_year", "")).strip() for c in top_chunks if str(c.get("fiscal_year", "")).strip()}
    company_conflict = (top1_c != asked_c) and (asked_c in companies) and (len(companies) >= 2)
    year_conflict = (top1_y != asked_y) and (asked_y in years) and (len(years) >= 2)
    return bool(company_conflict or year_conflict)


def decide_status(
    question: str,
    predicted_answer: str,
    top_chunks: list[dict],
    tickers: list[str] | None = None,
    years: list[str] | None = None,
    conflict: bool = False,
    refused_by_rule: bool = False,
) -> dict:
    """Gán trạng thái answered / partial_answer / refused / ambiguous.

    Thu tu uu tien: refused theo rule -> ambiguous khi mau thuan ->
    refused khi khong co chunk -> partial khi thieu metadata ->
    answered khi du chung cu.
    """
    if refused_by_rule or is_refusal(predicted_answer):
        return {"status": "refused", "reason": "rule_or_empty_evidence"}
    if conflict:
        return {"status": "ambiguous", "reason": "conflicting_values"}
    if not top_chunks:
        return {"status": "refused", "reason": "no_chunks"}
    if not str(predicted_answer or "").strip():
        return {"status": "partial_answer", "reason": "missing_answer"}
    top1 = top_chunks[0] if top_chunks else {}
    if tickers:
        if top1.get("company_id") not in tickers:
            return {"status": "partial_answer", "reason": "company_mismatch"}
    if years:
        if str(top1.get("fiscal_year", "")) not in {str(y) for y in years}:
            return {"status": "partial_answer", "reason": "year_mismatch"}
    if not str(top1.get("page", "")).strip():
        return {"status": "partial_answer", "reason": "missing_page"}
    return {"status": "answered", "reason": "evidence_sufficient"}


def citation_complete(top_chunks: list[dict]) -> bool:
    """Kiem tra trich dan day du: top-1 co chunk_id, page, company, year."""
    if not top_chunks:
        return False
    top1 = top_chunks[0]
    return all(
        str(top1.get(k, "")).strip()
        for k in ("chunk_id", "page", "company_id", "fiscal_year")
    )


def refusal_label(predicted_answer: str, needs_more_evidence: bool) -> str:
    """Nhan dung/sai cho tu choi: dung khi tu choi dung cho, sai nguoc lai."""
    pred_ref = is_refusal(predicted_answer)
    if needs_more_evidence and pred_ref:
        return "true_refusal"
    if needs_more_evidence and not pred_ref:
        return "missed_refusal"
    if not needs_more_evidence and pred_ref:
        return "false_refusal"
    return "true_answer"
