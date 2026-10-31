"""Render selected PDF pages to PNG. Usage: python -I render_pages.py pdf outdir prefix page1 page2 ..."""
import sys, pymupdf
doc = pymupdf.open(sys.argv[1]); out, pre = sys.argv[2], sys.argv[3]
print("pages", doc.page_count)
for p in map(int, sys.argv[4:]):
    doc[p-1].get_pixmap(dpi=150).save(f"{out}/{pre}_p{p}.png")
