"""Execute the standalone workshop against an installed wheel.

Readers do not need this runner or its recorded public-metadata cassette.
Fixture mode rejects every unrecorded HTTP request. Live/record modes allow
only the public metadata API and the official small manifests used by the lesson.
Payload subprocesses are prohibited in all validation modes.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gzip
from importlib.metadata import distribution, version
import json
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient

NAME = 'TCIA_Dataset_and_Participant_Queries.ipynb'
ROOT = Path(__file__).resolve().parents[1]

PRELUDE = r'''
import base64 as _b64, gzip as _gzip, json as _json
from pathlib import Path as _Path
from urllib.parse import urlsplit as _split
import httpx as _httpx
import subprocess as _subprocess
_mode = MODE_VALUE
_cassette_path = _Path(CASSETTE_VALUE)
_capture = _json.loads(_gzip.decompress(_cassette_path.read_bytes())) if _mode == 'fixture' else {'requests': {}}
_original_send = _httpx.Client.send

def _request_key(request):
    return _json.dumps([request.method, str(request.url), request.content.decode()], separators=(',', ':'))

def _send_metadata(self, request, **kwargs):
    url = _split(str(request.url))
    allowed = (url.scheme == 'https' and (
        (url.hostname == 'tcia.duckdns.org' and url.path.startswith('/v2/')) or
        (url.hostname == 'www.cancerimagingarchive.net' and url.path.startswith('/wp-content/uploads/')
         and url.path.endswith(('.tcia', '.csv')))))
    if not allowed or request.headers.get('authorization'):
        raise AssertionError('Validation forbids payloads, credentials, and unexpected HTTP routes.')
    key = _request_key(request)
    if _mode == 'fixture':
        if key not in _capture['requests']:
            raise AssertionError('Unrecorded metadata request: ' + request.method + ' ' + url.path)
        item = _capture['requests'][key]
        return _httpx.Response(item['status'], headers=item['headers'],
                               content=_b64.b64decode(item['body']), request=request)
    response = _original_send(self, request, **kwargs)
    body = response.read()
    if len(body) > 10_000_000:
        raise AssertionError('Unexpectedly large metadata response.')
    _capture['requests'][key] = {'status': response.status_code,
        'headers': {'content-type': response.headers.get('content-type', '')},
        'body': _b64.b64encode(body).decode()}
    return response

_httpx.Client.send = _send_metadata

def _forbid_transfer(*args, **kwargs):
    raise AssertionError('Payload commands must remain off during notebook validation.')
_subprocess.run = _forbid_transfer
_subprocess.check_call = _forbid_transfer
print('RECORDED PUBLIC METADATA - not a live query' if _mode == 'fixture' else 'LIVE PUBLIC METADATA - no image transfers')
'''

POSTLUDE = r'''
assert not INSTALL_FROM_PYPI
assert not DOWNLOAD_PUBLIC_DICOM and not DOWNLOAD_CONTROLLED_CMB and not DOWNLOAD_CONTROLLED_CT
assert not SOURCE_NIFTI and not MASK_NIFTI
assert len(cohort) > 0 and len(brain_cohort) > 0 and len(face_selection) > 0
assert cohort['short_title'].nunique() >= 2, 'Default cohort must actually span datasets.'
assert {'CT', 'SEG'}.issubset(set(face_selection['modality']))
assert set(face_selection['access_level']) == {'controlled'}
assert len(download_plan) == len(retriever_groups) + len(other_groups)
assert len(other_groups) > 0, 'Reassess the package limitation if current routing has changed.'
assert set(pd.read_csv(face_manifest).columns) == {'drs_uri'}
assert len(pd.read_csv(face_manifest)) == face_selection['drs_uri'].nunique()
assert participant_assets.shape[0] > 0 and len(example_facts) > 0
assert len(brain_files) > 0
if _mode == 'record':
    _capture['observed_at_utc'] = datetime.now(timezone.utc).isoformat()
    _capture['fingerprint'] = SNAPSHOT
    _cassette_path.parent.mkdir(parents=True, exist_ok=True)
    _cassette_path.write_bytes(_gzip.compress(_json.dumps(_capture, separators=(',', ':')).encode(), mtime=0))
_report = {'fingerprint': SNAPSHOT, 'dataset_groups': len(download_plan),
    'cli_groups': len(retriever_groups), 'collection_link_groups': len(other_groups),
    'candidate_participant_records': len(candidates), 'matched_participant_records': len(cohort),
    'matched_collections': sorted(cohort['short_title'].unique().tolist()),
    'resolved_clinical_values': len(clinical_summary), 'example_clinical_facts': len(example_facts),
    'brain_participant_records': int(brain_cohort['participant_key'].nunique()),
    'brain_segmentation_files': len(brain_cohort), 'brain_example_files': len(brain_files),
    'controlled_ct_seg_studies': len(face_cohort), 'controlled_selected_files': len(face_selection),
    'unique_http_requests': len(_capture['requests']), 'payload_transfers': 0,
    'package_version': version('tcia_utils'), 'python': sys.version.split()[0]}
_Path(REPORT_VALUE).write_text(_json.dumps(_report, indent=2))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=ROOT / 'tcia_utils_v4')
    parser.add_argument('--mode', choices=['fixture', 'live', 'record'], default='fixture')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--executed', type=Path, help='optional local executed copy, never the maintained source')
    args = parser.parse_args()
    notebooks = args.directory.resolve()
    source = notebooks / NAME
    cassette = notebooks / '_fixtures' / 'workshop-public-metadata.json.gz'
    import tcia_utils
    if 'site-packages' not in Path(tcia_utils.__file__).resolve().parts:
        raise RuntimeError('Install the wheel; source-tree imports are not validation evidence.')
    direct_url = distribution('tcia_utils').read_text('direct_url.json')
    if direct_url and json.loads(direct_url).get('dir_info', {}).get('editable'):
        raise RuntimeError('Editable installs are not allowed for notebook validation.')
    with tempfile.TemporaryDirectory(prefix='tcia-workshop-qa-') as tmp:
        temporary = Path(tmp)
        kernel = temporary / 'kernels' / 'tcia-workshop'
        kernel.mkdir(parents=True)
        (kernel / 'kernel.json').write_text(json.dumps({
            'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
            'display_name': 'TCIA workshop validation', 'language': 'python'}))
        os.environ['JUPYTER_PATH'] = str(temporary) + os.pathsep + os.environ.get('JUPYTER_PATH', '')
        os.environ['TCIA_EXAMPLE_OUTPUT_DIR'] = str(temporary / 'output')
        report_path = temporary / 'report.json'
        nb = nbformat.read(source, as_version=4)
        nbformat.validate(nb)
        prelude = PRELUDE.replace('MODE_VALUE', repr(args.mode)).replace('CASSETTE_VALUE', repr(str(cassette)))
        postlude = 'import sys\n' + POSTLUDE.replace('REPORT_VALUE', repr(str(report_path)))
        nb.cells.insert(0, nbformat.v4.new_code_cell(prelude))
        nb.cells.append(nbformat.v4.new_code_cell(postlude))
        try:
            executed = NotebookClient(nb, timeout=240, kernel_name='tcia-workshop',
                resources={'metadata': {'path': str(notebooks)}}).execute()
        except Exception:
            nbformat.write(nb, temporary / 'failed.ipynb')
            raise
        # Do not retain QA-only injection cells in the readable executed copy.
        executed.cells = executed.cells[1:-1]
        outputs = '\n'.join(str(item.get('text', '')) for cell in executed.cells
                           for item in cell.get('outputs', []) if item.output_type == 'stream')
        import re
        if re.search(r'/Users/|/private/|Bearer\s+|BEGIN PRIVATE KEY', outputs, re.I):
            raise AssertionError('Notebook emitted a private path or credential-shaped text.')
        findings = json.loads(report_path.read_text())
        findings.update({'observed_at_utc': datetime.now(timezone.utc).isoformat(),
                         'mode': args.mode, 'notebook': NAME, 'ok': True,
                         'notebook_sha256': __import__('hashlib').sha256(source.read_bytes()).hexdigest()})
        if args.mode == 'fixture':
            findings['recorded_metadata_at_utc'] = json.loads(gzip.decompress(cassette.read_bytes()))['observed_at_utc']
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(findings, indent=2) + '\n')
        if args.executed:
            args.executed.parent.mkdir(parents=True, exist_ok=True)
            nbformat.write(executed, args.executed)
        print(json.dumps(findings, indent=2))

if __name__ == '__main__': main()
