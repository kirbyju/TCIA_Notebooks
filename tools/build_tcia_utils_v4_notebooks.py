"""Build the single TCIA workshop; reusable behavior lives in tcia_utils."""
from pathlib import Path
import nbformat as nbf
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tcia_utils_v4"
cells = []
def md(source): cells.append(nbf.v4.new_markdown_cell(source.strip()))
def code(source, **metadata): cells.append(nbf.v4.new_code_cell(source.strip(), metadata=metadata))

md(r'''[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb)

# Finding datasets and building participant cohorts with TCIA

In this hands-on lab we'll start with a dataset, then work our way down to individual participants. Along the way we'll find images, clinical information, and segmentation labels. You only need a little Python and some familiarity with pandas tables.

We'll work through four questions:

1. **Which datasets have the data I need, and how do I download a whole dataset?**
2. **Can I find participants with a particular image modality and diagnosis across datasets?**
3. **Where can I find public brain MR images with segmentation masks?**
4. **How do I prepare a controlled-access CT cohort with segmentations?**

Our main example is [CMB-GEC](https://www.cancerimagingarchive.net/collection/cmb-gec/), which includes radiology images, tissue-slide images, and links to clinical information. Later we'll look at brain MR and head-and-neck CT.

Use Python **3.11 or newer**. The installation cell sets up the packages used in this lab. This notebook is self-contained: you do not need other files from the repository.

Running all cells queries real, public metadata and saves small manifests and tables. Image downloads stay off until you choose to run them. You do not need an LLM account or a controlled-data account to explore the metadata.''')

md(r'''## Let's get set up

Run the next cell to install the packages used in this lab. In Colab, run the notebook from the top. In Jupyter, use a fresh Python 3.11+ environment. Restart the Python session if prompted after installation.

`pandas` helps us work with tables, and `nibabel` is used by the optional NIfTI header check. Download support is included, but querying the metadata does not download any images.''')

code(r'''TCIA_UTILS_WHEEL = ""  # Path to the supplied workshop wheel, if not already installed.
if TCIA_UTILS_WHEEL:
    import subprocess, sys
    from pathlib import Path

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            f"{Path(TCIA_UTILS_WHEEL).expanduser().resolve()}[tables,downloads]",
            "nibabel>=5,<6",
        ]
    )''', tags=['installation'])

code(r'''from pathlib import Path
from importlib.metadata import version
from datetime import datetime, timezone
from urllib.parse import urlsplit
import hashlib
import json
import os

import httpx
import pandas as pd
from IPython.display import display, Markdown
from tcia_utils import TCIAClient, DownloadError

assert hasattr(
    TCIAClient, "download_manifest"
), "Install the supplied workshop wheel, then restart Python and run from the top."
pd.set_option("display.max_colwidth", 85)
OUTPUT = Path(os.environ.get("TCIA_EXAMPLE_OUTPUT_DIR", "tcia-workshop-output"))
OUTPUT.mkdir(parents=True, exist_ok=True)
BASE_URL = os.environ.get("TCIA_REST_BASE_URL", "https://tcia.duckdns.org")
tcia = TCIAClient(base_url=BASE_URL, timeout=120, pin_snapshot=True)
status = tcia.status()
SNAPSHOT = status.provenance.release_fingerprint
print("tcia_utils:", version("tcia_utils"))
print("Metadata observed:", datetime.now(timezone.utc).date())
print("Service ready:", status.data.readiness["status"])''')

md(r'''TCIA's search service uses a prepared metadata snapshot so we can ask questions before downloading images. We'll keep original links with our results because the snapshot can lag behind a dataset's web page.

When we use `to_dataframe(all_pages=True)`, the package collects every search page. We also ask the client to keep the same snapshot throughout this session; it will tell us to restart if the metadata changes.''')

md(r'''## 1. Which dataset should I download?

A **Collection** is a published dataset. An **Analysis Result** is another published contribution, often containing annotations or measurements made from existing images. Keep the dataset name and type together so we know exactly which contribution we're using.

There are also two independent choices to understand:

| Choice | What it means for us |
| --- | --- |
| Public or controlled access | Public files can be retrieved under their license. Controlled files require approval before download, even when their descriptions are public. |
| DICOM or non-DICOM | DICOM is a medical imaging format. Other useful formats include NIfTI image volumes, SVS tissue slides, spreadsheets, and archives. Non-DICOM does not mean non-image. |

A single collection can contain several combinations. **Public** also does not mean unrestricted use: read each download's license, including any noncommercial condition.

Start in the [TCIA Dataset Explorer](https://www.cancerimagingarchive.net/dataset-explorer/). Try a cancer-location filter and a modality filter, then open a matching collection's page. For this lesson, choose **CMB-GEC**, open its **Data Access** tab, and note the separate download/manifest links and licenses. The Explorer helps us find the dataset; its page describes the individual download groups.

In Python, we can explore the same kinds of collection attributes. Let's try a cancer location and image modality. Change these values and rerun the cell to explore.''')

code(r'''CANCER_LOCATION = "Esophagus"
IMAGE_MODALITY = "CT"
datasets = tcia.search_datasets(
    dataset_type="collection",
    cancer_locations=[CANCER_LOCATION],
    modalities=[IMAGE_MODALITY],
    limit=100,
).to_dataframe(all_pages=True)
print("Matching collections:", len(datasets))
display(
    datasets.reindex(
        columns=[
            "short_title",
            "title",
            "data_categories",
            "download_data_types",
            "cancer_types",
            "cancer_locations",
            "resolved_access_level",
            "download_file_types",
            "external_resource_labels",
            "tcia_page",
        ]
    )
)''')

md(r'''The `data_categories` column tells us what kinds of downloadable data a collection publishes, such as radiology or pathology images. `download_data_types` shows modalities and other data types, while `download_file_types` shows formats. External resources, such as linked clinical information, stay in their own column.

These are **collection-level** labels. Finding a collection with CT and a cancer label does not tell us that every participant has both. We'll check participant-level information in section 2.

Now let's open CMB-GEC. The download table is especially useful: it tells us which files are public, which need approval, and which formats we'll receive.''')

code(r'''DATASET = "CMB-GEC"
detail = tcia.get_dataset(DATASET)
collection = next((row for row in detail.data["datasets"] if row["dataset_type"] == "Collection"))
display(
    Markdown(
        f"### [{collection['short_title']}]({collection['tcia_page']})\n\n{collection['title']}"
    )
)
print("Dataset version:", collection["current_version_number"])
print("Public external clinical resource linked:", collection["has_external_clinical_resource"])
plan = tcia.plan_downloads(DATASET)
downloads = plan.to_dataframe()
display(
    downloads.reindex(
        columns=[
            "download_id",
            "download_title",
            "download_category",
            "download_requirements",
            "python_supported",
            "subjects",
            "studies",
            "series",
            "images",
            "access_level",
            "data_types",
            "file_types",
            "license_label",
            "download_size",
            "download_size_unit",
            "download_url",
        ]
    ).convert_dtypes().astype(object).fillna("Not reported")
)
downloads.to_csv(OUTPUT / "CMB-GEC_download_inventory.csv", index=False)''')

md(r'''CMB-GEC is a good reminder that **a dataset is not always one download**. Its download categories distinguish radiology images, tissue-slide images, clinical tables, and other supporting files. Access and file format are separate attributes.

The download tables also show **patients/subjects, studies, series, and images** using the published `subjects`, `studies`, `series`, and `images` fields. These counts describe each **full download group**, not the small sample we'll try later. “Not reported” means the count is unavailable; it does not mean zero. Some counts do not apply to non-DICOM data. Groups can overlap, so adding their counts does not establish a total number of unique patients.

The download plan includes a `download_requirements` column describing the published download instructions. `python_supported` tells us which groups this package can transfer using Python and pip-installed dependencies. These are separate from access approval: controlled files still require your approved key. Groups needing another application remain in the inventory with their official links, but this notebook does not install or run those applications. A manifest is a shopping list; it does not contain the images or grant access to controlled files.''')

code(r'''download_plan = downloads
python_groups = download_plan[download_plan["python_supported"]]
external_groups = download_plan[~download_plan["python_supported"]]
manifest_groups = python_groups[
    python_groups["download_method"].isin(["dicom_manifest", "tabular_manifest"])
]
display(
    download_plan.reindex(
        columns=[
            "download_id",
            "download_title",
            "download_category",
            "download_requirements",
            "python_supported",
            "subjects",
            "studies",
            "series",
            "images",
            "access_level",
            "file_types",
        ]
    ).convert_dtypes().astype(object).fillna("Not reported")
)
print("Selected download groups:", len(download_plan))
print("Groups supported by Python:", len(python_groups))
print("Groups requiring an external download route:", len(external_groups))''')

md(r'''### Save the manifests, then choose whether to download

The next cell uses `tcia.save_manifests()` to save the small official manifest files, with their original contents, source links, and checksums. It does not download images. Package links stay in the inventory; they are not mistaken for manifests.

**Controlled access:** the classification in the table comes from the download's license metadata. Public descriptions and manifests are not authorization. Read the [current TCIA access policy](https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/), request the required dbGaP authorization, and create your own JSON API key using the linked instructions. For CMB-GEC's controlled images the policy identifies **phs002192**. You can still save and inspect the public manifest without that key.''')

code(r'''manifest_report = tcia.save_manifests(manifest_groups, OUTPUT)
saved_manifests = manifest_report.records
display(manifest_report.to_dataframe())''')

md(r'''### Download directly from Python

Let's start with the **public DICOM imaging group**. We already saved its manifest, so we can pass that file straight to `tcia.download_manifest()`. The package reads the identifiers and handles the transfer; we do not need to parse the file ourselves. It prints “Preparing download selection…” immediately. The first public DICOM call prepares its imaging index; later calls through the same `tcia` client reuse it. File-transfer progress follows preparation. Use `progress=False` if you want to suppress these progress messages and the transfer bar.

This function accepts a **local path or an HTTPS URL**, for either a `.tcia` manifest or a supported CSV/TSV manifest. It reads the manifest's route column and chooses the appropriate download method. If part of the requested selection is unavailable, it tells us rather than silently dropping those files.

Before a large download, let's **try one item**. Passing `max_items=1` downloads the first whole DICOM series or file in the manifest. This is a real transfer, so it can help us check the setup and inspect the data. A whole series or file can still be large: this option limits the number of items, not the number of bytes.

Leave `DOWNLOAD_PUBLIC_DICOM = False` to keep exploring without a transfer. If you enable it, the next cell downloads one DICOM series into a sample folder. The report shows how many items were selected and how many were available. These are the first items in the supplied order, so they may not represent every kind of data in the collection.

After checking the sample, use a separate destination and omit `max_items` to request the full manifest. A successful sample does not establish that every remaining item is available or that an image and segmentation match.''')

code(r'''DOWNLOAD_PUBLIC_DICOM = False
public_manifest = next(
    item for item in saved_manifests if item["route_column"] == "SeriesInstanceUID"
)

if DOWNLOAD_PUBLIC_DICOM:
    report = tcia.download_manifest(
        OUTPUT / public_manifest["manifest"], OUTPUT / "samples" / DATASET, max_items=1
    )
    display(report.to_dataframe())
else:
    print("Public DICOM download is off. Set DOWNLOAD_PUBLIC_DICOM = True when ready.")''', tags=['optional-download'])

md(r'''### Groups requiring another application

The tissue-slide group in CMB-GEC needs a separate transfer application, so it stays outside this notebook's Python downloads. Its counts, published requirements, and official link remain in the inventory above. Follow that link or use our [separate package-download notebook](https://github.com/kirbyju/TCIA_Notebooks/blob/main/TCIA_Aspera_CLI_Downloads.ipynb) when you need those original files.

Other collections may offer non-DICOM files through Python-supported manifests or HTTPS links. Use `python_supported` to check each group. Downloading only the Python-supported groups does **not** mean we have downloaded the entire collection.''')

md(r'''### Download the controlled group after approval

For controlled images, the Python function also needs the **path** to your own JSON API key. It uses the official file identifiers and the authorized service. It does not print or copy the key. Don't paste key contents into a notebook, repository, or chat.

Leave the next cell unchanged to continue without a controlled download. An approved user can enter a key-file path and set `DOWNLOAD_CONTROLLED_CMB = True` to try the first file in the manifest. It still needs the same authorization as a larger download. Authorization for one study may not cover another.''')

code(r'''CREDENTIAL_FILE = ""  # Path to your own approved JSON key file; never the key value.
DOWNLOAD_CONTROLLED_CMB = False
controlled_manifest = next(item for item in saved_manifests if item["route_column"] == "drs_uri")

if DOWNLOAD_CONTROLLED_CMB:
    report = tcia.download_manifest(
        controlled_manifest["url"],  # A URL works just like a local manifest path.
        OUTPUT / "samples" / DATASET,
        credential_file=CREDENTIAL_FILE,
        max_items=1,
    )
    display(report.to_dataframe())
else:
    print("Controlled CMB-GEC download is off. Public manifests are ready for an approved user.")''', tags=['optional-download'])

md(r'''Before calling a dataset download complete, compare your downloaded files and the SDK completion report with **every row** in the inventory. Resolve failed or skipped files, follow the separate download route for the tissue-slide group, and follow the collection's external-resource links if your project needs those data too. A manifest on disk or a successful metadata query is not evidence that images were transferred.

Let's save the dataset citation as well. Keep the citation and license information with your project, and follow the collection page's acknowledgement instructions.''')

code(r'''citation = tcia.get_citation(collection["doi"], style="apa")
print(citation.data["record"]["formatted_citation"])
(OUTPUT / "CMB-GEC_citation.json").write_text(json.dumps(citation.data, indent=2))''')

md(r'''## 2. Which participants have the modality and diagnosis I need?

Suppose we want CT images from participants whose available diagnosis includes “Carcinoma.” We'll search **CMB-GEC and CMB-LCA together**. Change the collection list, modality, and diagnosis text to try your own question. Removing the collection restriction would search much more broadly and take longer.

This is a participant query, not a search of collection descriptions. We'll first find participants with the selected modality, then match their available clinical information. Our diagnosis match is a simple, case-insensitive text search; it does not know that two different medical terms can mean the same thing.''')

code(r'''COHORT_COLLECTIONS = ["CMB-GEC", "CMB-LCA"]
COHORT_MODALITY = "CT"
DIAGNOSIS_TEXT = "Carcinoma"
candidates = tcia.search_participants(
    short_titles=COHORT_COLLECTIONS,
    dataset_type="collection",
    modalities=[COHORT_MODALITY],
    limit=500,
).to_dataframe(all_pages=True)
if candidates.empty:
    candidates = pd.DataFrame(
        columns=["short_title", "display_participant_id", "participant_key", "modalities"]
    )
    print("No participants matched. Try another collection or modality.")
print("Candidate participant records:", len(candidates))
display(
    candidates.reindex(
        columns=[
            "short_title",
            "display_participant_id",
            "modalities",
            "file_formats",
            "has_open_data",
            "has_controlled_data",
        ]
    ).head(10)
)''')

md(r'''Clinical information can come from a collection's own files or public clinical enrichment from other resources. The API keeps the source and whether a value was **recorded for the participant** or **inferred from the dataset**. For example, a collection-level cancer label is useful for discovery, but it is not a confirmed diagnosis for each person.

`tcia.clinical_for_participants()` handles the batching and checks the returned identities. We'll join exact participant IDs **within each collection**. We won't guess an ID conversion or assume that the same ID in two collections means the same person. Unmatched IDs stay visible.''')

code(r'''clinical_result = tcia.clinical_for_participants(candidates)
clinical = clinical_result.to_dataframe(
    "subjects",
    columns=[
        "short_title",
        "subject_id",
        "primary_diagnosis",
        "primary_diagnosis_is_inferred",
        "primary_site",
        "primary_site_is_inferred",
        "resolved_values",
        "resolved_sources",
        "conflicts",
    ],
)
with_clinical = candidates.merge(
    clinical,
    how="left",
    left_on=["short_title", "display_participant_id"],
    right_on=["short_title", "subject_id"],
    validate="many_to_one",
    indicator="clinical_link",
)
print("Clinical linkage (no fuzzy ID matching):")
display(with_clinical["clinical_link"].value_counts())
print("Available diagnosis labels:")
display(with_clinical["primary_diagnosis"].value_counts(dropna=False).to_frame("participants"))''')

md(r'''Let's apply the diagnosis filter. In the **next code cell**, choose whether to allow diagnoses inferred from the dataset:

- Leave `INCLUDE_INFERRED_DIAGNOSES = True` to allow matching diagnosis labels, including inferred ones.
- Set it to `False` to keep only matching diagnoses explicitly marked as reported for that participant. Rows with an unknown inference status are also left out.

The results include a separate column, `primary_diagnosis_is_inferred`: `True` means the diagnosis was inferred, `False` means it was reported at the participant level, and a blank means the inference status is unknown. This column stays in the displayed table and the saved CSV/JSON so you can tell how each diagnosis was obtained. It is different from the `INCLUDE_INFERRED_DIAGNOSES` setting, which controls what we include. Change that setting and rerun the next cell to compare the cohorts; you do not need to repeat the earlier metadata queries.

We are counting **dataset-scoped participant records**. We have not deduplicated people across collections, and a missing clinical value does not mean a participant has no diagnosis. This cohort is limited to the selected collections and the information currently indexed.''')

code(r'''INCLUDE_INFERRED_DIAGNOSES = True  # False keeps only explicitly reported diagnoses.

matches = (
    with_clinical["primary_diagnosis"]
    .astype("string")
    .fillna("")
    .str.contains(DIAGNOSIS_TEXT, case=False, regex=False)
)
if not INCLUDE_INFERRED_DIAGNOSES:
    matches &= with_clinical["primary_diagnosis_is_inferred"].eq(False)
cohort = with_clinical.loc[matches].copy()
print("Matching participant records:", len(cohort))
display(
    cohort.reindex(
        columns=[
            "short_title",
            "display_participant_id",
            "modalities",
            "primary_diagnosis",
            "primary_diagnosis_is_inferred",
            "primary_site",
            "primary_site_is_inferred",
            "has_open_data",
            "has_controlled_data",
        ]
    )
)
cohort.to_json(OUTPUT / "modality_diagnosis_cohort.json", orient="records", indent=2)
cohort.drop(columns=["resolved_values", "resolved_sources", "conflicts"]).to_csv(
    OUTPUT / "modality_diagnosis_cohort.csv", index=False
)''')

md(r'''### What else do we know about these participants?

The short table above is only a starting point. Let's put **all resolved clinical concepts** for the matched participants into a second table. That can include demographics, outcomes, treatment-related values, or molecular findings when those were indexed. We keep the source evidence beside each value rather than assuming all collections report the same things.

These clinical summaries are a **derived curation layer**. They do not replace the [original dataset descriptions and clinical files](https://www.cancerimagingarchive.net/collections/). CMB-GEC links additional clinical resources on its page; the API includes the public facts it has indexed, not every field available at those links or any restricted clinical file. Blank means “not available here,” not “does not exist.”''')

code(r'''clinical_values = clinical_result.to_dataframe(
    "values",
    columns=[
        "short_title",
        "participant_id",
        "concept",
        "value",
        "is_inferred",
        "evidence_scope",
        "source_evidence",
    ],
)
clinical_summary = clinical_values.merge(
    cohort[["short_title", "display_participant_id"]],
    left_on=["short_title", "participant_id"],
    right_on=["short_title", "display_participant_id"],
    how="inner",
    validate="many_to_one",
).drop(columns="display_participant_id")
display(clinical_summary.drop(columns="source_evidence").head(25))
clinical_summary.to_json(OUTPUT / "cohort_clinical_evidence.json", orient="records", indent=2)
print(
    "The displayed rows are a preview; the JSON export contains every resolved value collected above."
)''')

md(r'''For a closer look, choose one matching participant. The first cell lists their known data types, access levels, formats, and geometry summaries. The next keeps the original clinical facts, source links, and disagreements for that participant. We use CMB-GEC first when it is present in the cohort.''')

code(r'''ordered = cohort.assign(example_first=cohort["short_title"].ne("CMB-GEC")).sort_values(
    ["example_first", "short_title", "display_participant_id"]
)
example = ordered.iloc[0].to_dict() if len(ordered) else None
participant_assets = pd.DataFrame()
if example:
    print(example["short_title"], example["display_participant_id"])
    participant = tcia.get_participant(example["participant_key"])
    participant_assets = tcia.list_participant_assets(
        example["participant_key"], limit=500
    ).to_dataframe(all_pages=True)
    display(
        participant_assets.reindex(
            columns=[
                "data_category",
                "data_type",
                "modality",
                "access_level",
                "file_format",
                "file_count",
                "geometry_status",
            ]
        )
    )
    (OUTPUT / "example_participant.json").write_text(json.dumps(participant.data, indent=2))
    participant_assets.to_json(
        OUTPUT / "example_participant_assets.json", orient="records", indent=2
    )
else:
    print("No matches. Try a diagnosis label from the table above.")''')

code(r'''example_facts = []
if example:
    facts = tcia.list_clinical_facts(
        example["short_title"], subject_id=example["subject_id"], limit=500
    )
    conflicts = tcia.list_clinical_conflicts(
        example["short_title"], subject_id=example["subject_id"], limit=500
    )
    example_facts = facts.data["facts"]
    display(
        pd.DataFrame(example_facts).reindex(
            columns=[
                "concept",
                "value_text",
                "value_resolved",
                "is_inferred",
                "evidence_scope",
                "source_url",
                "source_date",
                "qc_status",
            ]
        )
    )
    print("Clinical conflict rows:", conflicts.data["count"])
    if conflicts.data["count"]:
        display(pd.DataFrame(conflicts.data["conflicts"]))
    print(
        "Facts returned:",
        facts.data["count"],
        "(bounded at 500; this is not an all-facts pagination route)",
    )
    (OUTPUT / "example_clinical_facts.json").write_text(json.dumps(facts.data, indent=2))
    (OUTPUT / "example_clinical_conflicts.json").write_text(json.dumps(conflicts.data, indent=2))''')

md(r'''### From this clinical cohort to radiology images

Now that we have our participant list, let's use it to choose some images. We'll keep the **CMB-LCA participants in `cohort`**, so the diagnosis and inference settings we just used still apply. We aren't starting a new clinical search.

For the radiology example, choose **CT in DICOM format**. `plan_participant_images()` finds all indexed matching public CT series for these participants and shows coverage, including participants with no matches. It matches participant IDs within the collection and checks its published image manifest. It does not add other participants, modalities, or controlled images.

Leave the switch off to inspect metadata only. If you turn it on, `max_items=1` downloads **one whole CT series**, including all of its DICOM image files. After inspecting that sample, omit `max_items` to download all matching public CT series in this plan. Rebuild the plan if you change the clinical filters. A single series can still be large.''')

code(r'''clinical_image_participants = cohort[cohort["short_title"].eq("CMB-LCA")].copy()
ct_images = tcia.plan_participant_images(
    clinical_image_participants, modality="CT", file_format="DICOM"
)
display(ct_images.coverage_to_dataframe())
display(
    ct_images.to_dataframe().reindex(
        columns=["short_title", "participant_id", "study_instance_uid", "series_instance_uid",
                 "modality", "file_format", "instance_count", "size_bytes"]
    )
)
if ct_images.unresolved:
    display(pd.DataFrame(ct_images.unresolved))

DOWNLOAD_CLINICAL_CT = False
if DOWNLOAD_CLINICAL_CT and ct_images.rows:
    report = tcia.download_images(ct_images, OUTPUT / "clinical-ct-sample", max_items=1)
    display(report.to_dataframe())
else:
    print("Clinical CT download is off, or no matching public series were found.")''', tags=['optional-download'])

md(r'''### Use the same clinical cohort for whole-slide pathology images

For a pathology project, keep the **same CMB-LCA participant list** and ask for **Whole Slide Image in non-DICOM format**. This gives us individual slide files rather than a full-collection package. The coverage table tells us which clinically matched participants have downloadable slides; a participant with CT is not guaranteed to have a slide here.

These are **public slide copies**, which may have been reformatted for browser viewing. Their equivalence to the submitter's original files is not established. If your analysis requires the submitted originals, follow the original-file download on the [CMB-LCA collection page](https://www.cancerimagingarchive.net/collection/cmb-lca/). That separate application workflow is outside this notebook.

The next cell plans all matching public slides, but `max_items=1` keeps the opt-in download to **one whole slide file**. Omit that limit to download all matching slide files in the plan. Whole-slide files can be large even when we're downloading only one. Any matched file without a supported route remains unresolved and stops the transfer; we do not silently skip it.''')

code(r'''slide_images = tcia.plan_participant_images(
    clinical_image_participants, modality="Whole Slide Image", file_format="non-DICOM"
)
display(slide_images.coverage_to_dataframe())
display(
    slide_images.to_dataframe().reindex(
        columns=["short_title", "participant_id", "modality", "file_format", "file_name",
                 "size_bytes", "download_representation", "python_supported"]
    )
)
if slide_images.unresolved:
    display(pd.DataFrame(slide_images.unresolved))

DOWNLOAD_CLINICAL_SLIDES = False
if DOWNLOAD_CLINICAL_SLIDES and slide_images.rows:
    report = tcia.download_images(slide_images, OUTPUT / "clinical-slide-sample", max_items=1)
    display(report.to_dataframe())
else:
    print("Clinical slide download is off, or no matching public slides were found.")''', tags=['optional-download'])

md(r'''## 3. Where are the public brain MR images with segmentation masks?

A **segmentation** labels parts of an image, such as a tumor. The label image is useful for training or evaluating a model, but we also need the source image and an understanding of how the two line up.

We'll search [UCSF-PDGM](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/) and [UPENN-GBM](https://www.cancerimagingarchive.net/collection/upenn-gbm/). These provide public brain MR data in **NIfTI**, a common volume format with filenames ending in `.nii` or `.nii.gz`.

First find participants with public NIfTI MR data. Then look for indexed segmentation files and join them within each collection. We deliberately keep participants with unchecked geometry so “not checked” is not confused with “bad image.”''')

code(r'''BRAIN_COLLECTIONS = ["UCSF-PDGM", "UPENN-GBM"]
brain_candidates = tcia.search_participants(
    short_titles=BRAIN_COLLECTIONS,
    dataset_type="collection",
    modalities=["MR"],
    access_levels=["open"],
    file_formats=["NIFTI"],
    limit=500,
).to_dataframe(all_pages=True)
brain_masks = tcia.search_public_assets(
    short_titles=BRAIN_COLLECTIONS,
    modalities=["MR"],
    file_formats=["NIFTI"],
    object_roles=["segmentation"],
    requires_annotations=True,
    limit=500,
).to_dataframe(all_pages=True)
if brain_candidates.empty:
    brain_candidates = pd.DataFrame(
        columns=["short_title", "display_participant_id", "participant_key"]
    )
if brain_masks.empty:
    brain_masks = pd.DataFrame(
        columns=["short_title", "subject_id", "asset_id", "file_name", "geometry_status"]
    )
linked_masks = brain_masks.drop(
    columns=["participant_key", "display_participant_id"], errors="ignore"
).merge(
    brain_candidates[["short_title", "display_participant_id", "participant_key"]],
    left_on=["short_title", "subject_id"],
    right_on=["short_title", "display_participant_id"],
    how="left",
    validate="many_to_one",
    indicator="participant_link",
)
brain_cohort = linked_masks[linked_masks["participant_link"] == "both"].copy()
print("Public MR participant records:", len(brain_candidates))
print("Indexed segmentation files:", len(brain_masks))
print(
    "Segmentation files without an exact inventory ID match:",
    linked_masks["participant_link"].eq("left_only").sum(),
)
display(
    brain_cohort.groupby("short_title").agg(
        participant_records=("participant_key", "nunique"),
        segmentation_files=("asset_id", "nunique"),
    )
)
display(brain_cohort[["short_title", "subject_id", "file_name", "geometry_status"]].head(10))
brain_cohort.to_json(OUTPUT / "brain_mr_segmentation_inventory.json", orient="records", indent=2)''')

md(r'''This tells us that a participant has both public MR data and segmentation files. Some masks label brain tissue and others label tumor regions; check the file descriptions for the labels you need. This table does **not** establish which individual MR volume each mask annotates. Use the dataset's file descriptions and naming documentation to select the corresponding source image.

Also, participant IDs do not always equal unique people. The UCSF-PDGM description explains that some original IDs were later recognized as follow-up scans of the same person. Use the collection's documented relationships when splitting training and test data; don't split related scans between them just because their filenames differ.

### What does the geometry information tell us?

Geometry describes the image grid: dimensions, voxel spacing, and orientation. `checked_grid_geometry` means a grid assessment was recorded. It does not prove that a mask matches a source image or that either is suitable for your model. `not_checked` means we don't have an assessment here.

Let's inspect one participant's source-image and segmentation records, including any detailed geometry information the service exposes.''')

code(r'''brain_files = pd.DataFrame()
if len(brain_cohort):
    brain_example = brain_cohort.sort_values(["short_title", "subject_id", "file_name"]).iloc[0]
    brain_files = tcia.search_public_assets(
        short_titles=[brain_example["short_title"]],
        participant_id=brain_example["subject_id"],
        file_formats=["NIFTI"],
        limit=500,
    ).to_dataframe(all_pages=True)
    display(
        brain_files.reindex(
            columns=[
                "subject_id",
                "file_name",
                "object_role",
                "geometry_status",
                "geometry_assessment_method",
                "geometry_assessed_at_utc",
                "geometry_details_json",
            ]
        )
    )
    detailed = (
        brain_files["geometry_details_json"]
        .apply(lambda value: isinstance(value, dict) and bool(value))
        .sum()
    )
    print("Files with populated geometry details:", detailed, "of", len(brain_files))
    if not detailed:
        print(
            "This snapshot provides assessment status, but no dimensions, spacing, or affine values for these files."
        )
    brain_files.to_json(OUTPUT / "brain_example_files.json", orient="records", indent=2)
else:
    print("No indexed masks matched these filters in this snapshot.")''')

md(r'''To obtain these NIfTI files, choose the published package for the collection. The table below includes its download category, link, license, and size. For groups marked `python_supported`, pass their `download_id` to `tcia.download_dataset()`. For other groups, follow the official download link; this package does not install or invoke a separate application.

An indexed path inside an archive is not a standalone download URL. A Python-supported route retrieves the published files; it does not invent per-file links. Groups requiring a separate application stay outside this download demo. Extract the files and choose a documented matching image/mask pair before using the optional header check below.''')

code(r'''brain_downloads = pd.concat(
    [tcia.plan_downloads(title).to_dataframe() for title in BRAIN_COLLECTIONS],
    ignore_index=True,
)
display(
    brain_downloads.reindex(
        columns=[
            "short_title",
            "download_title",
            "download_category",
            "download_requirements",
            "python_supported",
            "subjects",
            "studies",
            "series",
            "images",
            "file_types",
            "license_label",
            "download_size",
            "download_size_unit",
            "download_url",
        ]
    ).convert_dtypes().astype(object).fillna("Not reported")
)
brain_downloads.to_csv(OUTPUT / "brain_dataset_downloads.csv", index=False)''')

md(r'''Once the files are on your computer, this optional check reads their NIfTI headers. Set the two paths to a **documented matching pair**. We'll compare grid shape, voxel sizes, orientation, and the affine matrix (which places the grid in physical space). A matching grid is a useful first check, not a replacement for visually checking the overlay or verifying label meanings from the dataset documentation.''')

code(r'''SOURCE_NIFTI = ""  # A downloaded source image, for example /path/to/image.nii.gz
MASK_NIFTI = ""  # Its documented matching mask.

if SOURCE_NIFTI and MASK_NIFTI:
    import nibabel as nib
    import numpy as np

    image, mask = nib.load(SOURCE_NIFTI), nib.load(MASK_NIFTI)
    display(
        pd.DataFrame(
            [
                {
                    "file": Path(path).name,
                    "shape": obj.shape,
                    "voxel_sizes": obj.header.get_zooms(),
                    "spatial_units": obj.header.get_xyzt_units()[0],
                    "orientation": nib.aff2axcodes(obj.affine),
                }
                for path, obj in [(SOURCE_NIFTI, image), (MASK_NIFTI, mask)]
            ]
        )
    )
    same_grid = (
        image.shape[:3] == mask.shape[:3]
        and image.header.get_xyzt_units()[0] != "unknown"
        and image.header.get_xyzt_units()[0] == mask.header.get_xyzt_units()[0]
        and np.allclose(image.affine, mask.affine, atol=1e-5)
    )
    print("Same spatial grid:", same_grid)
    print("Image affine:\n", image.affine)
    print("Mask affine:\n", mask.affine)
else:
    print(
        "Optional local-file check skipped. Fill in both paths after downloading a matching pair."
    )''', tags=['optional-local-files'])

md(r'''## 4. Which controlled CT images have segmentation labels?

We'll finish with [HEAD-NECK-RADIOMICS-HN1](https://www.cancerimagingarchive.net/collection/head-neck-radiomics-hn1/). Its Data Access section warns that the images could be used to reconstruct a human face. The imaging download is **controlled access**, as indicated by its license metadata. The collection also has public supporting files, so don't assume every row has the same access rule.

Review the [current access policy](https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/) before attempting a download. The policy identifies **phs004225** for this group of facial-image datasets. Public file metadata is available without approval; retrieving the images requires the appropriate authorization and your own JSON key.

The labels here include DICOM **SEG** (segmentation images) and **RTSTRUCT** (radiotherapy contours). We'll require **CT and SEG for the same participant and study**. Contours can also be useful labels, but they are not automatically voxel masks.''')

code(r'''FACE_COLLECTION = "HEAD-NECK-RADIOMICS-HN1"
face_downloads = tcia.plan_downloads(FACE_COLLECTION).to_dataframe()
display(
    face_downloads.reindex(
        columns=[
            "download_id",
            "download_title",
            "download_category",
            "download_requirements",
            "python_supported",
            "subjects",
            "studies",
            "series",
            "images",
            "access_level",
            "data_types",
            "license_label",
            "download_url",
        ]
    ).convert_dtypes().astype(object).fillna("Not reported")
)
face_result = tcia.list_controlled_files(FACE_COLLECTION, limit=500)
if face_result.data["count"] == face_result.data["limit"]:
    raise RuntimeError(
        "File inventory reached the API cap. Narrow the query before building a cohort."
    )
face_files = pd.DataFrame(face_result.data["files"])
face_files["participant_id"] = face_files["participant_id"].fillna("")
face_files["study_instance_uid"] = face_files["study_instance_uid"].fillna("")
usable = face_files[(face_files["participant_id"] != "") & (face_files["study_instance_uid"] != "")]
modalities_by_study = usable.groupby(["short_title", "participant_id", "study_instance_uid"])[
    "modality"
].agg(set)
matching_studies = modalities_by_study[
    modalities_by_study.apply(lambda values: {"CT", "SEG"}.issubset(values))
]
face_cohort = matching_studies.reset_index(name="available_modalities")
print("Public file metadata returned:", len(face_files), "(route cap: 500)")
print("Participant-study pairs with CT and SEG:", len(face_cohort))
display(face_cohort.head(10))
face_cohort.to_json(OUTPUT / "controlled_ct_seg_cohort.json", orient="records", indent=2)''')

md(r'''CT and SEG appearing in the same study is stronger evidence than a collection-level “has segmentations” label. It still does not verify the exact referenced CT series or the segment names inside a SEG object. After an authorized download, check those DICOM references and labels before using the pair for training.

Let's prepare a **one-participant example** with one candidate CT file and one candidate SEG file from the same study. We choose one of each modality before applying the two-file limit, so two CT files cannot crowd out the segmentation. The exact image/label references still need checking after download. We'll write the CT and SEG file identifiers already provided by the official metadata. The manifest will contain just one `drs_uri` column, which `download_manifest()` accepts. We'll save the fuller metadata separately so we can trace every selected file.''')

code(r'''face_selection = pd.DataFrame()
face_manifest = None
if len(face_cohort):
    selected_study = face_cohort.sort_values(["participant_id", "study_instance_uid"]).iloc[0]
    face_selection = usable[
        usable["participant_id"].eq(selected_study["participant_id"])
        & usable["study_instance_uid"].eq(selected_study["study_instance_uid"])
        & usable["modality"].isin(["CT", "SEG"])
    ].copy()
    if face_selection["drs_uri"].isna().any() or face_selection["drs_uri"].eq("").any():
        raise ValueError("A selected file has no download identifier; no partial manifest written.")
    # Keep one candidate CT file and one candidate SEG file from this study.
    face_selection = face_selection.sort_values(
        ["modality", "series_instance_uid", "drs_uri"]
    ).drop_duplicates("modality").copy()
    face_manifest = OUTPUT / "controlled_ct_and_seg.csv"
    face_selection[["drs_uri"]].drop_duplicates().to_csv(face_manifest, index=False)
    face_selection.to_json(
        OUTPUT / "controlled_ct_and_seg_evidence.json", orient="records", indent=2
    )
    display(
        face_selection[
            ["participant_id", "modality", "series_instance_uid", "file_size_bytes", "file_name"]
        ]
    )
    print("Manifest:", face_manifest.name)
    print("Selected files:", face_selection["drs_uri"].nunique())
    print(
        "Known download size (MB):",
        round(face_selection["file_size_bytes"].fillna(0).sum() / 1_000_000, 2),
    )
    print("Files without a size estimate:", face_selection["file_size_bytes"].isna().sum())
else:
    print("No participant-study pair satisfied CT + SEG in this snapshot.")''')

md(r'''An approved user can use `tcia.download_files()` to retrieve exactly the selected CT/SEG files. Here we keep both files with `max_items=2`, so the demo includes the selected scan and segmentation rather than cutting the pair in half. It does not add other scans or labels. Approval must cover **this** study as well.

Keep `DOWNLOAD_CONTROLLED_CT = False` unless you're ready to retrieve the subset with your own key. To obtain the full imaging dataset instead, use `download_dataset()` with its imaging download ID from the table above. The small manifest we created is only our selected subset.''')

code(r'''DOWNLOAD_CONTROLLED_CT = False
if DOWNLOAD_CONTROLLED_CT:
    if face_selection.empty:
        raise ValueError("No eligible CT/SEG subset was selected.")
    report = tcia.download_files(
        face_selection,
        OUTPUT / FACE_COLLECTION / "selected-ct-seg",
        credential_file=CREDENTIAL_FILE,
        max_items=2,
    )
    display(report.to_dataframe())
else:
    print("Controlled CT/SEG download is off. The selected manifest is ready for an approved user.")''', tags=['optional-download'])

md(r'''## Keep a record of what you used

We've gone from collection discovery to whole-dataset download planning, then built participant cohorts using modality, diagnosis, and segmentation availability. The saved tables include all search pages, while some displayed tables are deliberately short previews. The controlled-file and clinical-fact routes have explicit limits; they are not exhaustive archive-wide queries.

Before using a cohort in a study, review its source links, missing clinical values, inferred diagnoses, exact image/label relationships, and applicable licenses. Keep the dataset citations and split related scans at the person level when the dataset documents those relationships.

The next cell saves our query settings, metadata snapshot identity, original manifest URLs/checksums, and counts beside the exported tables. **It records metadata work, not proof that any image transfer completed.**''')

code(r'''run_record = {
    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    "tcia_utils_version": version("tcia_utils"),
    "metadata_snapshot": SNAPSHOT,
    "query": {
        "collections": COHORT_COLLECTIONS,
        "modality": COHORT_MODALITY,
        "diagnosis_text": DIAGNOSIS_TEXT,
        "include_inferred": INCLUDE_INFERRED_DIAGNOSES,
    },
    "dataset_download_groups": len(download_plan),
    "clinical_ct_series": len(ct_images.rows),
    "clinical_slide_files": len(slide_images.rows),
    "clinical_ct_index_version": ct_images.scope["imaging_index_version"],
    "saved_manifests": saved_manifests,
    "external_download_ids": external_groups["download_id"].tolist(),
    "candidate_records": len(candidates),
    "matching_records": len(cohort),
    "brain_collections": BRAIN_COLLECTIONS,
    "brain_segmentation_files": len(brain_cohort),
    "controlled_collection": FACE_COLLECTION,
    "controlled_selected_files": len(face_selection),
    "scope": "Dataset-scoped records; no cross-dataset person deduplication.",
    "clinical_caveat": "Derived clinical curation; original dataset descriptions and source clinical files remain authoritative.",
    "payload_completion_verified": False,
    "source_pages": [
        collection["tcia_page"],
        "https://www.cancerimagingarchive.net/collection/ucsf-pdgm/",
        "https://www.cancerimagingarchive.net/collection/upenn-gbm/",
        "https://www.cancerimagingarchive.net/collection/head-neck-radiomics-hn1/",
        "https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/",
    ],
}
(OUTPUT / "workshop_run.json").write_text(json.dumps(run_record, indent=2))
tcia.close()
print("Saved tables, manifests, and workshop_run.json in the notebook's output folder.")''')

md(r'''### Try your own question

Change `COHORT_COLLECTIONS`, `COHORT_MODALITY`, and `DIAGNOSIS_TEXT`, then rerun section 2 onward. Start with a small set of collections so you can inspect their clinical labels and coverage before widening the search.

For another challenge, change `BRAIN_COLLECTIONS` and compare how many participants have segmentation files with checked versus unchecked geometry. Keep both categories visible until you've decided what your project actually requires.

Useful links: [TCIA Dataset Explorer](https://www.cancerimagingarchive.net/dataset-explorer/), [CMB-GEC](https://www.cancerimagingarchive.net/collection/cmb-gec/), [UCSF-PDGM](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/), [UPENN-GBM](https://www.cancerimagingarchive.net/collection/upenn-gbm/), [HEAD-NECK-RADIOMICS-HN1](https://www.cancerimagingarchive.net/collection/head-neck-radiomics-hn1/), [controlled-access instructions](https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/).''')

notebook = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name":"Python 3", "language":"python", "name":"python3"},
    "language_info": {"name":"python", "version":"3.11"},
    "tcia_workshop": {"package_version":"4.0.0a4.dev0", "default_mode":"live_public_metadata",
        "payload_downloads_default":False, "audience":"junior data scientists"}})
for i, cell in enumerate(notebook.cells): cell.id = f"tcia-workshop-{i:02d}"
OUT.mkdir(exist_ok=True)
nbf.validate(notebook)
nbf.write(notebook, OUT / "TCIA_Dataset_and_Participant_Queries.ipynb")
print(f"Wrote one notebook with {len(cells)} cells.")
