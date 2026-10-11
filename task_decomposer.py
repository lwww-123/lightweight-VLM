import json
import os
from openai import OpenAI


class TaskDecomposer:

    def __init__(self):

        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        self.model = "qwen-plus"

        self.system_prompt = """
You are a task decomposition module for a robot manipulation system.

Your task is to decompose a high-level manipulation instruction
into a sequence of executable manipulation subtasks.

The robot has a single gripper and can hold at most one object at a time.

Only use the following five action types:

1. pick
   Pick up an object and keep holding it.
   object: the object. target: null.

2. place_on
   Place the object currently held on a target surface.
   object: the held object. target: the surface.

3. place_in
   Place the object currently held inside a container.
   object: the held object. target: the container.

4. open
   Open a container or appliance.
   object: null. target: the container or appliance.

5. close
   Close a container or appliance.
   object: null. target: the container or appliance.

Rules:

1. Output subtasks in the order they are physically executed.
   Resolve temporal words such as "before", "after", "once", "then"
   and "only after" into the real execution order. When the instruction
   already lists actions in execution order, keep that order exactly.
2. Picking up and placing an object are separate subtasks. Never merge them.
3. Verbs such as "put", "move" or "place X into Y" mean pick followed by
   place_on or place_in.
4. Every place_on / place_in must come after a pick of the same object,
   with no other pick in between. If the instruction places an object
   without mentioning picking it up, insert the pick immediately before
   that place.
5. Do not pick a second object while still holding one, and do not leave
   an object in the gripper at the end of the plan.
6. Resolve words such as "it", "inside" and "there" to the concrete
   object or target name.
7. Do not invent objects or targets, and do not add actions that the
   instruction does not require. The implicit pick in rule 4 is required.
8. Return only valid JSON.

Example:

Instruction: Pick up the bowl, open the cabinet, put the bowl inside, and close the cabinet.

{
    "subtasks": [
        {"id": 1, "action_type": "pick", "object": "bowl", "target": null, "order": 1},
        {"id": 2, "action_type": "open", "object": null, "target": "cabinet", "order": 2},
        {"id": 3, "action_type": "place_in", "object": "bowl", "target": "cabinet", "order": 3},
        {"id": 4, "action_type": "close", "object": null, "target": "cabinet", "order": 4}
    ]
}
"""

    def decompose(self, task_instruction):

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": task_instruction
                }
            ],
            temperature=0
        )

        result = response.choices[0].message.content

        print("\nRaw Qwen output:")
        print(result)

        # Remove Markdown code fences if the model adds them
        result = result.strip()

        if result.startswith("```json"):
            result = result[7:]

        elif result.startswith("```"):
            result = result[3:]

        if result.endswith("```"):
            result = result[:-3]

        result = result.strip()

        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            raise ValueError(
                "Qwen did not return valid JSON:\n" + result
            )

        return parsed["subtasks"]

    def generate_instruction(self, subtask):

        action = subtask["action_type"]
        obj = subtask["object"]
        target = subtask["target"]

        if action in ("pick", "place_on", "place_in") and obj is None:
            raise ValueError(f"{action} requires an object: {subtask}")

        if action in ("place_on", "place_in", "open", "close") and target is None:
            raise ValueError(f"{action} requires a target: {subtask}")

        if action == "pick":
            return f"Pick up the {obj}."

        elif action == "place_on":
            return f"Place the {obj} on the {target}."

        elif action == "place_in":
            return f"Place the {obj} in the {target}."

        # Legacy v1 action types, kept so older decomposed JSON files
        # can still be turned into instructions.
        elif action == "pick_and_place_on":
            return f"Pick up the {obj} and place it on the {target}."

        elif action == "pick_and_place_in":
            return f"Pick up the {obj} and place it in the {target}."

        elif action == "open":
            return f"Open the {target}."

        elif action == "close":
            return f"Close the {target}."

        else:
            raise ValueError(
                f"Unknown action type: {action}"
            )

    def validate_plan(self, subtasks):
        """Check a v2 plan against the single-gripper state rules.

        Returns a list of error strings; an empty list means the plan is valid.
        Whether a container starts open is unknown, so place_in is only
        rejected when the plan itself closed the target and did not reopen it.
        """

        errors = []
        valid_actions = ("pick", "place_on", "place_in", "open", "close")

        orders = [s.get("order") for s in subtasks]
        if orders != list(range(1, len(subtasks) + 1)):
            errors.append(f"order must be 1..{len(subtasks)} in sequence, got {orders}")

        held = None
        last_state = {}

        for subtask in sorted(subtasks, key=lambda s: s.get("order", 0)):

            step = subtask.get("order")
            action = subtask.get("action_type")
            obj = subtask.get("object")
            target = subtask.get("target")

            if action not in valid_actions:
                errors.append(f"step {step}: unknown action type {action!r}")
                continue

            if action == "pick":
                if obj is None or target is not None:
                    errors.append(f"step {step}: pick needs an object and a null target")
                if held is not None:
                    errors.append(f"step {step}: pick {obj} while still holding {held}")
                held = obj

            elif action in ("place_on", "place_in"):
                if obj is None or target is None:
                    errors.append(f"step {step}: {action} needs an object and a target")
                if held is None:
                    errors.append(f"step {step}: {action} {obj} without picking it up first")
                elif held != obj:
                    errors.append(f"step {step}: {action} {obj} while holding {held}")
                if action == "place_in" and last_state.get(target) == "close":
                    errors.append(f"step {step}: place_in {target} after it was closed")
                held = None

            else:
                if obj is not None or target is None:
                    errors.append(f"step {step}: {action} needs a null object and a target")
                last_state[target] = action

        if held is not None:
            errors.append(f"plan ends while still holding {held}")

        return errors

    def process(self, task_instruction):

        subtasks = self.decompose(task_instruction)

        errors = self.validate_plan(subtasks)
        if errors:
            raise ValueError(
                "Invalid plan:\n" + "\n".join(errors)
            )

        output = {
            "original_task": task_instruction,
            "subtasks": []
        }

        for subtask in subtasks:

            instruction = self.generate_instruction(subtask)

            output["subtasks"].append({
                "id": subtask["id"],
                "order": subtask["order"],
                "action_type": subtask["action_type"],
                "object": subtask["object"],
                "target": subtask["target"],
                "instruction": instruction
            })

        return output

    def save_json(self, data, filename="decomposed_task.json"):

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        print(f"\nJSON file saved to: {filename}")