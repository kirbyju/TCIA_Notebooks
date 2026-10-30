"""Project the existing public recording through local shared-plan code.

This is maintainer tooling, not a live refresh or payload download. It preserves
recording timestamps/fingerprint and explicitly records the local code hashes.
"""

import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit, urlencode

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--skill-source", type=Path, required=True)
parser.add_argument(
    "--cassette",
    type=Path,
    default=Path(__file__).resolve().parents[1]
    / "tcia_utils_v4/_fixtures/workshop-public-metadata.json.gz",
)
args = parser.parse_args()
root = args.skill_source.resolve()
sys.path.insert(0, str(root))
from mcp_server.tcia_query_mcp.service import TciaQueryService, compact_download

capture = json.loads(gzip.decompress(args.cassette.read_bytes()))
requests = capture["requests"]
details = {}
downloads = {}
sources = {}
for key, item in list(requests.items()):
    method, url, content = json.loads(key)
    path = urlsplit(url).path
    segments = path.strip("/").split("/")
    if item["status"] != 200:
        continue
    body = (
        json.loads(base64.b64decode(item["body"]))
        if item["headers"].get("content-type", "").startswith("application/json")
        else None
    )
    if body is None:
        continue
    if len(segments) == 3 and segments[:2] == ["v2", "datasets"]:
        details[unquote(segments[2]).casefold()] = body
        for row in body["datasets"]:
            sources[(row["dataset_type"], row["short_title"])] = row
    if len(segments) == 4 and segments[:2] == ["v2", "datasets"] and segments[3] == "downloads":
        if body["has_more"]:
            raise RuntimeError("A full download inventory is required for fixture projection")
        title = unquote(segments[2])
        downloads[title.casefold()] = body["downloads"]


class RecordedService(TciaQueryService):
    def get_dataset(self, title):
        rows = downloads[title.casefold()]
        actual = details.get(title.casefold())
        datasets = (
            actual["datasets"]
            if actual
            else list(
                {
                    (r["dataset_type"], r["short_title"]): {
                        "dataset_type": r["dataset_type"],
                        "short_title": r["short_title"],
                        "title": r.get("dataset_title"),
                    }
                    for r in rows
                }.values()
            )
        )
        return {
            "datasets": datasets,
            "current_downloads": [
                compact_download({**row, "title": row.get("dataset_title")}) for row in rows
            ],
        }


service = RecordedService()
for key, item in list(requests.items()):
    method, url, content = json.loads(key)
    if urlsplit(url).path != "/v2/datasets/search" or item["status"] != 200:
        continue
    body = json.loads(base64.b64decode(item["body"]))
    for row in body["datasets"]:
        source = sources.get((row["dataset_type"], row["short_title"]))
        if source is None:
            raise RuntimeError("Recording is missing category evidence for " + row["short_title"])
        row["data_categories"] = source["download_types"]
    item["body"] = base64.b64encode(json.dumps(body, separators=(",", ":")).encode()).decode()
for title in downloads:
    canonical = downloads[title][0]["short_title"]
    full = service.get_download_plan(canonical)
    selections = [None]
    other_ids = [
        r["download_id"]
        for r in full["downloads"]
        if r["download_method"] not in {"dicom_manifest", "tabular_manifest"}
    ]
    if other_ids:
        selections.append(other_ids)
    for selected_ids in selections:
        body = (
            full
            if selected_ids is None
            else service.get_download_plan(canonical, download_ids=selected_ids)
        )
        url = "https://tcia.duckdns.org/v2/datasets/" + canonical + "/download-plan"
        if selected_ids is not None:
            url += "?" + urlencode({"download_ids": selected_ids}, doseq=True)
        key = json.dumps(["GET", url, ""], separators=(",", ":"))
        requests[key] = {
            "status": 200,
            "headers": {"content-type": "application/json"},
            "body": base64.b64encode(json.dumps(body, separators=(",", ":")).encode()).decode(),
        }
capture["local_contract_projection"] = {
    "projected_at_utc": datetime.now(timezone.utc).isoformat(),
    "description": "Recorded public metadata projected through local shared-plan code; not a deployed-service response.",
    "plan_version": 1,
    "source_sha256": {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in [
            "scripts/tcia_download_requirements.py",
            "mcp_server/tcia_query_mcp/service.py",
        ]
    },
}
args.cassette.write_bytes(
    gzip.compress(json.dumps(capture, separators=(",", ":")).encode(), mtime=0)
)
print("Projected recorded metadata; original recording time and fingerprint retained.")
