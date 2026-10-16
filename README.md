# Language Task Decomposition for TurboVLA

## Overview

This project implements a language task decomposition module designed to provide
TurboVLA with simpler and more executable manipulation instructions.

The motivation is that high-level instructions can contain multiple manipulation
goals and linguistic relationships that are difficult to execute directly.
Instead of sending the original complex instruction to TurboVLA, an LLM is used
to decompose it into a sequence of simpler subtasks.

The overall pipeline is:
```
High-level instruction
        ↓
LLM-based task decomposition
        ↓
Structured subtasks
        ↓
TurboVLA execution
```

## 1. Defining the Decomposition Granularity

A key question is **how fine-grained** the decomposition should be.

If the task is decomposed too finely, the result may become unnecessarily
fragmented. If it is too coarse, the resulting instruction may still require TurboVLA to
perform additional semantic decomposition.

For this reason, we referred to the language structure used by the **LIBERO benchmark**,
particularly ```online_text_layout.json```, to determine a suitable level of
granularity.

Examples from the LIBERO instructions include:
```
put the yellow and white mug in the microwave and close it
put both the alphabet soup and the tomato sauce in the basket
put the bowl on the plate
open the middle drawer of the cabinet
pick up the black bowl between the plate and the ramekin and place it on the plate
```

These examples suggest that a suitable subtask should correspond to a complete
manipulation goal rather than an individual low-level motion.

For example: `Pick up the mug + place it on the plate` is treated as one subtask, rather than separating "pick up" and "place".

Therefore, we first designed the decomposition module to use a small set of manipulation-level
operations:
- pick_and_place_on
- pick_and_place_in
- open
- close

## 2. Task Decomposition
The module uses an LLM to transform a high-level instruction into structured subtasks.

Now we try **Qwen_Plus** API
```bash
export DASHSCOPE_API_KEY="API_KEY"
```
The final output is stored as a JSON file:
```decomposed_task.json```

with the following structure:
```JSON
{
    "original_task": "...",
    "subtasks": [
        {
            "id": 1,
            "order": 1,
            "action_type": "...",
            "object": "...",
            "target": "...",
            "instruction": "..."
        }
    ]
}
```

## 3. Prompt Design
The decomposition prompt is designed around six main requirements:
### 1. Identifying and analysing parallel structures​
such as ```and```
### 2. Synonymous expressions​
such as ```move → pick and place ```, ```close → shut```
### 3. Referential relationships​
such as  ```it```,```these```
### 4. Temporal reasoning
Temporal expressions such as:
```text
before
after
once
until
only after
finally
```
are interpreted as relationships between executable subtasks.

For example:
```
Before closing the drawer, put the mug on the plate.
```
should produce:
```
1. Pick up the mug and place it on the plate.
2. Close the drawer.
`````
### 5. Subordinate clauses and non-verbal constructions​
such as ```placing```,```is closed```

### 6. Distinguishing between general, abstract statements and actual actions
such as `organize the desk` are not treated as executable actions themselves.

## 4. Evaluation

To evaluate the ability of the module to handle increasingly complex language,
10 instructions were manually designed. The examples were based on the same manipulation vocabulary while introducing
different forms of linguistic complexity.

The baseline sentence is:

`
Organize the desk by putting the mug on the plate, placing the bowl in the basket, and closing the drawer.
`

With the output format saved as a JSON file:

```Json
{
    "subtasks": [
        {
            "id": 1,
            "order": 1,
            "action_type": "pick_and_place_on",
            "object": "mug",
            "target": "plate",
            "instruction": "Pick up the mug and place it on the plate."
        },
        {
            "id": 2,
            "order": 2,
            "action_type": "pick_and_place_in",
            "object": "bowl",
            "target": "basket",
            "instruction": "Pick up the bowl and place it in the basket."
        },
        {
            "id": 3,
            "order": 3,
            "action_type": "close",
            "object": null,
            "target": "drawer",
            "instruction": "Close the drawer."
        }
    ]
}
```

The module correctly decomposed all 10 test instructions, achieving a 100% success rate.












