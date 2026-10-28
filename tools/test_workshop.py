"""Check lesson behavior; reusable helper tests live in tcia_utils itself."""
import ast
from contextlib import redirect_stdout
import io
from pathlib import Path
from types import SimpleNamespace
import nbformat
import pandas as pd
import pytest
from tcia_utils import Result, Completeness

NOTEBOOK=Path(__file__).resolve().parents[1]/'tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb'

def source_containing(text):
    return next(c.source for c in nbformat.read(NOTEBOOK,as_version=4).cells if c.cell_type=='code' and text in c.source)


def test_lesson_has_no_custom_helpers_or_prerelease_tutorial():
    n=nbformat.read(NOTEBOOK,as_version=4)
    for c in n.cells:
        if c.cell_type=='code':
            assert not any(isinstance(node,ast.FunctionDef) for node in ast.walk(ast.parse(c.source)))
        else:
            assert 'Pre-release Versions' not in c.source
            assert 'first alpha' not in c.source and 'pip install tcia_utils` (ordinary' not in c.source
    assert 'download_category' in source_containing('download_plan = downloads')


def test_all_imaging_transfers_remain_opt_in():
    for flag in ['DOWNLOAD_PUBLIC_DICOM','DOWNLOAD_PUBLIC_NON_DICOM','DOWNLOAD_CONTROLLED_CMB','DOWNLOAD_CONTROLLED_CT']:
        source=source_containing(flag+' =')
        assert any(isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id==flag for target in node.targets)
                   and isinstance(node.value,ast.Constant) and node.value.value is False for node in ast.parse(source).body)


def test_controlled_cohort_requires_same_participant_and_study(tmp_path):
    rows=[]
    for participant,study,modality in [('A','1','CT'),('A','2','SEG'),('B','3','CT'),('B','3','SEG'),('C','4','CT'),('C','4','RTSTRUCT'),('','5','CT'),('','5','SEG')]:
        rows.append({'short_title':'EXAMPLE','participant_id':participant,'study_instance_uid':study,'modality':modality})
    fake=SimpleNamespace(plan_downloads=lambda *a,**k:SimpleNamespace(to_dataframe=lambda **k:pd.DataFrame()),
        list_controlled_files=lambda *a,**k:SimpleNamespace(data={'files':rows,'count':len(rows),'limit':500}))
    ns={'pd':pd,'tcia':fake,'display':lambda *a:None,'OUTPUT':tmp_path}
    with redirect_stdout(io.StringIO()):exec(source_containing('FACE_COLLECTION ='),ns)
    assert ns['face_cohort'].participant_id.tolist()==['B']


def test_empty_modality_search_is_a_clear_zero_match(tmp_path):
    fake=SimpleNamespace(search_participants=lambda **k:SimpleNamespace(to_dataframe=lambda **k:pd.DataFrame()),
        clinical_for_participants=lambda x:Result({'subjects':[]},(),None,Completeness('complete')))
    ns={'pd':pd,'tcia':fake,'display':lambda *a:None,'OUTPUT':tmp_path}
    output=io.StringIO()
    with redirect_stdout(output):
        exec(source_containing('COHORT_COLLECTIONS ='),ns)
        exec(source_containing('clinical_result ='),ns)
        exec(source_containing('matches ='),ns)
    assert ns['cohort'].empty and 'Try another collection or modality' in output.getvalue()


@pytest.mark.parametrize('mismatch',[False,True])
def test_nifti_grid_check_detects_affine_mismatch(tmp_path,mismatch):
    nib=pytest.importorskip('nibabel')
    import numpy as np
    image=nib.Nifti1Image(np.zeros((3,4,5),dtype=np.float32),np.eye(4))
    affine=np.eye(4)
    if mismatch:affine[0,3]=10
    mask=nib.Nifti1Image(np.zeros((3,4,5),dtype=np.int16),affine)
    for obj,name in [(image,'image.nii.gz'),(mask,'mask.nii.gz')]:
        obj.header.set_xyzt_units('mm');nib.save(obj,tmp_path/name)
    tree=ast.parse(source_containing('SOURCE_NIFTI ='));tree.body=tree.body[2:]
    ns={'SOURCE_NIFTI':str(tmp_path/'image.nii.gz'),'MASK_NIFTI':str(tmp_path/'mask.nii.gz'),
        'pd':pd,'Path':Path,'display':lambda *a:None}
    with redirect_stdout(io.StringIO()):exec(compile(tree,str(NOTEBOOK),'exec'),ns)
    assert bool(ns['same_grid']) is not mismatch
