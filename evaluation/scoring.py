"""Scoring helpers for the image analysis evaluation.

Pure functions only (no AWS calls), so they can be unit-tested without Bedrock.
"""

import re
import unicodedata
from collections import defaultdict

# Fields that are compared against the expected values.
# "detail" is free text, so it is only checked by the app's schema (<= 50 chars).
SCORED_FIELDS = ("name_of_item", "brand", "color", "serial_number")

NA = "na"


def normalize(value: str) -> str:
    """Lowercase, NFKC-normalize and collapse whitespace."""
    text = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"\s+", " ", text).strip().lower()


def _compact(value: str) -> str:
    """Drop spaces, hyphens and underscores (for serial / model numbers)."""
    return re.sub(r"[\s\-_]", "", normalize(value))


def _matches_any(actual: str, accepted: list[str]) -> bool:
    """True if any accepted term appears in the output.

    "NA" is a special case: it must match the whole output, otherwise
    "na" would match words such as "banana".
    """
    actual = normalize(actual)
    for term in accepted:
        term = normalize(term)
        if term == NA:
            if actual == NA:
                return True
        elif term in actual:
            return True
    return False


def score_field(field: str, actual: str, expected) -> bool:
    """Compare one output field with its expected value.

    expected is a string, or a list of accepted strings for name_of_item / color.
    """
    accepted = [expected] if isinstance(expected, str) else list(expected)

    if field in ("name_of_item", "color", "brand"):
        return _matches_any(actual, accepted)

    if field == "serial_number":
        return any(
            normalize(actual) == NA
            if normalize(term) == NA
            else _compact(actual) == _compact(term)
            for term in accepted
        )

    raise ValueError(f"unknown field: {field}")


def score_case(analysis: dict, expected: dict) -> dict[str, bool]:
    """Score every field that has an expected value. Missing fields are not scored."""
    return {
        field: score_field(field, analysis.get(field, ""), expected[field])
        for field in SCORED_FIELDS
        if field in expected
    }


def summarize(case_results: list[dict]) -> dict:
    """Aggregate per-case results.

    Each item needs: category, error (None or message), fields ({field: bool}).
    A case passes only if it had no error and every scored field is correct.
    """
    total = len(case_results)
    errors = sum(1 for r in case_results if r["error"])
    passed = sum(
        1 for r in case_results if not r["error"] and all(r["fields"].values())
    )

    field_hits: dict[str, int] = defaultdict(int)
    field_total: dict[str, int] = defaultdict(int)
    category_hits: dict[str, int] = defaultdict(int)
    category_total: dict[str, int] = defaultdict(int)

    for r in case_results:
        category_total[r["category"]] += 1
        if not r["error"] and all(r["fields"].values()):
            category_hits[r["category"]] += 1
        for field, ok in r["fields"].items():
            field_total[field] += 1
            field_hits[field] += int(ok)

    return {
        "total": total,
        "passed": passed,
        "errors": errors,
        "field_accuracy": {f: field_hits[f] / field_total[f] for f in field_total},
        "category_pass": {
            c: {"passed": category_hits[c], "total": category_total[c]}
            for c in category_total
        },
    }
