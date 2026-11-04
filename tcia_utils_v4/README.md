# Finding datasets and building participant cohorts with TCIA

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb)

This guided workshop is written for junior data scientists. It covers CMB-GEC
dataset discovery and downloads; combined modality, diagnosis and primary-site
cohorts across CMB-LCA and NSCLC-Radiomics; clinically selected CT and slide files;
and an open-access NSCLC-Radiomics CT/DICOM SEG sample. Public versus controlled
access and DICOM versus other formats are explained without requiring knowledge
of the hosting infrastructure.

The workshop installs tcia_utils 4.0.0a17 for Python 3.11+. Run the setup cell and
restart the runtime if prompted. The existing query API 0.7.1 provides the needed
metadata. This notebook update requires no server or artifact update.

Downloads use pip-installed tcia-data-retriever 0.1.0rc3. The main notebook does
not install or invoke Aspera. The separate
[Aspera notebook](../TCIA_Aspera_CLI_Downloads.ipynb) contains the brain MR/NIfTI
cohort and optional geometry lesson. It accepts saved participant cohorts and
`packageUrl,packagePath` CSV files from tcia_utils or the Participant Explorer.
Aspera installation and command invocation remain in that notebook.

The four public sample cells run directly: three use max_items=1 and the CT/SEG
sample uses max_items=2 to retain a scan series and a segmentation series. Limits
count whole series/files, not bytes. Controlled CMB-GEC downloads remain off until
an approved user supplies their own key. Rerun the same download call with the
same destination to retry or expand a sample. TDR automatically checks existing
files; the redundant resume argument has been removed. Accepted existing files
count as Skipped and completed; Synced describes public DICOM sync jobs, which
can fetch missing files. TDR owns retries, integrity checks, file layout and
route-specific archive handling.

Current download categories, requirements, methods, counts, access and licenses
remain visible. Unsupported external groups retain their official links. A
successful supported-group download does not prove the full collection was
acquired. Missing counts are not zero, and group counts may overlap. Metadata
CSV creation is preparation, not proof of a successful transfer.

Clinical filters are applied together before pagination. Matching is literal and
case-insensitive. Recorded-only mode requires source evidence and false inference
flags for both diagnosis and primary site. Derived clinical metadata support
discovery; original dataset descriptions and linked source files remain the
authoritative records. Participant identity remains dataset-scoped.

The public CT/SEG example requires CT and SEG within the same participant and
study. It does not prove the exact referenced source series, segment names or
image/mask alignment. Readers must verify those details before analysis.

Maintainer checks use tools/test_workshop.py, tools/test_aspera_cohort.py,
tools/run_tcia_workshop.py and tools/run_aspera_cohort.py. The main validation copy
turns the four public download calls into dry runs. The Aspera validation copy
intercepts all transfer commands. Independent HTTP and subprocess guards prohibit
imaging transfers. Both lessons passed against live public metadata and recorded
fixtures with the installed SDK wheel. The metadata snapshot was
be9e7f9cd4229cb581e0cab83988fde86fa2a7b6724be7b5e57cb75f4e5de637,
observed on 2026-11-04. The Aspera example exported two of 70 indexed files for
two participants. Ruby/Aspera installation and real Aspera payload transfer were
not executed by these checks. Recorded fixtures establish their captured state,
not the freshness of a later deployment.
