"""Chấm metric E0-E8, tách retrieval, citation, answer và refusal (Mục 4.6.5, RAGAS).

Đọc prediction CSV của một run và `qa_gold.jsonl`, tính trên dev và test:
- Retrieval (chỉ trên câu có evidence): recall@3, recall@5, recall@10,
  mrr@3, mrr@5, mrr@10, context_precision@5, context_recall@5.
  Ghi chú: file prediction hiện chỉ lưu top-5 nên recall@10 và mrr@10
  được tính trên top-5 đã lưu, bằng với @5.
- Citation: citation_precision_top1 (top-1 nằm trong evidence),
  citation_recall@5, citation_complete_rate (top-1 đủ chunk_id/page/company/year).
- Answer số (chỉ trên câu có gold_answer và không thiếu bằng chứng):
  numeric_match sau chuẩn hóa đơn vị, exact_match sau chuẩn hóa chuỗi.
- Answer status: answered / partial_answer / refused / ambiguous theo
  `src/retrieval/answer_policy.py` và `config/answer_policy.yaml`.
- Period (nghiệp vụ tài chính): company_accuracy, year_accuracy,
  version_accuracy, period_accuracy (cả 3 đúng), page_accuracy.
- Refusal: refusal_precision, refusal_recall, refusal_rate, false_answer_rate
  = 1 - (numeric đúng + từ chối đúng) / tổng số câu, kèm nhãn
  true_refusal / missed_refusal / false_refusal / true_answer.
- Unsupported_claim_rate: tỷ lệ câu trả lời có khẳng định số không tìm thấy
  trong top-5 chunk.
- Answer số (chỉ trên câu có gold_answer và không thiếu bằng chứng):
  numeric_match sau chuẩn hóa đơn vị, exact_match sau chuẩn hóa chuỗi.
- Period (nghiệp vụ tài chính): company_accuracy, year_accuracy,
  version_accuracy, period_accuracy (cả 3 đúng), page_accuracy
  (trang trích dẫn đúng, chỉ trên câu có source_page).
- Refusal: refusal_precision, refusal_recall, refusal_rate (giống recall
  trên nhóm thiếu bằng chứng).
- Unsupported_claim_rate: tỷ lệ câu trả lời có khẳng định số không tìm thấy
  trong top-5 chunk. faithfulness_heuristic = 1 - unsupported_claim_rate.
  answer_relevancy_heuristic = (numeric đúng + từ chối đúng) / tổng số câu.
- Faithfulness và answer_relevancy bằng LLM judge chưa áp dụng vì pipeline
  không gọi LLM API; hai cột heuristic ở trên là thay thế minh bạch.

Ví dụ:
    python src/evaluate/evaluate.py --run E0
    python src/evaluate/evaluate.py --run E3 --pred evaluation/test_predictions/test_predictions_E3.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.retrieval.answer_policy import (  # noqa: E402
    citation_complete,
    decide_status,
    detect_retrieval_conflict,
    is_refusal,
    refusal_label,
)
from src.retrieval.table_lookup import resolve_tickers  # noqa: E402

REFUSAL_TEXT = "Không đủ bằng chứng trong corpus để trả lời."
NUM_RE = re.compile(r"\(?-?\d[\d.\s,]*\d-?\)?%?")
YEAR_RE = re.compile(r"\b(20[0-2]\d)\b")


def norm_answer(text: str) -> str:
    text = (text or "").strip().lower()
    return " ".join(text.split())


def norm_num_token(raw: str) -> str:
    value = (raw or "").strip().lower().replace(" ", "")
    if not value:
        return ""
    negative = False
    if value.startswith("(") and value.endswith(")"):
        negative = True
        value = value[1:-1]
    is_pct = value.endswith("%")
    if is_pct:
        value = value[:-1]
    value = value.replace(",", ".")
    parts = value.split(".")
    if len(parts) > 2:
        value = "".join(parts[:-1]) + "." + parts[-1]
    value = re.sub(r"[^0-9.\-]", "", value)
    if value.startswith("-"):
        negative = not negative
        value = value[1:]
    if not value or value == ".":
        return ""
    if negative:
        value = "-" + value
    if is_pct:
        value = value + "%"
    return value


def parse_float(token: str) -> float | None:
    token = (token or "").strip()
    if not token:
        return None
    is_pct = token.endswith("%")
    if is_pct:
        token = token[:-1]
    try:
        return float(token)
    except ValueError:
        return None


def numeric_match_pred(pred_answer: str, gold_value: object, gold_answer: str) -> bool:
    if not pred_answer or not pred_answer.strip():
        return False
    if norm_answer(pred_answer) == norm_answer(REFUSAL_TEXT):
        return False
    try:
        gv = float(gold_value)
    except (TypeError, ValueError):
        return norm_answer(pred_answer) == norm_answer(gold_answer)
    cands = [parse_float(norm_num_token(t)) for t in NUM_RE.findall(pred_answer)]
    cands = [c for c in cands if c is not None]
    if not cands:
        return False
    return any(abs(c - gv) <= max(1e-4, abs(gv) * 1e-6) for c in cands)


def load_chunks() -> dict:
    path = ROOT / "data" / "processed" / "chunks.jsonl"
    idx: dict = {}
    if not path.exists():
        return idx
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            idx[r.get("chunk_id", "")] = r.get("text", "")
    return idx


def load_chunks_full() -> dict:
    path = ROOT / "data" / "processed" / "chunks.jsonl"
    idx: dict = {}
    if not path.exists():
        return idx
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            idx[r.get("chunk_id", "")] = r
    return idx


def numbers_in_context(pred_answer: str, context: str) -> bool:
    toks = [norm_num_token(t) for t in NUM_RE.findall(pred_answer or "")]
    toks = [t for t in toks if t]
    if not toks:
        return True
    ctx = norm_num_token(context)
    flat_ctx = (context or "").lower().replace(" ", "")
    for t in toks:
        core = t.rstrip("%")
        if core and core.replace(".", "") in flat_ctx.replace(".", ""):
            continue
        if t and t in ctx:
            continue
        return False
    return True


def recall_mrr_at(pred_chunks: list, gold_unique: list, k: int) -> tuple[float, float]:
    top = pred_chunks[:k]
    hit = any(c in top for c in gold_unique)
    rank = next((i + 1 for i, c in enumerate(top) if c in gold_unique), None)
    return (1.0 if hit else 0.0, 1.0 / rank if rank else 0.0)


def main() -> int:
    p = argparse.ArgumentParser(description="Chấm metric retrieval/answer/citation.")
    p.add_argument("--run", default="E0")
    p.add_argument("--pred", default=None)
    p.add_argument("--gold", default=str(ROOT / "data" / "annotations" / "qa_gold.jsonl"))
    p.add_argument("--out", default=str(ROOT / "evaluation" / "metrics_summary.csv"))
    p.add_argument("--test-dir", default=str(ROOT / "evaluation" / "test_predictions"))
    p.add_argument("--dev-dir", default=str(ROOT / "evaluation" / "dev_predictions"))
    p.add_argument("--refusal-dir", default=str(ROOT / "evaluation" / "refusal_labels"))
    args = p.parse_args()

    gold = {json.loads(line)["question_id"]: json.loads(line) for line in open(args.gold, encoding="utf-8")}
    if args.pred:
        pred_path = Path(args.pred)
    else:
        pred_path = Path(args.test_dir) / f"test_predictions_{args.run}.csv"
        legacy = ROOT / "evaluation" / f"test_predictions_{args.run}.csv"
        if not pred_path.exists() and legacy.exists():
            pred_path = legacy
    rows = list(csv.DictReader(open(pred_path, encoding="utf-8")))

    by_split: dict[str, list[dict]] = {"dev": [], "test": []}
    dev_path = Path(args.dev_dir) / pred_path.name.replace("test_", "dev_")
    legacy_dev = pred_path.parent / pred_path.name.replace("test_", "dev_")
    if not dev_path.exists() and legacy_dev.exists() and legacy_dev != pred_path:
        dev_path = legacy_dev
    all_rows = rows
    if dev_path.exists() and dev_path != pred_path:
        all_rows = list(csv.DictReader(open(dev_path, encoding="utf-8"))) + rows
    for r in all_rows:
        by_split.setdefault(r.get("split", "test"), []).append(r)

    chunks = load_chunks()
    chunks_full = load_chunks_full()

    summary: list[dict] = []
    detail_rows: list[dict] = []
    for split in ("dev", "test"):
        items = by_split.get(split, [])
        n = len(items)
        r3, r5, m3, m5 = [], [], [], []
        ctx_p, ctx_r = [], []
        cit_p_hit, cit_p_den = 0, 0
        cit_complete_hit, cit_complete_den = 0, 0
        ans_num_hit, ans_num_den = 0, 0
        ans_em_hit, ans_em_den = 0, 0
        comp_hit, comp_den = 0, 0
        year_hit, year_den = 0, 0
        ver_hit, ver_den = 0, 0
        period_hit, period_den = 0, 0
        page_hit, page_den = 0, 0
        ref_pred_pos, ref_tp = 0, 0
        ref_den = 0
        unsup_bad, unsup_den = 0, 0
        relev_hit = 0
        status_counts = {"answered": 0, "partial_answer": 0, "refused": 0, "ambiguous": 0}
        label_counts = {"true_refusal": 0, "missed_refusal": 0, "false_refusal": 0, "true_answer": 0}

        for r in items:
            g = gold.get(r["question_id"], {})
            pred_chunks = [c for c in (r.get("predicted_chunk_ids") or "").split(";") if c]
            gold_chunks = [c for c in (r.get("gold_chunk_ids") or "").split(";") if c]
            gold_unique = sorted(set(gold_chunks))

            if gold_unique:
                h3, m_3 = recall_mrr_at(pred_chunks, gold_unique, 3)
                h5, m_5 = recall_mrr_at(pred_chunks, gold_unique, 5)
                r3.append(h3)
                r5.append(h5)
                m3.append(m_3)
                m5.append(m_5)
                inter = len(set(pred_chunks[:5]) & set(gold_unique))
                ctx_p.append(inter / 5.0)
                ctx_r.append(inter / len(gold_unique) if gold_unique else 0.0)
                cit_p_den += 1
                if pred_chunks and pred_chunks[0] in gold_unique:
                    cit_p_hit += 1

            needs_ref = bool(g.get("needs_more_evidence"))
            pred_is_ref = is_refusal(r.get("predicted_answer", ""))
            if needs_ref:
                ref_den += 1
                if pred_is_ref:
                    ref_tp += 1
                    relev_hit += 1
            if pred_is_ref:
                ref_pred_pos += 1

            top_full = [chunks_full.get(c, {}) for c in pred_chunks[:5] if c in chunks_full]
            if top_full:
                cit_complete_den += 1
                if citation_complete(top_full):
                    cit_complete_hit += 1
            _qtext = g.get("question", "") or r.get("question", "")
            mtickers = resolve_tickers(_qtext)
            myears = YEAR_RE.findall(_qtext)
            top_for_status = [
                {
                    "chunk_id": c.get("chunk_id", ""),
                    "page": c.get("page", ""),
                    "company_id": c.get("company_id", ""),
                    "fiscal_year": c.get("fiscal_year", ""),
                }
                for c in top_full
            ]
            decided = decide_status(
                g.get("question", "") or r.get("question", ""),
                r.get("predicted_answer", ""),
                top_for_status,
                tickers=mtickers if len(mtickers) == 1 else None,
                years=myears if len(set(myears)) == 1 else None,
                conflict=detect_retrieval_conflict(mtickers, myears, top_for_status),
                refused_by_rule=pred_is_ref,
            )
            status_counts[decided["status"]] = status_counts.get(decided["status"], 0) + 1
            rlabel = refusal_label(r.get("predicted_answer", ""), needs_ref)
            label_counts[rlabel] = label_counts.get(rlabel, 0) + 1
            detail_rows.append(
                {
                    "run": args.run,
                    "split": split,
                    "question_id": r.get("question_id", ""),
                    "answer_status": decided["status"],
                    "status_reason": decided.get("reason", ""),
                    "refusal_label": rlabel,
                    "needs_more_evidence": needs_ref,
                    "citation_complete_top1": bool(top_for_status and citation_complete(top_for_status)),
                    "predicted_answer": r.get("predicted_answer", ""),
                    "predicted_top1_chunk_id": r.get("predicted_top1_chunk_id", ""),
                }
            )

            if needs_ref:
                pass
            elif g.get("gold_answer"):
                ans_num_den += 1
                ans_em_den += 1
                if numeric_match_pred(r.get("predicted_answer", ""), g.get("value"), g.get("gold_answer", "")):
                    ans_num_hit += 1
                    relev_hit += 1
                if norm_answer(r.get("predicted_answer", "")) == norm_answer(g.get("gold_answer", "")):
                    ans_em_hit += 1

            if g.get("company_id"):
                comp_den += 1
                pred_comp = (r.get("predicted_company") or "").strip().upper()
                if pred_comp and pred_comp == str(g.get("company_id", "")).strip().upper():
                    comp_hit += 1
            if str(g.get("fiscal_year", "")).strip():
                year_den += 1
                if str(r.get("predicted_year", "")).strip() == str(g.get("fiscal_year", "")).strip():
                    year_hit += 1
            gold_report = str(g.get("report_id", "")).strip()
            if gold_report:
                ver_den += 1
                gold_ver = "separate" if gold_report.endswith("_separate") else ("consolidated" if gold_report.endswith("_consolidated") else "")
                if gold_ver and (r.get("predicted_report_version") or "").strip() == gold_ver:
                    ver_hit += 1
            if g.get("company_id") and str(g.get("fiscal_year", "")).strip() and gold_report:
                period_den += 1
                pred_comp = (r.get("predicted_company") or "").strip().upper()
                gold_ver = "separate" if gold_report.endswith("_separate") else ("consolidated" if gold_report.endswith("_consolidated") else "")
                ok = (
                    pred_comp == str(g.get("company_id", "")).strip().upper()
                    and str(r.get("predicted_year", "")).strip() == str(g.get("fiscal_year", "")).strip()
                    and (r.get("predicted_report_version") or "").strip() == gold_ver
                )
                if ok:
                    period_hit += 1
            if str(g.get("source_page", "")).strip():
                page_den += 1
                if str(r.get("predicted_page", "")).strip() == str(g.get("source_page", "")).strip():
                    page_hit += 1

            pred_ans = (r.get("predicted_answer") or "").strip()
            if pred_ans and not pred_is_ref and not needs_ref and g.get("gold_answer"):
                unsup_den += 1
                ctx_text = " ".join(chunks.get(c, "") for c in pred_chunks[:5])
                if not numbers_in_context(pred_ans, ctx_text):
                    unsup_bad += 1

        k = max((len((r.get("predicted_chunk_ids") or "").split(";")) for r in items), default=0)
        ev_den = len(r3)
        unsup_rate = round(unsup_bad / unsup_den, 4) if unsup_den else 0.0
        r5v = round(sum(r5) / len(r5), 4) if r5 else 0.0
        m5v = round(sum(m5) / len(m5), 4) if m5 else 0.0
        cit_complete_rate = round(cit_complete_hit / cit_complete_den, 4) if cit_complete_den else 0.0
        relev = round(relev_hit / n, 4) if n else 0.0
        false_answer_rate = round(1.0 - relev, 4) if n else 0.0
        summary.append(
            {
                "run": args.run,
                "split": split,
                "n": n,
                "k": k,
                "recall_at_k": r5v,
                "mrr_at_k": m5v,
                "recall_at_3": round(sum(r3) / len(r3), 4) if r3 else 0.0,
                "recall_at_5": r5v,
                "recall_at_10": r5v,
                "mrr_at_3": round(sum(m3) / len(m3), 4) if m3 else 0.0,
                "mrr_at_5": m5v,
                "mrr_at_10": m5v,
                "context_precision_at_5": round(sum(ctx_p) / len(ctx_p), 4) if ctx_p else 0.0,
                "context_recall_at_5": round(sum(ctx_r) / len(ctx_r), 4) if ctx_r else 0.0,
                "citation_precision_top1": round(cit_p_hit / cit_p_den, 4) if cit_p_den else 0.0,
                "citation_recall_at_5": r5v,
                "citation_correctness": round(cit_p_hit / cit_p_den, 4) if cit_p_den else 0.0,
                "citation_complete_rate": cit_complete_rate,
                "citation_complete_den": cit_complete_den,
                "numeric_match": round(ans_num_hit / ans_num_den, 4) if ans_num_den else 0.0,
                "exact_match": round(ans_em_hit / ans_em_den, 4) if ans_em_den else 0.0,
                "period_accuracy": round(period_hit / period_den, 4) if period_den else 0.0,
                "company_accuracy": round(comp_hit / comp_den, 4) if comp_den else 0.0,
                "year_accuracy": round(year_hit / year_den, 4) if year_den else 0.0,
                "version_accuracy": round(ver_hit / ver_den, 4) if ver_den else 0.0,
                "page_accuracy": round(page_hit / page_den, 4) if page_den else 0.0,
                "evidence_den": ev_den,
                "unsupported_claim_rate": unsup_rate,
                "faithfulness_heuristic": round(1.0 - unsup_rate, 4) if unsup_den else 0.0,
                "answer_relevancy_heuristic": relev,
                "false_answer_rate": false_answer_rate,
                "status_answered": status_counts.get("answered", 0),
                "status_partial": status_counts.get("partial_answer", 0),
                "status_refused": status_counts.get("refused", 0),
                "status_ambiguous": status_counts.get("ambiguous", 0),
                "true_refusal": label_counts.get("true_refusal", 0),
                "missed_refusal": label_counts.get("missed_refusal", 0),
                "false_refusal": label_counts.get("false_refusal", 0),
                "true_answer": label_counts.get("true_answer", 0),
                "refusal_precision": round(ref_tp / ref_pred_pos, 4) if ref_pred_pos else 0.0,
                "refusal_recall": round(ref_tp / ref_den, 4) if ref_den else 0.0,
                "refusal_rate": round(ref_tp / ref_den, 4) if ref_den else 0.0,
                "refusal_den": ref_den,
                "prediction_file": pred_path.name,
            }
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    merged: list[dict] = []
    if out.exists():
        try:
            existing = list(csv.DictReader(open(out, encoding="utf-8")))
            merged = [r for r in existing if r.get("run") != args.run]
        except Exception:
            merged = []
    merged.extend(summary)
    order = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5, "E6": 6, "E7": 7, "E8": 8}
    merged.sort(key=lambda r: (order.get(r.get("run"), 9), r.get("split")))
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(merged)

    for s in summary:
        print(
            f"{s['run']}/{s['split']}: n={s['n']} R@3={s['recall_at_3']} R@5={s['recall_at_5']} "
            f"MRR@5={s['mrr_at_5']} ctxP={s['context_precision_at_5']} ctxR={s['context_recall_at_5']} "
            f"citeP={s['citation_precision_top1']} citeFull={s['citation_complete_rate']} "
            f"num={s['numeric_match']} em={s['exact_match']} "
            f"period={s['period_accuracy']} page={s['page_accuracy']} unsup={s['unsupported_claim_rate']} "
            f"faith={s['faithfulness_heuristic']} relev={s['answer_relevancy_heuristic']} "
            f"falseAns={s['false_answer_rate']} refP={s['refusal_precision']} refR={s['refusal_recall']}({s['refusal_den']}) "
            f"status=[ans={s['status_answered']}/part={s['status_partial']}/ref={s['status_refused']}/amb={s['status_ambiguous']}] "
            f"labels=[TR={s['true_refusal']}/MR={s['missed_refusal']}/FR={s['false_refusal']}/TA={s['true_answer']}]"
        )
    print(f"Đã ghi -> {out}")
    detail_path = Path(args.refusal_dir) / f"refusal_labels_{args.run}.csv"
    detail_path.parent.mkdir(parents=True, exist_ok=True)
    if detail_rows:
        with open(detail_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(detail_rows[0].keys()))
            w.writeheader()
            w.writerows(detail_rows)
        print(f"Đã ghi nhãn chi tiết -> {detail_path} ({len(detail_rows)} dòng)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
