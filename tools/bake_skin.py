"""Rebake actual 2048px skin detail from the vendored Giantborn procedural source."""
from pathlib import Path
import sys,os
root=Path(__file__).resolve().parents[1]/'characters/giantborn-wanderer'
sys.path.insert(0,str(root/'source/tools/giant/kit'))
import bake,mh_data
if os.name=='nt':
    mh_data.MPFB_DIR='\\\\?\\'+str((root/'source/tools/giant/mpfb2').resolve())
    mh_data.target_path=lambda rel:os.path.normpath(os.path.join(mh_data.MPFB_DIR,mh_data.target_rel(rel)))
os.environ.setdefault('BAKE_THREADS','8')
bake.SETTINGS['size']=2048
bake.run(str(root/'textures/bake'),('albedo','rough','normal'))
