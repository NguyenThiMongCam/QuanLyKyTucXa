"""Đọc / ghi file Excel (.xlsx) chỉ bằng thư viện chuẩn của Python (zipfile + xml) - không cần cài openpyxl.

write_xlsx(path, headers, rows, widths=None, sheet_name="Sheet1")
read_xlsx(path) -> list[list[str]]   (sheet đầu tiên; mọi ô trả về dạng chuỗi)
"""
import re
import zipfile
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_BAD_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _col_letter(i):
    """0 -> A, 25 -> Z, 26 -> AA"""
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _col_index(ref):
    letters = re.match(r"[A-Za-z]+", ref).group().upper()
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _cell(ref, value, style=0):
    s = f' s="{style}"' if style else ""
    if isinstance(value, bool) or value is None:
        value = "" if value is None else str(value)
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"{s}><v>{value}</v></c>'
    text = escape(_BAD_XML.sub("", str(value)))
    return f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def write_xlsx(path, headers, rows, widths=None, sheet_name="Sheet1"):
    sheet_name = re.sub(r"[\[\]:*?/\\]", " ", sheet_name)[:31] or "Sheet1"
    data = []
    data.append("<row r=\"1\">" + "".join(_cell(f"{_col_letter(i)}1", h, 1) for i, h in enumerate(headers)) + "</row>")
    for n, row in enumerate(rows, start=2):
        data.append(f'<row r="{n}">' + "".join(_cell(f"{_col_letter(i)}{n}", v) for i, v in enumerate(row)) + "</row>")
    cols = ""
    if widths:
        cols = "<cols>" + "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>'
                                  for i, w in enumerate(widths)) + "</cols>"
    sheet = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             f'<worksheet xmlns="{NS}"><sheetViews><sheetView workbookViewId="0">'
             f'<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
             f'{cols}<sheetData>{"".join(data)}</sheetData></worksheet>')
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="{NS}">'
              '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
              '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
              '<fills count="2"><fill><patternFill patternType="none"/></fill>'
              '<fill><patternFill patternType="gray125"/></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
              '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
    workbook = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<workbook xmlns="{NS}" xmlns:r="{REL_NS}"><sheets>'
                f'<sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               f'<Relationship Id="rId1" Type="{REL_NS}/worksheet" Target="worksheets/sheet1.xml"/>'
               f'<Relationship Id="rId2" Type="{REL_NS}/styles" Target="styles.xml"/></Relationships>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 f'<Relationship Id="rId1" Type="{REL_NS}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/xl/workbook.xml" '
             'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
             '<Override PartName="/xl/worksheets/sheet1.xml" '
             'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
             '<Override PartName="/xl/styles.xml" '
             'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles)
        z.writestr("xl/worksheets/sheet1.xml", sheet)


def _num_text(v):
    try:
        f = float(v)
    except ValueError:
        return v
    return str(int(f)) if f.is_integer() else repr(f)


def read_xlsx(path):
    """Đọc sheet đầu tiên, trả về list các dòng (mỗi dòng là list chuỗi). Ném ValueError nếu file hỏng."""
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        raise ValueError("File không phải định dạng .xlsx hợp lệ.")
    with z:
        names = set(z.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")):
                if _local(si.tag) == "si":
                    shared.append("".join(t.text or "" for t in si.iter() if _local(t.tag) == "t"))
        sheet_path = None
        try:                                            # tìm sheet đầu tiên qua workbook.xml + rels
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            first = next(e for e in wb.iter() if _local(e.tag) == "sheet")
            rid = next(v for k, v in first.attrib.items() if _local(k) == "id")
            for rel in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
                if rel.attrib.get("Id") == rid:
                    t = rel.attrib["Target"]
                    sheet_path = t.lstrip("/") if t.startswith("/") else "xl/" + t
        except (KeyError, StopIteration, ET.ParseError):
            pass
        if sheet_path not in names:
            cands = sorted(n for n in names if n.startswith("xl/worksheets/") and n.endswith(".xml"))
            if not cands:
                raise ValueError("Không tìm thấy trang tính nào trong file Excel.")
            sheet_path = cands[0]
        root = ET.fromstring(z.read(sheet_path))

    rows = []
    for row in root.iter():
        if _local(row.tag) != "row":
            continue
        cells, nxt = {}, 0
        for c in row:
            if _local(c.tag) != "c":
                continue
            idx = _col_index(c.attrib["r"]) if "r" in c.attrib else nxt
            nxt = idx + 1
            t, v = c.attrib.get("t"), ""
            vel = next((e for e in c if _local(e.tag) == "v"), None)
            if t == "inlineStr":
                v = "".join(e.text or "" for e in c.iter() if _local(e.tag) == "t")
            elif vel is not None and vel.text is not None:
                if t == "s":
                    try:
                        v = shared[int(vel.text)]
                    except (ValueError, IndexError):
                        v = ""
                elif t == "b":
                    v = "TRUE" if vel.text == "1" else "FALSE"
                elif t in ("str", "e"):
                    v = "" if t == "e" else vel.text
                else:
                    v = _num_text(vel.text)
            cells[idx] = v.strip()
        rn = int(row.attrib["r"]) if "r" in row.attrib else len(rows) + 1
        while len(rows) < rn - 1:                       # giữ đúng số dòng (dòng trống ở giữa)
            rows.append([])
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows