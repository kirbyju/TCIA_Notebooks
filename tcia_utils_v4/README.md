# TCIA Utils 4 preview tutorials

These five tutorials demonstrate the new `TCIAClient` API. They are prepared for
`tcia_utils==4.0.0a1`, which is not yet published as of 2026-10-15. The stable
3.x package uses a different API. This folder is the proposed canonical home;
the package repository will link here when the coordinated release is prepared.

| Notebook | Workflow |
| --- | --- |
| [01 Discover datasets and citations](01_discover_datasets_citations.ipynb) | Find visible TCIA datasets, review access, and obtain citations |
| [02 Public DICOM with IDC](02_public_dicom_idc.ipynb) | Verify TCIA identity, query idc-index, and prepare a series manifest |
| [03 Non-DICOM and annotations](03_non_dicom_annotations.ipynb) | Inspect available public data and annotation signals |
| [04 Controlled metadata](04_controlled_metadata_manifest.ipynb) | Inspect public controlled-file inventory and prepare a DRS manifest |
| [05 Participants and clinical evidence](05_participants_clinical_availability.ipynb) | Retain dataset-scoped identity, provenance, and inference flags |

## Setup

Use Python 3.11 or newer and a fresh environment. Clone this repository, retain
the complete folder, and open its notebooks in your Jupyter environment.
`_support.py` and `_fixtures/` are part of the tutorials, so downloading an
individual `.ipynb` is insufficient. Single-notebook Colab launch support is a
remaining release-preparation step; no Colab compatibility is claimed yet.

After the preview is published:

```bash
python -m pip install -r tcia_utils_v4/requirements.txt
```

Before publication, install the reviewed package wheel and then the example
dependencies listed after the `tcia_utils` line in `requirements.txt`. Do not
substitute the current stable 3.x package for the v4 wheel.

## Example modes

The default mode uses clearly labeled synthetic fixtures and makes no TCIA
service requests. The fixture files are small demonstration metadata, not
TCIA research evidence. To use bounded live metadata instead, set
`TCIA_EXAMPLE_MODE=live` in the environment before launching Jupyter. The default
live service is `https://tcia.duckdns.org`; `TCIA_V2_BASE_URL` can select another
compatible V2 host. Restart the kernel after changing these settings.

The examples inspect metadata and write local manifest files. They do not
transfer imaging payloads, run Data Retriever, or authenticate to controlled
repositories. Controlled metadata does not confer retrieval authorization.
Public DICOM detail uses idc-index directly. Keep access, licenses, dataset
identity, and completeness evidence with any saved selection.

## Validation

All five relocated notebooks passed [fixture execution](validation/2026-10-15-fixtures.json) and [bounded live execution](validation/2026-10-15-live.json) on 2026-10-15, using the installed 4.0.0a1 wheel and idc-index 0.13.0. The package repository's runner checks these notebooks. The recorded fixture and live results
identify exact package, IDC index, and observed service versions. Package CI
still needs to be updated to check out this repository at an immutable commit;
its current notebook gate points to the package's original examples folder.
