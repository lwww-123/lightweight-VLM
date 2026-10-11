"""Regression evaluation of the v2 (pick / place_on / place_in / open / close)
action schema on the L1-L10 test set.

The expected plan for each case is parsed from the fine-grained "expected"
strings already in baseline_eval.TEST_SET, so no new ground truth is written.
Results go to schema_v2_results.json (or --out); existing result files and
baseline_results.json are never overwritten.

Usage (from repo root):
    python eval/schema_v2_eval.py [--runs N] [--out FILE.json]
"""

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_decomposer import TaskDecomposer  # noqa: E402
from baseline_eval import TEST_SET, norm, to_triples  # noqa: E402


def parse_expected(step):
    """'pick up ketchup' / 'place ketchup in drawer' / 'open drawer' -> triple."""
    words = step.split()
    if words[:2] == ["pick", "up"]:
        return ("pick", norm(" ".join(words[2:])), None)
    if words[0] == "place":
        for prep in ("in", "on"):
            if prep in words:
                i = words.index(prep)
                return (
                    f"place_{prep}",
                    norm(" ".join(words[1:i])),
                    norm(" ".join(words[i + 1:])),
                )
    if words[0] in ("open", "close"):
        return (words[0], None, norm(" ".join(words[1:])))
    raise ValueError(f"cannot parse expected step: {step!r}")


def run(num_runs, out_name):
    # Committed results are kept as a record; a rerun must name a new file.
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), out_name)
    if os.path.exists(out_path):
        raise SystemExit(
            f"Refusing to overwrite existing results: {out_path}\n"
            "Pass --out <new_file>.json for a new run."
        )

    decomposer = TaskDecomposer()

    captured = {}
    original_create = decomposer.client.chat.completions.create

    def recording_create(*args, **kwargs):
        response = original_create(*args, **kwargs)
        captured["raw"] = response.choices[0].message.content
        return response

    decomposer.client.chat.completions.create = recording_create

    records = []
    for run_idx in range(num_runs):
        for case in TEST_SET:
            captured.clear()
            expected = [parse_expected(s) for s in case["expected"]]
            record = {
                "run": run_idx + 1,
                "id": case["id"],
                "input": case["input"],
                "expected_fine": [list(t) for t in expected],
                "raw_output": None,
                "parsed_subtasks": None,
                "parse_error": None,
                "predicted_triples": None,
                "validation_errors": None,
                "instructions": None,
                "exact_match": False,
            }
            try:
                record["parsed_subtasks"] = decomposer.decompose(case["input"])
            except Exception as e:  # keep going; record the failure
                record["parse_error"] = f"{type(e).__name__}: {e}"
            record["raw_output"] = captured.get("raw")

            if record["parsed_subtasks"] is not None:
                subtasks = record["parsed_subtasks"]
                predicted = to_triples(subtasks)
                record["predicted_triples"] = [list(t) for t in predicted]
                record["validation_errors"] = decomposer.validate_plan(subtasks)
                record["exact_match"] = predicted == expected
                try:
                    record["instructions"] = [
                        decomposer.generate_instruction(s)
                        for s in sorted(subtasks, key=lambda s: s.get("order", 0))
                    ]
                except ValueError as e:
                    record["instructions"] = f"ValueError: {e}"

            records.append(record)

    out = {
        "model": decomposer.model,
        "temperature": 0,
        "runs": num_runs,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "system_prompt": decomposer.system_prompt,
        "results": records,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    for r in records:
        print(
            f"run{r['run']} {r['id']:>4}  exact_match={r['exact_match']}  "
            f"valid={r['validation_errors'] == []}  pred={r['predicted_triples']}"
        )
    passed = sum(r["exact_match"] for r in records)
    print(f"\nexact_match: {passed}/{len(records)}")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--out", default="schema_v2_results.json")
    args = parser.parse_args()
    run(args.runs, args.out)
