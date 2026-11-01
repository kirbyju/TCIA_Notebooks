# Compare the TCIA Data Retriever and IDC download interfaces

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/benchmarks/TCIA_Downloader_Comparison.ipynb)

This standalone notebook embeds its runner and reviewed cohort. It compares the
published `tcia-data-retriever==0.1.0rc1` and `idc-index==0.13.4` interfaces on the
same public [CMB-GEC](https://www.cancerimagingarchive.net/collection/cmb-gec/)
objects: two CT/MR series, 96 DICOM instances, 29,013,394 payload bytes per trial,
licensed CC BY 4.0. Consult the collection page for the dataset citation and
acknowledgements. No imaging payloads or credentials are committed here.

The object prefixes match both the released TDR source's embedded index and IDC
v25 metadata. The runner checks IDC's version and source prefixes, then verifies
DICOM series/instance counts and SHA-256 fingerprints after every download.
Non-equivalent data or failures stop the comparison rather than produce a winner.

Three alternating trials per tool use fresh destinations in each of two cases:

* Fresh-process timing includes package/client initialization and the transfer call.
* Prepared-client timing excludes client initialization. IDC's metadata/query path
  is prepared with its transfer function intercepted; no warm-up images transfer.
  TDR's public interface launches its executable per call, so its internal setup
  remains part of the measured call.

Installation, benchmark-only source checks and post-download verification are
excluded from timing. Remote/CDN caches are not cleared. Concurrency differs
between the tools' defaults; TDR retries are disabled and IDC uses package defaults.
This is an interface pilot, not a networking-algorithm or universal speed claim.
It does not measure controlled, non-DICOM, large-file, interrupted or resumed
transfers. The first-visible-file timing is a filesystem observation.

With defaults, both cases transfer about 348 MB total. The budget guard uses the
reviewed metadata size with a margin; it is not a packet-level bandwidth cutoff.
Use the pinned cohort unless deliberately designing a different benchmark.
Every trial has a timeout and a log. The runner stops after the first failure.
Read the TCIA usage policy before supplying `--accept-data-policy`.

Run on macOS/Linux with an installed benchmark environment:

```bash
python benchmarks/benchmark_tcia_downloads.py \
  --cohort benchmarks/cmb-gec-cohort.json --output cold-results \
  --accept-data-policy
python benchmarks/benchmark_tcia_downloads.py \
  --cohort benchmarks/cmb-gec-cohort.json --output warm-results --warm \
  --accept-data-policy
```

The [local pilot report](results/2026-11-01-local.json) records all trial times,
versions, source revision, payload counts and hashes. Medians were about 2.60 s
for TDR versus 4.62 s for fresh IDC, and 2.60 s versus 2.83 s with IDC prepared.
All payloads were identical. Three small trials do not establish statistical or
cross-environment superiority; the prepared case is best described as comparable.
No Colab result is claimed until that notebook is actually run there.
