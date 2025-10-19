"""Tests for the generate_stage_artifacts helper utilities."""

from importlib import util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "python" / "generate_stage_artifacts.py"
SPEC = util.spec_from_file_location("generate_stage_artifacts", MODULE_PATH)
assert SPEC and SPEC.loader  # narrow type for mypy/pyright
gsa = util.module_from_spec(SPEC)
SPEC.loader.exec_module(gsa)  # type: ignore[assignment]


def test_cluster_metrics_preserves_value_order() -> None:
    cluster = {
        "id": "cluster-1",
        "label": "Emotional Connection",
        "core_emotion": "Hope",
        "conversion_potential": "High",
        "product_compatibility": "Great fit",
        "notes": "",
        "keywords": [
            {
                "term": "keyword a",
                "volume": 100,
                "difficulty": 10,
                "ctr_estimate": 0.1,
                "pinterest_angle": "First angle",
                "meta_hook": "Hook one",
                "emotional_driver": "Hope",
            },
            {
                "term": "keyword b",
                "volume": 80,
                "difficulty": 20,
                "ctr_estimate": 0.15,
                "pinterest_angle": "Second angle",
                "meta_hook": "Hook two",
                "emotional_driver": "Trust",
            },
            {
                "term": "keyword c",
                "volume": 60,
                "difficulty": 30,
                "ctr_estimate": 0.12,
                "pinterest_angle": "First angle",
                "meta_hook": "Hook one",
                "emotional_driver": "Joy",
            },
        ],
    }

    metrics = gsa.cluster_metrics(cluster)

    assert metrics["pinterest_angles"] == ["First angle", "Second angle"]
    assert metrics["meta_hooks"] == ["Hook one", "Hook two"]
    assert metrics["emotional_drivers"] == ["Hope", "Trust", "Joy"]
