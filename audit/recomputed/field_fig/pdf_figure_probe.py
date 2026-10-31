"""List images/vector drawings and metadata on PDF pages. Usage: python -I this.py pdf"""
import sys, pymupdf
doc = pymupdf.open(sys.argv[1]); print(doc.metadata)
for i, pg in enumerate(doc, 1):
    imgs = pg.get_images(full=True); dr = pg.get_drawings()
    if imgs or len(dr) > 5: print("page", i, "images", [(x[0], x[2], x[3]) for x in imgs], "vector paths", len(dr))
