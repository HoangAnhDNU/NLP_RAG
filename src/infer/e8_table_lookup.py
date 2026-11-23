"""E8: lookup co cau truc tren table_records truoc, hybrid RAG giai thich sau.

Duong di: normalize + trich company/nam/ban/chi tieu -> lookup table_records
(loc company/nam/ban + khop chi tieu) -> quy doi don vi ve don vi cau hoi ->
tra loi so truc tiep + giu chunk goc de kiem chung. Neu lookup truot thi
fallback ve hybrid BM25+LSA giong E2. Giam hallucination so lieu.
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
import yaml
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.preprocess.normalize import normalize_query, tokenize_vi  # noqa: E402
from src.retrieval.bm25 import BM25Retriever  # noqa: E402
from src.retrieval.pipeline_two_stage import minmax  # noqa: E402
from src.retrieval.table_lookup import synthesize_answer  # noqa: E402
def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
def load_records(path: Path) -> list[dict]:
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs
def main() -> int:
    p = argparse.ArgumentParser(description="Chay E8 table lookup.")
    p.add_argument("--config", default=str(ROOT / "config" / "e8_table_lookup.yaml"))
    p.add_argument("--gold", default=str(ROOT / "data" / "annotations" / "qa_gold.jsonl"))
    p.add_argument("--outdir", default=str(ROOT / "evaluation"))
    args = p.parse_args()
    cfg = load_config(Path(args.config))
    top_k = int(cfg["retrieval"]["top_k"]); save_k = max(top_k, 10); cand_k = int(cfg["retrieval"].get("candidate_k", 20))
    alpha = float(cfg["retrieval"].get("fusion_alpha", 0.5)) if "fusion_alpha" in cfg["retrieval"] else 0.5
    bonus = float(cfg["retrieval"].get("metadata_bonus", 0.15))
    min_score = float(cfg["retrieval"].get("lookup_min_score", 0.3))
    refusal_text = cfg["refusal"]["text"]; patterns = [s.lower() for s in cfg["refusal"].get("patterns", [])]
    e0_cfg = load_config(ROOT / "config" / "e0_bm25.yaml"); stopwords = set(e0_cfg.get("stopwords", []))
    e1_cfg = load_config(ROOT / cfg["model"]["dense_source"])
    chunks = [json.loads(line) for line in open(ROOT / cfg["corpus"]["chunks"], encoding="utf-8")]
    chunk_idx = {c["chunk_id"]: c for c in chunks}
    records = load_records(ROOT / cfg["corpus"]["table_records"])
    def tokenize(text: str) -> list[str]:
        toks = tokenize_vi(normalize_query(text))
        return [t for t in toks if t not in stopwords and len(t) > 1]
    tokenized_docs = [tokenize(c["text"]) for c in chunks]
    bm25 = BM25Retriever(k1=float(cfg["retrieval"].get("bm25_k1", 1.5)), b=float(cfg["retrieval"].get("bm25_b", 0.75))).fit(tokenized_docs)
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import Normalizer
    doc_texts = [" ".join(t) for t in tokenized_docs]
    ngram = tuple(e1_cfg["model"].get("ngram_range", [1, 2]))
    vectorizer = TfidfVectorizer(tokenizer=str.split, preprocessor=None, lowercase=False, ngram_range=ngram, sublinear_tf=True, min_df=2, norm="l2")
    X_tfidf = vectorizer.fit_transform(doc_texts)
    n_comp = min(int(e1_cfg["model"].get("svd_components", 128)), X_tfidf.shape[0] - 1, X_tfidf.shape[1])
    svd = TruncatedSVD(n_components=n_comp, random_state=42, algorithm="randomized")
    X_dense = Normalizer(copy=False).fit_transform(svd.fit_transform(X_tfidf))
    normalizer = Normalizer(copy=False)
    gold = [json.loads(line) for line in open(args.gold, encoding="utf-8")]
    fields = ["question_id", "question", "split", "gold_answer", "gold_chunk_ids", "predicted_chunk_ids", "predicted_top1_chunk_id", "predicted_company", "predicted_year", "predicted_report_version", "predicted_page", "predicted_n_tables", "retrieval_score_top1", "predicted_answer"]
    by_split: dict[str, list[dict]] = {"dev": [], "test": []}
    def hybrid_topk(q_toks: list[str], tickers: list[str], years: list[str]):
        bm25_scores = bm25.score(q_toks)
        q_vec = normalizer.transform(svd.transform(vectorizer.transform([" ".join(q_toks)])))
        dense_scores = (X_dense @ q_vec[0]).tolist()
        br = sorted(range(len(chunks)), key=lambda i: bm25_scores[i], reverse=True)[:cand_k]
        dr = sorted(range(len(chunks)), key=lambda i: dense_scores[i], reverse=True)[:cand_k]
        cand = list(dict.fromkeys(br + dr))
        bn = minmax([bm25_scores[i] for i in cand]); dn = minmax([dense_scores[i] for i in cand])
        fused = []
        for j, i in enumerate(cand):
            c = chunks[i]
            s = (1 - alpha) * bn[j] + alpha * dn[j]
            if tickers or years:
                cm = (not tickers) or (c.get("company_id") in tickers)
                ym = (not years) or (str(c.get("fiscal_year")) in years)
                if cm and ym: s += bonus
                elif cm or ym: s += bonus / 2
            fused.append((s, i))
        fused.sort(key=lambda x: x[0], reverse=True)
        return fused
    for g in gold:
        q = g["question"]
        q_toks = tokenize(q)
        synth = synthesize_answer(
            q,
            records,
            min_score=min_score,
            extra_refusal_patterns=patterns,
            refusal_text=refusal_text,
        )
        tickers, years = synth["tickers"], synth["years"]
        fused = hybrid_topk(q_toks, tickers, years)
        ranked = [i for _, i in fused[:save_k]]
        hybrid_top = max(0.0, min(1.0, float(fused[0][0]))) if fused else 0.0
        ev_cids = [] if synth["refused"] else list(synth["evidence_chunk_ids"])
        if ev_cids:
            ordered = list(ev_cids)
            for c in [chunks[i] for i in ranked]:
                if c["chunk_id"] not in ordered:
                    ordered.append(c["chunk_id"])
            pred_ids = ordered[:save_k]
            top_chunks = [chunk_idx[cid] for cid in pred_ids if cid in chunk_idx]
            top1 = top_chunks[0] if top_chunks else {}
            score_top = max(0.0, min(1.0, float(synth["lookup_score"] or hybrid_top)))
        else:
            top_chunks = [chunks[i] for i in ranked]
            top1 = top_chunks[0] if top_chunks else {}
            score_top = hybrid_top
        answer = synth["answer"]
        pred_company = synth["predicted_company"] if (not synth["refused"] and synth["predicted_company"]) else top1.get("company_id", "")
        pred_year = synth["predicted_year"] if (not synth["refused"] and synth["predicted_year"]) else top1.get("fiscal_year", "")
        pred_ver = synth["predicted_report_version"] if (not synth["refused"] and synth["predicted_report_version"]) else top1.get("report_version", "")
        pred_page = synth["predicted_page"] if (not synth["refused"] and synth["predicted_page"] != "") else top1.get("page", "")
        row = {
            "question_id": g["question_id"],
            "question": q,
            "split": g.get("split", ""),
            "gold_answer": g.get("gold_answer", ""),
            "gold_chunk_ids": ";".join(e["chunk_id"] for e in g.get("evidence", [])),
            "predicted_chunk_ids": ";".join(c["chunk_id"] for c in top_chunks),
            "predicted_top1_chunk_id": top1.get("chunk_id", ""),
            "predicted_company": pred_company,
            "predicted_year": pred_year,
            "predicted_report_version": pred_ver,
            "predicted_page": pred_page,
            "predicted_n_tables": top1.get("n_tables", ""),
            "retrieval_score_top1": f"{score_top:.4f}",
            "predicted_answer": answer,
        }
        by_split.setdefault(g.get("split", "test"), []).append(row)
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    for split in ("dev", "test"):
        subdir = outdir / ("dev_predictions" if split == "dev" else "test_predictions")
        subdir.mkdir(parents=True, exist_ok=True)
        out = subdir / f"{split}_predictions_E8.csv"
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(by_split.get(split, []))
        print(f"Da ghi {len(by_split.get(split, []))} dong {split} -> {out}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
