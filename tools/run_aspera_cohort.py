"""Execute only the Aspera cohort lesson with every transfer intercepted."""
from datetime import datetime, timezone
import argparse
import gzip
from importlib.metadata import distribution, version
import json
import os
from pathlib import Path
import sys
import tempfile
import nbformat
from nbclient import NotebookClient
from run_tcia_workshop import PRELUDE

ROOT=Path(__file__).resolve().parents[1]
POSTLUDE=r'''
assert aspera_manifest.scope['is_sample'] and len(aspera_manifest.rows)==2
assert aspera_manifest.scope['matching_files']>2
assert len(selected_participants)==2 and len(_transfer_calls)>0
paths={row['packagePath'] for row in aspera_manifest.rows}
assert {p for call in _transfer_calls for p in call[call.index('receive')+3:]}==paths
assert not SOURCE_NIFTI and not MASK_NIFTI
assert all('ALL' not in call for call in _transfer_calls)
if _mode == 'record':
    _capture['observed_at_utc']=datetime.now(timezone.utc).isoformat()
    _capture['fingerprint']=aspera_manifest.provenance.release_fingerprint
    _cassette_path.parent.mkdir(parents=True,exist_ok=True)
    _cassette_path.write_bytes(_gzip.compress(_json.dumps(_capture,separators=(',',':')).encode(),mtime=0))
_Path(REPORT_VALUE).write_text(_json.dumps({
    'ok':True,'metadata_snapshot':aspera_manifest.provenance.release_fingerprint,
    'selected_participants':len(selected_participants),'matching_files':aspera_manifest.scope['matching_files'],
    'exported_files':len(aspera_manifest.rows),'intercepted_aspera_calls':len(_transfer_calls),
    'payload_transfers':0,'package_version':version('tcia_utils'),'mode':_mode},indent=2))
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['fixture','live','record'],default='fixture')
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    import tcia_utils
    if 'site-packages' not in Path(tcia_utils.__file__).parts:
        raise RuntimeError('Validate an installed wheel, not a source-tree import')
    source=ROOT/'TCIA_Aspera_CLI_Downloads.ipynb'
    n=nbformat.read(source,as_version=4)
    cells=[c for c in n.cells if c.metadata.get('id','').startswith('aspera-cohort-')]
    assert cells
    cells=[c for c in cells if 'cohort-installation' not in c.metadata.get('tags',[])]
    for c in cells:
        c['id']=c.metadata['id']  # QA notebook uses the current cell-ID schema.
    cassette=ROOT/'tcia_utils_v4/_fixtures/aspera-cohort-public-metadata.json.gz'
    with tempfile.TemporaryDirectory(prefix='aspera-cohort-qa-') as directory:
        tmp=Path(directory)
        kernel=tmp/'kernels'/'aspera-cohort';kernel.mkdir(parents=True)
        (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Aspera cohort QA','language':'python'}))
        os.environ['JUPYTER_PATH']=str(tmp)+os.pathsep+os.environ.get('JUPYTER_PATH','')
        prelude=PRELUDE.replace('MODE_VALUE',repr(args.mode)).replace('CASSETTE_VALUE',repr(str(cassette)))
        prelude+='''\n_transfer_calls=[]\ndef _intercept_aspera(command, *args, **kwargs):\n    assert isinstance(command,list) and 'ascli' in command and 'receive' in command\n    _transfer_calls.append(command)\n    return 0\n_subprocess.call=_intercept_aspera\n'''
        report=tmp/'report.json'
        cells=[nbformat.v4.new_code_cell(prelude)]+cells+[nbformat.v4.new_code_cell('from datetime import datetime, timezone\nfrom importlib.metadata import version\n'+POSTLUDE.replace('REPORT_VALUE',repr(str(report))))]
        NotebookClient(nbformat.v4.new_notebook(cells=cells),timeout=300,kernel_name='aspera-cohort',resources={'metadata':{'path':str(tmp)}}).execute()
        findings=json.loads(report.read_text())
        findings['observed_at_utc']=datetime.now(timezone.utc).isoformat()
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(findings,indent=2)+'\n')
        print(json.dumps(findings,indent=2))

if __name__=='__main__':main()
