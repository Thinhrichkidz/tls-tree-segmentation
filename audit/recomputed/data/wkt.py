"""Print WKT VLR (LASF_Projection 2112) text and RIEGL extra-bytes description for LAS/LAZ headers only."""
import sys, laspy
for p in sys.argv[1:]:
    with laspy.open(p) as r:
        print('==', p)
        for v in r.header.vlrs:
            if v.record_id == 2112:
                raw = getattr(v, 'string', None) or bytes(v.record_data_bytes()).decode('latin-1')
                print('WKT:', raw if isinstance(raw, str) else raw)
            elif v.record_id == 4:
                print('ExtraBytes:', [(e.name, e.description) for e in getattr(v, 'extra_bytes_structs', [])][:5])
