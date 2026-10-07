from task_decomposer import TaskDecomposer


decomposer = TaskDecomposer()


task = """
 Before closing the drawer, put the mug on the plate and the bowl in the basket.
"""


results = decomposer.process(task)


decomposer.save_json(
    results,
    "decomposed_task.json"
)