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
into a sequence of complete and executable manipulation subtasks.

Only use the following four action types:

1. pick_and_place_on
   Pick up an object and place it on a target surface.

2. pick_and_place_in
   Pick up an object and place it inside a container.

3. open
   Open a container or appliance.

4. close
   Close a container or appliance.

Rules:
1.Please identify all actions before generating the output. First, identify every manipulation action explicitly stated or clearly implied by the instruction.
Inspect the entire sentence, including:

1. Main clauses and coordinated clauses.

2. Subordinate clauses, including temporal clauses.

3. Non-finite verb phrases, including gerunds and infinitives.

4. Actions appearing before or after words such as before, after, then, until, and while.

Do not ignore an action because it appears in a subordinate clause or is expressed using an -ing/-ed form.

2. Preserve all required actions

Every identified manipulation action must be represented in the output.Do not omit an action because it describes a temporal condition, appears at the beginning or end of a sentence, or is not part of the main clause. Do not add actions that are not supported by the instruction.

3. Convert actions into complete subtasks

Combine picking up an object and placing it at its destination into one subtask. Use pick_and_place_on for placement on a surface. Use pick_and_place_in for placement inside a container. Represent opening and closing as separate subtasks. Each subtask must represent one complete manipulation goal.

4. Preserve temporal constraints

Interpret temporal expressions as execution constraints:

1. Before X, do A and B: Complete A and B before executing X.

2. After X, do A and B: Execute X before A and B.

3. Then: Execute the indicated action after the preceding action.

4. Until/Once X: Do not treat X as completed before its required condition is satisfied.

When multiple actions are connected by and without an explicit ordering constraint, preserve their original textual order in the output.

5. Validate completeness and ordering

Before returning the result, check internally that:

1. Every identified action appears exactly once in the output.

2. No required action has been omitted.

3. No unsupported action has been added.

4. All object and target references are correct.

5. All temporal constraints are satisfied.

6. Every action type belongs to the allowed list.

If an instruction cannot be fully represented using the allowed action types, do not silently invent a substitute action.

6. If the instruction cannot be fully represented using the allowed action types, return an error message indicating that the instruction is unsupported.







Output format:

{
    "subtasks": [
        {
            "id": 1,
            "action_type": "pick_and_place_on",
            "object": "mug",
            "target": "plate",
            "order": 1
        }
    ]
}

For open and close actions, use the target field
and set object to null.
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

        if action == "pick_and_place_on":
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

    def process(self, task_instruction):

        subtasks = self.decompose(task_instruction)

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