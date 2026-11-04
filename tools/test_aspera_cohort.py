"""Validate the external-application adapter without installation or transfers."""
import ast
import csv
import json
from pathlib import Path
from types import SimpleNamespace
import nbformat
import pytest

NOTEBOOK=Path(__file__).resolve().parents[1]/'TCIA_Aspera_CLI_Downloads.ipynb'
URL='https://faspex.cancerimagingarchive.net/aspera/faspex/public/package?context=synthetic'


def adapter():
    cell=next(c for c in nbformat.read(NOTEBOOK,as_version=4).cells
              if c.cell_type=='code' and 'def receive_aspera_manifest' in c.source)
    tree=ast.parse(cell.source)
    tree.body=tree.body[:-1]  # Do not run the reader's transfer call in tests.
    calls=[]
    ns={'OUTPUT':Path('output'),'Path':Path,'subprocess':SimpleNamespace(call=lambda command:calls.append(command) or 0)}
    exec(compile(tree,str(NOTEBOOK),'exec'),ns)
    ns['subprocess']=SimpleNamespace(call=lambda command:calls.append(command) or 0)
    return ns['receive_aspera_manifest'], calls


def manifest(path, paths, url=URL):
    with path.open('w',newline='') as output:
        writer=csv.writer(output);writer.writerow(['packageUrl','packagePath'])
        writer.writerows((url,p) for p in paths)
    return path


def test_exact_paths_are_argv_not_shell_code_and_never_whole_packages(tmp_path):
    receive,calls=adapter()
    paths=['cohort/subject 1/image.nii.gz','cohort/subject 1/a;$(no command).nii.gz']
    source=manifest(tmp_path/'files.csv',paths)
    receive(source,tmp_path/'images',use_notebook_rvm=False)
    assert len(calls)==1 and calls[0][:4]==['ascli','faspex5','packages','receive']
    assert calls[0][4]=='--url='+URL
    assert calls[0][5].startswith('--to-folder=')
    assert calls[0][6:]==sorted(paths)
    receive(source,tmp_path/'images',use_notebook_rvm=True)
    assert calls[1][:2]==['bash','-lc']
    assert 'exec "$@"' in calls[1][2]
    assert URL not in calls[1][2] and all(p not in calls[1][2] for p in paths)


@pytest.mark.parametrize('path',['','folder/','../outside','-option','@ruby:danger','file\nname'])
def test_invalid_path_never_launches_a_transfer(tmp_path,path):
    receive,calls=adapter()
    with pytest.raises(ValueError):
        receive(manifest(tmp_path/'bad.csv',['safe/image.nii.gz',path]),tmp_path/'images')
    assert not calls and not (tmp_path/'images').exists()


@pytest.mark.parametrize('url',['http://faspex.cancerimagingarchive.net/aspera/faspex?context=a','https://other.example.org/?context=a','https://faspex.cancerimagingarchive.net/aspera/faspex?token=secret'])
def test_unrecognized_package_never_launches(tmp_path,url):
    receive,calls=adapter()
    with pytest.raises(ValueError):receive(manifest(tmp_path/'bad.csv',['image.nii.gz'],url),tmp_path/'images')
    assert not calls


def test_empty_list_does_not_request_a_whole_package(tmp_path):
    receive,calls=adapter()
    with pytest.raises(ValueError,match='no files'):receive(manifest(tmp_path/'empty.csv',[]),tmp_path/'images')
    assert not calls


def test_large_manifest_batches_and_deduplicates_exact_files(tmp_path):
    receive,calls=adapter()
    paths=[f'P{i}/image.nii.gz' for i in range(51)]
    receive(manifest(tmp_path/'large.csv',paths+paths[:1]),tmp_path/'images',use_notebook_rvm=False)
    assert len(calls)==2
    assert sorted(p for command in calls for p in command[6:])==sorted(paths)


def test_query_notebook_defers_aspera_and_nifti_to_separate_notebook():
    query=nbformat.read(NOTEBOOK.parent/'tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb',as_version=4)
    code='\n'.join(c.source for c in query.cells if c.cell_type=='code')
    assert 'BRAIN_COLLECTIONS' not in code and 'nibabel' not in code and 'resume=' not in code
    assert 'list_controlled_files' not in code and 'FACE_COLLECTION' not in code
    assert 'SEG_COLLECTION = "NSCLC-Radiomics"' in code
    assert any('TCIA_Aspera_CLI_Downloads.ipynb' in c.source for c in query.cells)


def test_saved_cohort_preserves_leading_zero_participant_ids(tmp_path):
    import pandas as pd
    source=tmp_path/'cohort.json'
    source.write_text(json.dumps([{'participant_key':'key','dataset_type':'Collection',
        'short_title':'EXAMPLE','display_participant_id':'0001'}]))
    cell=next(c for c in nbformat.read(NOTEBOOK,as_version=4).cells
              if c.cell_type=='code' and c.source.startswith('if COHORT_JSON:'))
    ns={'Path':Path,'json':json,'pd':pd,'COHORT_JSON':str(source),'OUTPUT':tmp_path,'display':lambda *a:None}
    exec(cell.source,ns)
    assert ns['selected_participants'].display_participant_id.tolist()==['0001']
