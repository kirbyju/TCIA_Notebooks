# Finding datasets and building participant cohorts with TCIA

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb)

The single guided workshop is written for junior data scientists. It covers
CMB-GEC dataset discovery and downloads, CT/diagnosis cohorts across CMB-GEC and
CMB-LCA, public brain MR/NIfTI segmentation metadata, and controlled CT/SEG
candidate selection. It explains public versus controlled access and DICOM versus
other formats without requiring knowledge of the hosting infrastructure.

The workshop installs tcia_utils 4.0.0a7 for Python 3.11+. In Colab, run the setup
cell and restart the runtime when prompted. The hosted REST service must include
the existing shared download plan, public slide descriptors and list-valued
attributes. This transfer-engine update needs no new server routes or bundle.

All supported image/file transfers now delegate to the pip-installed
`tcia-data-retriever==0.1.0rc1`. It bundles the headless transfer executable;
readers do not install Go, Node, a desktop application or another executable.
The `downloads` extra installs it. The separate `cohorts` extra supplies IDC's
public DICOM index for cohort/series metadata; IDC is not the transfer backend.
The tutorial setup installs both extras. Data Retriever owns transfer retries,
checksums, output layout, skip-existing behavior and archive extraction.

Read the TCIA data usage policy before running transfer cells. Those calls pass
accept_data_policy=True explicitly. The three public sample cells run directly,
each with max_items=1. These limits count whole series/files, not bytes. Controlled
examples remain off until an approved reader supplies their own key and enables
them. resume=True requests the transfer package's skip-existing behavior; it is
not a guarantee of partial-file byte-range resume. Ordinary copy mode can download
existing files again. Progress is shown by default. The current TDR Python wrapper
inherits console output even if SDK progress messages are disabled.

The current transfer package may keep a private copy of a supplied controlled key
in its application cache. Its guide documents the platform-specific behavior.
Use an isolated/temporary runtime when credential persistence is inappropriate.
The metadata service and SDK reports do not contain keys, tokens or signed URLs.
No real controlled-access transfer was used to validate this update.

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
image transfers. Recorded metadata and local projections are not deployment proof.

The clinically filtered cohort examples plan public CMB-LCA CT or slide files for
exactly the selected participants. Coverage includes zero matches; unresolved
routes stop execution. Public slide copies may have been reformatted and are not
asserted equivalent to the submitter's originals. Indexed paths inside an archive
are not invented standalone download URLs. Check exact scan/segmentation pairing
and geometry before analysis.

A separate [downloader benchmark](../benchmarks/TCIA_Downloader_Comparison.ipynb)
compares the two released interfaces on identical public CMB-GEC objects. It has
fresh-process and prepared-client cases, alternating trials, fresh destinations,
package/source provenance and DICOM count/hash verification. The small local pilot
is not a universal speed claim; the Colab notebook allows a second environment.

Use a fresh destination when moving from earlier download backends. The default
workshop folder is now tcia-workshop-files. resume=True continues TDR-owned
downloads; it does not import or migrate an earlier IDC/HTTP output tree.
