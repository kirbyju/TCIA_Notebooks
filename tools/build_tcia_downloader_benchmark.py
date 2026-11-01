"""Build the standalone Colab benchmark without fetching code at runtime."""
from pathlib import Path
import json
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT/'benchmarks/benchmark_tcia_downloads.py').read_text()
cohorts = {name: json.loads((ROOT/'benchmarks'/filename).read_text()) for name, filename in
           [('small', 'cmb-gec-cohort.json'), ('5gb', 'cmb-gec-5gb-cohort.json')]}
cells = []
def md(text): cells.append(nbf.v4.new_markdown_cell(text))
def code(text, **metadata): cells.append(nbf.v4.new_code_cell(text, metadata=metadata))

md('''# Compare TCIA downloaders on the same images

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/benchmarks/TCIA_Downloader_Comparison.ipynb)

Let's check how the pip-installed TCIA Data Retriever and IDC tools perform on the **same public [CMB-GEC](https://www.cancerimagingarchive.net/collection/cmb-gec/) images**. This version uses **TCIA Data Retriever 0.1.0rc2** and offers two workloads:

| Workload | One download | Images | Default comparison |
|---|---:|---:|---|
| `small` | 29 MB; 2 CT/MR series | 96 | Three trials per tool, both startup cases; about 348 MB total |
| `5gb` | 4.997 GB; 59 CT/MR series | 8,460 | Two trials per tool, fresh processes; about 20 GB total |

Sizes use decimal GB (1 GB = 1,000,000,000 bytes). The notebook starts with `small`; change `WORKLOAD` to `"5gb"` below for the larger comparison. All trial copies stay on disk, so the larger test needs at least 22 GB free. Downloading the same 5 GB with both tools counts twice, and repeating the pair counts twice again.

The images are licensed CC BY 4.0; consult the collection page for the dataset citation. We alternate the tools, use a new destination each time, and check that every DICOM instance is present and **byte-for-byte identical**. No controlled data or credentials are used.

Read the [TCIA data usage policy](https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/) before running the transfer cells. Those cells explicitly pass `--accept-data-policy`. Running them records your acceptance for these downloads.''')
code('''import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install",
    "tcia-data-retriever==0.1.0rc2", "idc-index==0.13.4", "idc-index-data==25.0.5",
    "s5cmd==0.3.3", "pydicom==3.0.2"])
''')
md('''## Set up the comparison

The two cohorts and runner are embedded below, so you do not need to clone a repository or fetch executable code from a moving branch. Expand the cell to inspect them.

We pass the same cloud object prefixes to TDR and verify that IDC's selected series resolve to those prefixes. The runner checks the package revision, IDC data version, DICOM counts, total bytes and file hashes. It stops if a tool fails or the data differ. If you already imported an older TDR version in this runtime, restart the runtime after installing rc2.''')
code('from pathlib import Path\nimport json\n\nRUNNER_SOURCE = '+repr(runner)+'\nCOHORTS = '+repr(cohorts)+'''
ROOT = Path("tcia-downloader-benchmark")
ROOT.mkdir(exist_ok=True)
RUNNER = ROOT / "benchmark_tcia_downloads.py"
RUNNER.write_text(RUNNER_SOURCE)
''', cellView='form', collapsed=True)
code('''from datetime import datetime, timezone
import shutil
import pandas as pd
from IPython.display import display

WORKLOAD = "small"  # Change to "5gb" for the larger test.
SETTINGS = {
    "small": {"repeats": 3, "modes": ["cold", "warm"], "budget_mb": 1000, "timeout": 180},
    "5gb": {"repeats": 2, "modes": ["cold"], "budget_mb": 22000, "timeout": 1800},
}
settings = SETTINGS[WORKLOAD]
COHORT = COHORTS[WORKLOAD]
COHORT_PATH = ROOT / f"{WORKLOAD}-cohort.json"
COHORT_PATH.write_text(json.dumps(COHORT, indent=2))
expected_mb = sum(r["series_size_MB"] for r in COHORT["series"]) * settings["repeats"] * 2 * len(settings["modes"])
assert 0 < expected_mb * 1.1 < settings["budget_mb"], "Reduce the cohort or repeat count."
assert shutil.disk_usage(ROOT).free > expected_mb * 1.1 * 1_000_000, "Not enough free disk space."
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
print("Selected series:", len(COHORT["series"]))
print("DICOM instances per download:", sum(r["instanceCount"] for r in COHORT["series"]))
print(f"Expected total payload for all selected trials: {expected_mb / 1000:.3f} GB")
''')
md('''## Run the selected trials

**Fresh-process** includes package imports, client/index initialization and the transfer call. The small test also measures a **prepared-client** case: IDC's index and download query are prepared first, without downloading images. TDR's public Python API starts its packaged executable for every call, so that executable's setup remains part of its call time.

A faster fresh start does not by itself prove faster network transfer. We exclude installation, benchmark-only source checks and verification from timing. Cloud caches cannot be reset here, and the tools have different default concurrency settings. This measures their Python interfaces as used here.

The larger test runs the order TDR, IDC, IDC, TDR. There is a timeout and log for every trial; the comparison stops on the first failure. Fresh folders prevent an earlier download from silently turning the next trial into a resume test. The size budget uses reviewed metadata with a margin; it is not a packet-level cutoff.''')
code('''reports = []
for mode in settings["modes"]:
    output = ROOT / f"{RUN_ID}-{WORKLOAD}-{mode}"
    command = [sys.executable, str(RUNNER), "--cohort", str(COHORT_PATH),
               "--output", str(output), "--repeats", str(settings["repeats"]),
               "--max-total-mb", str(settings["budget_mb"]),
               "--timeout", str(settings["timeout"]), "--accept-data-policy"]
    if mode == "warm":
        command.append("--warm")
    subprocess.run(command, check=True)
    report = json.loads((output / "report.json").read_text())
    reports.append(report)
    assert report["all_payloads_identical"]
    print(mode, "passed content verification; report:", output / "report.json")
''')
md('''## Compare the results

Lower elapsed time is better. Compare startup cases separately and keep the individual timings: a fast or slow run can move a median. With only two trials per tool in the large test, the reported median is the midpoint of those two times. The first-visible-file measurement is a filesystem observation, not a network first-byte measurement.

Keep the JSON reports when sharing results. They record package versions, source revisions, the selected data, settings and limitations. A 5 GB test tells us more about sustained transfers than the small example, but it still does not cover every collection, file size, network or controlled-access route.''')
code('''summary = pd.DataFrame([
    {"case": report["mode"], **row}
    for report in reports for row in report["summary"]
])
display(summary)
trials = pd.DataFrame([
    {"case": report["mode"], **{k: row[k] for k in
        ["engine", "repeat", "elapsed_seconds", "MiB_per_second", "instances", "payload_bytes"]}}
    for report in reports for row in report["trials"]
])
display(trials)
assert len({r["fingerprint"] for report in reports for r in report["trials"]}) == 1
print("All files matched across trials.")
''')
result_path = ROOT/'benchmarks/results/2026-11-01-rc2-large-local.json'
if result_path.exists():
    result = json.loads(result_path.read_text())
    rows = result['summary']
    table = '\n'.join(f"| {r['engine']} | {r['trials']} | {r['median_seconds']:.2f} | {r['median_MiB_per_second']:.2f} |" for r in rows)
    md('''## Local reference result

This Mac run used rc2 and the 4.997 GB cohort above, with two fresh-process trials per tool. These are local results; this notebook has not yet been measured in Colab.

| Tool | Trials | Median seconds | Median MiB/s |
|---|---:|---:|---:|
'''+table+'''

All four downloads contained the same 8,460 images and passed byte-for-byte verification. See the [full report](https://github.com/kirbyju/TCIA_Notebooks/blob/main/benchmarks/results/2026-11-01-rc2-large-local.json) for individual times, versions and limitations. The [earlier small rc1 pilot](https://github.com/kirbyju/TCIA_Notebooks/blob/main/benchmarks/results/2026-11-01-local.json) used a different release and workload; keep those results separate.''')
nb = nbf.v4.new_notebook(cells=cells, metadata={
    'kernelspec': {'name':'python3','display_name':'Python 3','language':'python'},
    'language_info': {'name':'python'},
    'tcia_benchmark': {'cohort':'CMB-GEC', 'tdr_version':'0.1.0rc2',
                       'default_workload':'small', 'workloads':['small','5gb']}})
for i,c in enumerate(nb.cells): c.id = f'tcia-benchmark-{i:02d}'
nbf.validate(nb)
nbf.write(nb, ROOT/'benchmarks/TCIA_Downloader_Comparison.ipynb')
