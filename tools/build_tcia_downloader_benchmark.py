"""Build the standalone Colab benchmark without fetching code at runtime."""
from pathlib import Path
import json
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/'benchmarks/benchmark_tcia_downloads.py').read_text()
cohort=json.loads((ROOT/'benchmarks/cmb-gec-cohort.json').read_text())
cells=[]
def md(text):cells.append(nbf.v4.new_markdown_cell(text))
def code(text,**metadata):cells.append(nbf.v4.new_code_cell(text,metadata=metadata))
md('''# Compare TCIA downloaders on the same images

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/benchmarks/TCIA_Downloader_Comparison.ipynb)

Let's check how the pip-installed TCIA Data Retriever and IDC tools perform on the **same public [CMB-GEC](https://www.cancerimagingarchive.net/collection/cmb-gec/) images**. We use two CT/MR series containing 96 DICOM instances, about 29 MB per download. The selected images are licensed CC BY 4.0; consult the collection page for the dataset citation. This is a small pilot, so it cannot tell us which tool is fastest for every collection or file type.

The benchmark alternates the tools, uses a new destination each time, and checks that every DICOM instance is present and **byte-for-byte identical**. We compare both fresh-process startup and a prepared-client case, since an existing analysis session may already have loaded imaging metadata. Installation and verification are excluded from timing.

There are three trials per tool in each case: about **348 MB total payload** with these defaults. Public cloud caches cannot be reset by this notebook. Network conditions and the tools' default concurrency can affect the result. No controlled data or credentials are used.

Read the [TCIA data usage policy](https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/) before running the transfer cells. Those cells explicitly pass `--accept-data-policy`. Running them records your acceptance for these downloads.''')
code('''import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install",
    "tcia-data-retriever==0.1.0rc1", "idc-index==0.13.4", "idc-index-data==25.0.5", "pydicom"])
''')
md('''## Set up the bounded comparison

The cohort and runner are embedded below, so you do not need to clone a repository or download executable code from a moving branch. Expand the cell to inspect them.

The selected cloud object prefixes match both packages' metadata. The runner checks the IDC data version and source URLs again before comparing results. It stops if a tool fails or returns a different set of images.''')
code('from pathlib import Path\nimport json\n\nRUNNER_SOURCE = '+repr(runner)+'\nCOHORT = '+repr(cohort)+'''\nROOT = Path("tcia-downloader-benchmark")
ROOT.mkdir(exist_ok=True)
RUNNER = ROOT / "benchmark_tcia_downloads.py"
COHORT_PATH = ROOT / "cohort.json"
RUNNER.write_text(RUNNER_SOURCE)
COHORT_PATH.write_text(json.dumps(COHORT, indent=2))
print("Selected series:", len(COHORT["series"]))
print("DICOM instances:", sum(r["instanceCount"] for r in COHORT["series"]))
''',cellView='form',collapsed=True)
code('''from datetime import datetime, timezone
import pandas as pd
from IPython.display import display

REPEATS = 3
TOTAL_BUDGET_MB = 1000
expected_mb = sum(r["series_size_MB"] for r in COHORT["series"]) * REPEATS * 4
assert 0 < expected_mb * 1.1 < TOTAL_BUDGET_MB, "Reduce the cohort or repeat count."
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
print(f"Expected total payload for both cases: {expected_mb:.1f} MB")
''')
md('''## Run both cases

**Fresh-process** includes package imports, client/index initialization and the transfer call. **Prepared-client** prepares IDC's index and download query first, without downloading images. The Data Retriever's public Python API starts its packaged executable for every call, so that executable's setup remains part of its call time.

These cases answer different questions. A faster fresh start does not by itself prove faster network transfer. The tools also have different default concurrency settings. This benchmark measures their Python interfaces as used here; it does not claim a controlled comparison of networking algorithms.

Each trial writes a log and checks DICOM identifiers, counts and SHA-256 hashes after timing. Fresh destinations prevent previously downloaded files from silently turning into a no-transfer test.''')
code('''reports = []
for mode in ["cold", "warm"]:
    output = ROOT / f"{RUN_ID}-{mode}"
    command = [sys.executable, str(RUNNER), "--cohort", str(COHORT_PATH),
               "--output", str(output), "--repeats", str(REPEATS),
               "--max-total-mb", str(TOTAL_BUDGET_MB), "--accept-data-policy"]
    if mode == "warm":
        command.append("--warm")
    subprocess.run(command, check=True)
    report = json.loads((output / "report.json").read_text())
    reports.append(report)
    assert report["all_payloads_identical"]
    print(mode, "passed content verification; report:", output / "report.json")
''')
md('''## Compare the results

Lower elapsed time is better. Compare the two cases separately and keep the raw trial timings: a single very fast or slow run can move a three-trial median. The first-visible-file measurement is a filesystem observation, not a network first-byte measurement.

Keep the JSON reports when sharing results. They record package versions, source revisions, the selected data, settings and limitations. We still need larger and different file shapes before making broad speed claims.''')
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
print("All files matched across trials:", len({r["fingerprint"] for report in reports for r in report["trials"]}) == 1)
''')
nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},'language_info':{'name':'python'},'tcia_benchmark':{'cohort':'CMB-GEC','instances':96,'default_payload_MB':348.160728}})
for i,c in enumerate(nb.cells):c.id=f'tcia-benchmark-{i:02d}'
nbf.validate(nb);nbf.write(nb,ROOT/'benchmarks/TCIA_Downloader_Comparison.ipynb')
