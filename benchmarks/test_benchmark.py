"""No-transfer checks for benchmark scope and consent guards."""
import json
from pathlib import Path
import subprocess
import sys
import pytest
import benchmark_tcia_downloads as benchmark


def fixture(tmp_path):
    path=tmp_path/'cohort.json'
    path.write_text(json.dumps({'series':[{'series_size_MB':29}]}))
    return path


def test_budget_guard_runs_before_any_subprocess_or_output(tmp_path,monkeypatch):
    monkeypatch.setattr(benchmark.subprocess,'Popen',lambda *a,**k:pytest.fail('No launch'))
    output=tmp_path/'out'
    with pytest.raises(ValueError,match='budget'):
        benchmark.run(fixture(tmp_path),output,repeats=100,max_total_mb=1000)
    assert not output.exists()


def test_existing_destination_cannot_turn_into_a_resume_benchmark(tmp_path,monkeypatch):
    monkeypatch.setattr(benchmark.subprocess,'Popen',lambda *a,**k:pytest.fail('No launch'))
    output=tmp_path/'out';output.mkdir()
    with pytest.raises(ValueError,match='fresh'):
        benchmark.run(fixture(tmp_path),output)


def test_cli_requires_explicit_policy_acceptance_before_reading_inputs(tmp_path):
    result=subprocess.run([sys.executable,str(Path(benchmark.__file__)),
        '--cohort',str(tmp_path/'absent.json'),'--output',str(tmp_path/'out')],capture_output=True,text=True)
    assert result.returncode==2
    assert 'Explicit policy acceptance' in result.stderr
    assert not (tmp_path/'out').exists()


def test_embedded_colab_runner_and_cohort_match_maintained_sources():
    import ast
    import nbformat
    root=Path(__file__).resolve().parent
    n=nbformat.read(root/'TCIA_Downloader_Comparison.ipynb',as_version=4)
    nbformat.validate(n)
    setup=next(c.source for c in n.cells if c.cell_type=='code' and 'RUNNER_SOURCE =' in c.source)
    tree=ast.parse(setup)
    embedded={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body
              if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)
              and n.targets[0].id in {'RUNNER_SOURCE','COHORT'}}
    assert embedded['RUNNER_SOURCE']==(root/'benchmark_tcia_downloads.py').read_text()
    assert embedded['COHORT']==json.loads((root/'cmb-gec-cohort.json').read_text())
