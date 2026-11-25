"""Demo Streamlit hỏi đáp báo cáo tài chính có trích dẫn (Mục 6.1).

Pipeline RAG thuần, không đọc thuộc gold: nhận câu hỏi -> trích metadata
-> BM25 cộng điểm metadata trên 40 báo cáo -> lookup có cấu trúc trên
`table_records.jsonl` -> ghép top-k chunks thành CONTEXT có citation
-> bộ sinh đáp án offline chỉ dùng CONTEXT theo `config/answer_policy.yaml`
-> hiển thị đáp án kèm nguồn. Gold chỉ dùng offline để chấm điểm.

Giao diện áp dụng hệ thống thiết kế Financial Intelligence (Data-Dense Dashboard):
bảng màu Cobalt Navy / Slate / Amber, SVG icons nhất quán, focus rõ ràng,
tabular-nums cho số liệu tài chính và hỗ trợ prefers-reduced-motion.

Chạy:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover
    raise SystemExit("Chưa cài streamlit. Chạy: pip install streamlit pyyaml")

from qa_engine import answer, load_engine  # noqa: E402

GROUP_TITLES = {
    "verified": "Sinh từ pipeline RAG (S_NEW_01 – S_NEW_07)",
    "refusal": "Kiểm tra từ chối (S_NEW_08 – S_NEW_10)",
    "paraphrase": "Diễn đạt lại (Paraphrase)",
    "vifinqa": "Câu gốc ViFinQA (Bảng đối chiếu)",
}

GROUP_BADGE = {
    "verified": ("RAG Verified", "badge-blue"),
    "refusal": ("Refusal Test", "badge-amber"),
    "paraphrase": ("Paraphrase", "badge-teal"),
    "vifinqa": ("ViFinQA", "badge-slate"),
}

# SVG inline icons (Heroicons-style, stroke=1.85, aria-hidden="true")
ICONS = {
    "ledger": '<svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 16l4-4 4 4 6-6"/><path d="M17 10h4v4"/></svg>',
    "check": '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/></svg>',
    "shield": '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 4v5c0 5.25-3.5 9.74-8 11-4.5-1.26-8-5.75-8-11V7l8-4z"/><path d="m14.5 9.5-5 5"/><path d="m9.5 9.5 5 5"/></svg>',
    "alert": '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "doc": '<svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    "calc": '<svg aria-hidden="true" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="8" y1="12" x2="10" y2="12"/><line x1="14" y1="12" x2="16" y2="12"/><line x1="8" y1="17" x2="10" y2="17"/><line x1="14" y1="17" x2="16" y2="17"/></svg>',
}


def load_samples() -> list[dict]:
    path = ROOT / "app" / "sample_questions.jsonl"
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    for r in rows:
        qid = r.get("qid", "")
        if qid in ("S_NEW_01", "S_NEW_02", "S_NEW_03", "S_NEW_04", "S_NEW_05", "S_NEW_06", "S_NEW_07"):
            r["group"] = "verified"
        elif qid in ("S_NEW_08", "S_NEW_09", "S_NEW_10"):
            r["group"] = "refusal"
        elif qid.startswith("PARA"):
            r["group"] = "paraphrase"
        else:
            r["group"] = "vifinqa"
    order = {"verified": 0, "refusal": 1, "paraphrase": 2, "vifinqa": 3}
    rows.sort(key=lambda r: (order.get(r["group"], 9), r.get("qid", "")))
    return rows


def inject_design_system() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

        :root {
            color-scheme: light;
            --color-primary: #1E40AF;
            --color-primary-dark: #1E3A8A;
            --color-secondary: #3B82F6;
            --color-accent: #D97706;
            --color-bg: #F8FAFC;
            --color-surface: #FFFFFF;
            --color-muted: #E9EEF6;
            --color-text: #0F172A;
            --color-text-muted: #475569;
            --color-border: #CBD5E1;
            --color-border-soft: #DBEAFE;
            --color-success: #047857;
            --color-success-bg: #ECFDF5;
            --color-danger: #DC2626;
            --color-danger-bg: #FEF2F2;
            --color-warn-bg: #FFFBEB;
            --font-sans: 'Fira Sans', 'Inter', 'Segoe UI', system-ui, sans-serif;
            --font-mono: 'Fira Code', 'Consolas', monospace;
            --radius-md: 10px;
            --radius-sm: 6px;
        }

        html, body, [class*="css"] {
            color-scheme: light;
            font-family: var(--font-sans);
            color: var(--color-text);
            background-color: var(--color-bg);
        }

        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"] {
            background-color: var(--color-bg) !important;
            color: var(--color-text) !important;
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2.5rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 1240px;
            overflow-x: clip;
        }

        /* Sidebar refinement + light-theme enforcement */
        section[data-testid="stSidebar"] {
            background-color: var(--color-surface) !important;
            color: var(--color-text) !important;
            border-right: 1px solid var(--color-border-soft);
        }
        section[data-testid="stSidebar"] :is(h1, h2, h3, h4, p, span, label, li, strong, div[data-testid="stMarkdownContainer"]) {
            color: var(--color-text) !important;
        }
        section[data-testid="stSidebar"] :is(.stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *) {
            color: var(--color-text-muted) !important;
        }
        section[data-testid="stSidebar"] .stButton > button {
            width: 100%;
            text-align: left !important;
            justify-content: flex-start !important;
            background: var(--color-bg) !important;
            color: var(--color-text) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: var(--radius-sm);
            padding: 0.45rem 0.65rem;
            font-size: 0.83rem;
            font-weight: 500;
            line-height: 1.32;
            cursor: pointer;
            transition: background-color 150ms ease, border-color 150ms ease, color 150ms ease;
        }
        section[data-testid="stSidebar"] .stButton > button > div,
        section[data-testid="stSidebar"] .stButton > button p {
            width: 100%;
            text-align: left !important;
            white-space: normal !important;
            color: inherit !important;
            margin: 0 !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background-color: #EFF6FF !important;
            border-color: var(--color-secondary) !important;
            color: var(--color-primary-dark) !important;
        }

        /* Enforce light contrast across native Streamlit markdown, inputs, expanders, tabs & buttons */
        [data-testid="stMarkdownContainer"] > :is(p, h1, h2, h3, h4, ul, ol, blockquote) {
            color: var(--color-text) !important;
        }
        [data-testid="stMarkdownContainer"] > :is(p, ul, ol) :is(strong, em, span) {
            color: inherit !important;
        }
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] * {
            color: var(--color-text-muted) !important;
        }
        code,
        [data-testid="stMarkdownContainer"] code,
        section[data-testid="stSidebar"] code,
        .fi-meta-strip code,
        .fi-subtitle code {
            background-color: #F1F5F9 !important;
            color: #0F172A !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 4px;
            padding: 0.08rem 0.35rem;
            font-family: var(--font-mono);
            font-size: 0.85em;
        }
        [data-testid="stTextArea"] label,
        [data-testid="stTextArea"] label *,
        [data-testid="stTextInput"] label,
        [data-testid="stTextInput"] label *,
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] * {
            color: var(--color-text) !important;
        }
        [data-testid="stTextArea"] textarea,
        [data-testid="stTextInput"] input {
            background-color: var(--color-surface) !important;
            color: var(--color-text) !important;
            -webkit-text-fill-color: var(--color-text) !important;
            caret-color: var(--color-text) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: var(--radius-sm) !important;
        }
        [data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stTextInput"] input::placeholder {
            color: #64748B !important;
            -webkit-text-fill-color: #64748B !important;
            opacity: 1 !important;
        }
        [data-testid="stExpander"] {
            background-color: var(--color-surface) !important;
            color: var(--color-text) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: var(--radius-sm) !important;
        }
        [data-testid="stExpander"] summary {
            background-color: var(--color-bg) !important;
            color: var(--color-text) !important;
        }
        [data-testid="stExpander"] summary * {
            color: var(--color-text) !important;
        }
        [data-testid="stExpanderDetails"] {
            background-color: var(--color-surface) !important;
            color: var(--color-text) !important;
        }
        [data-testid="stTabs"] button[role="tab"] {
            color: var(--color-text-muted) !important;
            background: transparent !important;
        }
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: var(--color-primary) !important;
            font-weight: 600 !important;
        }
        [data-testid="stAlert"] {
            color: var(--color-text) !important;
        }
        [data-testid="stAlert"] p {
            color: var(--color-text) !important;
        }

        /* Main primary & secondary buttons + focus states */
        .stButton > button {
            cursor: pointer;
            border-radius: var(--radius-sm);
            white-space: normal !important;
            height: auto !important;
            min-height: 2.35rem;
            transition: background-color 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
        }
        .stButton > button[kind="secondary"],
        [data-testid="baseButton-secondary"] {
            background-color: var(--color-surface) !important;
            color: var(--color-text) !important;
            border: 1px solid var(--color-border) !important;
        }
        .stButton > button[kind="secondary"] *,
        [data-testid="baseButton-secondary"] * {
            color: var(--color-text) !important;
        }
        .stButton > button[kind="secondary"]:hover,
        [data-testid="baseButton-secondary"]:hover {
            background-color: #EFF6FF !important;
            border-color: var(--color-secondary) !important;
            color: var(--color-primary-dark) !important;
        }
        .stButton > button[kind="primary"],
        [data-testid="baseButton-primary"] {
            background-color: var(--color-primary) !important;
            color: #FFFFFF !important;
            border: 1px solid var(--color-primary-dark) !important;
        }
        .stButton > button[kind="primary"] *,
        [data-testid="baseButton-primary"] * {
            color: #FFFFFF !important;
        }
        .stButton > button[kind="primary"]:hover,
        [data-testid="baseButton-primary"]:hover {
            background-color: var(--color-primary-dark) !important;
        }
        .stButton > button:focus-visible,
        textarea:focus-visible,
        [tabindex]:focus-visible {
            outline: 2px solid var(--color-primary) !important;
            outline-offset: 2px !important;
        }

        /* Hero Header Card */
        .fi-header {
            background: var(--color-surface);
            border: 1px solid var(--color-border-soft);
            border-top: 4px solid var(--color-primary);
            border-radius: var(--radius-md);
            padding: 1.1rem 1.35rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }
        .fi-header-top {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
        }
        .fi-brand {
            display: flex;
            align-items: center;
            gap: 0.65rem;
        }
        .fi-brand-icon {
            width: 38px;
            height: 38px;
            border-radius: 8px;
            background: #EFF6FF;
            border: 1px solid var(--color-border-soft);
            color: var(--color-primary);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .fi-header h1.fi-title, .fi-title {
            font-size: 1.42rem !important;
            font-weight: 700 !important;
            color: var(--color-primary-dark) !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.25 !important;
        }
        .fi-subtitle {
            font-size: 0.88rem;
            color: var(--color-text-muted);
            margin: 0.2rem 0 0 0;
        }
        .fi-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.8rem;
        }
        .fi-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            max-width: 100%;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: break-word;
            padding: 0.24rem 0.6rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            font-family: var(--font-mono);
            font-variant-numeric: tabular-nums;
            background: var(--color-muted);
            color: var(--color-primary-dark);
            border: 1px solid var(--color-border-soft);
        }

        /* Verdict Hero Card */
        .fi-verdict {
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-left: 5px solid var(--color-primary);
            border-radius: var(--radius-md);
            padding: 1.15rem 1.35rem;
            margin: 0.9rem 0 1rem 0;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
        }
        .fi-verdict.is-answered {
            border-left-color: var(--color-success);
        }
        .fi-verdict.is-refused {
            border-left-color: var(--color-danger);
            background: #FFFDFD;
        }
        .fi-verdict.is-ambiguous, .fi-verdict.is-partial {
            border-left-color: var(--color-accent);
        }
        .fi-verdict-top {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 0.6rem;
            margin-bottom: 0.65rem;
        }
        .fi-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.42rem;
            max-width: 100%;
            white-space: normal;
            line-height: 1.25;
            padding: 0.26rem 0.7rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
        }
        .fi-status-pill.answered {
            background: var(--color-success-bg);
            color: var(--color-success);
            border: 1px solid #A7F3D0;
        }
        .fi-status-pill.refused {
            background: var(--color-danger-bg);
            color: var(--color-danger);
            border: 1px solid #FECACA;
        }
        .fi-status-pill.ambiguous, .fi-status-pill.partial {
            background: var(--color-warn-bg);
            color: #B45309;
            border: 1px solid #FDE68A;
        }
        .fi-meta-inline {
            font-size: 0.8rem;
            color: var(--color-text-muted);
            font-family: var(--font-mono);
            max-width: 100%;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .fi-answer-value {
            font-family: var(--font-mono);
            font-variant-numeric: tabular-nums;
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--color-text);
            line-height: 1.25;
            margin: 0.25rem 0 0.55rem 0;
            max-width: 100%;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .fi-formula-box {
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
            background: var(--color-bg);
            border: 1px solid var(--color-border-soft);
            border-radius: var(--radius-sm);
            padding: 0.55rem 0.75rem;
            font-size: 0.86rem;
            color: var(--color-text);
            font-family: var(--font-mono);
            font-variant-numeric: tabular-nums;
            margin-top: 0.4rem;
            max-width: 100%;
            overflow: hidden;
        }
        .fi-formula-box span {
            min-width: 0;
            max-width: 100%;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .fi-cite-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.45rem;
            margin-top: 0.7rem;
        }
        .fi-cite-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--color-text-muted);
        }
        .fi-cite-tag {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            max-width: 100%;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: break-word;
            background: #EFF6FF;
            color: var(--color-primary);
            border: 1px solid var(--color-border-soft);
            border-radius: var(--radius-sm);
            padding: 0.2rem 0.55rem;
            font-family: var(--font-mono);
            font-size: 0.8rem;
            font-weight: 600;
        }

        /* KPI Entity Cards */
        .fi-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 0.5rem 0 0.9rem 0;
        }
        @media (max-width: 900px) {
            .fi-kpi-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        @media (max-width: 480px) {
            .fi-kpi-grid {
                grid-template-columns: minmax(0, 1fr);
            }
        }
        .fi-kpi-card {
            background: var(--color-surface);
            border: 1px solid var(--color-border-soft);
            border-radius: var(--radius-md);
            padding: 0.75rem 0.9rem;
            min-width: 0;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
        }
        .fi-kpi-label {
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--color-text-muted);
            margin-bottom: 0.25rem;
        }
        .fi-kpi-val {
            font-family: var(--font-mono);
            font-variant-numeric: tabular-nums;
            font-size: 1.08rem;
            font-weight: 700;
            color: var(--color-primary-dark);
            word-break: break-word;
        }
        .fi-kpi-sub {
            font-size: 0.76rem;
            color: var(--color-text-muted);
            margin-top: 0.15rem;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        /* Evidence snippet container */
        .fi-meta-strip {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem 1rem;
            font-size: 0.82rem;
            color: var(--color-text-muted);
            background: var(--color-bg);
            border: 1px solid var(--color-border-soft);
            border-radius: var(--radius-sm);
            padding: 0.45rem 0.75rem;
            margin-bottom: 0.6rem;
            max-width: 100%;
            overflow: hidden;
        }
        .fi-meta-strip span {
            min-width: 0;
            max-width: 100%;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .fi-meta-strip strong {
            color: var(--color-text);
        }
        .fi-meta-strip code {
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .fi-snippet-box {
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-sm);
            padding: 0.75rem 0.9rem;
            font-size: 0.88rem;
            line-height: 1.58;
            color: var(--color-text);
            margin-bottom: 0.65rem;
            max-width: 100%;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        [data-testid="stDataFrame"], .stDataFrame,
        [data-testid="stDataFrame"] > div {
            max-width: 100% !important;
            overflow-x: auto !important;
        }
        [data-testid="stCode"], [data-testid="stCode"] pre, .stCode pre {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            border: 1px solid var(--color-border) !important;
            max-width: 100% !important;
            white-space: pre-wrap !important;
            overflow-wrap: anywhere !important;
            word-break: break-word !important;
            overflow-x: auto !important;
        }
        [data-testid="stCode"] code {
            background-color: transparent !important;
            border: none !important;
            color: #0F172A !important;
            padding: 0 !important;
        }
        [data-testid="stExpander"] summary p {
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            word-break: break-word !important;
        }
        @media (max-width: 640px) {
            .block-container {
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }
            .fi-header, .fi-verdict {
                padding: 0.85rem 0.9rem;
            }
            .fi-answer-value {
                font-size: 1.32rem;
            }
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.45rem !important;
            }
            [data-testid="stHorizontalBlock"] > div[data-testid="column"],
            [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                flex: 1 1 100% !important;
                min-width: 100% !important;
                width: 100% !important;
            }
        }

        .fi-section-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--color-primary-dark);
            margin: 0.2rem 0 0.5rem 0;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                transition-duration: 0.01ms !important;
                animation-duration: 0.01ms !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(n_chunks: int) -> None:
    chunks_fmt = f"{n_chunks:,}".replace(",", ".")
    html_block = "".join([
        '<div class="fi-header">',
        '<div class="fi-header-top"><div class="fi-brand">',
        f'<div class="fi-brand-icon">{ICONS["ledger"]}</div>',
        '<div>',
        '<h1 class="fi-title">ViFinQA — Hệ thống Hỏi Đáp Báo cáo Tài chính Có Trích Dẫn</h1>',
        '<p class="fi-subtitle">Truy hồi lai (BM25 + Metadata + Table Lookup) · Sinh đáp án offline chỉ từ CONTEXT theo <code>config/answer_policy.yaml</code> (không đọc thuộc gold)</p>',
        '</div></div></div>',
        '<div class="fi-chip-row">',
        '<span class="fi-chip">4 Doanh nghiệp: HPG · HSG · NKG · MSR</span>',
        '<span class="fi-chip">40 Báo cáo (2020–2024)</span>',
        f'<span class="fi-chip">{chunks_fmt} Chunks</span>',
        '<span class="fi-chip">29.615 Table Records</span>',
        '</div></div>',
    ])
    st.markdown(html_block, unsafe_allow_html=True)


def render_verdict_card(result: dict, status: str, cite_ok: bool) -> None:
    refused = bool(result.get("refused") or status == "refused")
    src = html.escape(str(result.get("answer_source", "") or "-"))
    reason = html.escape(str(result.get("status_reason", "") or "-"))
    cite_label = "Đủ trích dẫn" if cite_ok else "Chưa đủ trích dẫn"

    if refused:
        css_cls, pill_cls, icon, badge_text = "is-refused", "refused", ICONS["shield"], "TỪ CHỐI — THIẾU BẰNG CHỨNG"
    elif status == "ambiguous":
        css_cls, pill_cls, icon, badge_text = "is-ambiguous", "ambiguous", ICONS["alert"], "CẦN LÀM RÕ (AMBIGUOUS)"
    elif result.get("answer"):
        css_cls, pill_cls, icon, badge_text = "is-answered", "answered", ICONS["check"], "ĐÃ TRẢ LỜI TỪ BẰNG CHỨNG"
    else:
        css_cls, pill_cls, icon, badge_text = "is-partial", "partial", ICONS["alert"], "TRUY HỒI CHỨNG CỨ (CHƯA CHỐT SỐ)"

    ans_raw = str(result.get("answer", "") or "")
    ans_html = (
        f'<div class="fi-answer-value">{html.escape(ans_raw)}</div>'
        if ans_raw
        else '<div class="fi-answer-value" style="font-size:1.05rem;color:#B45309;">Pipeline chưa tổng hợp được con số chắc chắn từ bảng — xem các chunk ứng viên bên dưới.</div>'
    )

    comp_raw = str(result.get("computation", "") or "")
    comp_html = (
        f'<div class="fi-formula-box">{ICONS["calc"]}<span><strong>Phép tính / Nguồn bảng:</strong> {html.escape(comp_raw)}</span></div>'
        if comp_raw
        else ""
    )

    ev_unique = list(dict.fromkeys(str(cid) for cid in (result.get("evidence") or []) if cid))
    ev_html = ""
    if ev_unique:
        tags = "".join(f'<span class="fi-cite-tag">{ICONS["doc"]} {html.escape(cid)}</span>' for cid in ev_unique)
        ev_html = f'<div class="fi-cite-row"><span class="fi-cite-label">Chunk chứng cứ:</span>{tags}</div>'

    refusal_note = ""
    if refused:
        refusal_note = (
            '<div style="margin-top:0.65rem;font-size:0.86rem;color:#475569;">'
            "Hệ thống áp dụng luật từ chối an toàn vì câu hỏi nằm ngoài phạm vi báo cáo năm trong corpus "
            "(ví dụ: quý, bán niên, kế hoạch, dự báo, giá cổ phiếu/vốn hóa thị trường)."
            "</div>"
        )

    card_html = "".join([
        f'<div class="fi-verdict {css_cls}">',
        '<div class="fi-verdict-top">',
        f'<span class="fi-status-pill {pill_cls}" role="status" aria-atomic="true">{icon}<span>{badge_text}</span></span>',
        f'<span class="fi-meta-inline">status={html.escape(status)} | source={src} | {cite_label} | reason={reason}</span>',
        '</div>',
        ans_html,
        comp_html,
        ev_html,
        refusal_note,
        '</div>',
    ])
    st.markdown(card_html, unsafe_allow_html=True)


def render_entities_grid(entities: dict) -> None:
    companies = ", ".join(entities.get("companies", [])) or "Chưa rõ"
    company_full = "; ".join(entities.get("company_names", [])) or "Không có tên công ty trích xuất"
    years = ", ".join(entities.get("years", [])) or "Chưa rõ"
    version = entities.get("report_version", "") or "Chưa rõ"
    unit = entities.get("target_unit", "") or "Theo đơn vị bảng"
    indicator = entities.get("indicator_guess", "") or "Tự động theo từ khóa"

    st.markdown('<div class="fi-section-title">Thực thể & Ràng buộc truy hồi đã trích</div>', unsafe_allow_html=True)
    grid_html = "".join([
        '<div class="fi-kpi-grid">',
        f'<div class="fi-kpi-card"><div class="fi-kpi-label">Doanh nghiệp</div><div class="fi-kpi-val">{html.escape(companies)}</div><div class="fi-kpi-sub">{html.escape(company_full)}</div></div>',
        f'<div class="fi-kpi-card"><div class="fi-kpi-label">Năm tài chính</div><div class="fi-kpi-val">{html.escape(years)}</div><div class="fi-kpi-sub">Phạm vi corpus: 2020–2024</div></div>',
        f'<div class="fi-kpi-card"><div class="fi-kpi-label">Phiên bản BCTC</div><div class="fi-kpi-val">{html.escape(version)}</div><div class="fi-kpi-sub">consolidated / separate</div></div>',
        f'<div class="fi-kpi-card"><div class="fi-kpi-label">Đơn vị & Chỉ tiêu</div><div class="fi-kpi-val">{html.escape(unit)}</div><div class="fi-kpi-sub">Chỉ tiêu: {html.escape(indicator)}</div></div>',
        '</div>',
    ])
    st.markdown(grid_html, unsafe_allow_html=True)


def select_question(q_text: str, qid: str = "") -> None:
    st.session_state["question"] = q_text
    if qid:
        st.session_state["active_qid"] = qid
    st.session_state["run_query"] = True


# ---------------------------------------------------------------------
# Page Setup & Engine Load
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="ViFinQA RAG — Hỏi đáp Báo cáo Tài chính",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_design_system()

chunks, _, _, _, _, _ = load_engine()
samples = load_samples()

if "question" not in st.session_state:
    st.session_state["question"] = samples[0]["question"]
if "active_qid" not in st.session_state:
    st.session_state["active_qid"] = samples[0]["qid"]

# ---------------------------------------------------------------------
# Sidebar: Settings + 13 Sample Questions (1-Click Run)
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Cấu hình truy hồi")
    top_k = st.slider("Số chứng cứ hiển thị (top-k)", 1, 10, 5)
    show_full = st.checkbox("Hiển thị toàn văn trang OCR", value=False)
    chunks_dot = f"{len(chunks):,}".replace(",", ".")
    st.caption(f"Đã nạp **{chunks_dot}** chunk · Config: `config/e0_bm25.yaml` & `config/e2_hybrid.yaml`.")
    st.divider()
    with st.expander(f"Bộ câu mẫu kiểm thử ({len(samples)} câu)", expanded=False):
        st.caption("Bấm vào một câu mẫu để nạp và chạy pipeline ngay.")

        current_group = None
        for s in samples:
            if s["group"] != current_group:
                current_group = s["group"]
                st.markdown(f"**{GROUP_TITLES[current_group]}**")
            label = s.get("label", s.get("qid", ""))
            short_lbl = label.split(" - ", 1)[-1] if " - " in label else label
            qid = s.get("qid", "")
            st.button(
                f"{qid} · {short_lbl}",
                key=f"sample_{qid}",
                on_click=select_question,
                args=(s["question"], qid),
            )

# ---------------------------------------------------------------------
# Main Workspace
# ---------------------------------------------------------------------
render_header(len(chunks))

with st.container():
    active_qid = st.session_state.get("active_qid", "")
    question = st.text_area(
        "Nhập câu hỏi tài chính (tiếng Việt, kèm công ty / năm / đơn vị)",
        key="question",
        height=88,
        placeholder="Ví dụ: Biên lợi nhuận gộp về bán hàng và cung cấp dịch vụ hợp nhất của CTCP Tập đoàn Hoa Sen năm 2024 là bao nhiêu phần trăm?",
    )
    ask = st.button("Truy vấn & Trích dẫn", type="primary")

if ask:
    st.session_state["run_query"] = True

should_run = bool(st.session_state.get("run_query", False))

if should_run and question.strip():
    with st.spinner("Đang truy hồi chứng cứ từ 40 báo cáo tài chính..."):
        result = answer(question.strip(), top_k)

    status = result.get("answer_status", "refused" if result.get("refused") else "answered")
    cite_ok = bool(result.get("citation_complete", False))
    entities = result.get("entities", {})

    render_verdict_card(result, status, cite_ok)

    if result.get("conflict_warning"):
        st.warning(f"Cảnh báo mâu thuẫn đơn vị / bối cảnh: {result['conflict_warning']}")

    if not result.get("answer") and not result.get("refused"):
        if result.get("candidates"):
            st.info("**Số ứng viên trong đoạn liên quan nhất:** " + "; ".join(result["candidates"]))
        if result.get("note"):
            st.caption(result["note"])
        if result.get("suggestions"):
            st.markdown("**Gợi ý câu hỏi gần nhất (bấm để chạy lại):**")
            for idx_s, s in enumerate(result["suggestions"]):
                st.button(
                    f"[{s['question_id']}, khớp {s['score']}] {s['question'][:85]}...",
                    key=f"sug_{s['question_id']}_{idx_s}",
                    on_click=select_question,
                    args=(s["question"], ""),
                )

    render_entities_grid(entities)

    hits = result.get("hits", [])
    ev_tab_title = "Chứng cứ (Chế độ Từ chối)" if not hits else f"Chứng cứ Top-{len(hits)} & Bảng số liệu gốc"
    tab_ev, tab_ctx = st.tabs([
        ev_tab_title,
        "CONTEXT gửi bộ sinh & Nhật ký truy hồi",
    ])

    with tab_ev:
        hits = result.get("hits", [])
        if not hits:
            st.info("Không có chunk nào được trích xuất do câu hỏi đã kích hoạt quy tắc từ chối ngoài phạm vi corpus.")
        else:
            st.caption("Các con số quan trọng trong đoạn trích được tô đậm. Mở từng thẻ để đối chiếu bảng `table_records.jsonl` và tài liệu gốc.")
            for i, h in enumerate(hits, 1):
                exp_title = (
                    f"#{i} · {h['company_id']} {h['fiscal_year']} ({h['report_version']}) "
                    f"— Trang {h['page']} · [{h['chunk_id']}] · Điểm {h['score']}"
                )
                with st.expander(exp_title, expanded=(i == 1)):
                    meta_html = "".join([
                        '<div class="fi-meta-strip">',
                        f'<span><strong>Tài liệu:</strong> <code>{html.escape(str(h.get("source_path", h.get("chunk_id", ""))))}</code></span>',
                        f'<span><strong>Đơn vị trang:</strong> <code>{html.escape(str(h.get("unit", "") or "không rõ"))}</code></span>',
                        f'<span><strong>Số bảng:</strong> {html.escape(str(h.get("n_tables", "")))}</span>',
                        f'<span><strong>Độ dài:</strong> {html.escape(str(h.get("full_len", "")))} ký tự</span>',
                        '</div>',
                    ])
                    st.markdown(meta_html, unsafe_allow_html=True)
                    st.markdown("**Đoạn trích liên quan:**")
                    st.markdown(h.get("snippet_highlight", h.get("snippet", "")))

                    rows = h.get("table_rows", [])
                    if rows:
                        st.markdown("**Dữ liệu bảng trích xuất (`table_records.jsonl`):**")
                        st.dataframe(
                            [
                                {
                                    "Chỉ tiêu (metric)": r.get("metric", ""),
                                    "Mã": r.get("metric_code", ""),
                                    "Kỳ": r.get("period_label", ""),
                                    "Năm": r.get("year", ""),
                                    "Giá trị thô": r.get("value_raw", ""),
                                    "Đơn vị": r.get("unit", ""),
                                    "Trang": r.get("page", ""),
                                }
                                for r in rows[:5]
                            ],
                            use_container_width=True,
                            hide_index=True,
                        )
                        if len(rows) > 5 or st.session_state.get(f"show_tbl_{h['chunk_id']}_{i}", False):
                            if st.button("Xem/Ẩn toàn bộ cột bảng gốc", key=f"tbl_{h['chunk_id']}_{i}"):
                                cur = st.session_state.get(f"show_tbl_{h['chunk_id']}_{i}", False)
                                st.session_state[f"show_tbl_{h['chunk_id']}_{i}"] = not cur
                                st.rerun()
                            if st.session_state.get(f"show_tbl_{h['chunk_id']}_{i}", False):
                                st.dataframe(
                                    [
                                        {
                                            "Chỉ tiêu": r.get("metric", ""),
                                            "Mã": r.get("metric_code", ""),
                                            "Kỳ": r.get("period_label", ""),
                                            "Năm": r.get("year", ""),
                                            "Giá trị chuẩn": r.get("value", ""),
                                            "Giá trị thô": r.get("value_raw", ""),
                                            "Đơn vị": r.get("unit", ""),
                                            "Bảng": r.get("table_index", ""),
                                            "Trang": r.get("page", ""),
                                            "Chunk": r.get("source_chunk_id", ""),
                                        }
                                        for r in rows
                                    ],
                                    use_container_width=True,
                                    hide_index=True,
                                )
                    if show_full:
                        st.text_area(
                            "Toàn văn trang OCR",
                            value=h["full_text"],
                            height=280,
                            key=f"full_{h['chunk_id']}_{i}",
                        )

    with tab_ctx:
        st.markdown("**Luồng xử lý:** `Câu hỏi -> Trích thực thể -> BM25 + Điểm metadata -> Lookup bảng -> Ghép CONTEXT -> Bộ sinh đáp án theo config/answer_policy.yaml`")
        if result.get("context"):
            st.code(result.get("context", ""), language="text")
        else:
            st.info("Không có CONTEXT vì câu hỏi bị từ chối ở tầng lọc quy tắc.")

elif should_run and not question.strip():
    st.error("Vui lòng nhập câu hỏi trước khi bấm Truy vấn & Trích dẫn.")
else:
    st.info("Chọn một câu mẫu ở thanh bên trái hoặc nhập câu hỏi rồi bấm Truy vấn & Trích dẫn để hệ thống truy hồi, đối chiếu bảng số liệu và hiển thị chứng cứ trích dẫn.")
