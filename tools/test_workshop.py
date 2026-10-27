"""Focused checks of the notebook's identity, access, and geometry boundaries."""
import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import nbformat
import pandas as pd
import pytest

NOTEBOOK = Path(__file__).resolve().parents[1] / 'tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb'

def source_containing(text):
    return next(cell.source for cell in nbformat.read(NOTEBOOK, as_version=4).cells
                if cell.cell_type == 'code' and text in cell.source)

def function(name, namespace):
    tree = ast.parse(source_containing('def ' + name + '('))
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(NOTEBOOK), 'exec'), namespace)
    return namespace[name]


def test_clinical_batches_keep_dataset_identity():
    def subjects(title, *, subject_ids, limit):
        return SimpleNamespace(data={'count': len(subject_ids), 'limit': limit, 'subjects': [
            {'short_title': title, 'subject_id': identifier, 'primary_diagnosis': title}
            for identifier in subject_ids]})
    query = Mock(side_effect=subjects)
    namespace = {'pd': pd, 'tcia': SimpleNamespace(list_clinical_subjects=query), 'checked': lambda x: x}
    clinical_for = function('clinical_for', namespace)
    # Identical identifiers from two collections must not become one clinical record.
    frame = pd.DataFrame([{'short_title': title, 'display_participant_id': str(i)}
                          for title in ['A', 'B'] for i in range(101)])
    result = clinical_for(frame)
    assert len(result) == 202 and query.call_count == 4
    assert len(result[result.subject_id == '0']) == 2
    assert result[result.short_title == 'A'].primary_diagnosis.eq('A').all()


@pytest.mark.parametrize('duplicate', [False, True])
def test_clinical_cap_and_ambiguous_identity_stop(duplicate):
    rows = [{'short_title': 'A', 'subject_id': '1'}] * 2
    response = SimpleNamespace(data={'count': 2 if duplicate else 500, 'limit': 500, 'subjects': rows})
    namespace = {'pd': pd, 'tcia': SimpleNamespace(list_clinical_subjects=lambda *a, **k: response), 'checked': lambda x: x}
    clinical_for = function('clinical_for', namespace)
    with pytest.raises(ValueError if duplicate else RuntimeError):
        clinical_for(pd.DataFrame([{'short_title': 'A', 'display_participant_id': '1'}]))


def test_controlled_cohort_requires_same_participant_and_study(tmp_path):
    rows = []
    for participant, study, modality in [('A','1','CT'),('A','2','SEG'),('B','3','CT'),
                                         ('B','3','SEG'),('C','4','CT'),('C','4','RTSTRUCT'),
                                         ('','5','CT'),('','5','SEG')]:
        rows.append({'short_title': 'EXAMPLE', 'participant_id': participant,
                     'study_instance_uid': study, 'modality': modality})
    fake = SimpleNamespace(list_downloads=lambda *a, **k: None,
        list_controlled_files=lambda *a, **k: SimpleNamespace(data={'files': rows, 'count': len(rows), 'limit': 500}))
    namespace = {'pd': pd, 'tcia': fake, 'checked': lambda x: x, 'all_rows': lambda x: pd.DataFrame(),
                 'display': lambda *a: None, 'OUTPUT': tmp_path}
    with redirect_stdout(io.StringIO()):
        exec(source_containing('FACE_COLLECTION ='), namespace)
    assert namespace['face_cohort'].participant_id.tolist() == ['B']


def test_controlled_command_uses_key_path_and_never_key_value(tmp_path):
    key = tmp_path / 'test-only-key.json'
    key.write_text(json.dumps({'api_key': 'FAKE_TEST_VALUE_NOT_A_REAL_KEY'}))
    key.chmod(0o600)
    runner = Mock()
    namespace = {'Path': Path, 'json': json, 'os': __import__('os'), 'subprocess': SimpleNamespace(run=runner),
                 'RETRIEVER': 'retriever', 'CREDENTIAL_FILE': str(key)}
    run = function('run_controlled', namespace)
    output = io.StringIO()
    with redirect_stdout(output): run(tmp_path/'subset.csv', tmp_path/'images')
    command = runner.call_args.args[0]
    assert command[command.index('--auth') + 1] == str(key)
    assert 'FAKE_TEST_VALUE_NOT_A_REAL_KEY' not in ' '.join(command) + output.getvalue()
    assert '--accept-data-policy' not in command
    namespace['CREDENTIAL_FILE'] = ''
    with pytest.raises(ValueError): run('subset.csv', 'images')


def test_manifest_saver_rejects_html_without_writing(tmp_path):
    original_client = httpx.Client
    mock_http = SimpleNamespace(Client=lambda **kwargs: original_client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text='<html>Not a manifest</html>')),
        **kwargs))
    namespace = {'Path': Path, 'urlsplit': __import__('urllib.parse', fromlist=['urlsplit']).urlsplit,
                 'httpx': mock_http, 'OUTPUT': tmp_path, 'hashlib': __import__('hashlib')}
    save = function('save_official_manifest', namespace)
    with pytest.raises(ValueError):
        save({'download_url': 'https://www.cancerimagingarchive.net/wp-content/uploads/manifest.csv',
              'short_title':'EXAMPLE', 'download_id':'1'})
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('mismatch', [False, True])
def test_nifti_grid_check_detects_affine_mismatch(tmp_path, mismatch):
    nib = pytest.importorskip('nibabel')
    import numpy as np
    image = nib.Nifti1Image(np.zeros((3, 4, 5), dtype=np.float32), np.eye(4))
    affine = np.eye(4)
    if mismatch: affine[0, 3] = 10
    mask = nib.Nifti1Image(np.zeros((3, 4, 5), dtype=np.int16), affine)
    for obj, name in [(image, 'image.nii.gz'), (mask, 'mask.nii.gz')]:
        obj.header.set_xyzt_units('mm'); nib.save(obj, tmp_path/name)
    tree = ast.parse(source_containing('SOURCE_NIFTI ='))
    # Supply paths to generated test volumes instead of the lesson's blank defaults.
    tree.body = tree.body[2:]
    namespace = {'SOURCE_NIFTI': str(tmp_path/'image.nii.gz'), 'MASK_NIFTI': str(tmp_path/'mask.nii.gz'),
                 'pd':pd, 'Path':Path, 'display': lambda *a: None}
    with redirect_stdout(io.StringIO()): exec(compile(tree, str(NOTEBOOK), 'exec'), namespace)
    assert bool(namespace['same_grid']) is not mismatch


def test_empty_modality_search_explains_no_matches(tmp_path):
    fake = SimpleNamespace(search_participants=lambda **kwargs: None)
    namespace = {'pd': pd, 'tcia': fake, 'all_rows': lambda x: pd.DataFrame(),
                 'checked': lambda x: x, 'display': lambda *a: None, 'OUTPUT':tmp_path}
    output = io.StringIO()
    with redirect_stdout(output):
        exec(source_containing('COHORT_COLLECTIONS ='), namespace)
        exec(source_containing('def clinical_for('), namespace)
        exec(source_containing('matches = with_clinical'), namespace)
    assert namespace['cohort'].empty
    assert 'Try another collection or modality' in output.getvalue()
