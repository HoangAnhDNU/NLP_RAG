"""Dung gold mo rong sach thay bo 50 cau: giu 50 cu + them T1/T2/T3/T5 sach."""
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
used_q = {" ".join(q["question"].lower().split()) for q in gold}

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

# T1: chi lay cot nam hien hanh (fiscal_year == year), round-robin 4 cong ty
t1pool = [r for r in pool if int(r.get("fiscal_year", 0)) == int(r.get("year", -1))]
by_comp: dict[str, list] = {}
for r in t1pool:
    by_comp.setdefault(str(r["company"]).upper(), []).append(r)
for comp in by_comp:
    by_comp[comp].sort(key=lambda r: (0 if r["statement"] == "income_statement" else 1, norm_name(r["metric"])))
order = sorted(by_comp)
used_metric = set()
t1 = []
guard = 0
idx = 0
NEED_T1 = 29
while len(t1) < NEED_T1 and guard < NEED_T1 * 60 + 800:
    guard += 1
    comp = order[idx % len(order)]
    idx += 1
    lst = by_comp.get(comp, [])
    if not lst:
        continue
    r = lst.pop(0)
    m = norm_name(r["metric"])
    if (comp, m) in used_metric:
        continue
    used_metric.add((comp, m))
    year = int(r["year"])
    vnd = to_vnd(r["value"], r["unit"])
    ut, vc = pick(vnd)
    is_bal = "balance" in str(r.get("statement", ""))
    when = f"tại ngày 31/12/{year}" if is_bal else f"năm {year}"
    q = f"{m} hợp nhất của {CNAMES[comp]} {when} là bao nhiêu {ut}?"
    if " ".join(q.lower().split()) in used_q:
        continue
    used_q.add(" ".join(q.lower().split()))
    t1.append({
        "question_id": f"CLEAN-T1-{comp}-{year}-{len(t1) + 1:02d}",
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
print(f"T1: {len(t1)}")

# T2/T3: cap cung (cong ty, metric, chunk) co >= 2 nam trong 2020-2024
by_key: dict[tuple, dict[int, dict]] = {}
for r in pool:
    by_key.setdefault(
        (str(r["company"]).upper(), norm_name(r["metric"]), r["source_chunk_id"]),
        {},
    )[int(r["year"])] = r
pairs = [(k, v) for k, v in by_key.items() if len(v) >= 2]
pairs.sort(key=lambda kv: (kv[0][0], kv[0][1]))
comp_pairs: dict[str, list] = {}
for (comp, m, ch), ym in pairs:
    comp_pairs.setdefault(comp, []).append(((comp, m, ch), ym))
corder = sorted(comp_pairs)
t2 = []
ci = 0
g2 = 0
NEED = 22
while len(t2) < NEED and g2 < NEED * 30 + 800:
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
    t2.append({
        "question_id": f"CLEAN-T2-{comp}-{y1}-{y2}-{len(t2) + 1:02d}",
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
print(f"T2: {len(t2)}")

t2keys = set()
for r in t2:
    mp = r["question"].split(" hợp nhất")[0]
    ch = r["evidence"][0]["chunk_id"]
    t2keys.add((r["company_id"], mp, ch))
by_key2: dict[tuple, dict[int, dict]] = {}
for r in pool:
    by_key2.setdefault(
        (str(r["company"]).upper(), norm_name(r["metric"]), r["source_chunk_id"]),
        {},
    )[int(r["year"])] = r
pairs2 = [(k, v) for k, v in by_key2.items() if len(v) >= 2]
pairs2.sort(key=lambda kv: (kv[0][0], kv[0][1]))
cp3: dict[str, list] = {}
for (comp, m, ch), ym in pairs2:
    if (comp, m, ch) in t2keys:
        continue
    cp3.setdefault(comp, []).append(((comp, m, ch), ym))
corder3 = sorted(cp3)
t3 = []
ci3 = 0
g3 = 0
while len(t3) < NEED and g3 < NEED * 40 + 1200:
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
    t3.append({
        "question_id": f"CLEAN-T3-{comp}-{y1}-{y2}-{len(t3) + 1:02d}",
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
print(f"T3: {len(t3)}")

t5 = [
    {"question_id": "CLEAN-T5-HPG-2024-01",
     "question": "Cổ tức tiền mặt năm 2024 của CTCP Tập đoàn Hòa Phát là bao nhiêu đồng một cổ phiếu?",
     "company_id": "HPG", "fiscal_year": "2024",
     "unanswerable_reason": "Corpus chỉ gồm báo cáo tài chính năm, không có dữ liệu cổ tức, giá thị trường hay báo cáo quý."},
    {"question_id": "CLEAN-T5-HSG-2024-02",
     "question": "Báo cáo quý 3 năm 2024 của CTCP Tập đoàn Hoa Sen ghi nhận doanh thu thuần bao nhiêu tỷ đồng?",
     "company_id": "HSG", "fiscal_year": "2024",
     "unanswerable_reason": "Corpus chỉ gồm báo cáo tài chính năm, không có báo cáo quý."},
    {"question_id": "CLEAN-T5-NKG-2024-03",
     "question": "Xếp hạng tín nhiệm năm 2024 của CTCP Thép Nam Kim là mức nào?",
     "company_id": "NKG", "fiscal_year": "2024",
     "unanswerable_reason": "Báo cáo tài chính không công bố xếp hạng tín nhiệm."},
    {"question_id": "CLEAN-T5-MSR-2024-04",
     "question": "Giá vonfram bình quân năm 2024 của CTCP Masan High-Tech Materials là bao nhiêu USD một tấn?",
     "company_id": "MSR", "fiscal_year": "2024",
     "unanswerable_reason": "Báo cáo tài chính không công bố giá bán vonfram theo USD."},
]
for c in t5:
    c.update({"gold_answer": REFUSAL, "answer_type": "unanswerable",
              "value": "", "unit": "", "report_id": "", "evidence": [],
              "computation": "", "source_page": "", "needs_more_evidence": True,
              "reviewer_id": "auto-builder", "review_status": "draft-needs-second-reviewer",
              "source": "table-clean", "split": "test"})
new = t1 + t2 + t3 + t5
print(f"new total: {len(new)}")
all_recs = gold + new
print(f"grand total: {len(all_recs)} (50 cu + {len(new)} moi)")

answerable = [r for r in all_recs if not r["needs_more_evidence"]]
unanswer = [r for r in all_recs if r["needs_more_evidence"]]
rng = random.Random(42)
rng.shuffle(answerable)
dev = answerable[:25]
test = answerable[25:] + unanswer
rng.shuffle(test)
split_of = {r["question_id"]: "dev" for r in dev}
split_of.update({r["question_id"]: "test" for r in test})
for r in all_recs:
    r["split"] = split_of[r["question_id"]]

import shutil
shutil.copy(ANNOT / "qa_gold.jsonl", ANNOT / "qa_gold_v1_50.jsonl")
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
            "disagreement_note": "mo rong gold v2, can hau kiem" if r.get("source") == "table-clean" else "",
        })
SPLITS.mkdir(parents=True, exist_ok=True)
with open(SPLITS / "dev.json", "w", encoding="utf-8") as f:
    json.dump(sorted(r["question_id"] for r in dev), f, ensure_ascii=False, indent=2)
with open(SPLITS / "test.json", "w", encoding="utf-8") as f:
    json.dump(sorted(r["question_id"] for r in test), f, ensure_ascii=False, indent=2)
meta = {"version": "v2", "seed": 42, "n_dev": len(dev), "n_test": len(test),
        "dev_ids": sorted(r["question_id"] for r in dev),
        "test_ids": sorted(r["question_id"] for r in test),
        "rule": "12 cau thieu bang chung deu nam o test; dev gom 25 cau tra loi duoc"}
meta_text = json.dumps(meta, ensure_ascii=False, sort_keys=True)
meta["sha256"] = hashlib.sha256(meta_text.encode("utf-8")).hexdigest()
with open(SPLITS / "split_meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
json.dump(meta, open("evaluation/split_freeze.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"dev {len(dev)} test {len(test)} unanswer {len(unanswer)} sha {meta['sha256'][:16]}")
