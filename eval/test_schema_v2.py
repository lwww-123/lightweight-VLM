"""Offline regression tests for the v2 action schema (no API calls).

Covers validate_plan(), generate_instruction(), and a before/after check that
the recorded v2 plans do not regress any case the v1 baseline got right.

Usage (from repo root):
    python -m pytest eval/test_schema_v2.py
"""

import json
import os
import sys

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(EVAL_DIR))
sys.path.insert(0, EVAL_DIR)

import pytest  # noqa: E402

from task_decomposer import TaskDecomposer  # noqa: E402
from schema_v2_eval import parse_expected  # noqa: E402
from baseline_eval import TEST_SET  # noqa: E402

# validate_plan / generate_instruction do not use the API client.
decomposer = TaskDecomposer.__new__(TaskDecomposer)


def plan(*steps):
    return [
        {"id": i, "order": i, "action_type": a, "object": o, "target": t}
        for i, (a, o, t) in enumerate(steps, 1)
    ]


L6_PLAN = plan(
    ("pick", "ketchup", None),
    ("open", None, "drawer"),
    ("place_in", "ketchup", "drawer"),
    ("close", None, "drawer"),
)


def test_l6_interleaved_plan_is_valid():
    assert decomposer.validate_plan(L6_PLAN) == []


@pytest.mark.parametrize("case", TEST_SET, ids=lambda c: c["id"])
def test_expected_plans_are_valid(case):
    expected = [parse_expected(s) for s in case["expected"]]
    assert decomposer.validate_plan(plan(*expected)) == []


@pytest.mark.parametrize(
    "steps, message",
    [
        ([("place_in", "ketchup", "drawer"), ("open", None, "drawer")],
         "without picking it up first"),
        ([("pick", "a", None), ("pick", "b", None)], "while still holding a"),
        ([("pick", "a", None), ("place_on", "b", "plate")], "while holding a"),
        ([("pick", "a", None)], "plan ends while still holding a"),
        ([("close", None, "drawer"), ("pick", "k", None), ("place_in", "k", "drawer")],
         "after it was closed"),
        ([("pick_and_place_in", "k", "drawer")], "unknown action type"),
        ([("pick", "k", "basket"), ("place_in", "k", "basket")], "null target"),
        ([("open", "k", "drawer")], "null object"),
    ],
)
def test_invalid_plans_are_rejected(steps, message):
    errors = decomposer.validate_plan(plan(*steps))
    assert any(message in e for e in errors), errors


def test_order_must_be_sequential():
    steps = plan(("pick", "k", None), ("place_in", "k", "basket"))
    steps[1]["order"] = 3
    assert any("order must be" in e for e in decomposer.validate_plan(steps))


def test_generate_instruction_l6():
    assert [decomposer.generate_instruction(s) for s in L6_PLAN] == [
        "Pick up the ketchup.",
        "Open the drawer.",
        "Place the ketchup in the drawer.",
        "Close the drawer.",
    ]


def test_generate_instruction_place_on_and_legacy():
    gen = decomposer.generate_instruction
    assert gen(plan(("place_on", "mug", "plate"))[0]) == "Place the mug on the plate."
    assert gen(plan(("pick_and_place_in", "milk", "basket"))[0]) == \
        "Pick up the milk and place it in the basket."


def test_generate_instruction_rejects_missing_fields():
    with pytest.raises(ValueError):
        decomposer.generate_instruction(plan(("pick", None, None))[0])
    with pytest.raises(ValueError):
        decomposer.generate_instruction(plan(("place_in", "k", None))[0])


def merge_adjacent(triples):
    """Map a v2 plan to v1 terms: adjacent pick X + place_* X -> pick_and_place_*."""
    merged, i = [], 0
    while i < len(triples):
        a, o, t = triples[i]
        if (a == "pick" and i + 1 < len(triples)
                and triples[i + 1][0] in ("place_on", "place_in")
                and triples[i + 1][1] == o):
            merged.append(["pick_and_" + triples[i + 1][0], o, triples[i + 1][2]])
            i += 2
        else:
            merged.append([a, o, t])
            i += 1
    return merged


def load_results(name):
    with open(os.path.join(EVAL_DIR, name), encoding="utf-8") as f:
        return json.load(f)["results"]


def test_recorded_v2_results_match_and_validate():
    for r in load_results("schema_v2_results.json"):
        assert r["exact_match"], (r["run"], r["id"], r["predicted_triples"])
        assert r["validation_errors"] == [], (r["run"], r["id"])


def test_no_regression_against_v1_baseline():
    v1 = {r["id"]: r for r in load_results("baseline_results.json")}
    for r in load_results("schema_v2_results.json"):
        old = v1[r["id"]]
        if old["exact_match"]:
            assert merge_adjacent(r["predicted_triples"]) == old["predicted_triples"], r["id"]
