"""Write the five small, editable TCIA Utils v4 teaching notebooks."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tcia_utils_v4"
OUT.mkdir(parents=True, exist_ok=True)


SETUP = '''from importlib.metadata import version
from _support import MODE, SHORT_TITLE, DOI, make_client, checked
print("SYNTHETIC FIXTURE MODE — results below are examples, not live TCIA evidence" if MODE == "fixture"
      else "LIVE METADATA MODE — bounded calls to the configured TCIA service")
print("tcia_utils", version("tcia_utils"))'''


def write(name: str, *cells: tuple[str, str]) -> None:
    notebook = nbf.v4.new_notebook(
        cells=[nbf.v4.new_markdown_cell(("Run these examples from the complete `tcia_utils_v4` folder; see [setup and preview-release instructions](README.md).\n\n" + source if i == 0 else source)) if kind == "md"
               else nbf.v4.new_code_cell(source) for i, (kind, source) in enumerate(cells)],
        metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                  "language_info": {"name": "python"}},
    )
    nbf.write(notebook, OUT / name)


write(
    "01_discover_datasets_citations.ipynb",
    ("md", "# Discover a TCIA dataset and cite it\n\nThis notebook uses the built `tcia_utils` package. The default mode is a **synthetic fixture**; set `TCIA_EXAMPLE_MODE=live` to make bounded metadata calls to a TCIA V2 REST host. DataCite records enrich visible TCIA dataset records and do not establish publication alone. No imaging payload is requested."),
    ("code", SETUP),
    ("code", '''with make_client() as tcia:
    status = checked("readiness", tcia.status)
    if status:
        print("release", status.provenance.release_fingerprint, "profile", status.data.installed_profile)
    page = checked("dataset search", lambda: tcia.search_datasets(short_titles=[SHORT_TITLE], limit=5))
    if page:
        for row in page.items:
            print("visible TCIA dataset", row.get("dataset_type"), row.get("short_title"), row.get("doi"))
        print("page", page.count, "completeness", page.completeness.state)
    detail = checked("dataset detail", lambda: tcia.get_dataset(SHORT_TITLE))
    if detail:
        print("dataset candidates", [(row.get("dataset_type"), row.get("short_title")) for row in detail.data["datasets"]])
        print("download access", [(row.get("download_id"), row.get("access_level")) for row in detail.data["current_downloads"]])
        print("related analyses are bounded suggestions", len(detail.data["related_analysis_results"]))'''),
    ("md", "A short title may identify both a Collection and an Analysis Result. Keep `dataset_type` with `short_title`. Use download-level access and license evidence before making a selection."),
    ("code", '''with make_client() as tcia:
    citation = checked("citation", lambda: tcia.get_citation(DOI, style="apa"))
    if citation:
        print("DataCite citation", citation.data["record"]["formatted_citation"])
        print("scope", citation.notes[0])
    impact = checked("impact", lambda: tcia.get_impact(SHORT_TITLE, publication_limit=3))
    if impact:
        for row in impact.data["impacts"]:
            print("DataCite citation events", row.get("datacite_citation_count"),
                  "verified analytical publications", row.get("verified_analytical_publication_count"))
        print("publication sublist completeness", impact.completeness.state)'''),
)


write(
    "02_public_dicom_idc.ipynb",
    ("md", "# Public DICOM detail with idc-index\n\nTCIA Utils establishes a visible dataset identity. `idc-index` supplies public DICOM series detail and viewer selection directly. The default fixture is synthetic and does **not** claim that its UID exists in IDC. Live mode queries at most three index rows by reviewed TCIA dataset DOI and patient ID. It never downloads DICOM objects."),
    ("code", SETUP),
    ("code", '''with make_client() as tcia:
    detail = checked("TCIA dataset identity", lambda: tcia.get_dataset(SHORT_TITLE))
    if detail:
        print("visible dataset DOI(s)", [row.get("doi") for row in detail.data["datasets"]])
        print("TCIA observation", detail.provenance.release_fingerprint)
verified_tcia_doi = bool(detail and any(
    str(row.get("doi") or "").casefold() == DOI.casefold()
    for row in detail.data["datasets"]))
print("expected DOI present in visible TCIA record", verified_tcia_doi)'''),
    ("code", '''from idc_index import IDCClient
from importlib.metadata import version as package_version
from pathlib import Path
import os
import tempfile
from tcia_utils import TCIAClient
print("idc-index", package_version("idc-index"), "index data", package_version("idc-index-data"))
selection_row = None
if MODE == "fixture":
    if verified_tcia_doi:
        selection_row = {"dataset_type": "collection", "short_title": SHORT_TITLE,
                         "doi": DOI, "access_level": "open", "route_kind": "SeriesInstanceUID",
                         "SeriesInstanceUID": "1.2.826.0.1.3680043.10.999.7",
                         "identifier_source": "reviewed", "evidence_mode": "synthetic_fixture",
                         "license_short_name": "synthetic-example"}
        print("SYNTHETIC FIXTURE series UID", selection_row["SeriesInstanceUID"])
        print("No IDC coverage or viewer URL is claimed for this synthetic UID.")
elif verified_tcia_doi:
    idc = IDCClient()
    print("IDC index version", idc.get_idc_version())
    sql = ("SELECT SeriesInstanceUID, StudyInstanceUID, PatientID, Modality, source_DOI, license_short_name "
           "FROM index WHERE lower(source_DOI) = '10.7937/k9/tcia.2016.eln8ygle' "
           "AND PatientID = '100_HM10395' ORDER BY SeriesInstanceUID LIMIT 3")
    rows = idc.sql_query(sql)
    print("IDC rows", len(rows), "(bounded at 3)")
    if not rows.empty:
        first = rows.iloc[0]
        if str(first["source_DOI"]).casefold() == DOI.casefold():
            uid = str(first["SeriesInstanceUID"])
            print("verified public SeriesInstanceUID", uid,
                  "source DOI", first["source_DOI"], "license", first["license_short_name"])
            print("IDC viewer URL", idc.get_viewer_URL(seriesInstanceUID=uid))
            selection_row = {"dataset_type": "collection", "short_title": SHORT_TITLE,
                             "doi": DOI, "access_level": "open", "route_kind": "SeriesInstanceUID",
                             "SeriesInstanceUID": uid, "identifier_source": "idc-index",
                             "PatientID": str(first["PatientID"]),
                             "source_DOI": str(first["source_DOI"]),
                             "license_short_name": str(first["license_short_name"]),
                             "idc_index_data_version": idc.get_idc_version()}
        else:
            print("IDC source DOI differs from TCIA identity; no handoff created.")
    else:
        print("IDC coverage unverified for this DOI/patient selection; no series handoff created.")'''),
    ("code", '''if selection_row and detail:
    selection = TCIAClient.select([selection_row], release_identity=detail.provenance,
                                  query_scope={"short_title": SHORT_TITLE, "doi": DOI,
                                               "record_grain": "series", "completeness": "unknown",
                                               "example_mode": "synthetic_fixture" if MODE == "fixture" else "live_idc_metadata"})
    destination = Path(os.environ.get("TCIA_EXAMPLE_OUTPUT_DIR") or tempfile.mkdtemp(prefix="tcia-v4-series-"))
    report = TCIAClient.export_selection(selection, destination)
    print("metadata-only manifest files", [path.name for path in report.files])
    print("exported", report.exported, "unresolved", report.unresolved)
else:
    print("No verified series selection; no manifest written.")'''),
    ("md", "A series UID from IDC is evidence for a public DICOM handoff. Keep its source DOI and patient scope with it. Do not parse opaque TCIA asset IDs into series UIDs. Viewer URLs are metadata links; no viewer or imaging payload is opened here."),
)


write(
    "03_non_dicom_annotations.ipynb",
    ("md", "# Non-DICOM availability and annotation signals\n\nThis notebook inspects public asset summaries and DICOM annotation download signals. An asset may be a package or transformed preview. An annotation signal does not prove which source image it annotates. Live service routes may be unavailable even when readiness is green; that is reported explicitly."),
    ("code", SETUP),
    ("code", '''with make_client() as tcia:
    assets = checked("public non-DICOM assets", lambda: tcia.search_public_assets(short_titles=[SHORT_TITLE], limit=1))
    if assets:
        for row in assets.items:
            print("asset", row.get("asset_id"), "format", row.get("file_format"),
                  "grain", row.get("asset_granularity"), "inventory", row.get("inventory_status"))
        print("scope", assets.response.get("scope"), "completeness", assets.completeness.state)
    annotations = checked("annotation downloads", lambda: tcia.search_annotation_downloads(short_titles=[SHORT_TITLE], limit=3))
    if annotations:
        print("annotation downloads", [(row.get("download_id"), row.get("access_level"))
                                       for row in annotations.data["downloads"]])
        print("relationship limit", annotations.data["scope"])
        print("bounded completeness", annotations.completeness.state)'''),
    ("md", "Public non-DICOM inventory can include narrowly reviewed IDC-missing DICOM exceptions; it is not a general DICOM series catalog. If a route fails, retain the unavailable state rather than treating it as zero matching assets. No file or image is fetched."),
)


write(
    "04_controlled_metadata_manifest.ipynb",
    ("md", "# Controlled public metadata to a manifest handoff\n\nA controlled inventory is public metadata, not authorization to retrieve a controlled payload. This example makes bounded metadata calls and writes a route-specific Data Retriever manifest plus an accounting companion in a temporary directory. It does not run Data Retriever, authenticate, or transfer data. The fixture inventory is synthetic."),
    ("code", SETUP),
    ("code", '''from pathlib import Path
import os
import tempfile
controlled_title = "EXAMPLE" if MODE == "fixture" else "CMB-PCA"
with make_client() as tcia:
    datasets = checked("controlled dataset inventory", lambda: tcia.search_controlled_datasets(limit=5))
    if datasets:
        print("bounded controlled datasets", datasets.data["count"], datasets.completeness.state)
    files = checked("controlled file inventory", lambda: tcia.list_controlled_files(
        controlled_title, limit=2 if MODE == "fixture" else 1))
    if files:
        print("public file metadata rows", files.data["count"], "with DRS URI",
              sum(bool(row.get("drs_uri")) for row in files.data["files"]))
        print("authorization reminder", files.data["warning"])
        selection = tcia.select(files.data["files"], release_identity=files.provenance,
                                query_scope={"short_title": controlled_title,
                                             "record_grain": "file", "completeness": "unknown"})
        destination = Path(os.environ.get("TCIA_EXAMPLE_OUTPUT_DIR") or tempfile.mkdtemp(prefix="tcia-v4-manifest-"))
        report = tcia.export_selection(selection, destination)
        print("manifest files", [path.name for path in report.files])
        print("accounting", {"exported": report.exported, "deduplicated": report.deduplicated,
                             "excluded": report.excluded, "unresolved": report.unresolved})'''),
    ("md", "Each CSV has exactly one recognized route column, such as `drs_uri`. The companion records unresolved rows and unknown sizes. An absent DRS URI stays unresolved. An actual controlled transfer requires a separate authorization workflow and is outside this notebook."),
)


write(
    "05_participants_clinical_availability.ipynb",
    ("md", "# Participants, clinical scope, and imaging availability\n\nParticipant identity is scoped to a TCIA dataset. Clinical subject IDs may need a reviewed crosswalk before joining to inventory IDs. A dataset-level inferred diagnosis is not an observed patient fact. This notebook reads small metadata selections only; live routes that fail are reported as unavailable."),
    ("code", SETUP),
    ("code", '''with make_client() as tcia:
    participants = checked("participant search", lambda: tcia.search_participants(
        short_titles=[SHORT_TITLE], limit=1))
    if participants:
        for row in participants.items:
            print("participant", row.get("dataset_type"), row.get("short_title"), row.get("participant_key"))
        print("identity scope", participants.response.get("identity_scope"))
        participant_key = participants.items[0]["participant_key"] if participants.items else None
    else:
        participant_key = None
    if participant_key:
        detail = checked("participant detail", lambda: tcia.get_participant(participant_key))
        if detail:
            print("source identifiers", len(detail.data["identifiers"]))
        assets = checked("participant assets", lambda: tcia.list_participant_assets(participant_key, limit=2))
        if assets:
            print("available asset summaries", assets.count, "completeness", assets.completeness.state)'''),
    ("code", '''with make_client() as tcia:
    subjects = checked("clinical subjects", lambda: tcia.list_clinical_subjects(SHORT_TITLE, limit=50))
    if subjects:
        for row in subjects.data["subjects"][:2]:
            print("clinical subject", row.get("subject_id"), "diagnosis", row.get("primary_diagnosis"),
                  "inferred", row.get("primary_diagnosis_is_inferred"))
        print("clinical list completeness", subjects.completeness.state)
    facts = checked("clinical facts", lambda: tcia.list_clinical_facts(SHORT_TITLE, limit=100))
    if facts:
        for row in facts.data["facts"][:2]:
            print("fact", row.get("subject_id"), row.get("concept"),
                  "scope", row.get("evidence_scope"), "inferred", row.get("is_inferred"))'''),
    ("md", "The bounded clinical lists are not full-cohort exports. `coverage_complete` only describes participant linking. Keep source priority, conflicts, and inference flags when analyzing clinical evidence; do not infer a patient diagnosis from a dataset label."),
)


print(f"Wrote five notebooks to {OUT}")
