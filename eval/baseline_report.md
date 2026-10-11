# TaskDecomposer Baseline Evaluation (L1–L10)

> **Note (2026-10-11): `baseline_results.json` is a reconstructed baseline.**
> The original file was accidentally overwritten. It was rebuilt from the original
> run's console output: the per-case predictions, exact_match and judgments below are
> exact, and L6's raw output is verbatim, but the other nine raw outputs are
> re-serialized from the parsed subtasks and are not the original API response text.
> This report itself was written from the original run and is unchanged.
> For publication, rerun the frozen v1 prompt (git `a77bc11`) into a new file.

- Model: `qwen-plus`, temperature 0, 1 run per instruction
- `task_decomposer.py` and the system prompt were not modified
- Full record (input / raw Qwen output / parsed subtasks / judgments): `baseline_results.json`
- Script: `baseline_eval.py`

## How expected subtasks were compared

The expected subtasks were written at pick / place granularity, while TaskDecomposer's
action space merges pick and place into `pick_and_place_in/on` (prompt rule 2 and rule 5).
So the comparison maps each "pick X + place X in Y" pair to one `pick_and_place_in(X, Y)`
step and requires the sequence of (action_type, object, target) to match exactly.

Under this mapping, L6's expected "pick before open" order cannot be expressed: the merged
step has to come after `open drawer`. That is a limit of the action space, not a model error.

## Results

| ID | Input | Expected (merged) | Qwen output (parsed) | Judgment | Failure type |
|---|---|---|---|---|---|
| L1 | Pick up the ketchup and place it in the basket. | pnp_in(ketchup→basket) | pnp_in(ketchup→basket) | Correct | – |
| L2 | Grab the ketchup and put it in the basket. | pnp_in(ketchup→basket) | pnp_in(ketchup→basket) | Correct | – |
| L3 | After picking up the ketchup, place it in the basket. | pnp_in(ketchup→basket) | pnp_in(ketchup→basket) | Correct | – |
| L4 | Open the drawer and then place the ketchup inside. | open(drawer); pnp_in(ketchup→drawer) | open(drawer); pnp_in(ketchup→drawer) | Correct | – |
| L5 | Before placing the ketchup in the drawer, open the drawer. | open(drawer); pnp_in(ketchup→drawer) | open(drawer); pnp_in(ketchup→drawer) | Correct | – |
| L6 | Pick up the ketchup, open the drawer, place the ketchup inside, and close the drawer. | open(drawer); pnp_in(ketchup→drawer); close(drawer) | **pnp_in(ketchup→drawer)**; open(drawer); pnp_in(ketchup→drawer); close(drawer) | Partially correct | redundant subtask; wrong order |
| L7 | First open the drawer, then pick up the ketchup and place it inside before closing it. | open; pnp_in(ketchup→drawer); close | open; pnp_in(ketchup→drawer); close | Correct | – |
| L8 | Put the ketchup into the drawer only after the drawer has been opened. | open(drawer); pnp_in(ketchup→drawer) | open(drawer); pnp_in(ketchup→drawer) | Correct | – |
| L9 | After opening the drawer, pick up the ketchup; once it is inside, close the drawer. | open; pnp_in(ketchup→drawer); close | open; pnp_in(ketchup→drawer); close | Correct | – |
| L10 | Open the drawer, move the ketchup into it, close the drawer, then pick up the milk and place it in the basket. | open; pnp_in(ketchup→drawer); close; pnp_in(milk→basket) | open; pnp_in(ketchup→drawer); close; pnp_in(milk→basket) | Correct | – |

**Total: Correct 9 / Partially correct 1 / Wrong 0.** All 10 raw outputs were valid JSON with no Markdown fences.

### Failure type counts

| Failure type | Count |
|---|---|
| action not recognized | 0 |
| wrong order | 1 (L6) |
| missing subtask | 0 |
| wrong object/target | 0 |
| redundant subtask | 1 (L6) |
| coreference error | 0 |
| temporal relation error | 0 |
| multi-object composition error | 0 |

## Main failure pattern

**Interleaved pick and place (L6).** When another action (open drawer) separates "pick up X"
from "place X", the model creates a full `pick_and_place_in` for each clause: the "pick up
the ketchup" clause becomes `pick_and_place_in(ketchup, drawer)` with the target borrowed
from the later clause, and the "place it inside" clause becomes a second one. The result
has an extra step, and that step comes before `open drawer`, so it places into a closed
drawer. Removing step 1 leaves exactly the expected plan.

The cause is a tension in the prompt: rules 2/5 forbid splitting pick and place, while rule 4
says to keep the instruction's order. L6's order cannot be kept without splitting, and the
model resolves the conflict by duplicating the step. Every other case keeps pick and place
in the same clause or adjacent clauses, and all of those are correct.

## What worked

- Synonyms (grab / put / move … into) → L2, L10
- Reversed temporal phrasing ("Before …", "After …", "only after … has been opened") → L3, L5, L8, L9
- Coreference (it / inside / closing it) → L4, L7, L9, L10
- Implicit place ("once it is inside") → L9
- Two objects with mixed targets → L10

## Caveats

- 1 run per instruction at temperature 0. That shows typical behavior, not how stable it is.
- The set is small and uses one scene vocabulary (ketchup / drawer / basket / milk). Only L10
  has more than one object, so "no multi-object errors" is weak evidence.
- At merged granularity, the step-level difference in L6 (pick before open) is invisible.
  If the downstream policy needs to know where the robot is holding the object, the merged
  action space cannot represent it.
