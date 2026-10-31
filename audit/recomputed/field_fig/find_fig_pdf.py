"""Find small single-page PDFs whose page size matches a target (w h in pt). Usage: python -I this.py w h root..."""
import sys, os, pymupdf
w, h = float(sys.argv[1]), float(sys.argv[2])
for root in sys.argv[3:]:
    for dp, dn, fn in os.walk(root):
        dn[:] = [x for x in dn if x not in ("environment", ".venv", ".home-venv", "node_modules")]
        for f in fn:
            if f.lower().endswith(".pdf"):
                p = os.path.join(dp, f)
                try:
                    d = pymupdf.open(p)
                    r = d[0].rect
                    if d.page_count <= 2 and (abs(r.width - w) < 3 and abs(r.height - h) < 3 or "status" in f.lower()):
                        print(p, d.page_count, round(r.width, 1), round(r.height, 1))
                except Exception as e:
                    pass
