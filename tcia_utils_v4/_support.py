"""Explicit synthetic fixture transport for the five v4 teaching notebooks."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import unquote

import httpx
from tcia_utils import TCIAClient, TCIAError


FIXTURES = Path(__file__).resolve().parent / "_fixtures"
MODE = os.environ.get("TCIA_EXAMPLE_MODE", "fixture").strip().lower()
if MODE not in {"fixture", "live"}:
    raise ValueError("TCIA_EXAMPLE_MODE must be fixture or live")
SHORT_TITLE = "EXAMPLE" if MODE == "fixture" else "4D-Lung"
DOI = "10.0000/example" if MODE == "fixture" else "10.7937/K9/TCIA.2016.ELN8YGLE"
PARTICIPANT_KEY = "collection:EXAMPLE:0007"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _page(rows: list[dict], key: str, limit: int, **other) -> dict:
    return {key: rows, "count": len(rows), "limit": limit, "has_more": False,
            "truncated": False, "next_cursor": None, **other}


def _handler(request: httpx.Request) -> httpx.Response:
    path = unquote(request.url.path)
    incoming = json.loads(request.content) if request.method == "POST" and request.content else {}
    limit = int(incoming.get("limit") or request.url.params.get("limit") or
                request.url.params.get("publication_limit") or 25)
    if path == "/v2/ready":
        body = {"status": "ready", "release_fingerprint": "synthetic-fixture-v1",
                "release_tag": "synthetic-only", "installed_profile": "research_detail"}
    elif path == "/v2/bundle":
        body = {"v2_bundle_manifest_exists": True, "v2_install_state_exists": True,
                "v2_capabilities": {"participant_search": True,
                                    "public_non_dicom_detail": True,
                                    "controlled_access_detail": True,
                                    "clinical_detail": True,
                                    "datacite_metadata": True,
                                    "verified_analytical_publications": True},
                "v2_install": {"release_fingerprint": "synthetic-fixture-v1",
                               "installed_profile": "research_detail"},
                "v2_bundle": {"release_fingerprint": "synthetic-fixture-v1"}}
    elif path == "/v2/datasets/search":
        row = _fixture("mixed_access_dataset.json")["datasets"][0]
        body = _page([row], "datasets", limit, note="SYNTHETIC FIXTURE: visible records only")
    elif path == "/v2/datasets/EXAMPLE":
        body = _fixture("mixed_access_dataset.json")
    elif path == "/v2/datasets/EXAMPLE/access":
        detail = _fixture("mixed_access_dataset.json")
        body = {"dataset": detail["datasets"][0],
                "download_groups": {"open": [detail["current_downloads"][0]],
                                    "controlled": [detail["current_downloads"][1]]},
                "controlled_access_policy_url": "https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/",
                "notes": ["SYNTHETIC FIXTURE: inspect each download access level."]}
    elif path == "/v2/datasets/EXAMPLE/downloads":
        body = _page(_fixture("mixed_access_dataset.json")["current_downloads"][:limit],
                     "downloads", limit, short_title="EXAMPLE")
    elif path == "/v2/datacite/dois":
        body = _page([{"doi": DOI, "tcia_short_name": "EXAMPLE", "title": "Synthetic mixed-access collection",
                       "citation_count": 2, "view_count": 5, "download_count": 9}],
                     "dois", limit, metrics_note="SYNTHETIC FIXTURE: DataCite events are not TCIA downloads.")
    elif path.startswith("/v2/datacite/dois/"):
        style = request.url.params.get("citation_style", "apa")
        body = {"record": {"doi": DOI, "citation_style": style,
                           "formatted_citation": "Synthetic dataset (2026). TCIA. doi:10.0000/example",
                           "metadata": {"title": "Synthetic dataset"}},
                "provenance_note": "SYNTHETIC FIXTURE: DataCite enrichment only."}
    elif path == "/v2/publications/verified-use":
        body = _page([{"rec_number": "synthetic-001", "title": "Synthetic analytical use",
                       "linked_tcia_dataset_dois": [DOI]}], "publications", limit,
                     verification_note="SYNTHETIC FIXTURE: TCIA-maintained verified analytical use.")
    elif path == "/v2/datasets/EXAMPLE/impact":
        body = {"impacts": [{"dataset_type": "collection", "short_title": "EXAMPLE",
                             "datacite_citation_count": 2,
                             "verified_analytical_publication_count": 1}],
                "verified_publications": [{"rec_number": "synthetic-001"}],
                "publication_limit": limit,
                "notes": ["SYNTHETIC FIXTURE: DataCite events differ from verified analytical use."]}
    elif path == "/v2/public-non-dicom/assets":
        row = _fixture("partial_public_assets.json")["assets"][0]
        body = _page([row], "assets", limit,
                     scope="SYNTHETIC FIXTURE: public non-DICOM and reviewed exceptions.",
                     annotation_relationship_scope="No source-image relationship inferred.")
    elif path == "/v2/dicom/annotation-downloads":
        download = {"short_title": "EXAMPLE", "dataset_type": "collection",
                    "download_id": "synthetic-annotation", "download_title": "Synthetic annotation",
                    "access_level": "open"}
        body = {"downloads": [download], "count": 1, "limit": limit,
                "routing_note": "SYNTHETIC FIXTURE: annotation availability only.",
                "scope": "Download-level signal, no source-image relationship.",
                "public_dicom_annotation_detail": {"authority": "IDC"}}
    elif path == "/v2/controlled-access/datasets":
        body = {"datasets": [{"dataset": {"short_title": "EXAMPLE", "dataset_type": "collection",
                                          "resolved_access_level": "mixed"},
                              "matching_downloads": [_fixture("mixed_access_dataset.json")["current_downloads"][1]]}],
                "count": 1, "limit": limit,
                "controlled_access_policy_url": "https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/",
                "note": "SYNTHETIC FIXTURE: public inventory metadata, no access authorization."}
    elif path == "/v2/controlled-access/EXAMPLE/files":
        body = _fixture("bounded_controlled_files.json")
    elif path == "/v2/participants/search":
        row = _fixture("partial_participants.json")["participants"][0]
        body = _page([row], "participants", limit,
                     identity_scope="Participant identity is dataset-scoped.",
                     public_dicom_detail_route="IDC/idc-index")
    elif path == f"/v2/participants/{PARTICIPANT_KEY}":
        participant = _fixture("partial_participants.json")["participants"][0]
        body = {"participant": participant, "identifiers": [], "count": 1,
                "identity_scope": "Participant identity is dataset-scoped."}
    elif path == f"/v2/participants/{PARTICIPANT_KEY}/assets":
        row = {**_fixture("partial_public_assets.json")["assets"][0],
               "participant_key": PARTICIPANT_KEY}
        body = _page([row], "assets", limit, participant_key=PARTICIPANT_KEY,
                     public_dicom_detail_route="IDC/idc-index")
    elif path == "/v2/datasets/EXAMPLE/participant-coverage":
        body = {"short_title": "EXAMPLE", "dataset_type": "collection",
                "participant_count": 1, "unlinked_dataset_assets": [],
                "participant_link_issues": [], "sources": [], "coverage_complete": True}
    elif path == "/v2/clinical/EXAMPLE/subjects":
        body = _fixture("inferred_clinical_subjects.json")
    elif path == "/v2/clinical/EXAMPLE/facts":
        body = _fixture("inferred_clinical_facts.json")
    elif path == "/v2/clinical/EXAMPLE/conflicts":
        body = {"short_title": "EXAMPLE", "dataset_types": ["collection"],
                "conflicts": [], "count": 0, "limit": limit,
                "note": "SYNTHETIC FIXTURE: no conflicts in this small selection."}
    else:
        return httpx.Response(404, json={"status": 404, "code": "fixture_not_mapped",
                                         "detail": f"Fixture route not mapped: {path}", "retryable": False})
    return httpx.Response(200, json=body)


def make_client() -> TCIAClient:
    """Return a built-package client using an explicit fixture or live host."""
    if MODE == "fixture":
        transport = httpx.MockTransport(_handler)
        return TCIAClient(base_url="https://fixture.example", retries=0,
                          http_client=httpx.Client(transport=transport))
    return TCIAClient(base_url=os.environ.get("TCIA_V2_BASE_URL", "https://tcia.duckdns.org"),
                      timeout=15.0, retries=1)


def checked(label: str, operation):
    """Report live failure; fixture failures are test failures."""
    try:
        return operation()
    except TCIAError as exc:
        if MODE == "fixture":
            raise
        print(f"{label}: unavailable on this service (status={exc.status}, code={exc.code}): {exc.detail}")
        return None
