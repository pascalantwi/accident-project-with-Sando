"""Export manuscript/manuscript_draft.md to Word (.docx) and PDF.

The markdown is lightly adapted for pandoc (superscripts, line breaks, figure images without
duplicate captions, internal cross-reference links turned into plain text, citation links kept),
converted to .docx with journal-style formatting (Times New Roman 12 pt, US Letter, 1-inch margins,
9 pt tables), and the .docx is converted to PDF with LibreOffice so both files match.

Usage: python src/manuscript/export.py      # writes manuscript/manuscript_draft.docx and .pdf
"""
import pathlib
import re
import shutil
import subprocess
import tempfile

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Inches, Pt, RGBColor

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHROME = shutil.which("chromium") or "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
PRINT_CSS = """
@page { size: Letter; margin: 1in; }
body { font-family: 'Times New Roman', 'Liberation Serif', serif; font-size: 12pt; line-height: 1.35;
       max-width: none; margin: 0; padding: 0; color: #000; }
h1 { font-size: 16pt; line-height: 1.25; margin: 0 0 10pt; }
h2 { font-size: 14pt; margin: 16pt 0 6pt; break-after: avoid; }
h3 { font-size: 12pt; margin: 12pt 0 4pt; break-after: avoid; }
p { margin: 0 0 7pt; text-align: justify; hyphens: auto; }
a { color: #1f4e9c; text-decoration: none; }
img { display: block; max-width: 100%; margin: 8pt auto 4pt; break-inside: avoid; }
figure { margin: 0; break-inside: avoid; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; line-height: 1.2; margin: 4pt 0 12pt;
        break-inside: auto; }
th, td { padding: 2pt 4pt; vertical-align: top; text-align: left; }
thead th { border-top: 1.2pt solid #000; border-bottom: 0.8pt solid #000; font-weight: normal; }
tbody tr:last-child td { border-bottom: 1.2pt solid #000; }
td[style*="right"], th[style*="right"] { text-align: right; }
math[display="block"] { margin: 8pt auto; }
p:has(+ table), p:has(+ figure), p:has(+ p > img) { break-after: avoid; }
p:has(> img) { break-after: avoid; }
hr { border: none; border-top: 0.6pt solid #888; margin: 18pt 0; }
"""
SRC = ROOT / "manuscript" / "manuscript_draft.md"
OUT = ROOT / "manuscript" / "manuscript_draft.docx"


def prepare(md):
    md = re.sub(r'<a id="[\w-]+"></a>', "", md)                                # anchors
    md = re.sub(r"<sup>(.*?)</sup>", lambda m: "^" + m.group(1).replace("\\*", "\\*") + "^", md)
    md = md.replace("<br>\n", "\\\n")                                         # hard line breaks
    md = re.sub(r"\[([^\[\]]+)\]\(#[\w-]+\)", r"\1", md)                       # internal links -> text
    # figures: image without alt text (the bold caption paragraph that follows is the caption)
    md = re.sub(r"!\[[^\]]*\]\(([^)]+\.png)\)", r"![](\1){width=6.3in}", md)
    md = re.sub(r"^\*\[Author note: (.*?)\]\*$", r"*[Author note: \1]*", md, flags=re.M)
    return md


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def set_fonts(st, name="Times New Roman"):
    """Set explicit fonts on a style and drop theme-font references that override them."""
    rpr = st.element.get_or_add_rPr()
    rfonts = rpr.find(W_NS + "rFonts")
    if rfonts is None:
        rfonts = rpr.makeelement(W_NS + "rFonts", {})
        rpr.insert(0, rfonts)
    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        rfonts.attrib.pop(W_NS + attr, None)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(W_NS + attr, name)


def fit_table(table, total_in=6.5, font_pt=9):
    """Column widths in proportion to content, never narrower than the longest word."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    ncol = len(table.columns)
    need, want = [1.0] * ncol, [1.0] * ncol
    for row in table.rows:
        for j, cell in enumerate(row.cells[:ncol]):
            text = cell.text.strip()
            words = text.split() or [""]
            need[j] = max(need[j], max(len(w) for w in words))
            want[j] = max(want[j], min(len(text), 28))
    # every column first gets room for its longest word (~0.075 in per character at 9 pt plus
    # cell padding); the remaining width is shared in proportion to the column's content
    minimum = [n * 0.085 * font_pt / 9 + 0.24 for n in need]
    spare = max(total_in - sum(minimum), 0.0)
    extra = [max(w - n, 0.0) for n, w in zip(need, want)]
    widths = [m + (spare * e / sum(extra) if sum(extra) else spare / ncol) for m, e in zip(minimum, extra)]
    widths = [w * total_in / sum(widths) for w in widths]
    tbl = table._tbl
    tblPr = tbl.tblPr
    layout = tblPr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tblPr.append(layout)
    layout.set(qn("w:type"), "fixed")
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:w"), str(int(total_in * 1440)))
    tblW.set(qn("w:type"), "dxa")
    grid = tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(w * 1440)))
    for row in table.rows:
        for j, cell in enumerate(row.cells[:ncol]):
            cell.width = Inches(widths[j])
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                for r in p.runs:
                    r.font.size = Pt(font_pt)
                    r.font.name = "Times New Roman"
    return True


def section_break(paragraph, landscape):
    """Insert a paragraph before `paragraph` that ends a section (portrait or landscape)."""
    import copy
    from docx.oxml.ns import qn
    new_p = paragraph.insert_paragraph_before()
    sect = copy.deepcopy(paragraph.part.document.sections[-1]._sectPr)
    pgSz = sect.find(qn("w:pgSz"))
    w, h = Inches(8.5), Inches(11)
    if landscape:
        pgSz.set(qn("w:orient"), "landscape")
        pgSz.set(qn("w:w"), str(int(h.inches * 1440)))
        pgSz.set(qn("w:h"), str(int(w.inches * 1440)))
    else:
        pgSz.attrib.pop(qn("w:orient"), None)
        pgSz.set(qn("w:w"), str(int(w.inches * 1440)))
        pgSz.set(qn("w:h"), str(int(h.inches * 1440)))
    for t in sect.findall(qn("w:type")):
        sect.remove(t)
    new_p._p.get_or_add_pPr().append(sect)
    return new_p


WIDE_TABLES = ("Scenario",)          # tables set on a landscape page (also any table with 9+ columns)


def style(path):
    doc = Document(path)
    for sec in doc.sections:
        sec.orientation = WD_ORIENT.PORTRAIT
        sec.page_width, sec.page_height = Inches(8.5), Inches(11)
        for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(sec, side, Inches(1))
    styles = {st.name.lower(): st for st in doc.styles if st.name}
    sizes = {"normal": 12, "body text": 12, "first paragraph": 12, "compact": 12, "title": 16,
             "heading 1": 14, "heading 2": 12, "heading 3": 12, "abstract": 11, "bibliography": 11}
    for name, size in sizes.items():
        st = styles.get(name)
        if st is None:
            continue
        set_fonts(st)
        st.font.size = Pt(size)
        if name.startswith("heading") or name == "title":
            st.font.color.rgb = RGBColor(0, 0, 0)
    for name in ("body text", "first paragraph"):
        if name in styles:
            pf = styles[name].paragraph_format
            pf.space_after, pf.line_spacing = Pt(6), 1.15
    from docx.text.paragraph import Paragraph
    for table in doc.tables:
        wide = table.rows[0].cells[0].text.strip() in WIDE_TABLES or len(table.columns) >= 9
        fit_table(table, total_in=9.0 if wide else 6.5)
        if wide:
            body = table._tbl.getparent()
            idx = list(body).index(table._tbl)
            prev = body[idx - 1]
            if prev.tag != W_NS + "p":
                from docx.oxml import OxmlElement
                prev = OxmlElement("w:p")
                table._tbl.addprevious(prev)
            caption = Paragraph(prev, table._parent)                 # "Table n." caption paragraph
            nxt = table._tbl.getnext()
            if nxt is None or nxt.tag != W_NS + "p":                  # make sure a paragraph follows
                from docx.oxml import OxmlElement
                nxt = OxmlElement("w:p")
                table._tbl.addnext(nxt)
            after = Paragraph(nxt, table._parent)                    # paragraph following the table
            section_break(caption, landscape=False)                 # ends the portrait section
            section_break(after, landscape=True)                    # ends the landscape section
    doc.save(path)


def main():
    md = prepare(SRC.read_text())
    with tempfile.TemporaryDirectory() as tmp:
        tmp_md = pathlib.Path(tmp) / "manuscript.md"
        tmp_md.write_text(md)
        subprocess.run(["pandoc", str(tmp_md), "-f", "markdown+pipe_tables+tex_math_dollars+superscript",
                        "-t", "docx", "--resource-path", str(SRC.parent), "-o", str(OUT)], check=True)
        style(OUT)
        css = pathlib.Path(tmp) / "print.css"
        css.write_text(PRINT_CSS)
        html = pathlib.Path(tmp) / "manuscript.html"
        subprocess.run(["pandoc", str(tmp_md), "-f", "markdown+pipe_tables+tex_math_dollars+superscript",
                        "-t", "html5", "-s", "--mathml", "--embed-resources", "--css", str(css),
                        "--metadata", "pagetitle=Manuscript", "--resource-path", str(SRC.parent),
                        "-o", str(html)], check=True)
        subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={OUT.with_suffix('.pdf')}", html.as_uri()],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(OUT, OUT.with_suffix(".pdf"))


if __name__ == "__main__":
    main()
