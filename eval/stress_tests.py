"""Unseen stress tests for the v2 action schema.

Objects, containers and sentence structures are chosen to differ from
L1-L10 and from the few-shot example in the system prompt. Expected plans
use the same string format as baseline_eval.TEST_SET and follow the prompt
rules: real execution order, implicit pick before place, no added actions.
"""

STRESS_SET = [
    # Different objects / containers, no temporal words.
    {
        "id": "S1",
        "category": "new object/container",
        "input": "Put the apple in the bowl.",
        "expected": ["pick up apple", "place apple in bowl"],
    },
    {
        "id": "S2",
        "category": "new object/container",
        "input": "Place the mug on the stove.",
        "expected": ["pick up mug", "place mug on stove"],
    },
    # before / after / once, including order reversal.
    {
        "id": "S3",
        "category": "temporal",
        "input": "After opening the microwave, put the mug inside.",
        "expected": ["open microwave", "pick up mug", "place mug in microwave"],
    },
    {
        "id": "S4",
        "category": "temporal",
        "input": "Before putting the cream cheese in the basket, put the bowl on the plate.",
        "expected": [
            "pick up bowl",
            "place bowl on plate",
            "pick up cream cheese",
            "place cream cheese in basket",
        ],
    },
    {
        "id": "S5",
        "category": "temporal",
        "input": "Put the mug on the table after you put the bowl in the sink.",
        "expected": [
            "pick up bowl",
            "place bowl in sink",
            "pick up mug",
            "place mug on table",
        ],
    },
    {
        "id": "S6",
        "category": "temporal",
        "input": "Close the cabinet only after you have put the spoon on the shelf.",
        "expected": ["pick up spoon", "place spoon on shelf", "close cabinet"],
    },
    {
        "id": "S7",
        "category": "temporal",
        "input": "Once you have closed the microwave, pick up the plate and put it in the basket.",
        "expected": ["close microwave", "pick up plate", "place plate in basket"],
    },
    {
        "id": "S8",
        "category": "temporal",
        "input": "Open the cabinet; once it is open, move the spoon into it, then close it.",
        "expected": [
            "open cabinet",
            "pick up spoon",
            "place spoon in cabinet",
            "close cabinet",
        ],
    },
    # Another action between pick and place.
    {
        "id": "S9",
        "category": "interleaved",
        "input": "Pick up the mug, open the microwave, and put the mug in the microwave.",
        "expected": ["pick up mug", "open microwave", "place mug in microwave"],
    },
    {
        "id": "S10",
        "category": "interleaved",
        "input": "Grab the apple, close the fridge, then set the apple on the plate.",
        "expected": ["pick up apple", "close fridge", "place apple on plate"],
    },
    {
        "id": "S11",
        "category": "interleaved",
        "input": "Pick up the yogurt; before you put it in the fridge, open the fridge.",
        "expected": ["pick up yogurt", "open fridge", "place yogurt in fridge"],
    },
    {
        "id": "S12",
        "category": "interleaved",
        "input": "Pick up the book, open the box, put the book inside, close the box, "
                 "and then put the cup on the shelf.",
        "expected": [
            "pick up book",
            "open box",
            "place book in box",
            "close box",
            "pick up cup",
            "place cup on shelf",
        ],
    },
]
