"""Project verified recorded inputs through the shared planner, never transfer images.

The identity refresh makes bounded public TCIA metadata requests. Ordinary
regeneration uses the retained verified identities and the existing IDC fixture.
These projected plans are explicitly not deployed-service responses.
"""

import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import quote, urlsplit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--skill-source", type=Path, required=True)
parser.add_argument("--participants", type=Path)
parser.add_argument("--refresh-identities", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
p = root / "tcia_utils_v4/_fixtures/workshop-public-metadata.json.gz"
capture = json.loads(gzip.decompress(p.read_bytes()))
sys.path.insert(0, str(args.skill_source.resolve()))
from mcp_server.tcia_query_mcp.service import TciaQueryService, public_asset_download


def fetch(path):
    output = subprocess.run(
        [
            "/usr/bin/curl",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "30",
            "https://tcia.duckdns.org" + path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(output.stdout)


projection = capture.get("participant_plan_projection", {})
if args.refresh_identities:
    if args.participants is None:
        raise SystemExit("--participants is required to refresh identities")
    before = fetch("/v2/ready")
    assert (
        before["release_fingerprint"] == capture["fingerprint"]
    ), "Use a recording from this deployed snapshot"
    keys = sorted(
        {r["participant_key"] for r in json.loads(args.participants.read_text())}
    )
    identities = {key: fetch("/v2/participants/" + quote(key, safe="")) for key in keys}
    titles = {d["participant"]["short_title"] for d in identities.values()}
    datasets = {
        title: fetch("/v2/datasets/" + quote(title, safe="")) for title in titles
    }
    assert fetch("/v2/ready")["release_fingerprint"] == before["release_fingerprint"]
    projection = {
        "identity_observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "identity_fingerprint": before["release_fingerprint"],
        "identities": identities,
        "datasets": datasets,
    }
if not projection.get("identities"):
    raise SystemExit("No retained verified identities; refresh them explicitly first")
index_path = p.with_name("cohort-public-dicom.json.gz")
index = json.loads(gzip.decompress(index_path.read_bytes()))
assets = []
for key, response in capture["requests"].items():
    method, url, body = json.loads(key)
    if (
        urlsplit(url).path == "/v2/public-non-dicom/assets"
        and response["status"] == 200
    ):
        data = json.loads(base64.b64decode(response["body"]))
        assets.extend(data["assets"])
assets = list({a["asset_id"]: public_asset_download(a) for a in assets}.values())


class RecordedProvider:
    def resolve(self, doi, ids, modality, **kwargs):
        rows = [
            {
                **r,
                "license_short_name": r.get("license_short_name"),
                "analysis_result_id": r.get("analysis_result_id"),
            }
            for r in index["rows"]
            if r["PatientID"] in ids
            and r["source_DOI"].lower() == doi.lower()
            and r["Modality"].casefold() == modality.casefold()
            and (
                not kwargs["collection_ids"]
                or r["collection_id"] in kwargs["collection_ids"]
            )
        ]
        return {
            "rows": rows,
            "version": {
                "idc_version": index["idc_version"],
                "idc_index_data_version": index["data_package_version"],
                "api_version": "fixture_projection",
                "build": None,
            },
        }


class RecordedService(TciaQueryService):
    def get_participant(self, *, participant_key):
        return projection["identities"][participant_key]

    def get_dataset(self, title):
        return projection["datasets"][title]

    def bundle_info(self):
        return {"v2_bundle": {"release_fingerprint": capture["fingerprint"]}}

    def find_public_non_dicom_assets(self, **kw):
        assert kw.get("cursor") is None
        selected = [
            a
            for a in assets
            if a["short_title"] in kw["short_titles"]
            and a.get("subject_id") == kw["participant_id"]
            and str(a.get("modality", "")).casefold() == kw["modalities"][0].casefold()
        ]
        return {"assets": selected, "has_more": False, "next_cursor": None}


keys = sorted(projection["identities"])
with tempfile.TemporaryDirectory() as directory:
    placeholder = Path(directory) / "metadata"
    placeholder.touch()
    service = RecordedService(
        snapshot_db=placeholder,
        participant_db=placeholder,
        public_non_dicom_db=placeholder,
        idc_metadata=RecordedProvider(),
    )
    counts = {}
    for modality, file_format in [("CT", "DICOM"), ("Whole Slide Image", "non-DICOM")]:
        body = {
            "participant_keys": keys,
            "modality": modality,
            "file_format": file_format,
        }
        plan = service.get_participant_download_plan(**body)
        assert plan["complete"] and plan["rows"]
        key = json.dumps(
            [
                "POST",
                "https://tcia.duckdns.org/v2/participants/download-plan",
                json.dumps(body, separators=(",", ":")),
            ],
            separators=(",", ":"),
        )
        capture["requests"][key] = {
            "status": 200,
            "headers": {"content-type": "application/json"},
            "body": base64.b64encode(
                json.dumps(plan, separators=(",", ":")).encode()
            ).decode(),
        }
        counts[file_format] = len(plan["rows"])
projection.update(
    {
        "projected_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Verified TCIA identities and recorded provider metadata projected through local planner code; not deployed responses.",
        "source_sha256": {
            name: hashlib.sha256((args.skill_source / name).read_bytes()).hexdigest()
            for name in [
                "mcp_server/tcia_query_mcp/participant_downloads.py",
                "mcp_server/tcia_query_mcp/idc_metadata.py",
                "mcp_server/tcia_query_mcp/service.py",
                "mcp_server/tcia_query_mcp/models.py",
            ]
        },
        "idc_fixture_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
        "counts": counts,
    }
)
capture["participant_plan_projection"] = projection
p.write_bytes(
    gzip.compress(json.dumps(capture, separators=(",", ":")).encode(), mtime=0)
)
print({"participants": len(keys), "selected_images": counts, "payload_transfers": 0})
