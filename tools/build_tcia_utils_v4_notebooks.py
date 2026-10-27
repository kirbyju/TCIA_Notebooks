"""Build the single, standalone v4 workshop notebook (no learner-side helpers)."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tcia_utils_v4'
cells = []
def md(source): cells.append(nbf.v4.new_markdown_cell(source.strip()))
def code(source, **metadata): cells.append(nbf.v4.new_code_cell(source.strip(), metadata=metadata))

md('''[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb)

# Finding datasets and building participant cohorts with TCIA

In this hands-on lab we'll start with a dataset, then work our way down to individual participants. Along the way we'll find images, clinical information, and segmentation labels. You only need a little Python and some familiarity with pandas tables.

We'll work through four questions:

1. **Which datasets have the data I need, and how do I download a whole dataset?**
2. **Can I find participants with a particular image modality and diagnosis across datasets?**
3. **Where can I find public brain MR images with segmentation masks?**
4. **How do I prepare a controlled-access CT cohort with segmentations?**

Our main example is [CMB-GEC](https://www.cancerimagingarchive.net/collection/cmb-gec/), which includes radiology images, tissue-slide images, and links to clinical information. Later we'll look at brain MR and head-and-neck CT.

**Preview release:** this notebook explicitly opts into the new `tcia_utils` **4.0.0a1** API and requires Python **3.11 or newer**. The ordinary 3.x installation has a different API. Run the installation cell below in a fresh Colab or Jupyter session to try this alpha. This `.ipynb` is self-contained: it does not need other files from this repository.

Running all cells queries real, public metadata and saves small manifests and tables. Image downloads stay off until you choose to run them. You do not need an LLM account or a controlled-data account to explore the metadata.''')
md('''## Let's get set up

A **preview release** lets us try the new API before making it the normal version that everyone installs. The `a1` in `4.0.0a1` means this is the first alpha preview.

| What you install | Which version you get |
| --- | --- |
| `pip install tcia_utils` (ordinary pip settings) | The stable release; publishing this alpha does not switch ordinary installs to v4. |
| `pip install "tcia_utils[tables]==4.0.0a1"` | This specific preview, once it is published. |

The preview is public on PyPI once released; anyone who opts into prereleases can try it. Pinning the exact version makes our test reproducible. Pip also lets users opt into previews with `--pre`; we don't need that flag when we request this exact alpha version. See [pip's prerelease guidance](https://pip.pypa.io/en/stable/cli/pip_install/#pre-release-versions).

**Testing in Colab:** click **Open In Colab** above and run the notebook from the top. The next cell installs this exact alpha in your Colab session. Restart the Python session if prompted after installation. The searches use real public metadata; large image downloads remain your choice.

**Testing in Jupyter:** open this notebook in a fresh Python 3.11+ environment and run the same installation cell. If you already installed this exact preview and its dependencies there, you can set `INSTALL_FROM_PYPI = False` to skip reinstallation.

`pandas` helps us work with tables. `nibabel` is used only by the optional NIfTI check near the end. If something goes wrong, report the failing cell and error message at the [tcia_utils issue tracker](https://github.com/kirbyju/tcia_utils/issues), along with your Python and package versions. Keep credentials out of reports.''')
code('''INSTALL_FROM_PYPI = True  # This notebook opts into the exact alpha release.
if INSTALL_FROM_PYPI:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "tcia_utils[tables]==4.0.0a1", "nibabel>=5,<6"])''', tags=['installation'])
code('''from pathlib import Path
from importlib.metadata import version
from datetime import datetime, timezone
from urllib.parse import urlsplit
import hashlib
import json
import os
import shlex
import subprocess

import httpx
import pandas as pd
from IPython.display import display, Markdown
from tcia_utils import TCIAClient

assert version("tcia_utils").startswith("4."), "Please install the v4 preview first."
pd.set_option("display.max_colwidth", 85)
OUTPUT = Path(os.environ.get("TCIA_EXAMPLE_OUTPUT_DIR", "tcia-workshop-output"))
OUTPUT.mkdir(parents=True, exist_ok=True)
tcia = TCIAClient(base_url="https://tcia.duckdns.org", timeout=120)
status = tcia.status()
SNAPSHOT = status.provenance.release_fingerprint
print("tcia_utils:", version("tcia_utils"))
print("Metadata observed:", datetime.now(timezone.utc).date())
print("Service ready:", status.data.readiness["status"])''')
md('''TCIA's search service uses a prepared metadata snapshot. That gives us a convenient place to ask questions without downloading images first. The snapshot can lag behind a dataset's web page, so we'll keep the original links with our results.

One small helper will collect **every page** of a search. A page size of 100 or 500 controls how many rows arrive at a time; it does not limit our cohort to that many participants. We'll also stop if the metadata snapshot changes halfway through our work, so we don't mix two versions.''')
code('''def checked(result):
    if result.provenance.release_fingerprint != SNAPSHOT:
        raise RuntimeError("Metadata changed. Restart and run the notebook again.")
    return result


def all_rows(page):
    records = []
    for part in page.iter_pages():
        checked(part)
        records.extend(part.items)
    return pd.DataFrame(records)''')
md('''## 1. Which dataset should I download?

A **Collection** is a published dataset. An **Analysis Result** is another published contribution, often containing annotations or measurements made from existing images. Keep the dataset name and type together so we know exactly which contribution we're using.

There are also two independent choices to understand:

| Choice | What it means for us |
| --- | --- |
| Public or controlled access | Public files can be retrieved under their license. Controlled files require approval before download, even when their descriptions are public. |
| DICOM or non-DICOM | DICOM is a medical imaging format. Other useful formats include NIfTI image volumes, SVS tissue slides, spreadsheets, and archives. Non-DICOM does not mean non-image. |

A single collection can contain several combinations. **Public** also does not mean unrestricted use: read each download's license, including any noncommercial condition.

Start in the [TCIA Dataset Explorer](https://www.cancerimagingarchive.net/dataset-explorer/). Try a cancer-location filter and a modality filter, then open a matching collection's page. For this lesson, choose **CMB-GEC**, open its **Data Access** tab, and note the separate download/manifest links and licenses. The Explorer helps us find the dataset; its page describes the individual download groups.

In Python, we can explore the same kinds of collection attributes. Let's try a cancer location and image modality. Change these values and rerun the cell to explore.''')
code('''CANCER_LOCATION = "Esophagus"
IMAGE_MODALITY = "CT"

datasets = all_rows(tcia.search_datasets(
    dataset_type="collection", cancer_locations=[CANCER_LOCATION],
    modalities=[IMAGE_MODALITY], limit=100))
print("Matching collections:", len(datasets))
display(datasets.reindex(columns=["short_title", "title", "cancer_types",
    "cancer_locations", "resolved_access_level", "download_file_types", "tcia_page"]))''')
md('''These are **collection-level** labels. Finding a collection with CT and a cancer label does not tell us that every participant has both. We'll check participant-level information in section 2.

Now let's open CMB-GEC. The download table is especially useful: it tells us which files are public, which need approval, and which formats we'll receive.''')
code('''DATASET = "CMB-GEC"
detail = checked(tcia.get_dataset(DATASET))
collection = next(row for row in detail.data["datasets"] if row["dataset_type"] == "Collection")
display(Markdown(f"### [{collection['short_title']}]({collection['tcia_page']})\\n\\n{collection['title']}"))
print("Dataset version:", collection["current_version_number"])
print("Public external clinical resource linked:", collection["has_external_clinical_resource"])

# Use the paginated download listing so we collect all current download groups.
downloads = all_rows(tcia.list_downloads(DATASET, limit=100))
display(downloads.reindex(columns=["download_id", "download_title", "access_level",
    "data_types", "file_types", "license_label", "download_size", "download_size_unit", "download_url"]))
downloads.to_csv(OUTPUT / "CMB-GEC_download_inventory.csv", index=False)''')
md('''CMB-GEC is a good reminder that **a dataset is not always one download**. We need its public DICOM images, public tissue-slide images and metadata, and controlled images of the head to obtain all the imaging groups listed here. The linked clinical resources are separate from these imaging downloads; the collection page explains what they contain.

A **manifest** is a shopping list for a downloader. Downloading the manifest does not download the images, and a controlled manifest does not grant permission to retrieve them.

Let's separate download groups that the TCIA Data Retriever can accept from groups that currently need the collection's download link. We'll account for both rather than silently skip one.''')
code('''download_plan = downloads.copy()
download_plan["method"] = download_plan["requirements_label"].fillna("").apply(
    lambda label: "TCIA Data Retriever" if label == "TCIA Data Retriever" else "Collection download link")
display(download_plan[["download_id", "download_title", "access_level", "method", "download_url"]])

retriever_groups = download_plan[download_plan["method"] == "TCIA Data Retriever"]
other_groups = download_plan[download_plan["method"] != "TCIA Data Retriever"]
print("All current imaging download groups:", len(download_plan))
print("Groups prepared for the CLI:", len(retriever_groups))
print("Groups requiring the collection download link:", len(other_groups))''')
md('''### Save the manifests, then choose whether to download

The next cell saves only the small official manifest files. It keeps their original contents and records a checksum so we can identify exactly which shopping lists we used. We never turn a download-package link into an image URL by guessing.

**Controlled access:** the classification in the table comes from the download's license metadata. Public descriptions and manifests are not authorization. Read the [current TCIA access policy](https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/), request the required dbGaP authorization, and create your own JSON API key using the linked instructions. For CMB-GEC's controlled images the policy identifies **phs002192**. You can still save and inspect the public manifest without that key.''')
code('''def save_official_manifest(row):
    url = row["download_url"]
    parsed = urlsplit(url)
    suffix = Path(parsed.path).suffix.lower()
    if parsed.scheme != "https" or parsed.hostname != "www.cancerimagingarchive.net" or suffix not in {".tcia", ".csv"}:
        raise ValueError("This helper only saves official TCIA .tcia or .csv manifests.")
    # The size cap catches an accidental payload URL before we save a large file.
    with httpx.Client(follow_redirects=True, timeout=120) as http:
        with http.stream("GET", url) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 10_000_000:
                    raise ValueError("Larger than expected for a manifest; please review the link.")
                chunks.append(chunk)
    content = b"".join(chunks)
    # A successful web response is not enough: check that it really is a manifest.
    text = content.decode("utf-8-sig")
    if suffix == ".tcia":
        marker = "ListOfSeriesToDownload="
        if marker not in text or not text.split(marker, 1)[1].strip():
            raise ValueError("Expected a nonempty series manifest.")
    else:
        import csv, io
        rows = list(csv.DictReader(io.StringIO(text)))
        if not rows or any(not row.get("drs_uri", "").startswith("drs://") for row in rows):
            raise ValueError("Expected a nonempty controlled-file manifest with drs_uri values.")
    path = OUTPUT / f"{row['short_title']}_{row['download_id']}{suffix}"
    path.write_bytes(content)
    return {"download_id": row["download_id"], "manifest": path.name,
            "url": url, "sha256": hashlib.sha256(content).hexdigest()}

saved_manifests = [save_official_manifest(row) for row in retriever_groups.to_dict("records")]
display(pd.DataFrame(saved_manifests))''')
md('''Install the current [TCIA Data Retriever](https://github.com/TCIA/data-retriever/releases) for your operating system. You can use its desktop interface or CLI; the commands below use the CLI. Set `RETRIEVER` to the executable's location on the computer running this notebook. The [Linux installation notebook](https://github.com/kirbyju/TCIA_Notebooks/blob/main/TCIA_Linux_Data_Retriever_App.ipynb) includes a hosted-notebook example.

The command's `--input` is the manifest, `--output` is your destination, and `--skip-existing` helps resume an interrupted download. We use a list of arguments so spaces in file paths work too.

The next cell **prints the public-image command**. Change `DOWNLOAD_PUBLIC_DICOM` only when you're ready to transfer the full public DICOM group and have checked the size above.''')
code('''RETRIEVER = "TCIA_Data_Retriever"  # Or the full path to your executable.
DOWNLOAD_PUBLIC_DICOM = False

public_groups = retriever_groups[~retriever_groups["controlled_access"]]
public_commands = []
for row in public_groups.to_dict("records"):
    item = next(item for item in saved_manifests if item["download_id"] == row["download_id"])
    command = [RETRIEVER, "--cli", "--input", str(OUTPUT / item["manifest"]),
               "--output", str(OUTPUT / DATASET / "public-dicom"), "--skip-existing"]
    public_commands.append(command)
    print(shlex.join(command))
    if DOWNLOAD_PUBLIC_DICOM:
        subprocess.run(command, check=True)
print("Public DICOM transfer requested:", DOWNLOAD_PUBLIC_DICOM)''', tags=['optional-download'])
md('''What about the public tissue-slide files? Open their **collection download link** below and follow the download instructions there. This is a real limitation of the current all-in-one workflow: the CLI cannot retrieve that package yet. Running the DICOM commands alone does **not** download the complete collection. Keep this row in your checklist, including the accompanying pathology metadata; a slide preview is not a replacement for the original slide file.''')
code('''for row in other_groups.to_dict("records"):
    display(Markdown(f"- [{row['download_title']}]({row['download_url']}) — {row['download_size']} {row['download_size_unit']}, {row['access_level']}"))''')
md('''After approval, the controlled-image command adds `--auth` with the **path** to your JSON key. Don't paste the key into a notebook, source repository, or chat. The key stays on your computer. Authorization for one study may not cover another.

Leave this cell unchanged to continue the lesson without a controlled download. To transfer the full controlled CMB-GEC group, enter your own key-file path and set `DOWNLOAD_CONTROLLED_CMB` to `True`. The downloader will still enforce the study's access requirements.''')
code('''CREDENTIAL_FILE = ""  # Your own approved JSON key file; never the key value.
DOWNLOAD_CONTROLLED_CMB = False


def run_controlled(manifest, destination):
    if not CREDENTIAL_FILE:
        raise ValueError("Set CREDENTIAL_FILE to your own approved JSON key file.")
    key_path = Path(CREDENTIAL_FILE)
    key = json.loads(key_path.read_text())
    if not isinstance(key, dict) or not isinstance(key.get("api_key"), str) or not key["api_key"].strip():
        raise ValueError("The credential file must contain a nonempty api_key.")
    if os.name == "posix" and key_path.stat().st_mode & 0o077:
        print("Your key file is readable by other users. Consider restricting it with chmod 600.")
    subprocess.run([RETRIEVER, "--cli", "--input", str(manifest),
                    "--output", str(destination), "--auth", CREDENTIAL_FILE,
                    "--skip-existing"], check=True)

if DOWNLOAD_CONTROLLED_CMB:
    for row in retriever_groups[retriever_groups["controlled_access"]].to_dict("records"):
        item = next(item for item in saved_manifests if item["download_id"] == row["download_id"])
        run_controlled(OUTPUT / item["manifest"], OUTPUT / DATASET / "controlled-dicom")
else:
    print("Controlled CMB-GEC download is off. The manifests are ready for an approved user.")''', tags=['optional-download'])
md('''Before calling a dataset download complete, compare your downloaded files and the Data Retriever's completion report with **every row** in the inventory. Resolve failed or skipped files, finish the tissue-slide package, and follow the collection's external-resource links if your project needs those data too. A manifest on disk or a successful metadata query is not evidence that images were transferred.

Let's save the dataset citation as well. Keep the citation and license information with your project, and follow the collection page's acknowledgement instructions.''')
code('''citation = checked(tcia.get_citation(collection["doi"], style="apa"))
print(citation.data["record"]["formatted_citation"])
(OUTPUT / "CMB-GEC_citation.json").write_text(json.dumps(citation.data, indent=2))''')
md('''## 2. Which participants have the modality and diagnosis I need?

Suppose we want CT images from participants whose available diagnosis includes “Carcinoma.” We'll search **CMB-GEC and CMB-LCA together**. Change the collection list, modality, and diagnosis text to try your own question. Removing the collection restriction would search much more broadly and take longer.

This is a participant query, not a search of collection descriptions. We'll first find participants with the selected modality, then match their available clinical information. Our diagnosis match is a simple, case-insensitive text search; it does not know that two different medical terms can mean the same thing.''')
code('''COHORT_COLLECTIONS = ["CMB-GEC", "CMB-LCA"]
COHORT_MODALITY = "CT"
DIAGNOSIS_TEXT = "Carcinoma"
INCLUDE_INFERRED_DIAGNOSES = True

candidates = all_rows(tcia.search_participants(
    short_titles=COHORT_COLLECTIONS, dataset_type="collection",
    modalities=[COHORT_MODALITY], limit=500))
if candidates.empty:
    candidates = pd.DataFrame(columns=["short_title", "display_participant_id", "participant_key", "modalities"])
    print("No participants matched. Try another collection or modality.")
print("Candidate participant records:", len(candidates))
display(candidates.reindex(columns=["short_title", "display_participant_id", "modalities",
    "file_formats", "has_open_data", "has_controlled_data"]).head(10))''')
md('''Clinical information can come from a collection's own files or public clinical enrichment from other resources. The API keeps the source and whether a value was **recorded for the participant** or **inferred from the dataset**. For example, a collection-level cancer label is useful for discovery, but it is not a confirmed diagnosis for each person.

We'll ask for the clinical records in small batches and join exact participant IDs **within each collection**. We won't guess an ID conversion or assume that an ID in two collections means the same person. Unmatched IDs stay visible rather than disappearing from our accounting.''')
code('''def clinical_for(participants):
    records = []
    for title, group in participants.groupby("short_title"):
        ids = group["display_participant_id"].drop_duplicates().tolist()
        for start in range(0, len(ids), 100):
            response = checked(tcia.list_clinical_subjects(
                title, subject_ids=ids[start:start + 100], limit=500))
            if response.data["count"] == response.data["limit"]:
                raise RuntimeError("Clinical response reached its cap; narrow the batch before continuing.")
            records.extend(response.data["subjects"])
    fields = ["short_title", "subject_id", "primary_diagnosis", "primary_diagnosis_is_inferred",
              "primary_site", "primary_site_is_inferred", "resolved_values", "resolved_sources", "conflicts"]
    table = pd.DataFrame(records, columns=fields)
    if table.duplicated(["short_title", "subject_id"]).any():
        raise ValueError("Ambiguous clinical identity; review the source records before joining.")
    return table

clinical = clinical_for(candidates)
with_clinical = candidates.merge(clinical, how="left",
    left_on=["short_title", "display_participant_id"], right_on=["short_title", "subject_id"],
    validate="many_to_one", indicator="clinical_link")
print("Clinical linkage (no fuzzy ID matching):")
display(with_clinical["clinical_link"].value_counts())
print("Available diagnosis labels:")
display(with_clinical["primary_diagnosis"].value_counts(dropna=False).to_frame("participants"))''')
md('''Let's apply the diagnosis filter and see how many participant records remain. Set `INCLUDE_INFERRED_DIAGNOSES = False` above if you want recorded diagnoses only. The flag travels with the results either way.

We are counting **dataset-scoped participant records**. We have not deduplicated people across collections, and a missing clinical value does not mean a participant has no diagnosis. This cohort is limited to the selected collections and the information currently indexed.''')
code('''matches = with_clinical["primary_diagnosis"].astype("string").fillna("").str.contains(
    DIAGNOSIS_TEXT, case=False, regex=False)
if not INCLUDE_INFERRED_DIAGNOSES:
    matches &= with_clinical["primary_diagnosis_is_inferred"].eq(False)
cohort = with_clinical.loc[matches].copy()
print("Matching participant records:", len(cohort))
display(cohort.reindex(columns=["short_title", "display_participant_id", "modalities",
    "primary_diagnosis", "primary_diagnosis_is_inferred", "primary_site",
    "primary_site_is_inferred", "has_open_data", "has_controlled_data"]))
cohort.to_json(OUTPUT / "modality_diagnosis_cohort.json", orient="records", indent=2)
cohort.drop(columns=["resolved_values", "resolved_sources", "conflicts"]).to_csv(
    OUTPUT / "modality_diagnosis_cohort.csv", index=False)''')
md('''### What else do we know about these participants?

The short table above is only a starting point. Let's put **all resolved clinical concepts** for the matched participants into a second table. That can include demographics, outcomes, treatment-related values, or molecular findings when those were indexed. We keep the source evidence beside each value rather than assuming all collections report the same things.

These clinical summaries are a **derived curation layer**. They do not replace the [original dataset descriptions and clinical files](https://www.cancerimagingarchive.net/collections/). CMB-GEC links additional clinical resources on its page; the API includes the public facts it has indexed, not every field available at those links or any restricted clinical file. Blank means “not available here,” not “does not exist.”''')
code('''clinical_values = []
for participant in cohort.to_dict("records"):
    values = participant.get("resolved_values")
    sources = participant.get("resolved_sources")
    if not isinstance(values, dict):
        continue
    for concept, value in values.items():
        source = (sources or {}).get(concept, {})
        clinical_values.append({"short_title": participant["short_title"],
            "participant_id": participant["display_participant_id"], "concept": concept,
            "value": value, "is_inferred": source.get("is_inferred"),
            "evidence_scope": source.get("evidence_scope"), "source_evidence": source})
clinical_summary = pd.DataFrame(clinical_values)
display(clinical_summary.drop(columns="source_evidence", errors="ignore").head(25))
clinical_summary.to_json(OUTPUT / "cohort_clinical_evidence.json", orient="records", indent=2)
print("The displayed rows are a preview; the JSON export contains every resolved value collected above.")''')
md('''For a closer look, choose one matching participant. The first cell lists their known data types, access levels, formats, and geometry summaries. The next keeps the original clinical facts, source links, and disagreements for that participant. We use CMB-GEC first when it is present in the cohort.''')
code('''ordered = cohort.assign(example_first=cohort["short_title"].ne("CMB-GEC")).sort_values(
    ["example_first", "short_title", "display_participant_id"])
example = ordered.iloc[0].to_dict() if len(ordered) else None
participant_assets = pd.DataFrame()
if example:
    print(example["short_title"], example["display_participant_id"])
    participant = checked(tcia.get_participant(example["participant_key"]))
    participant_assets = all_rows(tcia.list_participant_assets(example["participant_key"], limit=500))
    display(participant_assets.reindex(columns=["data_category", "data_type", "modality", "access_level",
        "file_format", "file_count", "geometry_status"]))
    (OUTPUT / "example_participant.json").write_text(json.dumps(participant.data, indent=2))
    participant_assets.to_json(OUTPUT / "example_participant_assets.json", orient="records", indent=2)
else:
    print("No matches. Try a diagnosis label from the table above.")''')
code('''example_facts = []
if example:
    facts = checked(tcia.list_clinical_facts(example["short_title"],
        subject_id=example["subject_id"], limit=500))
    conflicts = checked(tcia.list_clinical_conflicts(example["short_title"],
        subject_id=example["subject_id"], limit=500))
    example_facts = facts.data["facts"]
    display(pd.DataFrame(example_facts).reindex(columns=["concept", "value_text", "value_resolved",
        "is_inferred", "evidence_scope", "source_url", "source_date", "qc_status"]))
    print("Clinical conflict rows:", conflicts.data["count"])
    if conflicts.data["count"]:
        display(pd.DataFrame(conflicts.data["conflicts"]))
    print("Facts returned:", facts.data["count"], "(bounded at 500; this is not an all-facts pagination route)")
    (OUTPUT / "example_clinical_facts.json").write_text(json.dumps(facts.data, indent=2))
    (OUTPUT / "example_clinical_conflicts.json").write_text(json.dumps(conflicts.data, indent=2))''')
md('''## 3. Where are the public brain MR images with segmentation masks?

A **segmentation** labels parts of an image, such as a tumor. The label image is useful for training or evaluating a model, but we also need the source image and an understanding of how the two line up.

We'll search [UCSF-PDGM](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/) and [UPENN-GBM](https://www.cancerimagingarchive.net/collection/upenn-gbm/). These provide public brain MR data in **NIfTI**, a common volume format with filenames ending in `.nii` or `.nii.gz`.

First find participants with public NIfTI MR data. Then look for indexed segmentation files and join them within each collection. We deliberately keep participants with unchecked geometry so “not checked” is not confused with “bad image.”''')
code('''BRAIN_COLLECTIONS = ["UCSF-PDGM", "UPENN-GBM"]
brain_candidates = all_rows(tcia.search_participants(
    short_titles=BRAIN_COLLECTIONS, dataset_type="collection", modalities=["MR"],
    access_levels=["open"], file_formats=["NIFTI"], limit=500))
brain_masks = all_rows(tcia.search_public_assets(
    short_titles=BRAIN_COLLECTIONS, modalities=["MR"], file_formats=["NIFTI"],
    object_roles=["segmentation"], requires_annotations=True, limit=500))
if brain_candidates.empty:
    brain_candidates = pd.DataFrame(columns=["short_title", "display_participant_id", "participant_key"])
if brain_masks.empty:
    brain_masks = pd.DataFrame(columns=["short_title", "subject_id", "asset_id", "file_name", "geometry_status"])
linked_masks = brain_masks.drop(columns=["participant_key", "display_participant_id"], errors="ignore").merge(
    brain_candidates[["short_title", "display_participant_id", "participant_key"]],
    left_on=["short_title", "subject_id"], right_on=["short_title", "display_participant_id"],
    how="left", validate="many_to_one", indicator="participant_link")
brain_cohort = linked_masks[linked_masks["participant_link"] == "both"].copy()
print("Public MR participant records:", len(brain_candidates))
print("Indexed segmentation files:", len(brain_masks))
print("Segmentation files without an exact inventory ID match:", linked_masks["participant_link"].eq("left_only").sum())
display(brain_cohort.groupby("short_title").agg(
    participant_records=("participant_key", "nunique"), segmentation_files=("asset_id", "nunique")))
display(brain_cohort[["short_title", "subject_id", "file_name", "geometry_status"]].head(10))
brain_cohort.to_json(OUTPUT / "brain_mr_segmentation_inventory.json", orient="records", indent=2)''')
md('''This tells us that a participant has both public MR data and segmentation files. Some masks label brain tissue and others label tumor regions; check the file descriptions for the labels you need. This table does **not** establish which individual MR volume each mask annotates. Use the dataset's file descriptions and naming documentation to select the corresponding source image.

Also, participant IDs do not always equal unique people. The UCSF-PDGM description explains that some original IDs were later recognized as follow-up scans of the same person. Use the collection's documented relationships when splitting training and test data; don't split related scans between them just because their filenames differ.

### What does the geometry information tell us?

Geometry describes the image grid: dimensions, voxel spacing, and orientation. `checked_grid_geometry` means a grid assessment was recorded. It does not prove that a mask matches a source image or that either is suitable for your model. `not_checked` means we don't have an assessment here.

Let's inspect one participant's source-image and segmentation records, including any detailed geometry information the service exposes.''')
code('''brain_files = pd.DataFrame()
if len(brain_cohort):
    brain_example = brain_cohort.sort_values(["short_title", "subject_id", "file_name"]).iloc[0]
    brain_files = all_rows(tcia.search_public_assets(
        short_titles=[brain_example["short_title"]], participant_id=brain_example["subject_id"],
        file_formats=["NIFTI"], limit=500))
    display(brain_files.reindex(columns=["subject_id", "file_name", "object_role", "geometry_status",
        "geometry_assessment_method", "geometry_assessed_at_utc", "geometry_details_json"]))
    detailed = brain_files["geometry_details_json"].apply(lambda value: isinstance(value, dict) and bool(value)).sum()
    print("Files with populated geometry details:", detailed, "of", len(brain_files))
    if not detailed:
        print("This snapshot provides assessment status, but no dimensions, spacing, or affine values for these files.")
    brain_files.to_json(OUTPUT / "brain_example_files.json", orient="records", indent=2)
else:
    print("No indexed masks matched these filters in this snapshot.")''')
md('''To obtain the files, use the current download group on the collection page. The table below includes its official link and license. Some downloads contain a whole archive; an indexed file path inside that archive is not a standalone download URL. The API currently exposes the file inventory, not a per-file download route for these NIfTI files.

Download the published package if you need it, extract it, and choose the matching image and mask described by the dataset. This lesson does not silently download a large archive just to inspect a header.''')
code('''brain_downloads = pd.concat([
    all_rows(tcia.list_downloads(title, limit=100)) for title in BRAIN_COLLECTIONS
], ignore_index=True)
display(brain_downloads.reindex(columns=["short_title", "download_title", "file_types", "license_label",
    "download_size", "download_size_unit", "download_url"]))
brain_downloads.to_csv(OUTPUT / "brain_dataset_downloads.csv", index=False)''')
md('''Once the files are on your computer, this optional check reads their NIfTI headers. Set the two paths to a **documented matching pair**. We'll compare grid shape, voxel sizes, orientation, and the affine matrix (which places the grid in physical space). A matching grid is a useful first check, not a replacement for visually checking the overlay or verifying label meanings from the dataset documentation.''')
code('''SOURCE_NIFTI = ""  # A downloaded source image, for example /path/to/image.nii.gz
MASK_NIFTI = ""    # Its documented matching mask.

if SOURCE_NIFTI and MASK_NIFTI:
    import nibabel as nib
    import numpy as np
    image, mask = nib.load(SOURCE_NIFTI), nib.load(MASK_NIFTI)
    display(pd.DataFrame([
        {"file": Path(path).name, "shape": obj.shape, "voxel_sizes": obj.header.get_zooms(),
         "spatial_units": obj.header.get_xyzt_units()[0], "orientation": nib.aff2axcodes(obj.affine)}
        for path, obj in [(SOURCE_NIFTI, image), (MASK_NIFTI, mask)]]))
    same_grid = (image.shape[:3] == mask.shape[:3]
                 and image.header.get_xyzt_units()[0] != "unknown"
                 and image.header.get_xyzt_units()[0] == mask.header.get_xyzt_units()[0]
                 and np.allclose(image.affine, mask.affine, atol=1e-5))
    print("Same spatial grid:", same_grid)
    print("Image affine:\\n", image.affine)
    print("Mask affine:\\n", mask.affine)
else:
    print("Optional local-file check skipped. Fill in both paths after downloading a matching pair.")''', tags=['optional-local-files'])
md('''## 4. Which controlled CT images have segmentation labels?

We'll finish with [HEAD-NECK-RADIOMICS-HN1](https://www.cancerimagingarchive.net/collection/head-neck-radiomics-hn1/). Its Data Access section warns that the images could be used to reconstruct a human face. The imaging download is **controlled access**, as indicated by its license metadata. The collection also has public supporting files, so don't assume every row has the same access rule.

Review the [current access policy](https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/) before attempting a download. The policy identifies **phs004225** for this group of facial-image datasets. Public file metadata is available without approval; retrieving the images requires the appropriate authorization and your own JSON key.

The labels here include DICOM **SEG** (segmentation images) and **RTSTRUCT** (radiotherapy contours). We'll require **CT and SEG for the same participant and study**. Contours can also be useful labels, but they are not automatically voxel masks.''')
code('''FACE_COLLECTION = "HEAD-NECK-RADIOMICS-HN1"
face_downloads = all_rows(tcia.list_downloads(FACE_COLLECTION, limit=100))
display(face_downloads.reindex(columns=["download_id", "download_title", "access_level",
    "data_types", "license_label", "download_url"]))

# This route is bounded, not paginated. Stop at its cap rather than claim a complete cohort.
face_result = checked(tcia.list_controlled_files(FACE_COLLECTION, limit=500))
if face_result.data["count"] == face_result.data["limit"]:
    raise RuntimeError("File inventory reached the API cap. Narrow the query before building a cohort.")
face_files = pd.DataFrame(face_result.data["files"])
face_files["participant_id"] = face_files["participant_id"].fillna("")
face_files["study_instance_uid"] = face_files["study_instance_uid"].fillna("")
usable = face_files[(face_files["participant_id"] != "") & (face_files["study_instance_uid"] != "")]
modalities_by_study = usable.groupby(["short_title", "participant_id", "study_instance_uid"])["modality"].agg(set)
matching_studies = modalities_by_study[modalities_by_study.apply(lambda values: {"CT", "SEG"}.issubset(values))]
face_cohort = matching_studies.reset_index(name="available_modalities")
print("Public file metadata returned:", len(face_files), "(route cap: 500)")
print("Participant-study pairs with CT and SEG:", len(face_cohort))
display(face_cohort.head(10))
face_cohort.to_json(OUTPUT / "controlled_ct_seg_cohort.json", orient="records", indent=2)''')
md('''CT and SEG appearing in the same study is stronger evidence than a collection-level “has segmentations” label. It still does not verify the exact referenced CT series or the segment names inside a SEG object. After an authorized download, check those DICOM references and labels before using the pair for training.

Let's prepare a **one-participant example**, rather than download the entire controlled collection. We'll write the CT and SEG file identifiers already provided by the official metadata. The manifest will contain just one `drs_uri` column, which the Data Retriever accepts. We'll save the fuller metadata separately so we can trace every selected file.''')
code('''face_selection = pd.DataFrame()
face_manifest = None
if len(face_cohort):
    selected_study = face_cohort.sort_values(["participant_id", "study_instance_uid"]).iloc[0]
    face_selection = usable[
        usable["participant_id"].eq(selected_study["participant_id"])
        & usable["study_instance_uid"].eq(selected_study["study_instance_uid"])
        & usable["modality"].isin(["CT", "SEG"])].copy()
    if face_selection["drs_uri"].isna().any() or face_selection["drs_uri"].eq("").any():
        raise ValueError("A selected file has no download identifier; no partial manifest written.")
    face_manifest = OUTPUT / "controlled_ct_and_seg.csv"
    face_selection[["drs_uri"]].drop_duplicates().to_csv(face_manifest, index=False)
    face_selection.to_json(OUTPUT / "controlled_ct_and_seg_evidence.json", orient="records", indent=2)
    display(face_selection[["participant_id", "modality", "series_instance_uid", "file_size_bytes", "file_name"]])
    print("Manifest:", face_manifest.name)
    print("Selected files:", face_selection["drs_uri"].nunique())
    print("Known download size (MB):", round(face_selection["file_size_bytes"].fillna(0).sum() / 1_000_000, 2))
    print("Files without a size estimate:", face_selection["file_size_bytes"].isna().sum())
else:
    print("No participant-study pair satisfied CT + SEG in this snapshot.")''')
md('''An approved user can run the command below with their own key. It uses the same `run_controlled` helper as the CMB-GEC example, but approval must cover **this** study too. Keep `DOWNLOAD_CONTROLLED_CT` off unless you are ready to retrieve this selected subset. To download the full imaging dataset instead, use its official manifest URL in the download table above; the small manifest we just created is only our selected CT/SEG subset.''')
code('''DOWNLOAD_CONTROLLED_CT = False
if DOWNLOAD_CONTROLLED_CT:
    if face_manifest is None:
        raise ValueError("No eligible CT/SEG subset was selected.")
    run_controlled(face_manifest, OUTPUT / FACE_COLLECTION / "selected-ct-seg")
else:
    print("Controlled CT/SEG download is off. An approved user can use the prepared manifest.")''', tags=['optional-download'])
md('''## Keep a record of what you used

We've gone from collection discovery to whole-dataset download planning, then built participant cohorts using modality, diagnosis, and segmentation availability. The saved tables include all search pages, while some displayed tables are deliberately short previews. The controlled-file and clinical-fact routes have explicit limits; they are not exhaustive archive-wide queries.

Before using a cohort in a study, review its source links, missing clinical values, inferred diagnoses, exact image/label relationships, and applicable licenses. Keep the dataset citations and split related scans at the person level when the dataset documents those relationships.

The next cell saves our query settings, metadata snapshot identity, original manifest URLs/checksums, and counts beside the exported tables. **It records metadata work, not proof that any image transfer completed.**''')
code('''run_record = {
    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    "tcia_utils_version": version("tcia_utils"), "metadata_snapshot": SNAPSHOT,
    "query": {"collections": COHORT_COLLECTIONS, "modality": COHORT_MODALITY,
              "diagnosis_text": DIAGNOSIS_TEXT, "include_inferred": INCLUDE_INFERRED_DIAGNOSES},
    "dataset_download_groups": len(download_plan), "saved_manifests": saved_manifests,
    "download_groups_requiring_collection_link": other_groups["download_id"].tolist(),
    "candidate_records": len(candidates), "matching_records": len(cohort),
    "brain_collections": BRAIN_COLLECTIONS, "brain_segmentation_files": len(brain_cohort),
    "controlled_collection": FACE_COLLECTION, "controlled_selected_files": len(face_selection),
    "scope": "Dataset-scoped records; no cross-dataset person deduplication.",
    "clinical_caveat": "Derived clinical curation; original dataset descriptions and source clinical files remain authoritative.",
    "payload_completion_verified": False,
    "source_pages": [collection["tcia_page"],
        "https://www.cancerimagingarchive.net/collection/ucsf-pdgm/",
        "https://www.cancerimagingarchive.net/collection/upenn-gbm/",
        "https://www.cancerimagingarchive.net/collection/head-neck-radiomics-hn1/",
        "https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/"]}
(OUTPUT / "workshop_run.json").write_text(json.dumps(run_record, indent=2))
tcia.close()
print("Saved tables, manifests, and workshop_run.json in the notebook's output folder.")''')
md('''### Try your own question

Change `COHORT_COLLECTIONS`, `COHORT_MODALITY`, and `DIAGNOSIS_TEXT`, then rerun section 2 onward. Start with a small set of collections so you can inspect their clinical labels and coverage before widening the search.

For another challenge, change `BRAIN_COLLECTIONS` and compare how many participants have segmentation files with checked versus unchecked geometry. Keep both categories visible until you've decided what your project actually requires.

Useful links: [TCIA Dataset Explorer](https://www.cancerimagingarchive.net/dataset-explorer/), [CMB-GEC](https://www.cancerimagingarchive.net/collection/cmb-gec/), [UCSF-PDGM](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/), [UPENN-GBM](https://www.cancerimagingarchive.net/collection/upenn-gbm/), [HEAD-NECK-RADIOMICS-HN1](https://www.cancerimagingarchive.net/collection/head-neck-radiomics-hn1/), [controlled-access instructions](https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/), and [TCIA Data Retriever](https://github.com/TCIA/data-retriever).''')

notebook = nbf.v4.new_notebook(cells=cells, metadata={
    'kernelspec': {'display_name':'Python 3', 'language':'python', 'name':'python3'},
    'language_info': {'name':'python', 'version':'3.11'},
    'tcia_workshop': {'package_version':'4.0.0a1', 'default_mode':'live_public_metadata',
        'payload_downloads_default':False, 'audience':'junior data scientists'}})
# Stable IDs make regeneration reviewable.
for i, cell in enumerate(notebook.cells): cell.id = f'tcia-workshop-{i:02d}'
OUT.mkdir(exist_ok=True)
nbf.validate(notebook)
nbf.write(notebook, OUT / 'TCIA_Dataset_and_Participant_Queries.ipynb')
print(f'Wrote one notebook with {len(cells)} cells.')
