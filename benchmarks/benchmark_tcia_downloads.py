"""Bounded public-data comparison of the released TDR and IDC Python interfaces.

Run this module as a script. Every trial runs in a child process with a fresh
output directory; installation and post-download verification are not timed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import signal
import shutil
import statistics
import subprocess
import sys
import threading
from time import perf_counter, sleep

POLICY = "https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/"


def inventory(directory, cohort):
    import pydicom
    expected = {row['SeriesInstanceUID']: int(row['instanceCount']) for row in cohort['series']}
    counts = {uid: 0 for uid in expected}
    objects = {}
    size = 0
    for path in directory.rglob('*.dcm'):
        ds = pydicom.dcmread(path, stop_before_pixels=True,
                            specific_tags=['SeriesInstanceUID', 'SOPInstanceUID'])
        uid, sop = str(ds.SeriesInstanceUID), str(ds.SOPInstanceUID)
        if uid not in counts or sop in objects:
            raise RuntimeError('Unexpected series or duplicate DICOM instance')
        payload = path.read_bytes()
        objects[sop] = hashlib.sha256(payload).hexdigest()
        size += len(payload)
        counts[uid] += 1
    if counts != expected:
        raise RuntimeError(f'DICOM instance counts differ: {counts} vs {expected}')
    expected_bytes = int(sum(Decimal(str(row['series_size_MB'])) * 1_000_000
                             for row in cohort['series']))
    if size != expected_bytes:
        raise RuntimeError(f'DICOM payload size differs: {size} vs {expected_bytes}')
    fingerprint = hashlib.sha256(json.dumps(objects, sort_keys=True).encode()).hexdigest()
    return {'instances': len(objects), 'payload_bytes': size, 'fingerprint': fingerprint,
            'series_instance_counts': counts}


def trial(engine, cohort_path, destination, result_path, warm=False):
    cohort = json.loads(cohort_path.read_text())
    if destination.exists():
        raise RuntimeError('A trial must have a new output directory')
    destination.mkdir(parents=True)
    first = []
    stop = threading.Event()
    started = perf_counter()

    def watch():
        while not stop.is_set():
            for path in destination.rglob('*.dcm'):
                try:
                    if path.stat().st_size:
                        first.append(perf_counter() - started)
                        return
                except FileNotFoundError:
                    pass
            stop.wait(0.1)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    validation_seconds = 0
    initialization_seconds = 0
    try:
        engine_report = None
        if engine == 'tdr':
            import tcia_data_retriever as tdr
            manifest = destination.parent / (destination.name + '.s5cmd')
            manifest.write_text(''.join('cp '+r['current_url']+' ./\n' for r in cohort['series']))
            initialization_seconds = perf_counter() - started
            if warm:
                started = perf_counter()
            engine_report = tdr.download(manifest, destination, accept_data_policy=True,
                                         skip_existing=False, max_retries=0)
            if (engine_report['total'] != len(cohort['series'])
                    or engine_report['failed'] != 0
                    or engine_report['status'] != 'success'):
                raise RuntimeError('TDR did not account for all selected series')
        else:
            from idc_index import IDCClient
            client = IDCClient()
            if client.get_idc_version() != cohort['idc_version']:
                raise RuntimeError('IDC data version differs from the pinned cohort')
            initialization_seconds = perf_counter() - started
            checking = perf_counter()
            index = client.index.set_index('SeriesInstanceUID')
            for row in cohort['series']:
                source = index.loc[row['SeriesInstanceUID']]
                actual = 's3://' + source.aws_bucket + '/' + source.crdc_series_uuid + '/*'
                if actual != row['current_url']:
                    raise RuntimeError('The two engines would use different source objects')
            validation_seconds = perf_counter() - checking
            if warm:
                original = client._s5cmd_run
                client._s5cmd_run = lambda **kw: None
                try:
                    client.download_dicom_series(
                        seriesInstanceUID=[cohort['series'][0]['SeriesInstanceUID']],
                        downloadDir=str(destination.parent / ('.metadata-warmup-'+destination.name)),
                        use_s5cmd_sync=False, quiet=True, show_progress_bar=False)
                finally:
                    client._s5cmd_run = original
                started = perf_counter()
                validation_seconds = 0
            client.download_dicom_series(
                seriesInstanceUID=[r['SeriesInstanceUID'] for r in cohort['series']],
                downloadDir=str(destination), use_s5cmd_sync=False,
                quiet=True, show_progress_bar=False)
        elapsed = perf_counter() - started - validation_seconds
    finally:
        stop.set()
        watcher.join(timeout=2)
    checked = inventory(destination, cohort)
    result = {'engine': engine, 'ok': True, 'elapsed_seconds': elapsed,
              'first_dicom_visible_seconds': first[0] - validation_seconds if first else None,
              'initialization_seconds': initialization_seconds, 'source_validation_seconds_excluded': validation_seconds,
              'warm_prepared_client': warm,
              'MiB_per_second': checked['payload_bytes'] / 2**20 / elapsed,
              'engine_report': engine_report, **checked}
    result_path.write_text(json.dumps(result, indent=2)+'\n')


def run(cohort_path, output, repeats=3, max_total_mb=1000, timeout=180, warm=False):
    cohort = json.loads(cohort_path.read_text())
    planned = sum(float(r['series_size_MB']) * 1_000_000 for r in cohort['series']) * 2 * repeats
    if repeats < 1 or planned <= 0 or planned * 1.1 > max_total_mb * 1_000_000:
        raise ValueError('Selection exceeds the configured total payload budget')
    if output.exists():
        raise ValueError('Use a fresh benchmark output directory')
    if shutil.disk_usage(output.parent).free < planned * 1.1:
        raise ValueError('Insufficient free disk space for all fresh trial copies')
    import tcia_data_retriever as tdr
    build = tdr.build_info()
    if cohort.get('tdr_version') and build['version'] != cohort['tdr_version']:
        raise ValueError('TDR version differs from the pinned cohort; restart the runtime after installing')
    if cohort.get('tdr_source_commit') and build['git_commit'] != cohort['tdr_source_commit']:
        raise ValueError('TDR source revision differs from the pinned cohort')
    output.mkdir(parents=True)
    results = []
    report = {'observed_at_utc': datetime.now(timezone.utc).isoformat(),
              'platform': platform.platform(), 'python': platform.python_version(),
              'versions': {p: version(p) for p in ['tcia-data-retriever', 'idc-index', 'idc-index-data', 'pydicom']},
              'cohort': cohort, 'cohort_sha256': hashlib.sha256(cohort_path.read_bytes()).hexdigest(),
              'expected_total_payload_bytes': int(planned), 'max_total_MB': max_total_mb,
              'mode': 'warm prepared-client API calls' if warm else 'fresh-process end-to-end',
              'destination_mode': 'fresh destination, normal copy, same S3 objects; alternating order',
              'settings': {'tdr_processes': 8, 'tdr_max_retries': 0,
                           'idc_workers': 'package default', 'idc_retries': 'package default',
                           'idc_sync': False}, 'trials': results}
    report['tdr_build'] = build
    script = Path(__file__).resolve()
    for repeat in range(repeats):
        order = ['tdr', 'idc'] if repeat % 2 == 0 else ['idc', 'tdr']
        for engine in order:
            name = f'{repeat+1:02d}-{engine}'
            destination, result_path = output / name, output / (name+'.json')
            args = [sys.executable, str(script), '--trial', engine, '--cohort', str(cohort_path),
                    '--output', str(destination), '--result', str(result_path), '--accept-data-policy']
            if warm:
                args.append('--warm')
            print(f'Running {name}: {len(cohort["series"])} series in a fresh directory', flush=True)
            with (output / (name+'.log')).open('w') as log:
                process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                try:
                    code = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGINT)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    code = 124
            if code or not result_path.is_file():
                results.append({'engine': engine, 'repeat': repeat+1, 'ok': False,
                                'returncode': code, 'log': name+'.log'})
                report['status'] = 'failed; no speed conclusion; stopped after first failure'
                (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
                raise RuntimeError(f'{name} failed; inspect {output / (name+".log")}')
            item = json.loads(result_path.read_text()); item['repeat'] = repeat+1
            results.append(item)
            if sum(r.get('payload_bytes', 0) for r in results) > max_total_mb*1_000_000:
                raise RuntimeError('Observed payload budget exceeded')
            if len({r['fingerprint'] for r in results}) != 1:
                raise RuntimeError('Downloaded DICOM bytes differ; do not compare performance as equivalent data')
            (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    report['status'] = 'success'
    report['all_payloads_identical'] = True
    report['summary'] = []
    for engine in ['tdr', 'idc']:
        rows = [r for r in results if r['engine'] == engine]
        report['summary'].append({'engine': engine, 'trials': len(rows),
            'median_seconds': statistics.median(r['elapsed_seconds'] for r in rows),
            'median_MiB_per_second': statistics.median(r['MiB_per_second'] for r in rows)})
    report['limitations'] = ['Public CT/MR cohort only; no controlled-access or non-DICOM speed claim.',
        'Fresh local destinations do not clear remote/CDN caches.',
        'Default concurrency differs; TDR retries disabled; IDC uses package defaults.',
        'Cold elapsed time includes imports, index/preparation and transfer; warm mode excludes client initialization.',
        'Warm IDC uses a metadata-only preparation call with transfer intercepted; TDR always starts its packaged executable per call.',
        'Installation, source validation and post-download verification are not timed.',
        'First visible DICOM is a filesystem observation, not a network first-byte measurement.']
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report['summary'], indent=2), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cohort', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--max-total-mb', type=float, default=1000)
    p.add_argument('--timeout', type=float, default=180)
    p.add_argument('--accept-data-policy', action='store_true')
    p.add_argument('--warm', action='store_true')
    p.add_argument('--trial', choices=['tdr', 'idc'])
    p.add_argument('--result', type=Path)
    args = p.parse_args()
    if not args.accept_data_policy:
        p.error('Explicit policy acceptance is required: '+POLICY)
    if args.trial:
        trial(args.trial, args.cohort.resolve(), args.output.resolve(), args.result.resolve(), args.warm)
    else:
        run(args.cohort.resolve(), args.output.resolve(), args.repeats, args.max_total_mb, args.timeout, args.warm)


if __name__ == '__main__':
    main()
