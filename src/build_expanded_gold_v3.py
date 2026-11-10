"""Mo rong gold v2 (127 cau) len v3 (200 cau): giu 127 cu + them 73 sach.

Them: T1 +26, T2 +22, T3 +21, T5 +4. Loc strict giong v2,
T2/T3 tu tinh chenh lech tu table_records, ID moi dung hau to B de tranh trung.
Split v3: giu split cu, them 15 cau tra loi duoc vao dev (25->40),
con lai vao test (102->160, gom 16 cau thieu bang chung).
"""
from __future__ import annotations
import csv, hashlib, json, random, re, sys
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
ANNOT = ROOT / "data" / "annotations"
PROC = ROOT / "data" / "processed"
SPLITS = ROOT / "data" / "splits"
CNAMES = {
    "HPG": "CTCP Tập đoàn Hòa Phát",
    "HSG": "CTCP Tập đoàn Hoa Sen",
    "NKG": "CTCP Thép Nam Kim",
    "MSR": "CTCP Masan High-Tech Materials",
}
REFUSAL = "Không đủ bằng chứng trong corpus để trả lời."
EN = re.compile(r"[A-Za-z]{3,}")
BAD = [
    "mang sang", "chuyen sang", "dieu chinh", "kể toán",
    "biến động", "biến đông", "goc ngoai",
    "(60 =", "(50 =", "(30 =", "(10 =",
]
FACTOR = {
    "nghìn tỷ đồng": 1e12, "trăm tỷ đồng": 1e11, "tỷ đồng": 1e9,
    "triệu đồng": 1e6, "nghìn đồng": 1e3, "đồng": 1, "%": 1, "": 1,
}
YEARS = {2020, 2021, 2022, 2023, 2024}

def to_vnd(v, u):
    return float(v or 0) * FACTOR.get((u or "").strip(), 1)

def pick(v):
    a = abs(float(v or 0))
    if a >= 1e12:
        return "nghìn tỷ đồng", round(float(v) / 1e12, 4)
    if a >= 1e9:
        return "tỷ đồng", round(float(v) / 1e9, 4)
    if a >= 1e6:
        return "triệu đồng", round(float(v) / 1e6, 4)
    return "đồng", round(float(v), 4)

def clean_metric(t):
    t = " ".join((t or "").split())
    if t.startswith("("):
        d = 0
        for i, ch in enumerate(t):
            if ch == "(":
                d += 1
            elif ch == ")":
                d -= 1
                if d == 0:
                    r = t[i + 1:].strip(" /-:;,.\\")
                    t = r if r else t
                    break
    cut = len(t)
    for s in ("(\\(", "(( ", "((( ", " ("):
        j = t.find(s)
        if j > 0:
            cut = min(cut, j)
    return " ".join(t[:cut].strip(" -:;,.\\").split())

def norm_name(m):
    t = clean_metric(m)
    t = t.replace("Chỉ phí", "Chi phí").replace("thuân", "thuần")
    return " ".join(t.split())

def is_clean(r):
    m = str(r.get("metric", ""))
    if EN.search(m):
        return False
    low = m.lower()
    for b in BAD:
        if b in low:
            return False
    if len(m.strip()) < 4:
        return False
    if "cổ phiếu" in low or "cơ bản" in low:
        return False
    if "PHÀI" in m or "TRÀ" in m:
        return False
    if m.strip() == m.strip().upper() and re.search(r"[A-ZÀ-Ỹ]{3,}", m):
        return False
    if not str(r.get("metric_code", "")).strip():
        return False
    try:
        y = int(r.get("year", 0))
    except (TypeError, ValueError):
        return False
    return y in YEARS

recs = [json.loads(l) for l in open(PROC / "table_records.jsonl", encoding="utf-8")]
pool = [
    r for r in recs
    if r.get("statement") in ("income_statement", "balance_sheet")
    and r.get("report_version") == "consolidated"
    and float(r.get("confidence", 0) or 0) >= 0.9
    and is_clean(r)
]
print(f"clean pool: {len(pool)}")
gold = [json.loads(l) for l in open(ANNOT / "qa_gold.jsonl", encoding="utf-8")]
print(f"base gold: {len(gold)}")
used_q = {" ".join(q["question"].lower().split()) for q in gold}
used_ids = {q["question_id"] for q in gold}

seen = set()
uniq = []
for r in sorted(pool, key=lambda r: (str(r["company"]), str(r["metric"]), int(r["year"]))):
    k = (str(r["company"]).upper(), norm_name(r["metric"]), int(r["year"]), r["source_chunk_id"])
    if k in seen:
        continue
    seen.add(k)
    uniq.append(r)
pool = uniq
print(f"uniq pool: {len(pool)}")

# thu thap metric da dung de tranh lap lai
used_t1_metric = set()
used_pair_keys = set()
for g in gold:
    if g.get("source") != "table-clean":
        continue
    qid = g.get("question_id", "")
    q = g.get("question", "")
    if qid.startswith("CLEAN-T1-"):
        mp = q.split(" hợp nhất")[0].strip()
        used_t1_metric.add((g.get("company_id"), mp))
    elif qid.startswith("CLEAN-T2-") or qid.startswith("CLEAN-T3-"):
        mp = q.split(" hợp nhất")[0].replace("Chênh lệch ", "").strip()
        ev = g.get("evidence") or []
        ch = ev[0].get("chunk_id") if ev else ""
        used_pair_keys.add((g.get("company_id"), mp, ch))

# T1 moi: +26
t1pool = [r for r in pool if int(r.get("fiscal_year", 0)) == int(r.get("year", -1))]
by_comp: dict[str, list] = {}
for r in t1pool:
    # bo metric da dung o v2 de da dang
    m = norm_name(r["metric"])
    comp = str(r["company"]).upper()
    if (comp, m) in used_t1_metric:
        continue
    # bo cau hoi trung
    is_bal = "balance" in str(r.get("statement", ""))
    year = int(r["year"])
    vnd = to_vnd(r["value"], r["unit"])
    ut, vc = pick(vnd)
    when = f"tại ngày 31/12/{year}" if is_bal else f"năm {year}"
    q = f"{m} hợp nhất của {CNAMES[comp]} {when} là bao nhiêu {ut}?"
    if " ".join(q.lower().split()) in used_q:
        continue
    by_comp.setdefault(comp, []).append(r)
for comp in by_comp:
    by_comp[comp].sort(key=lambda r: (0 if r["statement"] == "income_statement" else 1, norm_name(r["metric"])))
order = sorted(by_comp)
t1 = []
guard = 0
idx = 0
NEED_T1 = 26
while len(t1) < NEED_T1 and guard < NEED_T1 * 80 + 1200:
    guard += 1
    comp = order[idx % len(order)]
    idx += 1
    lst = by_comp.get(comp, [])
    if not lst:
        continue
    r = lst.pop(0)
    m = norm_name(r["metric"])
    if (comp, m) in used_t1_metric:
        continue
    used_t1_metric.add((comp, m))
    year = int(r["year"])
    vnd = to_vnd(r["value"], r["unit"])
    ut, vc = pick(vnd)
    is_bal = "balance" in str(r.get("statement", ""))
    when = f"tại ngày 31/12/{year}" if is_bal else f"năm {year}"
    q = f"{m} hợp nhất của {CNAMES[comp]} {when} là bao nhiêu {ut}?"
    if " ".join(q.lower().split()) in used_q:
        continue
    used_q.add(" ".join(q.lower().split()))
    qid = f"CLEAN-T1-{comp}-{year}-B{len(t1) + 1:02d}"
    assert qid not in used_ids, qid
    used_ids.add(qid)
    t1.append({
        "question_id": qid,
        "question": q,
        "gold_answer": f"{vc} {ut}",
        "answer_type": "numeric", "value": vc, "unit": ut,
        "company_id": comp, "fiscal_year": year,
        "report_id": f"{comp}_{year}_consolidated",
        "evidence": [{"chunk_id": r["source_chunk_id"], "source_page": r["page"],
                      "quote": f"{r['metric']} | {r['value_raw']}"}],
        "computation": f"{r['value_raw']} {r['unit']} = {vnd:,.0f} VND = {vc} {ut}.",
        "source_page": r["page"], "needs_more_evidence": False,
        "reviewer_id": "auto-builder", "review_status": "draft-needs-second-reviewer",
        "source": "table-clean", "split": "test",
    })
print(f"T1 new: {len(t1)}")

# T2/T3 chung: cap cung (cong ty, metric, chunk) co >= 2 nam
by_key: dict[tuple, dict[int, dict]] = {}
for r in pool:
    by_key.setdefault(
        (str(r["company"]).upper(), norm_name(r["metric"]), r["source_chunk_id"]),
        {},
    )[int(r["year"])] = r
pairs = [(k, v) for k, v in by_key.items() if len(v) >= 2]
# loai cap da dung o v2
pairs = [(k, v) for k, v in pairs if k not in used_pair_keys]
pairs.sort(key=lambda kv: (kv[0][0], kv[0][1]))
comp_pairs: dict[str, list] = {}
for (comp, m, ch), ym in pairs:
    comp_pairs.setdefault(comp, []).append(((comp, m, ch), ym))
corder = sorted(comp_pairs)
t2 = []
ci = 0
g2 = 0
NEED_T2 = 22
while len(t2) < NEED_T2 and g2 < NEED_T2 * 40 + 1200:
    g2 += 1
    cc = corder[ci % len(corder)]
    ci += 1
    lst = comp_pairs.get(cc, [])
    if not lst:
        continue
    (comp, m, ch), ym = lst.pop(0)
    ys = sorted(ym)
    y1, y2 = ys[0], ys[-1]
    if y1 == y2:
        continue
    r1, r2 = ym[y1], ym[y2]
    q = (f"{m} hợp nhất của {CNAMES[comp]} năm {y2} tăng hay giảm bao nhiêu "
         f"so với năm {y1} (cùng đơn vị báo cáo)?")
    if " ".join(q.lower().split()) in used_q:
        continue
    v1 = to_vnd(r1["value"], r1["unit"])
    v2 = to_vnd(r2["value"], r2["unit"])
    d = v2 - v1
    ut, vc = pick(d)
    used_q.add(" ".join(q.lower().split()))
    used_pair_keys.add((comp, m, ch))
    qid = f"CLEAN-T2-{comp}-{y1}-{y2}-B{len(t2) + 1:02d}"
    assert qid not in used_ids, qid
    used_ids.add(qid)
    t2.append({
        "question_id": qid,
        "question": q, "gold_answer": f"{vc} {ut}",
        "answer_type": "computation", "value": vc, "unit": ut,
        "company_id": comp, "fiscal_year": f"{y1}|{y2}", "report_id": "",
        "evidence": [
            {"chunk_id": ch, "source_page": r1["page"], "quote": f"{r1['metric']} | {r1['value_raw']}"},
            {"chunk_id": ch, "source_page": r2["page"], "quote": f"{r2['metric']} | {r2['value_raw']}"},
        ],
        "computation": (f"{r2['value_raw']} {r2['unit']} ({v2:,.0f} VND) - "
                        f"{r1['value_raw']} {r1['unit']} ({v1:,.0f} VND) = {d:,.0f} VND = {vc} {ut}."),
        "source_page": r2["page"], "needs_more_evidence": False,
        "reviewer_id": "auto-builder", "review_status": "draft-needs-second-reviewer",
        "source": "table-clean", "split": "test",
    })
print(f"T2 new: {len(t2)}")

# T3: dung phan con lai, tranh khoa T2 moi
t2keys = set((r["company_id"], r["question"].split(" hợp nhất")[0], r["evidence"][0]["chunk_id"]) for r in t2)
pairs3 = [(k, v) for k, v in by_key.items() if len(v) >= 2 and k not in used_pair_keys]
# loai them khoa trung ten metric voi T2 moi (phong trung cau hoi dao ngu)
pairs3.sort(key=lambda kv: (kv[0][0], kv[0][1]))
cp3: dict[str, list] = {}
for (comp, m, ch), ym in pairs3:
    if (comp, m, ch) in t2keys:
        continue
    cp3.setdefault(comp, []).append(((comp, m, ch), ym))
corder3 = sorted(cp3)
t3 = []
ci3 = 0
g3 = 0
NEED_T3 = 21
while len(t3) < NEED_T3 and g3 < NEED_T3 * 50 + 1600:
    g3 += 1
    cc = corder3[ci3 % len(corder3)]
    ci3 += 1
    lst = cp3.get(cc, [])
    if not lst:
        continue
    (comp, m, ch), ym = lst.pop(0)
    ys = sorted(ym)
    y1, y2 = ys[0], ys[-1]
    if y1 == y2:
        continue
    r1, r2 = ym[y1], ym[y2]
    q = (f"Chênh lệch {m} hợp nhất của {CNAMES[comp]} giữa năm {y2} "
         f"và năm {y1} là bao nhiêu (quy về cùng đơn vị)?")
    if " ".join(q.lower().split()) in used_q:
        continue
    v1 = to_vnd(r1["value"], r1["unit"])
    v2 = to_vnd(r2["value"], r2["unit"])
    d = v2 - v1
    ut, vc = pick(d)
    used_q.add(" ".join(q.lower().split()))
    used_pair_keys.add((comp, m, ch))
    qid = f"CLEAN-T3-{comp}-{y1}-{y2}-B{len(t3) + 1:02d}"
    assert qid not in used_ids, qid
    used_ids.add(qid)
    t3.append({
        "question_id": qid,
        "question": q, "gold_answer": f"{vc} {ut}",
        "answer_type": "computation", "value": vc, "unit": ut,
        "company_id": comp, "fiscal_year": f"{y1}|{y2}", "report_id": "",
        "evidence": [
            {"chunk_id": ch, "source_page": r1["page"], "quote": f"{r1['metric']} | {r1['value_raw']}"},
            {"chunk_id": ch, "source_page": r2["page"], "quote": f"{r2['metric']} | {r2['value_raw']}"},
        ],
        "computation": (f"{r2['value_raw']} {r2['unit']} ({v2:,.0f} VND) - "
                        f"{r1['value_raw']} {r1['unit']} ({v1:,.0f} VND) = {d:,.0f} VND = {vc} {ut}."),
        "source_page": r2["page"], "needs_more_evidence": False,
        "reviewer_id": "auto-builder", "review_status": "draft-needs-second-reviewer",
        "source": "table-clean", "split": "test",
    })
print(f"T3 new: {len(t3)}")

t5 = [
    {"question_id": "CLEAN-T5-HPG-2025-05",
     "question": "Kế hoạch doanh thu năm 2025 của CTCP Tập đoàn Hòa Phát là bao nhiêu nghìn tỷ đồng?",
     "company_id": "HPG", "fiscal_year": "2025",
     "unanswerable_reason": "Corpus chỉ gồm báo cáo 2020-2024, không có kế hoạch 2025."},
    {"question_id": "CLEAN-T5-HSG-2025-06",
     "question": "Cổ tức năm 2024 của CTCP Tập đoàn Hoa Sen là bao nhiêu đồng một cổ phiếu?",
     "company_id": "HSG", "fiscal_year": "2024",
     "unanswerable_reason": "Báo cáo tài chính năm không công bố cổ tức trên mỗi cổ phiếu."},
    {"question_id": "CLEAN-T5-NKG-2024-07",
     "question": "Báo cáo quý 1 năm 2024 của CTCP Thép Nam Kim ghi nhận lợi nhuận sau thuế bao nhiêu tỷ đồng?",
     "company_id": "NKG", "fiscal_year": "2024",
     "unanswerable_reason": "Corpus chỉ gồm báo cáo năm, không có báo cáo quý."},
    {"question_id": "CLEAN-T5-MSR-2025-08",
     "question": "Dự báo giá đồng năm 2025 của CTCP Masan High-Tech Materials là bao nhiêu USD một tấn?",
     "company_id": "MSR", "fiscal_year": "2025",
     "unanswerable_reason": "Báo cáo tài chính không công bố dự báo giá hàng hóa."},
]
for c in t5:
    assert c["question_id"] not in used_ids, c["question_id"]
    assert " ".join(c["question"].lower().split()) not in used_q
    used_q.add(" ".join(c["question"].lower().split()))
    used_ids.add(c["question_id"])
    c.update({"gold_answer": REFUSAL, "answer_type": "unanswerable",
              "value": "", "unit": "", "report_id": "", "evidence": [],
              "computation": "", "source_page": "", "needs_more_evidence": True,
              "reviewer_id": "auto-builder", "review_status": "draft-needs-second-reviewer",
              "source": "table-clean", "split": "test"})
new = t1 + t2 + t3 + t5
print(f"new total: {len(new)} (T1 {len(t1)} T2 {len(t2)} T3 {len(t3)} T5 {len(t5)})")
assert len(new) == 73, f"can 73 cau moi, hien co {len(new)}"
all_recs = gold + new
print(f"grand total: {len(all_recs)}")

# split v3: giu split cu, them 15 cau tra loi duoc vao dev
old_dev = {r["question_id"] for r in gold if r.get("split") == "dev"}
new_answerable = [r for r in new if not r["needs_more_evidence"]]
new_unanswer = [r for r in new if r["needs_more_evidence"]]
rng = random.Random(42 + 3)
rng.shuffle(new_answerable)
add_dev = {r["question_id"] for r in new_answerable[:15]}
for r in new:
    if r["needs_more_evidence"]:
        r["split"] = "test"
    elif r["question_id"] in add_dev:
        r["split"] = "dev"
    else:
        r["split"] = "test"
dev = [r for r in all_recs if r["split"] == "dev"]
test = [r for r in all_recs if r["split"] == "test"]
print(f"dev {len(dev)} test {len(test)} (target 40/160)")

import shutil
shutil.copy(ANNOT / "qa_gold.jsonl", ANNOT / "qa_gold_v2_127.jsonl")
with open(ANNOT / "qa_gold.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for r in all_recs:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

LF = ["question_id", "question", "company_id", "fiscal_year", "unit", "answer_type", "source"]
with open(ANNOT / "gold_labels.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=LF)
    w.writeheader()
    for r in all_recs:
        w.writerow({k: r.get(k, "") for k in LF})

with open(ANNOT / "review_log.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["item_id", "gold", "reviewer", "status",
                                      "guideline_version", "disagreement_note"])
    w.writeheader()
    for r in all_recs:
        st = r.get("review_status", "")
        w.writerow({
            "item_id": r["question_id"], "gold": r["gold_answer"],
            "reviewer": r.get("reviewer_id", ""),
            "status": "needs-second-reviewer" if st.startswith("draft") else st,
            "guideline_version": "v0.2",
            "disagreement_note": "mo rong gold v3, can hau kiem" if r in new else (r.get("disagreement_note", "") if isinstance(r.get("disagreement_note"), str) else ""),
        })
SPLITS.mkdir(parents=True, exist_ok=True)
with open(SPLITS / "dev.json", "w", encoding="utf-8") as f:
    json.dump(sorted(r["question_id"] for r in dev), f, ensure_ascii=False, indent=2)
with open(SPLITS / "test.json", "w", encoding="utf-8") as f:
    json.dump(sorted(r["question_id"] for r in test), f, ensure_ascii=False, indent=2)
meta = {"version": "v3", "seed": 42, "n_dev": len(dev), "n_test": len(test),
        "dev_ids": sorted(r["question_id"] for r in dev),
        "test_ids": sorted(r["question_id"] for r in test),
        "rule": "16 cau thieu bang chung deu nam o test; dev gom 40 cau tra loi duoc; giu split v2, them 15 cau moi vao dev"}
meta_text = json.dumps(meta, ensure_ascii=False, sort_keys=True)
meta["sha256"] = hashlib.sha256(meta_text.encode("utf-8")).hexdigest()
with open(SPLITS / "split_meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
json.dump(meta, open("evaluation/split_freeze.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"dev {len(dev)} test {len(test)} unanswer {sum(1 for r in all_recs if r['needs_more_evidence'])} sha {meta['sha256'][:16]}")
