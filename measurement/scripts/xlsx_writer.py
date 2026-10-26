"""Minimal dependency-free .xlsx writer (inline strings, numbers, bold header row, column widths, frozen header).

Used because no spreadsheet library is installed in the project environments. Values: str, int, float, None.
"""
import math
import zipfile
from xml.sax.saxutils import escape


def _col(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref, v, style):
    st = f' s="{style}"' if style else ''
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return f'<c r="{ref}"{st}/>'
    if isinstance(v, bool):
        v = 'TRUE' if v else 'FALSE'
    if isinstance(v, (int, float)):
        return f'<c r="{ref}"{st}><v>{repr(float(v)) if isinstance(v, float) else v}</v></c>'
    text = escape(str(v)).replace('\n', '&#10;')
    return f'<c r="{ref}"{st} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _sheet(rows, header_row, widths):
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
    if header_row:
        out.append(f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="{header_row}" topLeftCell="A{header_row + 1}" '
                   'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
    if widths:
        out.append('<cols>' + ''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
                                      for i, w in enumerate(widths, 1)) + '</cols>')
    out.append('<sheetData>')
    for r, row in enumerate(rows, 1):
        style = 1 if r == header_row else (2 if r == 1 else 0)
        out.append(f'<row r="{r}">' + ''.join(_cell(f'{_col(c)}{r}', v, style if (style != 2 or c == 1) else 0)
                                             for c, v in enumerate(row, 1)) + '</row>')
    out.append('</sheetData></worksheet>')
    return '\n'.join(out)


def read_xlsx_rows(path):
    """Read back a workbook written by write_xlsx: {sheet name: list of rows}, numbers as float, blanks as None."""
    import re
    import xml.etree.ElementTree as ET
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    with zipfile.ZipFile(path) as z:
        names = [s.get('name') for s in ET.fromstring(z.read('xl/workbook.xml')).iter(ns + 'sheet')]
        out = {}
        for i, name in enumerate(names, 1):
            rows = []
            for row in ET.fromstring(z.read(f'xl/worksheets/sheet{i}.xml')).iter(ns + 'row'):
                cells = {}
                for c in row.iter(ns + 'c'):
                    col = 0
                    for ch in re.match(r'[A-Z]+', c.get('r')).group():
                        col = col * 26 + ord(ch) - 64
                    v, t = c.find(ns + 'v'), c.find(f'{ns}is/{ns}t')
                    cells[col] = float(v.text) if v is not None else (t.text if t is not None else None)
                rows.append([cells.get(k) for k in range(1, max(cells, default=0) + 1)])
            out[name] = rows
        return out


def write_xlsx(path, sheets):
    """sheets: list of dict(name, rows, header_row (1-based or None), widths)."""
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED) as z:
        n = len(sheets)
        z.writestr('[Content_Types].xml',
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                   + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                             for i in range(1, n + 1)) + '</Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + ''.join(f'<sheet name="{escape(s["name"])}" sheetId="{i}" r:id="rId{i}"/>' for i, s in enumerate(sheets, 1)) + '</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                             for i in range(1, n + 1))
                   + f'<Relationship Id="rId{n + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr('xl/styles.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   '<fonts count="3"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font>'
                   '<font><b/><sz val="14"/><name val="Calibri"/></font></fonts>'
                   '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
                   '<fill><patternFill patternType="solid"><fgColor rgb="FFDDEBF7"/><bgColor indexed="64"/></patternFill></fill></fills>'
                   '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
                   '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                   '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
                   '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
                   '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs></styleSheet>')
        for i, s in enumerate(sheets, 1):
            z.writestr(f'xl/worksheets/sheet{i}.xml', _sheet(s['rows'], s.get('header_row'), s.get('widths')))
