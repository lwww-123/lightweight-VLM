"""Baseline evaluation of the current TaskDecomposer on the L1-L10 test set.

Does not modify task_decomposer.py or its system prompt. Each instruction is
run once. The raw Qwen output is captured by wrapping the client's create()
call on the instance, so it is recorded even when JSON parsing fails.

Usage (from repo root):
    python eval/baseline_eval.py
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_decomposer import TaskDecomposer  # noqa: E402


# Expected subtasks as originally written (pick / place granularity).
# "expected_merged" is the same plan expressed in TaskDecomposer's action
# space, where pick + place of the same object is one pick_and_place_* step.
TEST_SET = [
    {
        "id": "L1",
        "input": "Pick up the ketchup and place it in the basket.",
        "expected": ["pick up ketchup", "place ketchup in basket"],
        "expected_merged": [("pick_and_place_in", "ketchup", "basket")],
    },
    {
        "id": "L2",
        "input": "Grab the ketchup and put it in the basket.",
        "expected": ["pick up ketchup", "place ketchup in basket"],
        "expected_merged": [("pick_and_place_in", "ketchup", "basket")],
    },
    {
        "id": "L3",
        "input": "After picking up the ketchup, place it in the basket.",
        "expected": ["pick up ketchup", "place ketchup in basket"],
        "expected_merged": [("pick_and_place_in", "ketchup", "basket")],
    },
    {
        "id": "L4",
        "input": "Open the drawer and then place the ketchup inside.",
        "expected": ["open drawer", "pick up ketchup", "place ketchup in drawer"],
        "expected_merged": [
            ("open", None, "drawer"),
            ("pick_and_place_in", "ketchup", "drawer"),
        ],
    },
    {
        "id": "L5",
        "input": "Before placing the ketchup in the drawer, open the drawer.",
        "expected": ["open drawer", "pick up ketchup", "place ketchup in drawer"],
        "expected_merged": [
            ("open", None, "drawer"),
            ("pick_and_place_in", "ketchup", "drawer"),
        ],
    },
    {
        "id": "L6",
        "input": "Pick up the ketchup, open the drawer, place the ketchup inside, and close the drawer.",
        "expected": [
            "pick up ketchup",
            "open drawer",
            "place ketchup in drawer",
            "close drawer",
        ],
        # Pick-before-open cannot be expressed once pick and place are merged;
        # the place must follow the open, so the merged step goes after it.
        "expected_merged": [
            ("open", None, "drawer"),
            ("pick_and_place_in", "ketchup", "drawer"),
            ("close", None, "drawer"),
        ],
    },
    {
        "id": "L7",
        "input": "First open the drawer, then pick up the ketchup and place it inside before closing it.",
        "expected": [
            "open drawer",
            "pick up ketchup",
            "place ketchup in drawer",
            "close drawer",
        ],
        "expected_merged": [
            ("open", None, "drawer"),
            ("pick_and_place_in", "ketchup", "drawer"),
            ("close", None, "drawer"),
        ],
    },
    {
        "id": "L8",
        "input": "Put the ketchup into the drawer only after the drawer has been opened.",
        "expected": ["open drawer", "pick up ketchup", "place ketchup in drawer"],
        "expected_merged": [
            ("open", None, "drawer"),
            ("pick_and_place_in", "ketchup", "drawer"),
        ],
    },
    {
        "id": "L9",
        "input": "After opening the drawer, pick up the ketchup; once it is inside, close the drawer.",
        "expected": [
            "open drawer",
            "pick up ketchup",
            "place ketchup in drawer",
            "close drawer",
        ],
        "expected_merged": [
            ("open", None, "drawer"),
            ("pick_and_place_in", "ketchup", "drawer"),
            ("close", None, "drawer"),
        ],
    },
    {
        "id": "L10",
        "input": "Open the drawer, move the ketchup into it, close the drawer, then pick up the milk and place it in the basket.",
        "expected": [
            "open drawer",
            "pick up ketchup",
            "place ketchup in drawer",
            "close drawer",
            "pick up milk",
            "place milk in basket",
        ],
        "expected_merged": [
            ("open", None, "drawer"),
            ("pick_and_place_in", "ketchup", "drawer"),
            ("close", None, "drawer"),
            ("pick_and_place_in", "milk", "basket"),
        ],
    },
]


def norm(value):
    if value is None:
        return None
    value = str(value).strip().lower()
    if value in ("", "null", "none"):
        return None
    for prefix in ("the ", "a ", "an "):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value


def to_triples(subtasks):
    ordered = sorted(subtasks, key=lambda s: s.get("order", s.get("id", 0)))
    return [
        (norm(s.get("action_type")), norm(s.get("object")), norm(s.get("target")))
        for s in ordered
    ]


def run():
    # baseline_results.json is the frozen v1-schema baseline; the prompt has
    # since changed, so rerunning would silently replace it with v2 output.
    baseline_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baseline_results.json")
    if os.path.exists(baseline_path):
        raise SystemExit(
            f"Refusing to overwrite the frozen baseline: {baseline_path}\n"
            "Use eval/schema_v2_eval.py for the current schema."
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
    for case in TEST_SET:
        captured.clear()
        record = {
            "id": case["id"],
            "input": case["input"],
            "expected": case["expected"],
            "expected_merged": [list(t) for t in case["expected_merged"]],
            "raw_output": None,
            "parsed_subtasks": None,
            "parse_error": None,
        }
        try:
            record["parsed_subtasks"] = decomposer.decompose(case["input"])
        except Exception as e:  # keep going; record the failure
            record["parse_error"] = f"{type(e).__name__}: {e}"
        record["raw_output"] = captured.get("raw")

        if record["parsed_subtasks"] is not None:
            predicted = to_triples(record["parsed_subtasks"])
            record["predicted_triples"] = [list(t) for t in predicted]
            record["exact_match"] = predicted == [
                tuple(t) for t in case["expected_merged"]
            ]
        else:
            record["predicted_triples"] = None
            record["exact_match"] = False

        records.append(record)

    out = {
        "model": decomposer.model,
        "temperature": 0,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "system_prompt": decomposer.system_prompt,
        "results": records,
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baseline_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    for r in records:
        print(f"{r['id']:>4}  exact_match={r['exact_match']}  pred={r['predicted_triples']}")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    run()
