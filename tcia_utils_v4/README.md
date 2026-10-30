# Finding datasets and building participant cohorts with TCIA

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb)

Open [the workshop notebook](TCIA_Dataset_and_Participant_Queries.ipynb). It is a
single, self-contained lesson for junior data scientists, written in the
conversational style of the existing TCIA notebooks.

The lesson covers whole-dataset discovery and download planning with CMB-GEC;
CT-plus-diagnosis cohorts across CMB-GEC and CMB-LCA; public brain MR and NIfTI
segmentations in UCSF-PDGM and UPENN-GBM; and a controlled facial-CT/SEG subset
from HEAD-NECK-RADIOMICS-HN1. It explains public versus controlled access and
DICOM versus other file formats without teaching the hosting infrastructure.

This local review revision needs the **unpublished 4.0.0a4.dev0 wheel** and the
shared download-plan API changes from the query-skill worktree. Nothing in this
revision has been published to PyPI or deployed. The current public Colab notebook
still uses 4.0.0a3. Use the supplied wheel path in the installation cell, or install
that wheel into a fresh Python 3.11+ environment first. Set `TCIA_REST_BASE_URL`
when testing against an updated local/staging service.

The lesson now reads `data_categories` directly from collection search and displays
the shared plan's `download_requirements`. Its public DICOM example passes a local
manifest to `download_manifest()`, and the controlled example passes a URL to the
same method. No learner-defined parsing or routing function is needed.

By default, the notebook makes real public metadata queries and saves small
manifests and tables. All image transfers remain opt-in. Controlled transfers
require the reader's own approval and JSON key-file path. The notebook never
ships a credential or accepts a policy on the reader's behalf.

## Current workflow limits

- Python downloads use `tcia.download_dataset()` or `tcia.download_files()`. Public DICOM reuses `idc-index`, HTTPS files stream directly, and controlled files use the supported authorization API with the reader's approved key file. The notebook includes Data Retriever as an optional alternative.
- Original tissue-slide packages need separately installed/configured [Aspera CLI](https://github.com/IBM/aspera-cli) and IBM transfer tools. The SDK invokes these tools behind the same Python method; pip alone does not install them. The official download link remains available. Missing requirements stop the selection before payload transfers, and reports keep every selected group visible. DICOM-only transfers do not download the whole collection.
- Indexed NIfTI file paths are not per-file download URLs. Use the published
  package links. For the inspected files the service exposes geometry status,
  while detailed dimensions/spacing are empty. An optional local header check
  compares a documented image/mask pair after download.
- Public clinical enrichment is incomplete. Source evidence, inferred values,
  unmatched participant IDs, route caps, and dataset-scoped identity remain
  explicit. The API does not imply access to restricted clinical records.
- A same-participant/study CT+SEG match does not verify the exact DICOM source
  references or the segment names. Check those after an authorized download.

## Maintainer validation

`tools/build_tcia_utils_v4_notebooks.py` regenerates the notebook. Readers do
not need that script or the validation files. The five earlier draft tutorials
were replaced by this one lesson; dated 2026-10-15 reports describe those
superseded drafts only.

Run against an installed candidate wheel:

```bash
python tools/run_tcia_workshop.py --mode fixture
python tools/run_tcia_workshop.py --mode live --report /tmp/workshop-live.json
```

Fixture mode replays the compressed **recording of public metadata**, labels it
as recorded rather than live, and rejects unrecorded HTTP requests. The recording
is for regression tests, not a current research result. Live validation allows
only the metadata API and the small official manifest URLs used in the lesson.
Both modes explicitly skip the tagged PyPI installation cell to preserve the installed artifact under test, block transfer subprocesses, and require nonempty examples. Use
`--mode record` deliberately to refresh the recording after reviewing metadata
changes; this is separate from publishing or updating the live service.

The [live execution](validation/2026-10-25-live.json) and
[offline replay](validation/2026-10-25-fixtures.json) passed on Python 3.13 using
an installed preview wheel. The default CT/diagnosis query matched 17 participant
records across CMB-GEC and CMB-LCA. The brain query linked 2,261 segmentation files
to 1,106 participant records; the controlled example selected two CT/SEG files
for one participant/study. These are indexed records, not unique-person totals
or verified image/label reference pairs. Those historical checks tested the earlier notebook helpers. The current seven notebook tests cover lesson structure, opt-in flags, exact participant/study matching, empty cohorts, and geometry comparison. SDK tests now cover page collection, clinical batching, manifest handling, download routing, authentication boundaries, and transfer failure accounting.

[Download coverage](validation/2026-10-25-download-coverage.json) records the
251-series public DICOM manifest and the 30-row controlled CMB-GEC manifest.
All 251 public series identifiers appear in the Data Retriever's checked
main-branch index. No released CLI binary or image payload transfer was tested.

The release-ready notebook also passed [October 27 live metadata validation](validation/2026-10-27-release-live.json)
and [offline replay](validation/2026-10-27-release-fixture.json). Those checks
explicitly skip the PyPI installation cell to keep testing the installed wheel;
readers run the original installation cell to opt into the alpha.

The October 28 revision removes prerelease background from the lesson, displays published download categories, and uses SDK helpers instead of custom notebook functions. Its [live metadata validation](validation/2026-10-28-live.json) and [recorded replay](validation/2026-10-28-fixture.json) exercise the installed 4.0.0a2 wheel. Imaging transfers stay off; controlled and original-package payload routes are covered by synthetic adapter tests, not live authorized transfers. HTTP reports distinguish available size/checksum verification from delegated engine completion.

The 4.0.0a3 workshop shows collection-level data categories alongside modalities and file formats. The pathology example includes an explicit tool setup guide, a configurable executable path, and a metadata-only prerequisite check with actionable messages before the opt-in transfer. The current gem requires Ruby 3.2 or newer; see the linked installation guide for the runtime in use.

The category/setup revision passed [live metadata execution](validation/2026-10-28-a3-live.json) and [recorded replay](validation/2026-10-28-a3-fixture.json) using the installed 4.0.0a3 wheel. Both runs kept payload transfers off.

## Unpublished shared-contract validation

The fixture recording retains its original observation time and release fingerprint.
`tools/project_shared_download_fixture.py --skill-source /path/to/query-skill`
adds locally projected plan responses using that worktree's shared resolver and
records its source hashes. These are **not** responses from an updated deployed
service. Fixture execution is a local regression check, not a live research result.

All imaging switches remain off. The review build's checks exercise synthetic
transfers and fake credentials in the SDK; no controlled or original-package
payload was retrieved. Installation from a review wheel replaces the temporary
review setup; normal published-version setup will be restored during release
preparation after notebook review is complete.
