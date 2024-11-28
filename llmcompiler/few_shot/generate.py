# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : Generate Few-Shot
@Time    : 2024-11-28 15:49:18
"""
from typing import List

from llmcompiler.graph.output_parser import Task


def generate_few_shot_text_from_tasks(query: str, tasks: List[Task]) -> str:
    """Generate a usable `few-shot` text using the provided TASKS list.
    class Task(TypedDict):
        idx: int
        tool: BaseTool
        args: Union[str, Dict]
        dependencies: List[int]
        thought: Optional[str]
    TEXT：
        <Question>
        @Doc1 Company R&D Personnel Information
        <Execution Plan>
        1. search(doc="@Doc1", query="Company R&D Personnel Information", type="section")
        2. join()
        <END_OF_PLAN>
    """
    # Initialize the final text with the problem statement and query
    text = f"<Question>\n{query}\n<Execution Plan>\n"

    # Iterate over the tasks and format them into the execution plan
    for task in tasks:
        # Construct the task line based on the task information
        task_line = f"{task['idx']}. "

        # Handle the tool part, checking if it's a string or dict
        if isinstance(task['tool'], str):
            task_line += f"{task['tool']}()"
        else:
            task_line += f"{task['tool'].name}({', '.join(f'{key}={value}' for key, value in task['args'].items())})"

        # Add the task line to the execution plan
        text += task_line + "\n"

    # End of the plan
    text += "<END_OF_PLAN>"

    return text
