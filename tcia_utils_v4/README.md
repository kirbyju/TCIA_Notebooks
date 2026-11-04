# Finding datasets and building participant cohorts with TCIA

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb)

The single guided workshop is written for junior data scientists. It covers
CMB-GEC dataset discovery and downloads, combined CT/diagnosis/primary-site cohorts
across CMB-LCA and NSCLC-Radiomics (with CMB-GEC as a site-filter comparison), public brain MR/NIfTI segmentation metadata, and controlled CT/SEG
candidate selection. It explains public versus controlled access and DICOM versus
other formats without requiring knowledge of the hosting infrastructure.

The workshop installs tcia_utils 4.0.0a16 for Python 3.11+. In Colab, run the setup
cell and restart the runtime when prompted. The hosted REST service must include
query API 0.7.1+ with combined participant clinical filters, the shared participant
image-planning route, public slide descriptors and list-valued attributes.
This requires a source update and REST/MCP restart; no bundle rebuild is needed.

All supported image/file transfers now delegate to the pip-installed
`tcia-data-retriever==0.1.0rc3`. It bundles the headless transfer executable;
readers do not install Go, Node, a desktop application or another executable.
The `downloads` extra installs it. Participant image planning uses the same TCIA
service interface for public DICOM series and public non-DICOM files. The service
reuses IDC's versioned metadata for public DICOM and retains provider attribution.
No IDC package or separate provider query is required in the notebook. Advanced
IDC-specific queries and viewers remain available through IDC's own tools.
The tutorial setup installs both extras. Data Retriever owns transfer retries,
checksums, output layout, skip-existing behavior and archive extraction.

Read the TCIA data usage policy before running transfer cells. Those calls pass
accept_data_policy=True explicitly. The three public sample cells run directly,
each with max_items=1. These limits count whole series/files, not bytes. Controlled
examples remain off until an approved reader supplies their own key and enables
them. To expand a sample, keep the same destination and omit max_items; the
transfer package can reuse existing files without resume=True. That option
explicitly requests skip-existing checks, not partial-file byte-range resume.
In RC3, verified existing files count as Skipped and completed. Synced identifies
public DICOM sync jobs, which may transfer missing files. TDR streams plain progress lines into notebook output,
even if SDK preparation messages are disabled.

Supplied CLI/Python controlled keys are used for that invocation only, without a
saved credential copy or fallback to desktop GUI credentials.
The metadata service and SDK reports do not contain keys, tokens or signed URLs.
No real controlled-access transfer was used to validate this update.
Standalone file-manifest downloads use the SDK's generic manifest collection
label, and TDR preserves supplied archive filenames. This can differ from the
public DICOM hierarchy. Direct/controlled ZIP files remain archives. Use known
dataset context consistently if choosing download_dataset() instead.

External-only Aspera groups remain in the inventory with counts, published
requirements and official links. Separate application notebooks cover them.
Downloading supported groups is not proof of acquiring an entire collection.
Download tables show published full-group subjects/studies/series/images; counts
may overlap, and missing counts are not zero. Multi-value attributes remain lists.
The format_table helper adds display-only missing labels without changing exports.

Maintainer checks use tools/test_workshop.py and tools/run_tcia_workshop.py. The
runner exercises the installed wheel with recorded public metadata. Its private
validation copy uses dry_run=True and accept_data_policy=False for public sample
calls; controlled examples remain off. Independent HTTP/subprocess guards block
image transfers. Recorded metadata describe their captured snapshot and are not
proof that a later deployment or source update is equivalent.

Participant search applies modality, diagnosis and primary-site criteria together
before pagination. Text matching is literal and case-insensitive. Recorded-only
mode requires both selected clinical fields to have false inference flags and
patient-level source evidence. Missing values cannot satisfy either text filter.
The site is the clinical primary_site field, not the scanned body part. Full
clinical exploration enriches only the matches. Query settings, separate inference
flags and metadata snapshot remain with outputs.

The fixture contains actual public metadata responses from the deployed 0.7.1
API, recorded on 2026-11-03. The complete notebook passed against that deployment
using the built 4.0.0a16 wheel with all imaging transfers blocked. The default
combined search returned 322 records across CMB-LCA and NSCLC-Radiomics;
recorded-only diagnosis/site evidence returned 5 CMB-LCA records.

The clinically filtered cohort examples plan public CMB-LCA CT or slide files for
exactly the selected participants. Coverage includes zero matches; unresolved
routes stop execution. Public slide copies may have been reformatted and are not
asserted equivalent to the submitter's originals. Indexed paths inside an archive
are not invented standalone download URLs. Check exact scan/segmentation pairing
and geometry before analysis.

Use a fresh destination when moving from earlier download backends. The default
workshop folder is now tcia-workshop-files. resume=True continues TDR-owned
downloads; it does not import or migrate an earlier IDC/HTTP output tree.

Controlled CT/SEG downloads distinguish the reported DICOM-series size from exact
ZIP payload bytes. Server 0.7.1 supplies the size basis and published archive-size
label; only exact manifest byte counts are used as payload-size assertions. SDK
a15 also avoids asserting ambiguous controlled-inventory sizes when exact payload
metadata is absent. Available checksum and response-length checks remain enabled.
The metadata CSV is written during preparation and does not prove transfer success.

This notebook uses the RC3 candidate containing the TDR PR #13 counter change.
The TDR review remains open; this package preview supports testing before the
team completes formal review. No new download option is required.
