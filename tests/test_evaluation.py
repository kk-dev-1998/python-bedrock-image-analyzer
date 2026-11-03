import io
import json
from unittest.mock import MagicMock

from PIL import Image

from evaluation import run_eval
from evaluation.scoring import score_case, score_field, summarize


def test_name_matches_any_accepted_word():
    assert score_field("name_of_item", "Laptop computer", ["laptop", "notebook"])
    assert not score_field("name_of_item", "Phone", ["laptop", "notebook"])


def test_na_must_match_whole_value():
    # "na" is a substring of "banana" but must not count as NA
    assert not score_field("name_of_item", "Banana", ["NA"])
    assert score_field("name_of_item", "NA", ["NA"])


def test_brand_expected_na_rejects_hallucinated_brand():
    assert score_field("brand", "NA", "NA")
    assert not score_field("brand", "Sony", "NA")


def test_brand_is_case_insensitive_and_partial():
    assert score_field("brand", "Apple Inc.", "Apple")


def test_serial_number_ignores_spaces_and_hyphens():
    assert score_field("serial_number", "A-2345 6", "A23456")
    assert not score_field("serial_number", "NA", "A23456")


def test_missing_expected_field_is_not_scored():
    result = score_case({"name_of_item": "Key", "color": "Silver"}, {"name_of_item": ["key"]})
    assert result == {"name_of_item": True}


def test_summarize_counts_errors_and_categories():
    results = [
        {"category": "a", "error": None, "fields": {"brand": True, "color": True}},
        {"category": "a", "error": None, "fields": {"brand": False, "color": True}},
        {"category": "b", "error": "ValueError: bad json", "fields": {"brand": False, "color": False}},
    ]
    summary = summarize(results)
    assert summary["total"] == 3
    assert summary["passed"] == 1
    assert summary["errors"] == 1
    assert summary["field_accuracy"]["color"] == 2 / 3
    assert summary["category_pass"]["a"] == {"passed": 1, "total": 2}


def test_run_case_scores_output_without_calling_bedrock(tmp_path, monkeypatch):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="JPEG")
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "x.jpg").write_bytes(buffer.getvalue())

    analysis = MagicMock()
    analysis.model_dump.return_value = {
        "name_of_item": "Mug", "brand": "NA", "color": "White",
        "serial_number": "NA", "detail": "NA",
    }
    monkeypatch.setattr(
        run_eval, "analyze_image",
        lambda data, fmt: {"success": True, "analysis": analysis, "model_used": "test-model"},
    )

    case = {
        "id": "c1", "category": "no_logo", "image": "images/x.jpg",
        "expected": {"name_of_item": ["mug"], "brand": "NA", "color": ["white"]},
    }
    result = run_eval.run_case(case, base_dir=tmp_path)

    assert result["error"] is None
    assert all(result["fields"].values())


def test_run_case_records_error_and_continues(tmp_path, monkeypatch):
    (tmp_path / "x.jpg").write_bytes(b"dummy")

    def boom(data, fmt):
        raise ValueError("Bedrock returned invalid JSON")

    monkeypatch.setattr(run_eval, "analyze_image", boom)
    case = {"id": "c1", "category": "x", "image": "x.jpg", "expected": {"brand": "NA"}}
    result = run_eval.run_case(case, base_dir=tmp_path)

    assert "invalid JSON" in result["error"]
    assert result["fields"] == {"brand": False}


def test_cases_template_is_valid_json():
    path = run_eval.BASE_DIR / "cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))
    assert all({"id", "category", "image", "expected"} <= set(c) for c in cases)
