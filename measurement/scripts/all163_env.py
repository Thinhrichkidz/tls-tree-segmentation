"""Print the Python-side versions used by the all-163 batch as one JSON line."""
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'verification_output' / '_deps'))
import numpy
import scipy
import plyfile
import matplotlib

print(json.dumps(dict(python=sys.version.split()[0], numpy=numpy.__version__, scipy=scipy.__version__,
                      plyfile=getattr(plyfile, '__version__', 'unknown'), matplotlib=matplotlib.__version__,
                      machine=platform.machine(), processor=platform.processor(), os=platform.platform())))
