# Finding datasets and building participant cohorts with TCIA

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb)

The single workshop is written for junior data scientists. It covers CMB-GEC
whole-dataset discovery and download planning, CT/diagnosis cohorts across CMB-GEC
and CMB-LCA, public brain MR/NIfTI segmentation metadata, and controlled CT/SEG
candidate selection. It explains public versus controlled access and DICOM versus
other formats without teaching the hosting infrastructure.

The workshop installs the 4.0.0a5 preview from PyPI in Python 3.11+. In Colab,
run the installation cell, restart the runtime if prompted, and run from the top.
The hosted REST service must include the shared download-plan and explicit public
slide-file descriptors. Set TCIA_REST_BASE_URL for another updated service.

The download scope is Python and pip-installed dependencies. Public DICOM delegates
to idc-index (including its pip-supplied transfer executable); public HTTPS and
approved controlled files use Python HTTP streaming. No Data Retriever or Aspera
CLI is installed or executed. External-only groups remain in metadata with their
published software requirements, counts, and official links. Separate software
notebooks cover those applications. Downloading a supported subset is not full
collection acquisition.

Download tables include patients/subjects, studies, series and images for each
full group. Missing counts display as “Not reported”; CSVs keep missing values,
and zero stays zero. Overlapping groups must not be summed as unique people.

The three public image sample cells download when run, each with max_items=1.
Controlled downloads stay off until an approved reader enables them. The controlled
manifest demo uses max_items=1; the CT/SEG candidate demo keeps one file of each
modality with max_items=2. These limits count whole series/files, not bytes.
Progress is displayed by default. Preparation status appears before index loading;
the same client reuses the index.

Controlled transfers require the reader's approved JSON key-file path. No key
contents appear in the notebook, reports or metadata service. Python currently
uses a narrow httpx-based CRDC authorization adapter, not a general DRS client.
HTTP downloads check available sizes/checksums and restart rather than resume
interrupted files. Exact CT/SEG references and image quality need checking after
authorized transfer. Indexed paths inside archives are not per-file download URLs.

Maintainer checks use tools/test_workshop.py and tools/run_tcia_workshop.py.
Fixture mode preserves the public recording's original observation time and
fingerprint. Local shared-plan projections are explicitly marked; they do not
establish a deployed API or current research result. See validation/ for historical
checks. Validation prohibits credentials and imaging payloads. The recorded replay
skips installation and exercises an installed wheel. In the validation-only copy,
the three public sample calls use dry_run=True; controlled transfers remain off.
Independent HTTP and subprocess guards also prohibit image transfers.

The clinical section now ends with two CMB-LCA cohort downloads.
`plan_participant_images()` inventories public CT series or non-DICOM slide files
for exactly the clinically filtered participants; `download_images(..., max_items=1)`
uses the existing Python adapters for a one-item sample when the cell runs. Coverage includes
zero-match participants and unresolved routes block execution. Public slide copies
may be reformatted; they are not asserted equivalent to submitted originals.
The new explicit slide descriptors require the matching local API changes.
The added recording is bound to the same TCIA fingerprint as the earlier fixture,
with a separately identified bundled-IDC metadata subset and observation time.

Multi-value dataset and download attributes are lists, including singleton and
empty values. This requires the coordinated REST/MCP response update. Download
tables use the SDK's format_table() display helper, which keeps raw query/export
values intact and avoids pandas implicit-downcasting warnings.
