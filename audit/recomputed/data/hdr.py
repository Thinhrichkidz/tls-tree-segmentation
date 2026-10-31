"""Header-only reader for PLY/LAS/LAZ. Usage: python -I hdr.py OUT.csv PATH_OR_DIR [...]
Writes path,ext,size,mtime,n_points,comments/bbox. Never reads point bodies."""
import sys, os, csv, datetime, glob

def ply_header(p):
    with open(p, 'rb') as f:
        buf = b''
        while b'end_header' not in buf and len(buf) < 1_000_000:
            c = f.read(4096)
            if not c: break
            buf += c
    h = buf.split(b'end_header')[0].decode('latin-1', 'replace')
    n = None
    for line in h.splitlines():
        if line.startswith('element vertex'):
            n = int(line.split()[2])
    return n, h

def las_header(p):
    import laspy
    with laspy.open(p) as r:
        h = r.header
        info = dict(n=h.point_count, mins=list(h.mins), maxs=list(h.maxs), ver=str(h.version),
                    pf=h.point_format.id, sysid=h.system_identifier, sw=h.generating_software,
                    date=str(h.creation_date), scales=list(h.scales), offsets=list(h.offsets),
                    vlrs=[(v.user_id, v.record_id, v.description) for v in h.vlrs],
                    evlrs=[(v.user_id, v.record_id, v.description) for v in (h.evlrs or [])],
                    gps_type=int(h.global_encoding.gps_time_type) if hasattr(h.global_encoding, 'gps_time_type') else None,
                    wkt_bit=bool(getattr(h.global_encoding, 'wkt', False)),
                    dims=list(h.point_format.dimension_names))
        try:
            crs = h.parse_crs()
            info['crs'] = None if crs is None else crs.to_string()
        except Exception as e:
            info['crs'] = f'parse_crs error: {e!r}'
    return info

def files(args):
    for a in args:
        if os.path.isdir(a):
            for f in sorted(os.listdir(a)):
                fp = os.path.join(a, f)
                if os.path.isfile(fp): yield fp
        else:
            yield from sorted(glob.glob(a)) or [a]

if __name__ == '__main__':
    out = sys.argv[1]
    rows = []
    for p in files(sys.argv[2:]):
        ext = os.path.splitext(p)[1].lower()
        st = os.stat(p)
        row = dict(path=p, ext=ext, size=st.st_size,
                   mtime=datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds'),
                   n_points='', meta='')
        try:
            if ext == '.ply':
                n, h = ply_header(p)
                row['n_points'] = n
                row['meta'] = ' | '.join(l for l in h.splitlines() if not l.startswith('property'))
            elif ext in ('.las', '.laz'):
                i = las_header(p)
                row['n_points'] = i.pop('n')
                row['meta'] = repr(i)
        except Exception as e:
            row['meta'] = f'ERROR {e!r}'
        rows.append(row)
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f'{len(rows)} files -> {out}')
