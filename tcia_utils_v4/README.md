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

Use Python 3.11 or newer. The notebook explicitly installs the **4.0.0a1
preview** of `tcia_utils` and its table dependencies. Ordinary pip installs
continue to select the stable release; requesting this exact alpha is an opt-in.
The stable 3.x package has a different API. Use a fresh session or environment
for testing.

Click **Open In Colab** above and run the notebook from the top. In Jupyter,
open the same file and run its installation cell. If dependencies are already
installed, set `INSTALL_FROM_PYPI = False` to skip reinstallation. There is no
learner-side helper, fixture dependency, repository clone, or LLM requirement.
Single-file execution was checked in a local Jupyter kernel; a hosted Colab
runtime has not been tested. Report errors at the
[tcia_utils issue tracker](https://github.com/kirbyju/tcia_utils/issues), including
the failing cell and your Python/package versions. Never include credentials.

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
Both modes explicitly skip the tagged PyPI installation cell to preserve the installed artifact under test, block transfer subprocesses, and require nonempty examples. Use
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

The release-ready notebook also passed [October 27 live metadata validation](validation/2026-10-27-release-live.json)
and [offline replay](validation/2026-10-27-release-fixture.json). Those checks
explicitly skip the PyPI installation cell to keep testing the installed wheel;
readers run the original installation cell to opt into the alpha.
