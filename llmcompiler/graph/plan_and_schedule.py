# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import json
import re
import time
import logging
import itertools
from typing import Sequence
from concurrent.futures import ThreadPoolExecutor, wait

from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from langchain_core.messages import (
    BaseMessage,
    AIMessage
)

from llmcompiler.graph.planner import Planer
from llmcompiler.graph.output_parser import Task
from typing import Any, Union, Iterable, List, Dict
from typing_extensions import TypedDict
from langchain_core.runnables import (
    chain as as_runnable,
)

from llmcompiler.graph.prompt import TOOL_MESSAGE_TEMPLATE
from llmcompiler.graph.tool_message import ToolMessage
from llmcompiler.tools.generic.action_output import ActionOutput, ActionOutputError, Chart, DAGFlow, BaseChart
from llmcompiler.utils.string.string_sim import word_similarity_score
from llmcompiler.graph.token_calculate import SwitchLLM


def _get_observations(messages: List[BaseMessage]) -> Dict[int, Any]:
    # Get all previous tool responses
    results = {}
    for message in messages[::-1]:
        if isinstance(message, ToolMessage):
            results[int(message.additional_kwargs["idx"])] = message.content
    return results


class SchedulerInput(TypedDict):
    messages: List[BaseMessage]
    tasks: Iterable[Task]
    charts: List[Chart]
    tasks_temporary_save: List[Task]
    observations: Dict


def _execute_task(task, observations, config, charts: List[Chart], tasks_temporary_save: List[Task]):
    tool_to_use = task["tool"]
    if isinstance(tool_to_use, str):
        _print_task(task)
        return tool_to_use
    args = task["args"]
    try:
        if isinstance(args, str):
            resolved_args = _resolve_arg(args, observations, task, tasks_temporary_save)
        elif isinstance(args, dict):
            resolved_args = {
                key: _resolve_arg(val, observations, task, tasks_temporary_save, key) for key, val in args.items()
            }
        else:
            # This will likely fail
            resolved_args = args
    except Exception as e:
        return (
            f"ERROR(Failed to call {tool_to_use.name} with args {args}.)"
            f" Args could not be resolved. Error: {repr(e)}"
        )
    try:
        _print_task(task, resolved_args)
        action_output = tool_to_use.invoke(resolved_args, config)
        stream_output_chart(action_output, charts)
        return action_output
    except Exception as e:
        return (
                f"ERROR(Failed to call {tool_to_use.name} with args {args}."
                + f" Args resolved to {resolved_args}. Error: {repr(e)})"
        )


def _print_task(task: Task, resolved_args: Dict = None):
    """
    打印TASK
    """
    print("---")
    for key, value in task.items():
        if isinstance(value, BaseTool):
            print(f"{key}: {value.name}")
        else:
            print(f"{key}: {value}")
            if 'args' == key:
                _print_task_resolved_args(key, value, resolved_args)
    print("---")


def _print_task_resolved_args(key, value, resolved_args):
    """
    打印解析后的参数
    """
    show = ""
    if resolved_args is not None and 'args' == key:
        if value != resolved_args:
            print(f"{key}<Analyzed>: {resolved_args}")
            return resolved_args
    return show


def stream_output_chart(action_output: Any, charts: List[Chart]):
    """
    流式输出图表对象
    """
    if isinstance(action_output, ActionOutput) and action_output.status:
        value = action_output.any
        if isinstance(value, Chart):
            stream_output_chart_ele(value, charts)
        elif isinstance(value, List):
            for chart in value:
                if isinstance(chart, Chart):
                    stream_output_chart_ele(chart, charts)


def stream_output_chart_ele(value: Chart, charts: List[Chart]):
    """
    流式输出图表对象：输出时检查排查
    """
    if value not in charts:
        charts.append(value)
        # msg_pub.publish(type='chart', message=value)


def _resolve_arg(arg: Union[str, Any], observations: Dict[int, Any], cur_task: Task, tasks_temporary_save: List[Task],
                 field: str = None):
    """
    解析参数
    1. 解析依赖的TASK ID
    2. 获取TASK ID的返回值
    3. 解析参数
    """
    # For dependencies on other tasks
    if isinstance(arg, str):
        return _resolve_arg_str(arg, observations, cur_task, tasks_temporary_save, field)
    elif isinstance(arg, list):
        return [_resolve_arg_str(a, observations, cur_task, tasks_temporary_save, field) for a in arg]
    else:
        return str(arg)


def _resolve_arg_str(arg: str, observations: Dict[int, Any], cur_task: Task, tasks_temporary_save: List[Task],
                     cur_field: str = None):
    """
    :param arg: 模型生成的参数 （例如：${1}、${1}[0]、${1}[0].code...）
    :param observations: 其它TASK返回结果
    :param field: 当前参数值对应的传入字段
    """
    idx = _resolve_arg_str_idx(arg, cur_task, tasks_temporary_save)
    if idx is None or idx == -1 or idx == arg:
        return arg
    else:
        value = observations.get(idx, arg)
        if isinstance(value, ActionOutput) and _is_match_arg(arg):
            # JOIN机制中依赖的Task已经执行了，observations已经获取了其它Tool运行的结果
            value = _tools_dag_flow_value(value.dag_kwargs, idx, tasks_temporary_save, arg, cur_field)
            if value is not None:
                return value
    return arg


def _is_match_arg(arg: str) -> bool:
    """
    判断是否需要进行参数值匹配
    """
    if '$' in arg:
        return True
    if arg.startswith("{") and arg.endswith("}"):
        return True
    if arg.startswith("<") and arg.endswith(">"):
        return True
    return False


def _resolve_arg_str_idx(arg: Any, cur_task: Task, tasks_temporary_save: List[Task]) -> Any:
    """
    匹配 TASK ID
    """
    # $1 or ${1} -> 1
    # ${2}[0].code -> 2
    ID_PATTERN = r"\$\{?(\d+)\}?"

    def replace_match(match):
        # If the string is ${123}, match.group(0) is ${123}, and match.group(1) is 123.
        # Return the match group, in this case the index, from the string. This is the index
        # number we get back.
        return str(match.group(1))

    idx_str = re.sub(ID_PATTERN, replace_match, arg)
    try:
        if idx_str != arg:
            # 获取解析后结果
            return int(idx_str)
        else:
            # 解析不到ID默认使用上一个TASK ID，不能使用当前任务的ID，不能使用Join类任务ID
            temp_tasks = [tp for tp in tasks_temporary_save if
                          tp["idx"] != cur_task["idx"] and tp["tool"] != "join"]
            if temp_tasks:
                return temp_tasks[-1]["idx"]
    except ValueError:
        # 处理类似 ${2}[0].code -> 2[0].code 无法解析的问题
        return _resolve_arg_str_idx_error(idx_str)


def _resolve_arg_str_idx_error(text: str) -> int:
    """
    匹配字符串中第一个数字
    处理类似 ${2}[0].code -> 2[0].code 无法解析的问题
    <date>1.fund_date</date>
    """
    match = re.search(r'\d+', text)
    if match:
        return int(match.group())
    else:
        return -1


def _tools_dag_flow_value(tool_observation: DAGFlow, idx: int, tasks_temporary_save: List[Task], arg: str = None,
                          cur_field: str = None) -> Any:
    """
    获取参数值
    :param tool_observation: 当前任务依赖的上一步Task结果
    :param idx: 当前任务依赖的Task ID
    :param arg: 当前Task，LLM生成的参数
    :param cur_field: 当前Task入参字段
    :param cur_task: 当前Task
    获取参数值方法：
    - 解析字段名获取【标准方法，准确率最高】
    - 猜字段如果出错则有可能触发Replan过程
    """
    # 1. ==============匹配字段==============
    if '.' in arg:
        field = arg.split('.')[-1]
        value = tool_observation.kwargs.get(field, arg)
        if value != arg:
            return value
    # 2. ==============猜字段：从依赖任务的输出中猜，字段全匹配==============
    if '$' in arg:
        value = tool_observation.kwargs.get(cur_field, arg)
        if value != arg:
            return value
    # 3. ==============猜字段：从依赖任务的输入猜字段，字段全匹配==============
    # 从依赖的Task中尝试直接获取相同的参数
    if tasks_temporary_save:
        task: Task = [tk for tk in tasks_temporary_save if tk["idx"] == idx and tk["tool"] != "join"][0]
        if task is not None:
            value = task["args"].get(cur_field, arg)
            if value != arg and '$' not in value:
                return value
    # 4. ==============猜字段：匹配不到字段则猜字段，基于字段匹配度从上一个Task输出中猜字段==============
    return _resolve_arg_parse_random(cur_field, tool_observation)


def _resolve_arg_parse_random(cur_field: str, tool_observation: DAGFlow) -> Any:
    min_similarity = 100
    best_key = None
    data = tool_observation.kwargs
    for key in data.keys():
        similarity = word_similarity_score(cur_field, key)  # 猜一个KEY
        if similarity < min_similarity:
            min_similarity = similarity
            best_key = key
    if best_key:
        return data.get(best_key)


@as_runnable
def schedule_task(task_inputs, config):
    task: Task = task_inputs["task"]
    observations: Dict[int, Any] = task_inputs["observations"]
    charts: List[Chart] = task_inputs["charts"]
    tasks_temporary_save: List[Task] = task_inputs["tasks_temporary_save"]
    try:
        observation = _execute_task(task, observations, config, charts, tasks_temporary_save)
    except Exception as e:
        import traceback

        observation = traceback.format_exception(type(e), e, e.__traceback__)
    observations[task["idx"]] = observation


def schedule_pending_task(
        task: Task, observations: Dict[int, Any], charts: List[Chart],
        tasks_temporary_save: List[Task], retry_after: float = 0.2, timeout: float = 5
):
    """
    :param task: 当前任务
    :param observations: 观察结果，保存任务ID以及运行结果
    :param charts: 存放中间结果
    :param msg_pub: 消息处理对象
    :param retry_after: 多少秒后重新判断当前任务的依赖是否满足
    :param timeout: 依赖分析超时时间
    """
    start_time = time.time()
    while True:
        # 检查超时
        if time.time() - start_time > timeout:
            logging.error(
                f"Timeout: Dependency analysis for {task['tool'].name if isinstance(task['tool'], BaseTool) else task['tool']} exceeded {timeout} seconds.")
            break
        # 依赖分析
        deps = task["dependencies"]
        if deps and (any([dep not in observations for dep in deps])):
            if isinstance(task['tool'], BaseTool):
                logging.warning(f"Dependencies not yet satisfied: {task['tool'].name}")
            else:
                logging.warning(f"Dependencies not yet satisfied: {task['tool']}")
            time.sleep(retry_after)
            continue
        schedule_task.invoke({"task": task, "observations": observations, "charts": charts,
                              "tasks_temporary_save": tasks_temporary_save})
        break


TOOL_RESPONSE_PROMPT = PromptTemplate(input_variables=["response", "input"], template=TOOL_MESSAGE_TEMPLATE)


@as_runnable
def schedule_tasks(scheduler_input: SchedulerInput) -> List[ToolMessage]:
    """Group the tasks into a DAG schedule."""
    # For streaming, we are making a few simplifying assumption:
    # 1. The LLM does not create cyclic dependencies
    # 2. That the LLM will not generate tasks with future deps
    # If this ceases to be a good assumption, you can either
    # adjust to do a proper topological sort (not-stream)
    # or use a more complicated data structure
    charts = scheduler_input["charts"]
    tasks_temporary_save = scheduler_input["tasks_temporary_save"]
    tasks = scheduler_input["tasks"]
    args_for_tasks = {}
    messages = scheduler_input["messages"]
    # If we are re-planning, we may have calls that depend on previous
    # plans. Start with those. <observations = _get_observations(messages)>
    observations = scheduler_input["observations"]
    task_names = {}
    originals = set(observations)
    # ^^ We assume each task inserts a different key above to
    # avoid race conditions...
    futures = []
    retry_after = 0.25  # Retry every quarter second
    timeout = 5
    with ThreadPoolExecutor() as executor:
        for task in tasks:
            tasks_temporary_save.append(task)
            deps = task["dependencies"]
            task_names[task["idx"]] = (
                task["tool"] if isinstance(task["tool"], str) else task["tool"].name
            )
            args_for_tasks[task["idx"]] = (task["args"])
            if (
                    # Depends on other tasks
                    deps
                    and (any([dep not in observations for dep in deps]))
            ):
                futures.append(
                    executor.submit(
                        schedule_pending_task, task, observations, charts, tasks_temporary_save, retry_after,
                        timeout
                    )
                )
            else:
                # No deps or all deps satisfied
                # can schedule now
                schedule_task.invoke(dict(task=task, observations=observations, charts=charts,
                                          tasks_temporary_save=tasks_temporary_save))
                # futures.append(executor.submit(schedule_task.invoke dict(task=task, observations=observations)))

        # All tasks have been submitted or enqueued
        # Wait for them to complete
        wait(futures)
    # Convert observations to new tool messages to add to the state
    new_observations = {
        k: (task_names[k], args_for_tasks[k], observations[k])
        for k in sorted(observations.keys() - originals)
    }
    tool_messages = []
    # 剔除`join`，并过滤重复后添加到<Tool Messages>
    for k, (name, task_args, obs) in new_observations.items():
        ai_message = AIMessage(content=f"{name}{dict_to_query_string(task_args)}")
        if 'join' != name and ai_message not in tool_messages:
            tool_messages.append(ai_message)
            tool_messages.append(ToolMessage(name=name,
                                             content=TOOL_RESPONSE_PROMPT.format(
                                                 response=modify_action_output(obs), input=""),
                                             additional_kwargs={"idx": k, 'args': task_args}))
    return tool_messages


def dict_to_query_string(d: Union[Dict, Any]) -> str:
    if isinstance(d, Dict):
        return "(" + ", ".join([f"{k}=\"{v}\"" for k, v in d.items()]) + ")"
    else:
        return str(d)


def modify_action_output(action_output: Union[ActionOutput, ActionOutputError, Any], extra_msg: str = ''):
    """
    :param action_output: 处理ActionOutput：决定哪些信息被带入下一次调用LLM的Prompts
    :param extra_msg: 一般是给下次规划时的一些额外提示信息
    """
    if isinstance(action_output, ActionOutput) or isinstance(action_output, ActionOutputError):
        # =================修改默认ActionOutput=================
        # ActionOutput响应结果为False则将`msg`赋值给当前步骤
        if not action_output.status:
            return action_output.msg + '\n' + extra_msg
        # 修改指定的Action的结果，ActionOutput响应结果设置为指定消息
        elif not action_output.any_to_prompt:
            return action_output.msg + '\n' + extra_msg

        # =================重置默认ActionOutput=================
        else:
            if isinstance(action_output.any, Chart):
                temp_chart = reset_prompt_chart(action_output.any)
                any_str = temp_chart.json(ensure_ascii=False)
            elif isinstance(action_output.any, List):
                if any(isinstance(x, Chart) for x in action_output.any):
                    temp_charts = reset_prompt_charts(action_output.any)
                    any_str = json.dumps([c.dict() for c in temp_charts], ensure_ascii=False)
                else:
                    any_str = json.dumps(action_output.any, ensure_ascii=False)
            else:
                any_str = action_output.any
            return "\n".join([action_output.msg, any_str, "\n" + extra_msg])
    else:
        return action_output


def reset_prompt_chart(chart: Chart) -> BaseChart:
    """去掉不需要传入到Prompt中的字段"""
    return BaseChart(title=chart.title, data=chart.data)


def reset_prompt_charts(charts: List[Chart]) -> List[BaseChart]:
    """去掉不需要传入到Prompt中的字段"""
    re_charts = []
    for ct in charts:
        re_charts.append(reset_prompt_chart(ct))
    return re_charts


class PlanAndSchedule:
    """
    Planner: stream a DAG of tasks.
    Task Fetching Unit: schedules and executes the tasks as soon as they are executable
    """

    def __init__(self, llm: Union[SwitchLLM, List[SwitchLLM]], tools: Sequence[BaseTool],
                 re_llm: Union[SwitchLLM, List[SwitchLLM]] = None):
        self.llm = llm
        self.re_llm = re_llm
        self.tools = tools
        self.charts = []
        self.tasks_temporary_save = []
        self.observations = {}  # Save all previous tool responses

    # @as_runnable
    def init(self, messages: List[BaseMessage], config):
        planner = Planer(self.llm, self.tools, self.re_llm).init()
        tasks = planner.stream(messages, config)
        # Begin executing the planner immediately
        try:
            tasks = itertools.chain([next(tasks)], tasks)
        except StopIteration:
            tasks = iter([])

        scheduled_tasks = schedule_tasks.invoke(
            SchedulerInput(messages=messages, tasks=tasks, charts=self.charts,
                           tasks_temporary_save=self.tasks_temporary_save, observations=self.observations),
            config,
        )
        return scheduled_tasks