"""Dependency-free .xlsx writer with cell styles (fills, bold, borders, wrap, number formats), frozen panes and widths.

A cell is a plain value, or a tuple (value, style) where style is a dict with optional keys:
fill (hex RGB), bold (bool), size (int), border (bool), wrap (bool), fmt (Excel number format string).
Header styling follows ITSMe_top10_results.xlsx: bold, fill DDEBF7, thin border, wrapped, top-aligned.
"""
import math
import zipfile
from xml.sax.saxutils import escape

HEADER = dict(bold=True, fill='DDEBF7', border=True, wrap=True)
TITLE = dict(bold=True, size=14)


def _col(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


class _Styles:
    def __init__(self):
        self.fonts = [(False, 11)]
        self.fills = [None, 'gray125']
        self.fmts = {}
        self.xfs = [(0, 0, 0, False, 0)]

    def index(self, st):
        if not st:
            return 0
        font = (bool(st.get('bold')), int(st.get('size', 11)))
        if font not in self.fonts:
            self.fonts.append(font)
        fill = st.get('fill')
        if fill and fill not in self.fills:
            self.fills.append(fill)
        fmt = st.get('fmt')
        if fmt and fmt not in self.fmts:
            self.fmts[fmt] = 164 + len(self.fmts)
        key = (self.fonts.index(font), self.fills.index(fill) if fill else 0, 1 if st.get('border') else 0,
               bool(st.get('wrap')), self.fmts.get(fmt, 0))
        if key not in self.xfs:
            self.xfs.append(key)
        return self.xfs.index(key)

    def xml(self):
        fmts = ''.join(f'<numFmt numFmtId="{i}" formatCode="{escape(f)}"/>' for f, i in self.fmts.items())
        fonts = ''.join(f'<font>{"<b/>" if b else ""}<sz val="{s}"/><name val="Calibri"/><family val="2"/></font>' for b, s in self.fonts)
        fills = '<fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>' + ''.join(
            f'<fill><patternFill patternType="solid"><fgColor rgb="FF{f}"/><bgColor indexed="64"/></patternFill></fill>' for f in self.fills[2:])
        xfs = ''.join(
            f'<xf numFmtId="{n}" fontId="{fo}" fillId="{fi}" borderId="{bo}" xfId="0"'
            f'{" applyNumberFormat=\"1\"" if n else ""}{" applyFont=\"1\"" if fo else ""}{" applyFill=\"1\"" if fi else ""}'
            f'{" applyBorder=\"1\"" if bo else ""}{" applyAlignment=\"1\"><alignment vertical=\"top\" wrapText=\"1\"/></xf>" if wr else "/>"}'
            for fo, fi, bo, wr, n in self.xfs)
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<numFmts count="{len(self.fmts)}">{fmts}</numFmts><fonts count="{len(self.fonts)}">{fonts}</fonts>'
                f'<fills count="{len(self.fills)}">{fills}</fills>'
                '<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>'
                '<border><left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/><diagonal/></border></borders>'
                '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                f'<cellXfs count="{len(self.xfs)}">{xfs}</cellXfs>'
                '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')


def _cell(ref, cell, styles):
    v, st = cell if isinstance(cell, tuple) else (cell, None)
    s = styles.index(st)
    sa = f' s="{s}"' if s else ''
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return f'<c r="{ref}"{sa}/>' if s else ''
    if isinstance(v, bool):
        return f'<c r="{ref}"{sa} t="b"><v>{int(v)}</v></c>'
    if isinstance(v, (int, float)):
        return f'<c r="{ref}"{sa}><v>{repr(float(v)) if isinstance(v, float) else v}</v></c>'
    return f'<c r="{ref}"{sa} t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'


def _filter_names(sheets):
    import re
    absref = lambda ref: ':'.join(re.sub(r'([A-Z]+)(\d+)', r'$\1$\2', p) for p in ref.split(':'))
    names = ''.join(f'<definedName name="_xlnm._FilterDatabase" localSheetId="{i}" hidden="1">'
                    f"'{escape(s['name'])}'!{absref(s['_filter_ref'])}</definedName>"
                    for i, s in enumerate(sheets) if s.get('_filter_ref'))
    return f'<definedNames>{names}</definedNames>' if names else ''


def write_xlsx(path, sheets):
    """sheets: list of dict(name, rows, freeze=(cols, rows) or None, widths=[...], filter_row=header row for an AutoFilter)."""
    styles = _Styles()
    bodies = []
    for sh in sheets:
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
        fz = sh.get('freeze')
        if fz:
            c, r = fz
            attrs = (f' xSplit="{c}"' if c else '') + (f' ySplit="{r}"' if r else '')
            pane = 'bottomRight' if c and r else ('bottomLeft' if r else 'topRight')
            out.append(f'<sheetViews><sheetView workbookViewId="0"><pane{attrs} topLeftCell="{_col(c + 1)}{r + 1}" '
                       f'activePane="{pane}" state="frozen"/></sheetView></sheetViews>')
        if sh.get('widths'):
            out.append('<cols>' + ''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
                                          for i, w in enumerate(sh['widths'], 1)) + '</cols>')
        out.append('<sheetData>')
        for r, row in enumerate(sh['rows'], 1):
            cells = ''.join(_cell(f'{_col(c)}{r}', v, styles) for c, v in enumerate(row, 1))
            out.append(f'<row r="{r}">{cells}</row>')
        out.append('</sheetData>')
        if sh.get('filter_row'):
            fr = sh['filter_row']
            sh['_filter_ref'] = f'A{fr}:{_col(max(len(r) for r in sh["rows"][fr - 1:]))}{len(sh["rows"])}'
            out.append(f'<autoFilter ref="{sh["_filter_ref"]}"/>')
        out.append('</worksheet>')
        bodies.append('\n'.join(out))
    n = len(sheets)
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED) as z:
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
                   + ''.join(f'<sheet name="{escape(s["name"])}" sheetId="{i}" r:id="rId{i}"/>' for i, s in enumerate(sheets, 1))
                   + '</sheets>' + _filter_names(sheets) + '</workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                             for i in range(1, n + 1))
                   + f'<Relationship Id="rId{n + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr('xl/styles.xml', styles.xml())
        for i, body in enumerate(bodies, 1):
            z.writestr(f'xl/worksheets/sheet{i}.xml', body)
