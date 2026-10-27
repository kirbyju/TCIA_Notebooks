# Finding datasets and building participant cohorts with TCIA

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/codex/tcia-utils-v4-notebooks/tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb)

Open [the workshop notebook](TCIA_Dataset_and_Participant_Queries.ipynb). It is a
single, self-contained lesson for junior data scientists, written in the
conversational style of the existing TCIA notebooks.

The lesson covers whole-dataset discovery and download planning with CMB-GEC;
CT-plus-diagnosis cohorts across CMB-GEC and CMB-LCA; public brain MR and NIfTI
segmentations in UCSF-PDGM and UPENN-GBM; and a controlled facial-CT/SEG subset
from HEAD-NECK-RADIOMICS-HN1. It explains public versus controlled access and
DICOM versus other file formats without teaching the hosting infrastructure.

Use Python 3.11 or newer. The notebook requires the **4.0.0a1 preview** of
`tcia_utils`, which is not yet published as of 2026-10-27. Before publication,
install the reviewed candidate wheel and pandas. After publication, its
installation cell can install the preview and optional NIfTI header reader.
The stable 3.x package has a different API. Ordinary pip installs continue to
select the stable version; requesting `tcia_utils[tables]==4.0.0a1` explicitly
selects the alpha after publication. Users who enable prereleases, for example
with `--pre`, can also opt in.

The Colab badge targets `codex/tcia-utils-v4-notebooks`; it becomes usable when
that branch is pushed to GitHub. Once the alpha is on PyPI, set
`INSTALL_FROM_PYPI = True` in a fresh Colab session and run from the top. Before
the branch is available, upload the notebook through Colab's File menu and
install the supplied wheel. The badge is a launch link, not evidence of a tested
hosted runtime. There is no learner-side helper,
fixture dependency, repository clone, or LLM requirement. Single-file portability
was checked in a local Jupyter kernel; a hosted Colab runtime has not been tested.

By default, the notebook makes real public metadata queries and saves small
manifests and tables. All image transfers remain opt-in. Controlled transfers
require the reader's own approval and JSON key-file path. The notebook never
ships a credential or accepts a policy on the reader's behalf.

## Current workflow limits

- CMB-GEC's public tissue-slide package cannot currently be retrieved by the
  Data Retriever CLI. Its official collection download link is included and
  counted separately. The notebook does not claim that the DICOM commands
  download the entire collection.
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
Both modes block transfer subprocesses and require nonempty examples. Use
`--mode record` deliberately to refresh the recording after reviewing metadata
changes; this is separate from publishing or updating the live service.

The [live execution](validation/2026-10-25-live.json) and
[offline replay](validation/2026-10-25-fixtures.json) passed on Python 3.13 using
an installed preview wheel. The default CT/diagnosis query matched 17 participant
records across CMB-GEC and CMB-LCA. The brain query linked 2,261 segmentation files
to 1,106 participant records; the controlled example selected two CT/SEG files
for one participant/study. These are indexed records, not unique-person totals
or verified image/label reference pairs. Nine focused tests cover identity,
empty searches, route caps, credential-path handling, manifest validation, and
geometry comparison.

[Download coverage](validation/2026-10-25-download-coverage.json) records the
251-series public DICOM manifest and the 30-row controlled CMB-GEC manifest.
All 251 public series identifiers appear in the Data Retriever's checked
main-branch index. No released CLI binary or image payload transfer was tested.
