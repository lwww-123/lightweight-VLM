from task_decomposer import TaskDecomposer


decomposer = TaskDecomposer()


task = """
Put the mug somewhere appropriate and close the drawer.
"""


results = decomposer.process(task)


decomposer.save_json(
    results,
    "decomposed_task.json"
)