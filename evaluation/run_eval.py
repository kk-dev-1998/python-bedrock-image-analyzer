"""Run the image analysis evaluation against Amazon Bedrock.

Usage (from the repository root):
    python -m evaluation.run_eval
    python -m evaluation.run_eval --repeat 3

WARNING: this calls Bedrock for real, so it costs money.
Credentials and the model ID are read from .env / the environment, exactly like the app.
Results are written to evaluation/results/ (git-ignored).
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.bedrock import analyze_image
from evaluation.scoring import SCORED_FIELDS, score_case, summarize

BASE_DIR = Path(__file__).parent
FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}


def run_case(case: dict, base_dir: Path = BASE_DIR) -> dict:
    """Call analyze_image for one case and score the output."""
    expected = case["expected"]
    image_path = base_dir / case["image"]

    result = {
        "id": case["id"],
        "category": case["category"],
        "image": case["image"],
        "output": None,
        "model_used": None,
        "error": None,
    }

    started = time.perf_counter()
    try:
        response = analyze_image(
            image_path.read_bytes(), FORMATS[image_path.suffix.lower()]
        )
        result["output"] = response["analysis"].model_dump()
        result["model_used"] = response["model_used"]
    except Exception as e:  # one failure must not abort the whole run
        result["error"] = f"{type(e).__name__}: {e}"
    result["latency_sec"] = round(time.perf_counter() - started, 2)

    if result["error"]:
        # Count every expected field as wrong when there is no usable output.
        result["fields"] = {f: False for f in SCORED_FIELDS if f in expected}
    else:
        result["fields"] = score_case(result["output"], expected)
    return result


def print_summary(summary: dict, results: list[dict], cases: dict) -> None:
    total = summary["total"]
    rate = summary["passed"] / total if total else 0
    print(f"\ncase pass rate: {summary['passed']}/{total} ({rate:.0%})")
    print(f"errors (invalid output / API failure): {summary['errors']}")

    print("field accuracy:")
    for field, acc in summary["field_accuracy"].items():
        print(f"  {field:<14} {acc:.0%}")

    print("by category:")
    for category, c in summary["category_pass"].items():
        print(f"  {category:<20} {c['passed']}/{c['total']}")

    failures = [r for r in results if r["error"] or not all(r["fields"].values())]
    if failures:
        print("failures:")
    for r in failures:
        if r["error"]:
            print(f"  {r['id']}: {r['error']}")
            continue
        for field, ok in r["fields"].items():
            if not ok:
                expected = cases[r["id"]]["expected"][field]
                print(f"  {r['id']} {field}: expected {expected!r}, got {r['output'][field]!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cases", type=Path, default=BASE_DIR / "cases.json")
    parser.add_argument("--repeat", type=int, default=1, help="runs per case")
    parser.add_argument("--out", type=Path, default=BASE_DIR / "results")
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))["cases"]
    cases_by_id = {c["id"]: c for c in cases}

    runnable = []
    for case in cases:
        if (BASE_DIR / case["image"]).exists():
            runnable.append(case)
        else:
            print(f"skip {case['id']}: image not found ({case['image']})")

    results = []
    for case in runnable:
        for run in range(1, args.repeat + 1):
            result = run_case(case, BASE_DIR)
            result["run"] = run
            results.append(result)
            status = "ERROR" if result["error"] else (
                "ok" if all(result["fields"].values()) else "ng"
            )
            print(f"{case['id']} run {run}: {status} ({result['latency_sec']}s)")

    summary = summarize(results)
    print_summary(summary, results, cases_by_id)

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_file = args.out / f"{stamp}.json"
    out_file.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nsaved: {out_file}")


if __name__ == "__main__":
    main()
