import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_release_is_438():
    data=json.loads((ROOT/'release.json').read_text(encoding='utf-8'))
    assert data['release']=='4.46.0'

def test_benchmark_script_is_present_and_dependency_free():
    text=(ROOT/'scripts/benchmark_suite.py').read_text(encoding='utf-8')
    assert 'ThreadPoolExecutor' in text
    assert 'benchmark_report.json' in text
