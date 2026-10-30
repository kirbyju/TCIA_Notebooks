"""Record only added public metadata against the existing fixture's exact bundle.

No image bodies are requested. The IDC subset is bundled-index metadata only.
Run the shared-contract projector afterward; derived routes are not deployed output.
"""
from pathlib import Path
from datetime import datetime,timezone
import base64,gzip,hashlib,json
import httpx
import pandas as pd
import idc_index_data

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'tcia_utils_v4/_fixtures/workshop-public-metadata.json.gz'
capture=json.loads(gzip.decompress(path.read_bytes()))
requests=capture['requests']
with httpx.Client(timeout=90,follow_redirects=True) as client:
    ready=client.get('https://tcia.duckdns.org/v2/ready').json()
    assert ready['release_fingerprint']==capture['fingerprint'],'Do not mix TCIA bundle generations'
    def fetch(url,params=None):
        request=client.build_request('GET',url,params=params)
        response=client.send(request);response.raise_for_status()
        body=response.content
        assert len(body)<10_000_000
        key=json.dumps(['GET',str(request.url),''],separators=(',',':'))
        requests[key]={'status':response.status_code,'headers':{'content-type':response.headers.get('content-type','')},
                       'body':base64.b64encode(body).decode()}
        return response
    detail=fetch('https://tcia.duckdns.org/v2/datasets/CMB-LCA').json()
    downloads=fetch('https://tcia.duckdns.org/v2/datasets/CMB-LCA/downloads',{'limit':100}).json()
    assert not downloads['has_more']
    assets=fetch('https://tcia.duckdns.org/v2/public-non-dicom/assets',
                 {'short_titles':['CMB-LCA'],'modalities':['Whole Slide Image'],'requires_annotations':False,'limit':500}).json()
    assert not assets['has_more'],'Extend recording to every cursor before using this fixture'
    manifest=next(r for r in detail['current_downloads'] if r['access_level']=='open' and r['download_url'].endswith('.tcia'))
    content=fetch(manifest['download_url']).content
    marker='ListOfSeriesToDownload='
    uids={line.strip() for line in content.decode('utf-8-sig').split(marker,1)[1].splitlines() if line.strip()}
    after=client.get('https://tcia.duckdns.org/v2/ready').json()
    assert after['release_fingerprint']==capture['fingerprint']
columns=['PatientID','SeriesInstanceUID','StudyInstanceUID','Modality','instanceCount','series_size_MB']
index=pd.read_parquet(idc_index_data.IDC_INDEX_PARQUET_FILEPATH,columns=columns)
subset=index[index['SeriesInstanceUID'].isin(uids)]
missing=sorted(uids-set(subset['SeriesInstanceUID']))
if missing:raise RuntimeError(f'{len(missing)} official series missing from bundled IDC index; investigate before demo')
idc={'observed_at_utc':datetime.now(timezone.utc).isoformat(),'data_package_version':idc_index_data.__version__,
     'idc_version':'v'+idc_index_data.__version__.split('.')[0],
     'basis':'Metadata-only subset of bundled IDC index, scoped by the official CMB-LCA public DICOM manifest',
     'manifest_sha256':hashlib.sha256(content).hexdigest(),'rows':json.loads(subset.to_json(orient='records'))}
idc_path=path.with_name('cohort-public-dicom.json.gz')
idc_path.write_bytes(gzip.compress(json.dumps(idc,separators=(',',':')).encode(),mtime=0))
capture['cohort_download_extension']={'observed_at_utc':datetime.now(timezone.utc).isoformat(),
    'release_fingerprint':ready['release_fingerprint'],'slide_records':len(assets['assets']),
    'dicom_series_records':len(subset),'idc_fixture_sha256':hashlib.sha256(idc_path.read_bytes()).hexdigest(),
    'scope':'Added metadata only, same TCIA bundle; no image payloads'}
path.write_bytes(gzip.compress(json.dumps(capture,separators=(',',':')).encode(),mtime=0))
print(json.dumps(capture['cohort_download_extension'],indent=2))
