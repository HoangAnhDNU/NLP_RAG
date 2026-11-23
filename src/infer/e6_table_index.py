"""E6: index rieng noi dung bang, ket hop full-text (khong tai model ngoai)."""
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
from src.retrieval.pipeline_two_stage import detect_meta_extended, minmax, table_only_text  # noqa: E402
def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
def main() -> int:
    p = argparse.ArgumentParser(description="Chay E6 table index.")
    p.add_argument("--config", default=str(ROOT / "config" / "e6_table_index.yaml"))
    p.add_argument("--gold", default=str(ROOT / "data" / "annotations" / "qa_gold.jsonl"))
    p.add_argument("--outdir", default=str(ROOT / "evaluation"))
    args = p.parse_args()
    cfg = load_config(Path(args.config))
    top_k = int(cfg["retrieval"]["top_k"]); cand_k = int(cfg["retrieval"].get("candidate_k", 20))
    alpha = float(cfg["retrieval"].get("fusion_alpha", 0.5)); bonus = float(cfg["retrieval"].get("metadata_bonus", 0.15))
    wf = float(cfg["retrieval"].get("full_bm25_weight", 0.7)); wt = float(cfg["retrieval"].get("table_bm25_weight", 0.3))
    refusal_text = cfg["refusal"]["text"]; patterns = [s.lower() for s in cfg["refusal"].get("patterns", [])]
    e0_cfg = load_config(ROOT / "config" / "e0_bm25.yaml"); stopwords = set(e0_cfg.get("stopwords", []))
    e1_cfg = load_config(ROOT / cfg["model"]["dense_source"])
    chunks = [json.loads(line) for line in open(ROOT / cfg["corpus"]["chunks"], encoding="utf-8")]
    def tokenize(text: str) -> list[str]:
        toks = tokenize_vi(normalize_query(text))
        return [t for t in toks if t not in stopwords and len(t) > 1]
    tokenized_docs = [tokenize(c["text"]) for c in chunks]
    table_docs = [tokenize(table_only_text(c) or c["text"][:200]) for c in chunks]
    bm25_full = BM25Retriever(k1=float(cfg["retrieval"].get("bm25_k1", 1.5)), b=float(cfg["retrieval"].get("bm25_b", 0.75))).fit(tokenized_docs)
    bm25_tab = BM25Retriever(k1=float(cfg["retrieval"].get("bm25_k1", 1.5)), b=float(cfg["retrieval"].get("bm25_b", 0.75))).fit(table_docs)
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
    for g in gold:
        q_toks = tokenize(g["question"])
        bf = bm25_full.score(q_toks); bt = bm25_tab.score(q_toks)
        bm25_scores = [wf * a + wt * b for a, b in zip(bf, bt)]
        q_vec = normalizer.transform(svd.transform(vectorizer.transform([" ".join(q_toks)])))
        dense_scores = (X_dense @ q_vec[0]).tolist()
        bm25_rank = sorted(range(len(chunks)), key=lambda i: bm25_scores[i], reverse=True)[:cand_k]
        dense_rank = sorted(range(len(chunks)), key=lambda i: dense_scores[i], reverse=True)[:cand_k]
        cand = list(dict.fromkeys(bm25_rank + dense_rank))
        b_norm = minmax([bm25_scores[i] for i in cand]); d_norm = minmax([dense_scores[i] for i in cand])
        meta = detect_meta_extended(g["question"]); tickers, years = meta["tickers"], meta["years"]
        fused = []
        for j, i in enumerate(cand):
            c = chunks[i]
            s = (1 - alpha) * b_norm[j] + alpha * d_norm[j]
            if tickers or years:
                cm = (not tickers) or (c.get("company_id") in tickers)
                ym = (not years) or (str(c.get("fiscal_year")) in years)
                if cm and ym: s += bonus
                elif cm or ym: s += bonus / 2
            fused.append((s, i))
        fused.sort(key=lambda x: x[0], reverse=True)
        save_k = max(top_k, 10)
        ranked = [i for _, i in fused[:save_k]]
        top_chunks = [chunks[i] for i in ranked]; top1 = top_chunks[0] if top_chunks else {}
        refused = any(pat in g["question"].lower() for pat in patterns)
        row = {"question_id": g["question_id"], "question": g["question"], "split": g.get("split", ""), "gold_answer": g.get("gold_answer", ""), "gold_chunk_ids": ";".join(e["chunk_id"] for e in g.get("evidence", [])), "predicted_chunk_ids": ";".join(c["chunk_id"] for c in top_chunks), "predicted_top1_chunk_id": top1.get("chunk_id", ""), "predicted_company": top1.get("company_id", ""), "predicted_year": top1.get("fiscal_year", ""), "predicted_report_version": top1.get("report_version", ""), "predicted_page": top1.get("page", ""), "predicted_n_tables": top1.get("n_tables", ""), "retrieval_score_top1": f"{fused[0][0]:.4f}" if fused else "0.0000", "predicted_answer": refusal_text if refused else ""}
        by_split.setdefault(g.get("split", "test"), []).append(row)
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    for split in ("dev", "test"):
        subdir = outdir / ("dev_predictions" if split == "dev" else "test_predictions")
        subdir.mkdir(parents=True, exist_ok=True)
        out = subdir / f"{split}_predictions_E6.csv"
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(by_split.get(split, []))
        print(f"Da ghi {len(by_split.get(split, []))} dong {split} -> {out}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
