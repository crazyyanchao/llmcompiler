# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import ast
import re
import logging
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers.transform import BaseTransformOutputParser
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from typing_extensions import TypedDict

from llmcompiler.service.status import init_base_call_tools

THOUGHT_PATTERN = r"Thought: ([^\n]*)"
ACTION_PATTERN = r"\n*(\d+)\. (\w+)\((.*)\)(\s*#\w+\n)?"
# $1 or ${1} -> 1
ID_PATTERN = r"\$\{?(\d+)\}?"
ID_PATTERN_V2 = r"\$\{(\d+)\}|\{(\d+)\}|\$(\d+)"
END_OF_PLAN = "<END_OF_PLAN>"


### Helper functions


def _ast_parse(arg: str) -> Any:
    try:
        return ast.literal_eval(arg)
    except:  # noqa
        return arg


def _parse_llm_compiler_action_args(args: str, tool: Union[str, BaseTool]) -> Union[str, Dict, Tuple]:
    """Parse arguments from a string."""
    if args == "":
        return ()
    if isinstance(tool, str):
        return ()
    extracted_args = {}
    tool_key = None
    prev_idx = None
    sort_keys = _sort_keys(args, list(tool.args.keys()))
    for key in sort_keys:
        # Split if present
        if f"{key}=" in args:
            idx = args.index(f"{key}=")
            if prev_idx is not None:
                extracted_args[tool_key] = _ast_parse(
                    args[prev_idx:idx].strip().rstrip(",")
                )
            args = args.split(f"{key}=", 1)[1]
            tool_key = key
            prev_idx = 0
    if prev_idx is not None:
        extracted_args[tool_key] = _ast_parse(
            args[prev_idx:].strip().rstrip(",").rstrip(")")
        )
    return extracted_args


def _sort_keys(text: str, keys: List[str]) -> List[str]:
    """按照KEY包含的顺序排序KEYS"""

    def sort_key(key):
        try:
            return text.index(key)
        except ValueError:
            return float('inf')

    sorted_keys_v1 = sorted(keys, key=sort_key)
    sorted_keys_v2 = _custom_sort(sorted_keys_v1)
    return sorted_keys_v2


def _custom_sort(fields):
    """根据字段被包含关系对列表进行排序"""
    sorted_fields = []
    while fields:
        for field in fields:
            if all(not _filed_contains(other, field) for other in fields if other != field):
                sorted_fields.append(field)
                fields.remove(field)
                break
    return sorted_fields


def _filed_contains(a, b):
    return b in a


def default_dependency_rule(idx, args: str):
    """支持`${1}`中数字抽取"""
    matches = re.findall(ID_PATTERN, args)
    numbers = [int(match) for match in matches]
    return idx in numbers


def default_dependency_rule_v2(idx, args: str):
    """支持`$1` OR `${1}`中数字抽取"""
    matches = re.findall(ID_PATTERN_V2, args)
    numbers = [int(num) for match in matches for num in match if num]
    return idx in numbers


def _get_dependencies_from_graph(
        idx: int, tool_name: str, args: Dict[str, Any]
) -> list[int]:
    """Get dependencies from a graph."""
    if tool_name == "join":
        return list(range(1, idx))
    return [i for i in range(1, idx) if default_dependency_rule(i, str(args))]


class Task(TypedDict):
    idx: int
    tool: BaseTool
    args: Union[str, Dict]
    dependencies: List[int]
    thought: Optional[str]


def instantiate_task(
        tools: Sequence[BaseTool],
        idx: int,
        tool_name: str,
        args: Union[str, Any],
        thought: Optional[str] = None,
) -> Task:
    tool = None
    if tool_name == "join":
        tool = "join"
    else:
        try:
            tool = tools[[tool.name for tool in tools].index(tool_name)]
        except ValueError:
            logging.error(f"Tool <{tool_name}> not found.")
            # raise OutputParserException(f"Tool {tool_name} not found.") from e
    if tool is not None:
        tool_args = _parse_llm_compiler_action_args(args, tool)
        dependencies = _get_dependencies_from_graph(idx, tool_name, tool_args)
        task = Task(
            idx=idx,
            tool=tool,
            args=tool_args,
            dependencies=dependencies,
            thought=thought,
        )
        return task


class LLMCompilerPlanParser(BaseTransformOutputParser[dict], extra="allow"):
    """Planning output parser."""

    tools: List[BaseTool]
    # 任务编号初始值
    task_num: int = 0

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def _transform(self, input: Iterator[Union[str, BaseMessage]]) -> Iterator[Task]:
        texts = []
        # TODO: Cleanup tuple state tracking here.
        thought = None
        print("================================ Planer Compiler ================================")
        for chunk in input:
            # Assume input is str. TODO: support vision/other formats
            text = chunk if isinstance(chunk, str) else str(chunk.content)
            base_call_tools = init_base_call_tools(text=text, tools=self.tools)
            if base_call_tools.count() > 0:
                # 流式输出时不打印该日志
                print(','.join([tb.tool_name for tb in base_call_tools.call_status]))
            for task, thought in self.ingest_token(text, texts, thought):
                yield task
        # Final possible task
        if texts:
            task, _ = self._parse_task("".join(texts), thought)
            if task:
                yield task

    def parse(self, text: str) -> List[Task]:
        tasks = list(self._transform([text]))
        return tasks

    def stream(
            self,
            input: Union[str, BaseMessage],
            config: Optional[RunnableConfig] = None,
            **kwargs: Optional[Any],
    ) -> Iterator[Task]:
        yield from self.transform([input], config, **kwargs)

    def ingest_token(
            self, token: str, buffer: List[str], thought: Optional[str]
    ) -> Iterator[Tuple[Optional[Task], str]]:
        buffer.append(token)
        if "\n" in token:
            buffer_ = "".join(buffer).split("\n")
            suffix = buffer_[-1]
            for line in buffer_[:-1]:
                task, thought = self._parse_task(line, thought)
                if task:
                    yield task, thought
            self._init_task_num()
            buffer.clear()
            buffer.append(suffix)

    def _task_num(self) -> int:
        """
        获取TASK编号，累加后返回【任务编号使用要与参数替换`$*`结合起来】
        """
        self.task_num += 1
        return self.task_num

    def _init_task_num(self):
        """
        初始化任务编号
        """
        self.task_num = 0

    def _parse_task(self, line: str, thought: Optional[str] = None):
        task = None
        line = line.strip()
        if match := re.match(THOUGHT_PATTERN, line):
            # Optionally, action can be preceded by a thought
            thought = match.group(1)
        elif match := re.match(ACTION_PATTERN, line):
            # if action is parsed, return the task, and clear the buffer
            idx, tool_name, args, _ = match.groups()
            idx = int(idx)
            task = instantiate_task(
                tools=self.tools,
                idx=idx,
                tool_name=tool_name,
                args=args,
                thought=thought,
            )
            thought = None
        # Else it is just dropped
        return task, thought
