"""Sinh báo cáo BTL dạng Word (.docx) theo đúng mẫu Học phần CSC4007 (Đại Nam)
từ tệp Markdown đã biên tập (`report/Bao_cao_BTL.md`), giữ nguyên trang bìa
chuẩn, tự động hóa mục lục / đánh số Hình & Bảng và xuất PDF qua Word COM.

Chạy:
    .\.venv\Scripts\python.exe src\evaluate\build_report_docx.py
"""

from __future__ import annotations

import argparse
import copy
import re
import shutil
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_LEADER
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

REPO = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE = REPO.parent / "Mau bao cao Báo cáo học phần.docx"
DEFAULT_MD = REPO / "report" / "Bao_cao_BTL.md"
DEFAULT_DOCX = REPO / "report" / "Bao_cao_BTL.docx"
DEFAULT_PDF = REPO / "report" / "Bao_cao_BTL.pdf"

FONT_SERIF = "Times New Roman"
FONT_MONO = "Consolas"
BLACK = RGBColor(0x00, 0x00, 0x00)
MUTED = RGBColor(0x33, 0x41, 0x55)
CONTENT_WIDTH_CM = 16.0  # A4 21.0 cm - 3.0 cm left - 2.0 cm right

COURSE_TEXT = "TÊN HỌC PHẦN: XỬ LÝ NGÔN NGỮ TỰ NHIÊN (CSC4007)"
TOPIC_TEXT = "ĐỀ TÀI: HỎI ĐÁP BÁO CÁO TÀI CHÍNH TIẾNG VIỆT CÓ TRÍCH DẪN BẰNG RAG"
COVER_YEAR_TEXT = "Hà Nội, năm 2026"
STUDENT_ROW = ("1", "1677030156", "Nguyễn Minh Phượng", "", "KHMT17-01")


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def _set_run_font(run, *, name: str = FONT_SERIF, size_pt: float = 13.0,
                  bold: bool | None = None, italic: bool | None = None,
                  color: RGBColor = BLACK) -> None:
    run.font.name = name
    run.font.size = Pt(size_pt)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), name)


def _strip_heading_style_and_toc_bookmarks(el) -> None:
    for p in el.iter(qn("w:p")):
        pPr = p.find(qn("w:pPr"))
        if pPr is not None:
            pStyle = pPr.find(qn("w:pStyle"))
            if pStyle is not None and pStyle.get(qn("w:val"), "").startswith("Heading"):
                pPr.remove(pStyle)
        for tag in ("w:bookmarkStart", "w:bookmarkEnd"):
            for bm in list(p.findall(qn(tag))):
                name = bm.get(qn("w:name"), "")
                if tag == "w:bookmarkEnd" or name.startswith("_Toc"):
                    p.remove(bm)


def _replace_para_text_preserve_sect(p_el, text: str, *, size_pt: float,
                                     bold: bool = True, align: str = "center") -> None:
    pPr = p_el.find(qn("w:pPr"))
    sect_pr = None
    if pPr is not None:
        old_sect = pPr.find(qn("w:sectPr"))
        if old_sect is not None:
            sect_pr = copy.deepcopy(old_sect)
    for child in list(p_el):
        if child.tag != qn("w:pPr"):
            p_el.remove(child)
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p_el.insert(0, pPr)
    for tag in ("w:pStyle", "w:ind", "w:jc"):
        node = pPr.find(qn(tag))
        if node is not None:
            pPr.remove(node)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), align)
    pPr.append(jc)
    if sect_pr is not None:
        existing_sect = pPr.find(qn("w:sectPr"))
        if existing_sect is None:
            pPr.append(sect_pr)

    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), FONT_SERIF)
    rPr.append(rFonts)
    if bold:
        rPr.append(OxmlElement("w:b"))
        rPr.append(OxmlElement("w:bCs"))
    col = OxmlElement("w:color")
    col.set(qn("w:val"), "000000")
    rPr.append(col)
    sz_val = str(int(round(size_pt * 2)))
    for tag in ("w:sz", "w:szCs"):
        s = OxmlElement(tag)
        s.set(qn("w:val"), sz_val)
        rPr.append(s)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    p_el.append(r)


def _set_cell_text(tc_el, text: str, *, bold: bool = False, size_pt: float = 12.0,
                   align: str = "center") -> None:
    for p in list(tc_el.findall(qn("w:p"))):
        tc_el.remove(p)
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    sp = OxmlElement("w:spacing")
    sp.set(qn("w:before"), "40")
    sp.set(qn("w:after"), "40")
    sp.set(qn("w:line"), "240")
    sp.set(qn("w:lineRule"), "auto")
    pPr.append(sp)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), align)
    pPr.append(jc)
    p.append(pPr)

    if text:
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        rFonts = OxmlElement("w:rFonts")
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rFonts.set(qn(attr), FONT_SERIF)
        rPr.append(rFonts)
        if bold:
            rPr.append(OxmlElement("w:b"))
            rPr.append(OxmlElement("w:bCs"))
        col = OxmlElement("w:color")
        col.set(qn("w:val"), "000000")
        rPr.append(col)
        sz_val = str(int(round(size_pt * 2)))
        for tag in ("w:sz", "w:szCs"):
            s = OxmlElement(tag)
            s.set(qn("w:val"), sz_val)
            rPr.append(s)
        r.append(rPr)
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = text
        r.append(t)
        p.append(r)
    tc_el.append(p)


def _add_field(paragraph, instr_text: str, *, placeholder: str = "",
               size_pt: float = 12.0, italic: bool = False,
               bold: bool = False, color: RGBColor = BLACK,
               font_name: str = FONT_SERIF) -> None:
    def _mk_run():
        r = paragraph.add_run()
        _set_run_font(r, name=font_name, size_pt=size_pt, bold=bold, italic=italic, color=color)
        return r

    r_begin = _mk_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    fld_begin.set(qn("w:dirty"), "true")
    r_begin._r.append(fld_begin)

    r_instr = _mk_run()
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instr_text} "
    r_instr._r.append(instr)

    r_sep = _mk_run()
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    r_sep._r.append(fld_sep)

    if placeholder:
        r_ph = _mk_run()
        r_ph.text = placeholder

    r_end = _mk_run()
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r_end._r.append(fld_end)


def _enable_update_fields_on_open(doc: Document) -> None:
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is None:
        upd = OxmlElement("w:updateFields")
        upd.set(qn("w:val"), "true")
        settings.append(upd)
    compat = settings.find(qn("w:compat"))
    if compat is None:
        compat = OxmlElement("w:compat")
        settings.append(compat)
    if compat.find(qn("w:doNotExpandShiftReturn")) is None:
        compat.append(OxmlElement("w:doNotExpandShiftReturn"))


def _configure_styles(doc: Document) -> None:
    styles = doc.styles

    def _conf(style_id: str, *, size_pt: float, bold: bool = False, italic: bool = False,
              align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing: float = 1.5,
              before_pt: float = 0.0, after_pt: float = 6.0,
              left_cm: float = 0.0, first_cm: float = 0.0,
              keep_with_next: bool | None = None, outline_lvl: int | None = None):
        st = styles[style_id]
        st.font.name = FONT_SERIF
        st.font.size = Pt(size_pt)
        st.font.bold = bold
        st.font.italic = italic
        st.font.color.rgb = BLACK
        rPr = st._element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.insert(0, rFonts)
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rFonts.set(qn(attr), FONT_SERIF)
        for theme_attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if qn(theme_attr) in rFonts.attrib:
                del rFonts.attrib[qn(theme_attr)]
        col = rPr.find(qn("w:color"))
        if col is not None:
            col.set(qn("w:val"), "000000")
            for k in list(col.attrib):
                if k != qn("w:val"):
                    del col.attrib[k]

        pf = st.paragraph_format
        pf.alignment = align
        pf.line_spacing = line_spacing
        pf.space_before = Pt(before_pt)
        pf.space_after = Pt(after_pt)
        pf.left_indent = Cm(left_cm)
        pf.first_line_indent = Cm(first_cm)
        if keep_with_next is not None:
            pf.keep_with_next = keep_with_next

        if outline_lvl is not None:
            pPr = st._element.get_or_add_pPr()
            ol = pPr.find(qn("w:outlineLvl"))
            if ol is None:
                ol = OxmlElement("w:outlineLvl")
                pPr.append(ol)
            ol.set(qn("w:val"), str(outline_lvl))

    _conf("Normal", size_pt=13.0, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.5, after_pt=6.0)
    _conf("Heading 1", size_pt=14.0, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
          line_spacing=1.15, before_pt=0.0, after_pt=12.0, keep_with_next=True, outline_lvl=0)
    _conf("TOC Heading", size_pt=14.0, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
          line_spacing=1.15, before_pt=0.0, after_pt=12.0, keep_with_next=True, outline_lvl=9)
    _conf("Heading 2", size_pt=13.0, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT,
          line_spacing=1.5, before_pt=12.0, after_pt=4.0, keep_with_next=True, outline_lvl=1)
    _conf("Heading 3", size_pt=13.0, bold=True, italic=True, align=WD_ALIGN_PARAGRAPH.LEFT,
          line_spacing=1.5, before_pt=8.0, after_pt=4.0, left_cm=0.0, keep_with_next=True, outline_lvl=2)
    _conf("Bibliography", size_pt=12.0, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
          line_spacing=1.35, before_pt=0.0, after_pt=6.0, left_cm=1.0, first_cm=-1.0)

    for toc_name, indent_cm, is_bold in [("TOC 1", 0.0, True), ("TOC 2", 0.5, False), ("TOC 3", 1.0, False)]:
        if toc_name in styles:
            _conf(toc_name, size_pt=13.0, bold=is_bold, align=WD_ALIGN_PARAGRAPH.LEFT,
                  line_spacing=1.25, before_pt=2.0, after_pt=2.0, left_cm=indent_cm)
            tabs = styles[toc_name].paragraph_format.tab_stops
            tabs.clear_all()
            tabs.add_tab_stop(Cm(CONTENT_WIDTH_CM), WD_ALIGN_PARAGRAPH.RIGHT, WD_TAB_LEADER.DOTS)


# ---------------------------------------------------------------------------
# Cover + sections setup
# ---------------------------------------------------------------------------

def _update_covers_and_strip_sample_body(doc: Document) -> None:
    body = doc.element.body
    children = list(body)
    # Inspect confirmed positions from template:
    # 0..14 Cover 1 (14 has sectPr), 15..29 Cover 2 (29 has sectPr), 30..-2 template content
    for idx in (7, 8, 9, 22, 23, 24):
        _strip_heading_style_and_toc_bookmarks(children[idx])

    # Cover 1 title/topic/year
    _replace_para_text_preserve_sect(children[4], COURSE_TEXT, size_pt=15.0, bold=True)
    _replace_para_text_preserve_sect(children[5], TOPIC_TEXT, size_pt=15.0, bold=True)
    _replace_para_text_preserve_sect(children[14], COVER_YEAR_TEXT, size_pt=14.0, bold=True)

    # Reduce trailing spacer paragraphs slightly on Cover 1 & 2 if needed so 2-line title fits 1 page
    for spacer_idx in (12, 13, 27, 28):
        p = children[spacer_idx]
        for child in list(p):
            if child.tag != qn("w:pPr"):
                p.remove(child)
        pPr = p.find(qn("w:pPr"))
        if pPr is not None:
            sp = pPr.find(qn("w:spacing"))
            if sp is None:
                sp = OxmlElement("w:spacing")
                pPr.append(sp)
            sp.set(qn("w:before"), "0")
            sp.set(qn("w:after"), "0")
            sp.set(qn("w:line"), "180")
            sp.set(qn("w:lineRule"), "auto")

    def _apply_fixed_cov_widths(tbl_el, cols_dxa: list[int]) -> None:
        tblPr = tbl_el.find(qn("w:tblPr"))
        if tblPr is not None:
            tblW = tblPr.find(qn("w:tblW"))
            if tblW is None:
                tblW = OxmlElement("w:tblW")
                tblPr.append(tblW)
            tblW.set(qn("w:w"), str(sum(cols_dxa)))
            tblW.set(qn("w:type"), "dxa")
            jc = tblPr.find(qn("w:jc"))
            if jc is None:
                jc = OxmlElement("w:jc")
                tblPr.append(jc)
            jc.set(qn("w:val"), "center")
            tblLayout = tblPr.find(qn("w:tblLayout"))
            if tblLayout is None:
                tblLayout = OxmlElement("w:tblLayout")
                tblPr.append(tblLayout)
            tblLayout.set(qn("w:type"), "fixed")
        grid = tbl_el.find(qn("w:tblGrid"))
        if grid is not None:
            for gc, w_dxa in zip(grid.findall(qn("w:gridCol")), cols_dxa):
                gc.set(qn("w:w"), str(w_dxa))
        for tr in tbl_el.findall(qn("w:tr")):
            ci = 0
            for tc in tr.findall(qn("w:tc")):
                tcPr = tc.find(qn("w:tcPr"))
                span = 1
                if tcPr is not None:
                    gs = tcPr.find(qn("w:gridSpan"))
                    if gs is not None and gs.get(qn("w:val")):
                        span = int(gs.get(qn("w:val")))
                    tcW = tcPr.find(qn("w:tcW"))
                    if tcW is None:
                        tcW = OxmlElement("w:tcW")
                        tcPr.insert(0, tcW)
                    tcW.set(qn("w:w"), str(sum(cols_dxa[ci : ci + span])))
                    tcW.set(qn("w:type"), "dxa")
                ci += span

    # Cover 1 student table (4 rows x 5 cols; 8500 dxa fits comfortably inside 15.5 cm frame)
    tbl1 = children[7]
    cov1_cols_dxa = [750, 1750, 3100, 1300, 1600]
    _apply_fixed_cov_widths(tbl1, cov1_cols_dxa)
    tbl1_rows = tbl1.findall(qn("w:tr"))
    for ri, row_vals in enumerate([
        ("STT", "Mã Sinh Viên", "Họ và Tên", "Ngày Sinh", "Lớp"),
        STUDENT_ROW,
        ("2", "", "", "", ""),
        ("3", "", "", "", ""),
    ]):
        tcs = tbl1_rows[ri].findall(qn("w:tc"))
        for ci, val in enumerate(row_vals):
            align = "left" if (ri > 0 and ci == 2 and val) else "center"
            _set_cell_text(tcs[ci], val, bold=(ri == 0), size_pt=12.0, align=align)

    # Cover 2 title/topic/year
    _replace_para_text_preserve_sect(children[19], COURSE_TEXT, size_pt=15.0, bold=True)
    _replace_para_text_preserve_sect(children[20], TOPIC_TEXT, size_pt=15.0, bold=True)
    _replace_para_text_preserve_sect(children[29], COVER_YEAR_TEXT, size_pt=14.0, bold=True)

    # Cover 2 grading table (5 rows; 8500 dxa fixed grid across header rows 0..1 & data rows 2..4)
    tbl2 = children[22]
    cov2_cols_dxa = [750, 1700, 2900, 1250, 950, 950]
    _apply_fixed_cov_widths(tbl2, cov2_cols_dxa)
    tbl2_rows = tbl2.findall(qn("w:tr"))
    for ri, row_vals in [(2, ("1", "1677030156", "Nguyễn Minh Phượng", "", "", "")),
                         (3, ("2", "", "", "", "", "")),
                         (4, ("3", "", "", "", "", ""))]:
        tcs = tbl2_rows[ri].findall(qn("w:tc"))
        for ci, val in enumerate(row_vals):
            align = "left" if (ci == 2 and val) else "center"
            _set_cell_text(tcs[ci], val, bold=False, size_pt=12.0, align=align)
    # Clean bold styling on Cover 2 header rows 0 & 1 without Heading3 style
    for ri in (0, 1):
        for tc in tbl2_rows[ri].findall(qn("w:tc")):
            txt = "".join(t.text or "" for t in tc.findall(f".//{qn('w:t')}")).strip()
            if txt:
                _set_cell_text(tc, txt, bold=True, size_pt=12.0, align="center")

    # Strip Heading3 style from CÁN BỘ CHẤM THI line (idx 24) while keeping bold 13pt
    _strip_heading_style_and_toc_bookmarks(children[24])
    for r in children[24].findall(qn("w:r")):
        rPr = r.find(qn("w:rPr"))
        if rPr is None:
            rPr = OxmlElement("w:rPr")
            r.insert(0, rPr)
        if rPr.find(qn("w:b")) is None:
            rPr.append(OxmlElement("w:b"))
        sz = rPr.find(qn("w:sz")) or OxmlElement("w:sz")
        sz.set(qn("w:val"), "26")
        if sz.getparent() is None:
            rPr.append(sz)

    # Remove all sample body elements from index 30 up to final sectPr
    for el in children[30:]:
        if el.tag != qn("w:sectPr"):
            body.remove(el)


def _clear_header_footer(part) -> None:
    part.is_linked_to_previous = False
    el = part._element
    for child in list(el):
        el.remove(child)
    p = OxmlElement("w:p")
    el.append(p)


def _configure_sections(doc: Document) -> None:
    # Clear covers headers & footers completely
    for si in (0, 1):
        sec = doc.sections[si]
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.different_first_page_header_footer = True
        for part in (sec.header, sec.footer, sec.first_page_header, sec.first_page_footer):
            _clear_header_footer(part)

    # Content section (index 2): A4 (210 x 297 mm), margins top=2, bottom=2, left=3, right=2 cm
    sec2 = doc.sections[2]
    sec2.start_type = WD_SECTION.NEW_PAGE
    sec2.page_width = Cm(21.0)
    sec2.page_height = Cm(29.7)
    sec2.top_margin = Cm(2.0)
    sec2.bottom_margin = Cm(2.0)
    sec2.left_margin = Cm(3.0)
    sec2.right_margin = Cm(2.0)
    sec2.header_distance = Cm(1.0)
    sec2.footer_distance = Cm(1.0)
    sec2.different_first_page_header_footer = False

    _clear_header_footer(sec2.header)
    sec2.footer.is_linked_to_previous = False
    ftr_el = sec2.footer._element
    for child in list(ftr_el):
        ftr_el.remove(child)

    fp = sec2.footer.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fp.paragraph_format.space_before = Pt(2)
    fp.paragraph_format.space_after = Pt(0)
    fp.paragraph_format.tab_stops.clear_all()
    fp.paragraph_format.tab_stops.add_tab_stop(Cm(CONTENT_WIDTH_CM), WD_ALIGN_PARAGRAPH.RIGHT)

    pPr = fp._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}><w:top w:val="single" w:sz="6" w:space="4" w:color="64748B"/></w:pBdr>'
    )
    pPr.append(pBdr)

    r_left = fp.add_run("Báo cáo học phần Xử lý ngôn ngữ tự nhiên (CSC4007)")
    _set_run_font(r_left, size_pt=10.0, italic=True, color=MUTED)
    fp.add_run("\t")
    r_pg_lbl = fp.add_run("Trang ")
    _set_run_font(r_pg_lbl, size_pt=10.0, italic=False, color=MUTED)
    _add_field(fp, "PAGE", placeholder="1", size_pt=10.0, color=MUTED)
    r_sep = fp.add_run(" / ")
    _set_run_font(r_sep, size_pt=10.0, italic=False, color=MUTED)
    _add_field(fp, "SECTIONPAGES", placeholder="1", size_pt=10.0, color=MUTED)

    # Restart page numbering at 1 on content Section 2 cleanly in OOXML schema order
    sect_pr = sec2._sectPr
    for old in list(sect_pr.findall(qn("w:pgNumType"))):
        sect_pr.remove(old)
    pg_num = OxmlElement("w:pgNumType")
    pg_num.set(qn("w:start"), "1")
    doc_grid = sect_pr.find(qn("w:docGrid"))
    if doc_grid is not None:
        doc_grid.addprevious(pg_num)
    else:
        sect_pr.append(pg_num)


# ---------------------------------------------------------------------------
# Inline Markdown renderer
# ---------------------------------------------------------------------------

_INLINE_RE = re.compile(
    r"(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[([^\]]+)\]\(([^)]+)\))"
)
_LONG_HEX_RE = re.compile(r"([0-9a-fA-F]{32,})")


def _split_underscore_segment(seg: str) -> list[str]:
    if len(seg) < 18 or "_" not in seg:
        return [seg]
    raw = [pt for pt in re.split(r"(?<=_)(?!_)", seg) if pt]
    if len(raw) <= 1:
        return [seg]
    merged: list[str] = []
    for pt in raw:
        if merged and len(merged[-1]) <= 5:
            merged[-1] += pt
        else:
            merged.append(pt)
    if len(merged) > 1 and len(merged[-1]) <= 4:
        merged[-2] += merged[-1]
        merged.pop()
    return merged


def _split_long_token(tok: str) -> list[str]:
    """Insert safe internal break boundaries for long unbroken paths, URLs, and hashes."""
    if len(tok) < 18:
        return [tok]
    if any(ch in tok for ch in ("/", "\\", "#")):
        raw = [pt for pt in re.split(r"(?<=[/\\#])(?![/\\])", tok) if pt]
        parts: list[str] = []
        for seg in raw:
            parts.extend(_split_underscore_segment(seg))
        return parts if len(parts) > 1 else [tok]
    if "_" in tok:
        parts = _split_underscore_segment(tok)
        return parts if len(parts) > 1 else [tok]
    m_hex = _LONG_HEX_RE.search(tok)
    if m_hex:
        hex_str = m_hex.group(1)
        chunks = [hex_str[k : k + 16] for k in range(0, len(hex_str), 16)]
        if m_hex.start() > 0:
            chunks[0] = tok[: m_hex.start()] + chunks[0]
        if m_hex.end() < len(tok):
            chunks[-1] += tok[m_hex.end() :]
        return chunks if len(chunks) > 1 else [tok]
    return [tok]


def _append_breakable_runs(
    p,
    text: str,
    *,
    font_name: str = FONT_SERIF,
    size_pt: float = 13.0,
    bold: bool = False,
    italic: bool = False,
    color: RGBColor = BLACK,
    allow_break: bool = True,
) -> None:
    if not text:
        return
    if not allow_break:
        r = p.add_run(text)
        _set_run_font(r, name=font_name, size_pt=size_pt, bold=bold, italic=italic, color=color)
        return

    buf: list[str] = []

    def _flush() -> None:
        if buf:
            r = p.add_run("".join(buf))
            _set_run_font(r, name=font_name, size_pt=size_pt, bold=bold, italic=italic, color=color)
            buf.clear()

    for piece in re.split(r"(\s+)", text):
        if not piece:
            continue
        if piece.isspace():
            buf.append(piece)
            continue
        parts = _split_long_token(piece)
        if len(parts) <= 1:
            buf.append(piece)
            continue
        _flush()
        for idx_pt, pt in enumerate(parts):
            r = p.add_run(pt)
            _set_run_font(r, name=font_name, size_pt=size_pt, bold=bold, italic=italic, color=color)
            if idx_pt < len(parts) - 1:
                r_zw = p.add_run("\u200b")
                _set_run_font(r_zw, name=FONT_SERIF, size_pt=size_pt, bold=bold, italic=italic, color=color)
    _flush()


def _add_inline_runs(p, text: str, *, base_size: float = 13.0,
                     base_bold: bool = False, base_italic: bool = False,
                     mono_size: float | None = None, allow_break: bool = True) -> None:
    if mono_size is None:
        mono_size = max(8.0, base_size - 1.5)
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            _append_breakable_runs(
                p, text[pos:m.start()],
                font_name=FONT_SERIF, size_pt=base_size,
                bold=base_bold, italic=base_italic, color=BLACK,
                allow_break=allow_break,
            )
        tok = m.group(0)
        if tok.startswith("`") and tok.endswith("`"):
            _append_breakable_runs(
                p, tok[1:-1],
                font_name=FONT_MONO, size_pt=mono_size,
                bold=base_bold, italic=base_italic, color=RGBColor(0x1E, 0x29, 0x3B),
                allow_break=allow_break,
            )
        elif tok.startswith("**") and tok.endswith("**"):
            _append_breakable_runs(
                p, tok[2:-2],
                font_name=FONT_SERIF, size_pt=base_size,
                bold=True, italic=base_italic, color=BLACK,
                allow_break=allow_break,
            )
        elif tok.startswith("*") and tok.endswith("*"):
            _append_breakable_runs(
                p, tok[1:-1],
                font_name=FONT_SERIF, size_pt=base_size,
                bold=base_bold, italic=True, color=BLACK,
                allow_break=allow_break,
            )
        elif m.group(2) is not None:
            # Show clean label; keep URL in bibliography if URL itself is distinct
            _append_breakable_runs(
                p, m.group(2),
                font_name=FONT_SERIF, size_pt=base_size,
                bold=base_bold, italic=base_italic, color=BLACK,
                allow_break=allow_break,
            )
        pos = m.end()
    if pos < len(text):
        _append_breakable_runs(
            p, text[pos:],
            font_name=FONT_SERIF, size_pt=base_size,
            bold=base_bold, italic=base_italic, color=BLACK,
            allow_break=allow_break,
        )


# ---------------------------------------------------------------------------
# Table & Figure builders
# ---------------------------------------------------------------------------

def _is_numeric_cell(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    return bool(re.fullmatch(r"[-+]?[\d.,]+(\s*%)?(\s*/\s*[\d.,]+(\s*%)?)*", s))


def _compute_col_widths(headers: list[str], rows: list[list[str]],
                        total_cm: float = CONTENT_WIDTH_CM) -> tuple[list[float], float]:
    ncols = len(headers)
    if ncols >= 13:
        font_pt = 7.0
    elif ncols >= 7:
        font_pt = 9.5
    else:
        font_pt = 11.5

    # Token-aware minimum widths so headers (KQKD, Tổng, numeric, company, MRR@10) never wrap mid-word
    tok_char_cm = 0.124 if ncols >= 13 else (0.165 if ncols >= 7 else 0.225)
    avg_char_cm = 0.105 if ncols >= 13 else (0.140 if ncols >= 7 else 0.170)
    pad_cm = 0.08 if ncols >= 13 else 0.34
    mins = []
    targets = []
    for ci in range(ncols):
        hdr_clean = re.sub(r"[`*]", "", headers[ci]).strip()
        col_texts = [hdr_clean]
        for row in rows:
            if ci < len(row):
                col_texts.append(re.sub(r"[`*]", "", row[ci]).strip())
        hdr_toks = [w for w in re.split(r"\s+", hdr_clean) if w]
        body_toks = [w for t in col_texts[1:] for w in re.split(r"\s+", t) if w]
        hdr_max = max((len(w) for w in hdr_toks), default=1)
        body_max = max((len(w) for w in body_toks), default=1)
        longest_token = max(hdr_max, body_max)
        max_cell_len = max((len(t) for t in col_texts), default=4)
        avg_len = sum(len(t) for t in col_texts) / max(1, len(col_texts))

        if ncols >= 13:
            if "/" in hdr_clean:
                w_min = max(max_cell_len * 0.095 + 0.10, 1.38)
                w_tgt = max(w_min, 1.55)
            else:
                # Headers are bold so give slightly wider floor per char than numeric body digits
                hdr_w = hdr_max * 0.128 + pad_cm
                body_w = body_max * 0.108 + pad_cm
                w_min = max(hdr_w, body_w, 0.62 if ci == 0 else 0.78)
                w_tgt = max(w_min, avg_len * avg_char_cm + pad_cm)
        elif ncols == 4 and (hdr_clean.startswith("Số") or hdr_clean.lower() == "run"):
            w_min = 1.15 if hdr_clean.lower() == "run" else max(longest_token * tok_char_cm + pad_cm, 2.25)
            w_tgt = w_min
        elif ncols == 4 and "cấu hình" in hdr_clean.lower():
            w_min = max(longest_token * 0.188 + pad_cm, 5.25)
            w_tgt = w_min
        elif ncols <= 4 and ci == 0 and hdr_clean.upper() == "STT":
            w_min = 1.25
            w_tgt = 1.25
        elif ncols <= 4 and "VIẾT TẮT" in hdr_clean.upper():
            w_min = max(longest_token * 0.24 + pad_cm, 2.05)
            w_tgt = w_min
        elif ncols == 5 and (hdr_clean.startswith("Tổng") or hdr_clean.startswith("Dev") or hdr_clean.startswith("Test")):
            w_min = max(longest_token * tok_char_cm + pad_cm, 1.75)
            w_tgt = w_min
        else:
            w_min = max(longest_token * tok_char_cm + pad_cm, 1.35)
            w_tgt = max(w_min, min(avg_len * avg_char_cm + 0.5, 9.0))
        mins.append(w_min)
        targets.append(w_tgt)

    min_sum = sum(mins)
    if min_sum >= total_cm:
        widths = [total_cm * m / min_sum for m in mins]
    else:
        extra_avail = total_cm - min_sum
        surpluses = [max(0.0, t - m) for m, t in zip(mins, targets)]
        surplus_sum = sum(surpluses)
        if surplus_sum > 0:
            widths = [m + extra_avail * (s / surplus_sum) for m, s in zip(mins, surpluses)]
        else:
            widths = [total_cm * m / min_sum for m in mins]

    widths = [round(w, 3) for w in widths]
    widths[-1] += round(total_cm - sum(widths), 3)
    return widths, font_pt


def _add_table_block(doc: Document, headers: list[str], rows: list[list[str]],
                     caption: str | None = None) -> None:
    widths, font_pt = _compute_col_widths(headers, rows)
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False

    tblPr = tbl._tbl.tblPr
    jc = tblPr.find(qn("w:jc"))
    if jc is None:
        jc = OxmlElement("w:jc")
        tblPr.append(jc)
    jc.set(qn("w:val"), "center")
    total_dxa = int(round(sum(widths) * 566.929133858))
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:w"), str(total_dxa))
    tblW.set(qn("w:type"), "dxa")
    tblLayout = parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>')
    tblPr.append(tblLayout)
    tblGrid = tbl._tbl.tblGrid
    if tblGrid is not None:
        for gc, w_cm in zip(tblGrid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(round(w_cm * 566.929133858))))
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="single" w:sz="8" w:space="0" w:color="1E293B"/>'
        '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="1E293B"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '</w:tblBorders>'
    )
    tblPr.append(borders)

    pad_v = 35 if len(headers) >= 13 else 70
    pad_h = 14 if len(headers) >= 13 else 85

    all_rows = [headers] + rows
    last_ri = len(all_rows) - 1
    for ri, row_vals in enumerate(all_rows):
        tr = tbl.rows[ri]
        trPr = tr._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        if ri == 0:
            trPr.append(OxmlElement("w:tblHeader"))

        is_bold_row = ri == 0 or (len(row_vals) > 0 and "**E8**" in row_vals[0])
        for ci in range(len(headers)):
            cell = tr.cells[ci]
            cell.width = Cm(widths[ci])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            tcPr = cell._tc.get_or_add_tcPr()
            tcW = tcPr.find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW")
                tcPr.insert(0, tcW)
            tcW.set(qn("w:w"), str(int(round(widths[ci] * 566.929133858))))
            tcW.set(qn("w:type"), "dxa")
            mar = parse_xml(
                f'<w:tcMar {nsdecls("w")}>'
                f'<w:top w:w="{pad_v}" w:type="dxa"/>'
                f'<w:bottom w:w="{pad_v}" w:type="dxa"/>'
                f'<w:left w:w="{pad_h}" w:type="dxa"/>'
                f'<w:right w:w="{pad_h}" w:type="dxa"/>'
                '</w:tcMar>'
            )
            tcPr.append(mar)
            if ri == 0:
                tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="E2E8F0"/>'))
            elif ri % 2 == 0:
                tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="F8FAFC"/>'))

            txt = row_vals[ci].strip() if ci < len(row_vals) else ""
            is_num_cell = _is_numeric_cell(re.sub(r"[`*]", "", txt))
            p = cell.paragraphs[0]
            pf = p.paragraph_format
            pf.space_before = Pt(0)
            pf.space_after = Pt(0)
            pf.line_spacing = 1.15
            if caption is not None and ri == last_ri:
                pf.keep_with_next = True
            if ri == 0 or is_num_cell or (len(headers) >= 13 and ci == 0) or (len(txt) <= 14 and "/" in txt):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif headers[ci].strip().upper() == "STT":
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _add_inline_runs(
                p, txt, base_size=font_pt, base_bold=is_bold_row,
                mono_size=max(7.0, font_pt - 2.0), allow_break=not is_num_cell,
            )

    if caption:
        # Remove literal "Bảng N: " prefix and insert dynamic SEQ field immediately BELOW table
        clean_cap = re.sub(r"^Bảng\s+\d+\s*:\s*", "", caption.strip())
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = cp.paragraph_format
        pf.line_spacing = 1.2
        pf.space_before = Pt(4)
        pf.space_after = Pt(8)
        pf.left_indent = Cm(0)
        pf.first_line_indent = Cm(0)
        pf.keep_with_next = False
        r1 = cp.add_run("Bảng ")
        _set_run_font(r1, size_pt=12.0, italic=True, color=BLACK)
        _add_field(cp, r"SEQ Bảng \* ARABIC", placeholder="1", size_pt=12.0, italic=True, color=BLACK)
        r2 = cp.add_run(f": {clean_cap}")
        _set_run_font(r2, size_pt=12.0, italic=True, color=BLACK)
    else:
        # Compact spacer after uncaptioned table
        sp = doc.add_paragraph()
        sp.paragraph_format.space_before = Pt(0)
        sp.paragraph_format.space_after = Pt(4)
        sp.paragraph_format.line_spacing = 1.0


def _add_figure_block(doc: Document, img_path: Path, alt_text: str) -> None:
    if not img_path.exists():
        raise FileNotFoundError(f"Missing figure file: {img_path}")
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(8)
    p_img.paragraph_format.space_after = Pt(4)
    p_img.paragraph_format.left_indent = Cm(0)
    p_img.paragraph_format.first_line_indent = Cm(0)
    p_img.paragraph_format.line_spacing = 1.0
    p_img.paragraph_format.keep_with_next = True
    run_img = p_img.add_run()
    run_img.add_picture(str(img_path), width=Cm(15.2))

    clean_alt = re.sub(r"^Hình\s+\d+\s*:\s*", "", alt_text.strip())
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(0)
    p_cap.paragraph_format.space_after = Pt(8)
    p_cap.paragraph_format.left_indent = Cm(0)
    p_cap.paragraph_format.first_line_indent = Cm(0)
    p_cap.paragraph_format.line_spacing = 1.2
    r1 = p_cap.add_run("Hình ")
    _set_run_font(r1, size_pt=12.0, italic=True, color=BLACK)
    _add_field(p_cap, r"SEQ Hình \* ARABIC", placeholder="1", size_pt=12.0, italic=True, color=BLACK)
    r2 = p_cap.add_run(f": {clean_alt}")
    _set_run_font(r2, size_pt=12.0, italic=True, color=BLACK)


def _add_toc_pages(doc: Document) -> None:
    specs = [
        ("MỤC LỤC", r'TOC \o "1-3" \h \z \u'),
        ("MỤC LỤC HÌNH ẢNH", r'TOC \h \z \c "Hình"'),
        ("MỤC LỤC BẢNG", r'TOC \h \z \c "Bảng"'),
    ]
    for title, instr in specs:
        h = doc.add_paragraph(title, style="TOC Heading")
        h.paragraph_format.page_break_before = True
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        _add_field(
            p, instr,
            placeholder="(Nhấn F9 hoặc cập nhật trường trong Word để hiển thị mục lục tự động)",
            size_pt=13.0, italic=True, color=MUTED,
        )


# ---------------------------------------------------------------------------
# Markdown parser -> Document elements
# ---------------------------------------------------------------------------

def _split_md_row(line: str) -> list[str]:
    sentinel = "\x00PIPE\x00"
    s = line.strip().replace("\\|", sentinel)
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.replace(sentinel, "|").strip() for c in s.split("|")]


def populate_body_from_markdown(doc: Document, md_path: Path) -> None:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    i = 0
    in_references = False
    toc_inserted = False
    first_h1_seen = False

    while i < len(lines):
        raw = lines[i]
        s = raw.strip()

        if not s or s.startswith("<!--"):
            i += 1
            continue

        # H1 chapters / front & back matter
        if s.startswith("## "):
            title = s[3:].strip()
            if title == "BẢNG CÁC TỪ VIẾT TẮT" and not toc_inserted:
                _add_toc_pages(doc)
                toc_inserted = True
            h = doc.add_paragraph(style="Heading 1")
            _add_inline_runs(h, title.upper(), base_size=14.0, base_bold=True)
            if first_h1_seen:
                h.paragraph_format.page_break_before = True
            first_h1_seen = True
            in_references = title == "DANH MỤC TÀI LIỆU THAM KHẢO"
            i += 1
            continue

        # H2 subsections
        if s.startswith("### "):
            title = s[4:].strip()
            h = doc.add_paragraph(style="Heading 2")
            _add_inline_runs(h, title, base_size=13.0, base_bold=True)
            i += 1
            continue

        # H3 sub-subsections
        if s.startswith("#### "):
            title = s[5:].strip()
            h = doc.add_paragraph(style="Heading 3")
            _add_inline_runs(h, title, base_size=13.0, base_bold=True, base_italic=True)
            i += 1
            continue

        # Images
        m_img = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", s)
        if m_img:
            alt, rel_path = m_img.group(1), m_img.group(2)
            img_path = (md_path.parent / rel_path).resolve()
            _add_figure_block(doc, img_path, alt)
            i += 1
            continue

        # Markdown table (optionally followed by *Bảng N: ...* caption below)
        if s.startswith("|") and i + 1 < len(lines) and re.fullmatch(r"[\|\s:-]+", lines[i + 1].strip()):
            headers = _split_md_row(lines[i])
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_split_md_row(lines[i]))
                i += 1
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            cap_text = None
            if j < len(lines):
                m_below = re.fullmatch(r"\*(Bảng\s+\d+:[^*]+)\*", lines[j].strip())
                if m_below:
                    cap_text = m_below.group(1)
                    i = j + 1
            _add_table_block(doc, headers, rows, caption=cap_text)
            continue

        # Lists (- ... or 1. ...)
        m_bul = re.match(r"^-\s+(.+)$", s)
        if m_bul:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.left_indent = Cm(0.75)
            p.paragraph_format.first_line_indent = Cm(-0.35)
            p.paragraph_format.space_after = Pt(4)
            r_dash = p.add_run("- ")
            _set_run_font(r_dash, size_pt=13.0, color=BLACK)
            _add_inline_runs(p, m_bul.group(1), base_size=13.0)
            i += 1
            continue

        # References inside DANH MỤC TÀI LIỆU THAM KHẢO
        if in_references:
            p = doc.add_paragraph(style="Bibliography")
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _add_inline_runs(p, s, base_size=12.0, mono_size=10.5)
            i += 1
            continue

        # Sub-items (a), b), c)...) -> justified per user requirement
        if re.match(r"^[a-z]\)\s+", s):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _add_inline_runs(p, s, base_size=13.0)
            i += 1
            continue

        # Numbered items (1., 2., 3...) inside body
        if re.match(r"^\d+\.\s+", s):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.left_indent = Cm(0.5)
            p.paragraph_format.first_line_indent = Cm(-0.5)
            _add_inline_runs(p, s, base_size=13.0)
            i += 1
            continue

        # Normal flowing paragraph (merge wrapped consecutive lines if any)
        para_lines = [s]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].strip().startswith(("#", "|", "![", "- ", "*Bảng "))
            and not re.match(r"^(\d+\.|[a-z]\))\s+", lines[i].strip())
        ):
            para_lines.append(lines[i].strip())
            i += 1
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _add_inline_runs(p, " ".join(para_lines), base_size=13.0)


def update_fields_and_export_pdf(docx_path: Path, pdf_path: Path) -> None:
    ps = f"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {{
    $doc = $word.Documents.Open('{str(docx_path.resolve())}')
    $doc.Repaginate()
    for ($i = 1; $i -le $doc.TablesOfContents.Count; $i++) {{
        $doc.TablesOfContents.Item($i).Update()
    }}
    for ($i = 1; $i -le $doc.TablesOfFigures.Count; $i++) {{
        $doc.TablesOfFigures.Item($i).Update()
    }}
    $null = $doc.Fields.Update()
    foreach ($sec in $doc.Sections) {{
        foreach ($hdr in $sec.Headers) {{ $null = $hdr.Range.Fields.Update() }}
        foreach ($ftr in $sec.Footers) {{ $null = $ftr.Range.Fields.Update() }}
    }}
    for ($i = 1; $i -le $doc.TablesOfContents.Count; $i++) {{
        $doc.TablesOfContents.Item($i).UpdatePageNumbers()
    }}
    for ($i = 1; $i -le $doc.TablesOfFigures.Count; $i++) {{
        $doc.TablesOfFigures.Item($i).UpdatePageNumbers()
    }}
    $doc.Repaginate()
    $pages = $doc.ComputeStatistics(2)
    $tocs = $doc.TablesOfContents.Count
    $tofs = $doc.TablesOfFigures.Count
    $doc.Save()
    $doc.ExportAsFixedFormat('{str(pdf_path.resolve())}', 17)
    Write-Output "WORD_EXPORT_OK pages=$pages tocs=$tocs tofs=$tofs"
    $doc.Close([ref]$false)
}} finally {{
    $word.Quit()
}}
"""
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Word COM export failed:\nSTDOUT:{res.stdout}\nSTDERR:{res.stderr}")
    print(res.stdout.strip())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--docx", type=Path, default=DEFAULT_DOCX)
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ap.add_argument("--skip-word-com", action="store_true")
    args = ap.parse_args()

    if not args.template.exists():
        raise FileNotFoundError(f"Template not found: {args.template}")
    if not args.md.exists():
        raise FileNotFoundError(f"Markdown report not found: {args.md}")

    args.docx.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.template, args.docx)

    doc = Document(str(args.docx))
    _configure_styles(doc)
    _update_covers_and_strip_sample_body(doc)
    _configure_sections(doc)
    _enable_update_fields_on_open(doc)
    populate_body_from_markdown(doc, args.md)
    doc.save(str(args.docx))
    print(f"Saved DOCX draft: {args.docx} ({args.docx.stat().st_size} bytes)")

    if not args.skip_word_com:
        update_fields_and_export_pdf(args.docx, args.pdf)
        print(f"Exported PDF: {args.pdf} ({args.pdf.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
