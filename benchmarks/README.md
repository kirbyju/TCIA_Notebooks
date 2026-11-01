# Compare the TCIA Data Retriever and IDC download interfaces

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/benchmarks/TCIA_Downloader_Comparison.ipynb)

This standalone notebook embeds its runner and two reviewed public
[CMB-GEC](https://www.cancerimagingarchive.net/collection/cmb-gec/) cohorts. It pins
`tcia-data-retriever==0.1.0rc2`, `idc-index==0.13.4` and `idc-index-data==25.0.5`.
The selected images are licensed CC BY 4.0. Consult the collection page for the
dataset citation and acknowledgements. No imaging payloads or credentials are
committed here.

| Workload | Per tool/trial | Default trial plan | Total payload |
|---|---:|---|---:|
| `small` | 2 CT/MR series; 96 images; 29,013,394 bytes | Three per tool in each of two startup cases | 348 MB |
| `5gb` | 59 CT/MR series; 8,460 images; 4,996,622,482 bytes | Two per tool, fresh processes; TDR / IDC / IDC / TDR | 19.99 GB |

GB means decimal GB. The notebook defaults to `small`; select `WORKLOAD = "5gb"`
for the larger comparison. Trial copies remain on disk. The 5 GB setting needs
at least 22 GB free and allows 30 minutes per trial. Metadata-based size and disk
guards run before launching a downloader; the budget is not a packet-level cutoff.

The larger cohort consists of whole public CT/MR series from the official manifest,
with at least 32 instances and no series above 350 MB. Hash-sorted series are added
until the selection reaches 4.95–5.00 GB. The committed cohort records the IDs,
counts, sizes, licenses, explicit source prefixes, manifest hash and TDR revision.

We give TDR the explicit S3 prefixes and verify that IDC's selected series resolve
to those same prefixes. Every trial uses a fresh destination. After timing, the
runner verifies the DICOM series/instance counts, total payload bytes and SHA-256
fingerprint of every instance. A failure or mismatch stops the comparison.

Fresh-process timing includes imports, client/index initialization and the transfer
call. The small test also has a prepared-client case: IDC's metadata/query path is
prepared with its transfer function intercepted, so no warm-up images transfer.
TDR's Python API starts its executable per call; that setup remains in call time.
Installation, benchmark-only source checks and post-download verification are
excluded. The first-visible-file measurement is a filesystem observation.

Remote/CDN caches cannot be cleared. Default concurrency differs; TDR has eight
series workers and retries disabled, while IDC uses package defaults. These are
interface measurements, not a controlled networking-algorithm experiment. They do
not cover controlled access, non-DICOM, very large individual files, interruption
or resume. Two large trials per tool are not enough to establish broad superiority.

Run on macOS/Linux with the pinned benchmark packages installed:

```bash
python benchmarks/benchmark_tcia_downloads.py \
  --cohort benchmarks/cmb-gec-5gb-cohort.json --output large-results \
  --repeats 2 --max-total-mb 22000 --timeout 1800 --accept-data-policy
```

Read the TCIA usage policy before supplying `--accept-data-policy`. Use a fresh
output path for each run. For the small test, use `cmb-gec-cohort.json` and the
runner's defaults; add `--warm` for the prepared-client case.

The [earlier rc1 pilot](results/2026-11-01-local.json) used only 29 MB per trial.
Its medians were 2.60 s for TDR versus 4.62 s for fresh IDC, and 2.60 s versus 2.83 s
with IDC prepared. Keep that historical release/workload separate from rc2 results.
No Colab performance result is claimed until the notebook is actually run there.

## Local rc2 result: approximately 5 GB

The [full rc2 report](results/2026-11-01-rc2-large-local.json) records the exact
cohort, versions, TDR source revision, transfer binary identity, settings, counts,
hashes and individual timings. All four copies contained 8,460 identical DICOM
instances and exactly 4,996,622,482 bytes each: 19,986,489,928 bytes in total.

| Tool | First trial | Second trial | Median (midpoint of two) |
|---|---:|---:|---:|
| TDR 0.1.0rc2 | 66.97 s | 75.14 s | 71.05 s |
| idc-index 0.13.4 | 90.24 s | 60.28 s | 75.26 s |

Each tool was faster in one pair. The overlapping timings are best described as
comparable on this workload; the 5.6% difference in midpoint is smaller than the
observed run-to-run variation. The earlier small pilot's startup advantage does
not establish a large-transfer advantage. This supports using TDR for transfers
without removing IDC's separate role in metadata queries.

IDC used s5cmd v2.3.0-991c9fb (256 object workers and ten retries by default).
The selected PATH executable was byte-identical to the installed s5cmd 0.3.3 wheel
binary. TDR used eight series workers and no retries. Worker granularity differs,
so this is a comparison of the configured interfaces rather than equal worker
counts. All trials succeeded; IDC request-level retries were not instrumented.
TDR reported 59 downloaded series and zero synced series in each trial.
