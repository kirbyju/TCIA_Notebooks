"""Check lesson behavior; reusable helper tests live in tcia_utils itself."""
import ast
from contextlib import redirect_stdout
import io
from pathlib import Path
from types import SimpleNamespace
import nbformat
import pandas as pd
import pytest
from tcia_utils import Result, Completeness, format_table

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


def test_controlled_transfers_remain_opt_in_and_public_samples_run_directly():
    n=nbformat.read(NOTEBOOK,as_version=4)
    assert n.metadata.tcia_workshop.payload_downloads_default is True
    assert n.metadata.tcia_workshop.controlled_downloads_default is False
    for flag in ['DOWNLOAD_CONTROLLED_CMB','DOWNLOAD_CONTROLLED_CT']:
        source=source_containing(flag+' =')
        assert any(isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id==flag for target in node.targets)
                   and isinstance(node.value,ast.Constant) and node.value.value is False for node in ast.parse(source).body)
    samples=[c for c in n.cells if 'sample-download' in c.metadata.get('tags',[])]
    assert len(samples)==3
    for cell in samples:
        assert 'DOWNLOAD_' not in cell.source
        assert 'progress=' not in cell.source and 'dry_run=' not in cell.source


def test_controlled_cohort_requires_same_participant_and_study(tmp_path):
    rows=[]
    for participant,study,modality in [('A','1','CT'),('A','2','SEG'),('B','3','CT'),('B','3','SEG'),('C','4','CT'),('C','4','RTSTRUCT'),('','5','CT'),('','5','SEG')]:
        rows.append({'short_title':'EXAMPLE','participant_id':participant,'study_instance_uid':study,'modality':modality})
    fake=SimpleNamespace(plan_downloads=lambda *a,**k:SimpleNamespace(to_dataframe=lambda **k:pd.DataFrame()),
        list_controlled_files=lambda *a,**k:SimpleNamespace(data={'files':rows,'count':len(rows),'limit':500}))
    ns={'format_table':format_table,'pd':pd,'tcia':fake,'display':lambda *a:None,'OUTPUT':tmp_path}
    with redirect_stdout(io.StringIO()):exec(source_containing('FACE_COLLECTION ='),ns)
    assert ns['face_cohort'].participant_id.tolist()==['B']


def test_empty_modality_search_is_a_clear_zero_match(tmp_path):
    fake=SimpleNamespace(search_participants=lambda **k:SimpleNamespace(to_dataframe=lambda **k:pd.DataFrame()),
        clinical_for_participants=lambda x:Result({'subjects':[]},(),None,Completeness('complete')))
    ns={'format_table':format_table,'pd':pd,'tcia':fake,'display':lambda *a:None,'OUTPUT':tmp_path}
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


def test_collection_results_display_categories_separately_from_types_and_formats():
    observed = []
    raw = pd.DataFrame([{'short_title':'EXAMPLE','dataset_type':'Collection',
                         'download_data_types':['CT','Whole Slide Image'],'download_file_types':['DICOM','SVS']}])
    described = raw.assign(data_categories=[['Radiology Images','Pathology Images']])
    fake = SimpleNamespace(
        search_datasets=lambda **k:SimpleNamespace(to_dataframe=lambda **k:described),
    )
    with redirect_stdout(io.StringIO()):
        exec(source_containing('CANCER_LOCATION ='), {'tcia':fake,'display':observed.append,'format_table':format_table})
    table = observed[0]
    assert table.loc[0,'data_categories']==['Radiology Images','Pathology Images']
    assert table.loc[0,'download_data_types']==['CT','Whole Slide Image']
    assert table.loc[0,'download_file_types']==['DICOM','SVS']


def test_manifest_examples_accept_local_path_and_url_without_notebook_parsing(tmp_path):
    calls=[]
    fake=SimpleNamespace(download_manifest=lambda *args,**kwargs:
        calls.append((args,kwargs)) or SimpleNamespace(to_dataframe=lambda:pd.DataFrame()))
    saved=[{'route_column':'SeriesInstanceUID','manifest':'public.tcia'},
           {'route_column':'drs_uri','manifest':'controlled.csv','url':'https://example.org/controlled.csv'}]
    ns={'tcia':fake,'saved_manifests':saved,'OUTPUT':tmp_path,'DATASET':'EXAMPLE','display':lambda *a:None}
    public=ast.parse(source_containing('public_manifest = next('))
    controlled=ast.parse(source_containing('CREDENTIAL_FILE ='))
    controlled.body[0].value=ast.Constant('approved-test-key.json')
    controlled.body[1].value=ast.Constant(True)
    with redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(public),str(NOTEBOOK),'exec'),ns)
        exec(compile(ast.fix_missing_locations(controlled),str(NOTEBOOK),'exec'),ns)
    assert calls[0][0][0]==tmp_path/'public.tcia'
    assert calls[0][1]['max_items']==calls[1][1]['max_items']==1
    assert calls[1][0][0]=='https://example.org/controlled.csv'
    assert calls[1][1]['credential_file']=='approved-test-key.json'


def test_demo_downloads_are_bounded_and_keep_controlled_scan_label_pair():
    for marker, limit in [('public_manifest = next(', 1), ('CREDENTIAL_FILE =', 1), ('DOWNLOAD_CONTROLLED_CT =', 2), ('clinical_image_participants =',1), ('slide_images =',1)]:
        calls = [node for node in ast.walk(ast.parse(source_containing(marker)))
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and node.func.attr in {'download_manifest', 'download_files', 'download_images'}]
        assert len(calls) == 1
        assert next(kw.value.value for kw in calls[0].keywords if kw.arg == 'max_items') == limit


def test_sample_pair_keeps_one_ct_and_one_seg_when_study_has_many_series(tmp_path):
    usable=pd.DataFrame([
        {'short_title':'EXAMPLE','participant_id':'P','study_instance_uid':'S',
         'modality':modality,'series_instance_uid':f'1.2.{i}',
         'drs_uri':f'drs://example/{i}','file_size_bytes':4,'file_name':f'{i}.zip'}
        for i,modality in enumerate(['CT','CT','CT','SEG','SEG'])])
    ns={'format_table':format_table,'pd':pd,'usable':usable,'face_cohort':pd.DataFrame([{'participant_id':'P','study_instance_uid':'S'}]),
        'OUTPUT':tmp_path,'display':lambda *a:None}
    with redirect_stdout(io.StringIO()):exec(source_containing('face_selection = pd.DataFrame()'),ns)
    assert ns['face_selection'].modality.tolist()==['CT','SEG']
    assert len(pd.read_csv(ns['face_manifest']))==2


def test_download_tables_show_published_counts_without_turning_missing_into_zero(tmp_path):
    from IPython.display import Markdown
    observed=[]
    rows=pd.DataFrame([
        {'download_id':'1','download_title':'Imaging','download_category':['Radiology Images'],
         'download_requirements':'Example','python_supported':True,'download_method':'dicom_manifest',
         'subjects':12,'studies':15,'series':0,'images':100},
        {'download_id':'2','download_title':'Other','download_category':['Pathology Images'],
         'download_requirements':'Example','python_supported':False,'download_method':'aspera_package',
         'subjects':None,'studies':None,'series':None,'images':None},
    ])
    collection={'dataset_type':'Collection','short_title':'EXAMPLE','tcia_page':'https://example.org',
                'title':'Example','current_version_number':'1','has_external_clinical_resource':False}
    fake=SimpleNamespace(get_dataset=lambda *a:SimpleNamespace(data={'datasets':[collection]}),
        plan_downloads=lambda *a:SimpleNamespace(to_dataframe=lambda:rows))
    ns={'format_table':format_table,'pd':pd,'tcia':fake,'display':observed.append,'Markdown':Markdown,'OUTPUT':tmp_path}
    with redirect_stdout(io.StringIO()):
        exec(source_containing('DATASET = "CMB-GEC"'),ns)
        exec(source_containing('download_plan = downloads'),ns)
    tables=[v for v in observed if isinstance(v,pd.DataFrame)]
    for table in tables:
        assert table.loc[0,['subjects','studies','series','images']].tolist()==[12,15,0,100]
        assert table.loc[1,['subjects','studies','series','images']].tolist()==['Not reported']*4
    exported=pd.read_csv(tmp_path/'CMB-GEC_download_inventory.csv')
    assert pd.isna(exported.loc[1,'subjects']) and exported.loc[0,'series']==0
    # The other dataset download tables use the same published fields.
    for marker in ['brain_downloads = pd.concat','FACE_COLLECTION =']:
        source=source_containing(marker)
        for name in ['subjects','studies','series','images']:
            assert f'"{name}"' in source


def test_notebook_does_not_install_or_invoke_external_download_applications():
    text=NOTEBOOK.read_text()
    for forbidden in ['data_retriever_command','backend=','ascli','gem install','PACKAGE_CLIENT','DOWNLOAD_PUBLIC_NON_DICOM']:
        assert forbidden not in text
    assert 'python_supported' in text


@pytest.mark.parametrize('include_inferred,expected', [(True,['reported','inferred','unknown']), (False,['reported'])])
def test_diagnosis_control_is_next_to_filter_and_export_retains_row_provenance(tmp_path,include_inferred,expected):
    rows=[]
    for name,inferred,diagnosis in [('reported',False,'Carcinoma'),('inferred',True,'Carcinoma'),
                                     ('unknown',None,'Carcinoma'),('other',False,'Other diagnosis')]:
        rows.append({'short_title':'EXAMPLE','display_participant_id':name,
                     'primary_diagnosis':diagnosis,'primary_diagnosis_is_inferred':inferred,
                     'resolved_values':{},'resolved_sources':{},'conflicts':[]})
    tree=ast.parse(source_containing('matches ='))
    assert isinstance(tree.body[0],ast.Assign)
    assert tree.body[0].targets[0].id=='INCLUDE_INFERRED_DIAGNOSES'
    tree.body[0].value=ast.Constant(include_inferred)
    ns={'format_table':format_table,'pd':pd,'with_clinical':pd.DataFrame(rows),'DIAGNOSIS_TEXT':'carcinoma',
        'OUTPUT':tmp_path,'display':lambda *a:None}
    with redirect_stdout(io.StringIO()):exec(compile(ast.fix_missing_locations(tree),str(NOTEBOOK),'exec'),ns)
    assert ns['cohort'].display_participant_id.tolist()==expected
    csv=pd.read_csv(tmp_path/'modality_diagnosis_cohort.csv')
    exported=pd.read_json(tmp_path/'modality_diagnosis_cohort.json')
    assert csv.display_participant_id.tolist()==expected
    assert exported.display_participant_id.tolist()==expected
    assert csv.loc[0,'primary_diagnosis_is_inferred']==False
    if include_inferred:
        assert csv.loc[1,'primary_diagnosis_is_inferred']==True
        assert pd.isna(csv.loc[2,'primary_diagnosis_is_inferred'])


def test_clinical_download_demos_reuse_the_filtered_cohort_and_keep_samples_small(tmp_path):
    calls=[]
    def plan(participants,**filters):
        calls.append(('plan',participants.copy(),filters))
        return SimpleNamespace(rows=[{'participant_id':'LCA-1'}],unresolved=[],
            coverage_to_dataframe=lambda:pd.DataFrame(),to_dataframe=lambda:pd.DataFrame())
    def download(plan,destination,**kwargs):
        calls.append(('download',destination,kwargs))
        return SimpleNamespace(to_dataframe=lambda:pd.DataFrame())
    fake=SimpleNamespace(plan_participant_images=plan,download_images=download)
    cohort=pd.DataFrame([{'short_title':'CMB-LCA','display_participant_id':'LCA-1'},
                         {'short_title':'CMB-GEC','display_participant_id':'GEC-1'}])
    ns={'format_table':format_table,'pd':pd,'cohort':cohort,'tcia':fake,'display':lambda *a:None,'OUTPUT':tmp_path}
    for marker in ['clinical_image_participants =','slide_images =']:
        tree=ast.parse(source_containing(marker))
        with redirect_stdout(io.StringIO()):exec(compile(ast.fix_missing_locations(tree),str(NOTEBOOK),'exec'),ns)
    assert calls[0][1].display_participant_id.tolist()==['LCA-1']
    assert calls[2][1].display_participant_id.tolist()==['LCA-1']
    assert calls[0][2]=={'modality':'CT','file_format':'DICOM'}
    assert calls[2][2]=={'modality':'Whole Slide Image','file_format':'non-DICOM'}
    assert calls[1][2]['max_items']==calls[3][2]['max_items']==1


@pytest.mark.parametrize('damage',['unbounded_sample','untagged_sample'])
def test_validation_rejects_unbounded_or_unclassified_sample_cells(damage):
    from run_tcia_workshop import prepare_sample_dry_runs
    n=nbformat.read(NOTEBOOK,as_version=4)
    cell=next(c for c in n.cells if 'sample-download' in c.metadata.get('tags',[]))
    if damage=='unbounded_sample':
        cell.source=cell.source.replace(', max_items=1','')
    else:
        cell.metadata.tags=[]
    with pytest.raises(RuntimeError):
        prepare_sample_dry_runs(n)
