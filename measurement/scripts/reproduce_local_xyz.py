"""Explicit ONE-tree derived-file reproduction; original data are read-only."""
from pathlib import Path
import argparse,csv,json,sys
W=Path(__file__).resolve().parents[1];ROOT=W.parent
parser=argparse.ArgumentParser();parser.add_argument('--tree',default='tree_146');parser.add_argument('--output',required=True);args=parser.parse_args()
sys.path.insert(0,str(ROOT/'verification_output/_deps'))
import numpy as np
from plyfile import PlyData
rows=list(csv.DictReader((W/'environment/home_selection_manifest.csv').open(encoding='utf-8-sig')))
row=next(r for r in rows if r['stable_tree_id']==args.tree)
transform=json.loads((W/'terrain_reference'/args.tree/'coordinate_transform.json').read_text())
offset=np.array(transform['absolute_to_local_subtract_xyz'],dtype='f8')
v=PlyData.read(str(ROOT/row['input_ply_path']),mmap='r')['vertex'].data
p=np.column_stack([v[k] for k in ['x','y','z']]).astype('f8');local=p-offset
out=Path(args.output).resolve()
if out.exists():raise FileExistsError('Choose a new diagnostic output; existing inputs will not be overwritten')
allowed=(W/'results').resolve()
if not out.is_relative_to(allowed):raise ValueError('Diagnostic output must be inside measurement_pipeline/results')
out.parent.mkdir(parents=True,exist_ok=True)
np.savetxt(out,local,fmt='%.12f',header='X Y Z',comments='')
check=np.loadtxt(out,skiprows=1);error=float(np.max(np.abs(check+offset-p)))
assert len(check)==int(row['point_count']) and error<1e-8
print(json.dumps(dict(tree=args.tree,points=len(p),roundtrip_max_error_m=error,output=str(out),original_modified=False),indent=2))
