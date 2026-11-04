"""Maintain the participant-cohort section without rewriting the original tutorial."""
from pathlib import Path
import json
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'TCIA_Aspera_CLI_Downloads.ipynb'
HEADING='# Download a participant cohort selected with tcia_utils'

def section():
    cells=[]
    def md(s): cells.append(nbf.v4.new_markdown_cell(s.strip()))
    def code(s, **metadata): cells.append(nbf.v4.new_code_cell(s.strip(),metadata=metadata))
    original=json.loads((ROOT/'tools/aspera_brain_section.json').read_text())
    md('''# Download a participant cohort selected with tcia_utils

So far we've picked paths by hand. What if we already know which participants interest us? `tcia_utils` can find their indexed files and save a CSV that this notebook passes to Aspera.

Run **Setup** above first, then you can jump straight to this section. The earlier whole-package examples are independent. The Python package queries metadata and writes the file list; the separately installed Aspera CLI performs the transfers.

We'll start with open-access brain MR data and segmentation masks from [UCSF-PDGM](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/) and [UPENN-GBM](https://www.cancerimagingarchive.net/collection/upenn-gbm/). Their images use NIfTI (`.nii` or `.nii.gz`). You can also load a participant cohort saved by the [TCIA queries notebook](https://colab.research.google.com/github/kirbyju/TCIA_Notebooks/blob/main/tcia_utils_v4/TCIA_Dataset_and_Participant_Queries.ipynb).

These are derived discovery metadata. The dataset descriptions and original supporting files remain the authoritative sources for cohort definitions and clinical values.''')
    code('''import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "tcia_utils[tables]==4.0.0a17", "nibabel>=5,<6"])''',tags=['cohort-installation'])
    code('''from pathlib import Path
import json
import pandas as pd
from tcia_utils import TCIAClient, format_table

OUTPUT = Path("tcia-aspera-cohort")
OUTPUT.mkdir(exist_ok=True)
tcia = TCIAClient(base_url="https://tcia.duckdns.org", timeout=120, pin_snapshot=True)
COHORT_JSON = ""  # Optional path to a saved records-style participant cohort JSON.
MODALITY = "MR"
FILE_FORMATS = ["NIFTI"]
MAX_ITEMS = 2  # Files, not participants or bytes. Use None for the full selected file list.''')
    md('''Leave `COHORT_JSON` empty for the brain MR example. We'll find participants with public MR images and indexed segmentation files, then start with two participants. A participant appearing in both tables does not establish a particular image/mask pair.

To use a cohort you selected elsewhere, enter its JSON path above. Preserve `participant_key`, `dataset_type`, `short_title`, and `display_participant_id`; a participant ID alone is ambiguous across datasets. Change `MODALITY` and `FILE_FORMATS` for your question. Those participants must have exact indexed files in an open-access Aspera package; other download routes belong in their own workflows.''')
    brain=original[1]['source']
    code('''if COHORT_JSON:
    selected_participants = pd.read_json(COHORT_JSON)
else:
'''+''.join('    '+line+'\n' for line in brain.splitlines())+'''
    selected_participants = brain_cohort[
        ["participant_key", "dataset_type", "short_title", "display_participant_id"]
    ].drop_duplicates().head(2).copy()

display(selected_participants)
selected_participants.to_json(OUTPUT / "selected_participants.json", orient="records", indent=2)''')
    md(original[2]['source'])
    code('''brain_files = pd.DataFrame()
if len(selected_participants):
    brain_example = selected_participants.iloc[0]
    brain_files = tcia.search_public_assets(
        short_titles=[brain_example["short_title"]],
        participant_id=brain_example["display_participant_id"],
        file_formats=FILE_FORMATS, limit=500,
    ).to_dataframe(all_pages=True)
    display(brain_files.reindex(columns=[
        "subject_id", "file_name", "object_role", "geometry_status",
        "geometry_assessment_method", "geometry_details_json",
    ]))
    brain_files.to_json(OUTPUT / "example_files.json", orient="records", indent=2)
else:
    print("No participants matched. Adjust the filters before exporting.")''')
    md('''### Save the selected file list

`export_aspera_manifest()` follows the exact participant-linked file paths in the index and matches them to current published package links. It does not guess folder names or download entire participant folders. This keeps indexed follow-up scans in scope as well.

The CSV has two columns: `packageUrl` and `packagePath`. It uses the same format as the Participant Explorer's Aspera file export, so an existing export can also be consumed by the transfer cell below.

`MAX_ITEMS=2` exports just two files across the cohort. Those first two files are not necessarily a matching source-image/mask pair, and two files can still be large. Inspect their names, sizes and the dataset documentation. Set `MAX_ITEMS=None` and rerun this cell to export all indexed matching files for the selected participants.''')
    code('''aspera_manifest = tcia.export_aspera_manifest(
    selected_participants, OUTPUT / "tcia_aspera_files.csv",
    modality=MODALITY, file_formats=FILE_FORMATS,
    max_items=MAX_ITEMS, overwrite=True,
)
display(format_table(pd.DataFrame(aspera_manifest.rows), columns=[
    "short_title", "display_participant_id", "file_name", "size_bytes", "packagePath",
]))
display(pd.DataFrame(aspera_manifest.coverage))
print("Matching indexed files:", aspera_manifest.scope["matching_files"])
print("Files in this manifest:", aspera_manifest.scope["exported_files"])
print("Manifest:", aspera_manifest.path)
(OUTPUT / "aspera_selection.json").write_text(aspera_manifest.to_json(indent=2))''')
    md('''### Download the files in the manifest

This small adapter reads the CSV, groups files by package and passes the exact paths as separate arguments to `ascli`. It never turns a missing path into a whole-package download. The adapter lives here because it depends on the separate Aspera installation, rather than being part of `tcia_utils`.

The command uses the Ruby environment created in **Setup**. If you installed `ascli` another way, set `USE_NOTEBOOK_RVM=False`. The setup pins [ascli 4.28.0](https://github.com/IBM/aspera-cli/releases/tag/v4.28.0), which includes fixes for receiving lists of files through public package links.

You can set `MANIFEST_FILE` to an existing `tcia_aspera_files.csv` exported from the Participant Explorer instead. Review its rows before running the next cell.''')
    code('''import csv
import subprocess
from collections import defaultdict
from pathlib import PurePosixPath
from urllib.parse import urlsplit, parse_qs

USE_NOTEBOOK_RVM = True
MANIFEST_FILE = OUTPUT / "tcia_aspera_files.csv"
DOWNLOAD_DIRECTORY = OUTPUT / "images"

def receive_aspera_manifest(manifest_file, destination, *, use_notebook_rvm=True):
    with Path(manifest_file).open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["packageUrl", "packagePath"]:
            raise ValueError("Expected packageUrl,packagePath CSV columns.")
        rows = list(reader)
    if not rows:
        raise ValueError("The manifest contains no files; nothing will be downloaded.")
    groups = defaultdict(set)
    for row in rows:
        url, path = row["packageUrl"], row["packagePath"]
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname != "faspex.cancerimagingarchive.net"
                or parsed.username or parsed.password or parsed.port not in {None, 443}
                or parsed.fragment or parsed.path.rstrip("/") not in
                {"/aspera/faspex", "/aspera/faspex/public/package"}
                or set(parse_qs(parsed.query)) != {"context"}
                or not path or path.startswith(("-", "@")) or path.endswith("/")
                or ".." in PurePosixPath(path).parts or "\\\\" in path
                or any(ord(c) < 32 for c in url + path)):
            raise ValueError("The manifest contains an invalid public package/file route.")
        groups[url].add(path)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for number, (url, paths) in enumerate(groups.items(), start=1):
        ordered = sorted(paths)
        # Short batches keep large cohort exports within command-line limits.
        for offset in range(0, len(ordered), 50):
            batch = ordered[offset:offset + 50]
            print(f"Package {number}/{len(groups)}: transferring {len(batch)} selected files", flush=True)
            command = ["ascli", "faspex5", "packages", "receive",
                       "--url=" + url, "--to-folder=" + str(destination), *batch]
            if use_notebook_rvm:
                command = ["bash", "-lc",
                    'source /etc/profile.d/rvm.sh && rvm use 3.3.4 >/dev/null && exec "$@"',
                    "aspera-cohort", *command]
            # Stream Aspera progress, while keeping package URLs out of exception messages.
            if subprocess.call(command) != 0:
                raise RuntimeError(f"Aspera package {number} failed. Review its transfer output.")
    print("Aspera finished the selected transfers. Check its transfer summary for details.")

receive_aspera_manifest(MANIFEST_FILE, DOWNLOAD_DIRECTORY, use_notebook_rvm=USE_NOTEBOOK_RVM)''',tags=['cohort-transfer'])
    md(original[6]['source'])
    code(original[7]['source'],tags=['optional-local-files'])
    code('''tcia.close()
print("Saved the participant cohort, exact file manifest and metadata selection in", OUTPUT)''')
    for i,c in enumerate(cells): c.id=f'aspera-cohort-{i:02d}'
    return cells


def main():
    notebook=json.loads(PATH.read_text())
    cells=[nbf.from_dict(c) for c in notebook['cells']]
    for c in cells:
        if isinstance(c.source, list): c.source=''.join(c.source)
    start=next((i for i,c in enumerate(cells) if c.cell_type=='markdown' and c.source.startswith(HEADING)),None)
    end=next(i for i,c in enumerate(cells) if c.cell_type=='markdown' and c.source.startswith('# Acknowledgements'))
    if start is None: start=end
    notebook['cells']=cells[:start]+section()+cells[end:]
    for c in notebook['cells'][:start]:
        c.source=c.source.replace('Ruby **>= 3.1**','Ruby **>= 3.2**').replace('(>= 3.1 required by aspera-cli)','(>= 3.2 required by aspera-cli)')
        if c.cell_type=='code': c.source=c.source.replace('gem install aspera-cli\n','gem install aspera-cli -v 4.28.0\n')
    for c in notebook['cells']:
        if 'id' in c: c.metadata['id']=c.pop('id')
        if isinstance(c.source,str): c.source=c.source.splitlines(keepends=True)
    PATH.write_text(json.dumps(notebook,indent=2,ensure_ascii=False)+'\n')
    print('Updated Aspera participant-cohort section.')

if __name__=='__main__': main()
