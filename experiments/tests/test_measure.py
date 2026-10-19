import json
import pytest
from experiments.tools.measure import memory_bytes, p95, summarize


def test_e05_p95_nearest_rank():
    assert p95([1,5,3]) == 5


@pytest.mark.parametrize("values", [[],[1,2],[1,2,3,4],[1,0,3],[1,float("nan"),3]])
def test_e05_rejects_invalid_samples(values):
    with pytest.raises(ValueError): p95(values)


@pytest.mark.parametrize("value,expected", [("2MiB",2097152),("1GB",1e9),("12.5MB",12500000)])
def test_e04_memory_units(value,expected):
    assert memory_bytes(value) == expected


def test_e04_e05_summary_and_busy_gate(tmp_path):
    path=tmp_path/"synthetic.json"
    raw={"trials":[{"seconds":v,"generation_started":True,"generation_overlap":True} for v in [1,2,5]],
         "memory":[{"phase":"idle","provider_bytes":999999999},{"phase":"login","provider_bytes":900000000}]}
    path.write_text(json.dumps(raw)); result=summarize(path)
    assert result["e04"] == result["e05"] == "PASS"
    raw["memory"][0]["provider_bytes"]=1000000000
    raw["trials"][0]["seconds"]=5.01
    path.write_text(json.dumps(raw)); result=summarize(path)
    assert result["e04"] == result["e05"] == "FAIL"
    raw["trials"][1]["generation_overlap"]=False
    path.write_text(json.dumps(raw)); assert summarize(path)["e05"] == "NAO_TESTADO"
