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

1. Each subtask must represent one complete manipulation goal.
2. Combine picking up and placing an object into one subtask.
3. Separate operations involving different objects or targets.
4. Preserve the logical order of the original instruction.
5. Do not split "pick up" and "place" into separate subtasks.
6. Do not invent objects, targets, or actions.
7. Return only valid JSON.

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