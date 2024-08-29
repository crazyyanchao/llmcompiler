# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : Decorator.
@Time    : 2024-08-06 19:31:00
"""

import time
import inspect
import numpy as np
import pandas as pd
import threading
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Any, Dict, Union
from langchain_core.tools import BaseTool

from llmcompiler.graph.output_parser import Task
from llmcompiler.graph.plan_and_schedule import ResolvedArgs
from llmcompiler.tools.basic import CompilerBaseTool
from llmcompiler.tools.configure.kwargs_clear import kwargs_filter_placeholder, kwargs_clear, kwargs_filter
from llmcompiler.tools.dag.dag_flow_params import RESOLVED_RAGS_DEPENDENCY_VAR, DISABLE_ROW_CALL
# from llmcompiler.tools.dag.dag_flow_params import DISABLE_ROW_CALL
from llmcompiler.tools.generic.action_output import ActionOutput, DAGFlow, ActionOutputError
from llmcompiler.utils.thread.pool_executor import max_worker


def tool_kwargs_filter(invalid_value: Optional[List[Any]] = None, pattern_str: Optional[str] = None):
    """
    @tool_kwargs_clear + @tool_kwargs_filter_placeholder
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            kwargs = kwargs_filter(kwargs, invalid_value, pattern_str)
            result = func(*args, **kwargs)
            return result

        return wrapper

    if callable(invalid_value):
        func = invalid_value
        invalid_value = ['', 'None', None, [], {}]
        pattern_str = r'\$\{.*?\}'
        return decorator(func)
    return decorator


def tool_kwargs_clear(invalid_value: List[Any]):
    """
    Remove invalid values.
    Tool input is filtered out if it is any value in the list. By default, the list is `['', 'None', None, [], {}]`.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            kwargs = kwargs_clear(kwargs, invalid_value)
            result = func(*args, **kwargs)
            return result

        return wrapper

    if callable(invalid_value):
        func = invalid_value
        invalid_value = ['', 'None', None, [], {}]
        return decorator(func)
    return decorator


def tool_kwargs_filter_placeholder(pattern_str: str):
    """
    Clean parameters that match the specified pattern.
    Filter kwargs placeholder.Does the string contain this pattern `${}`?
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            kwargs = kwargs_filter_placeholder(kwargs, pattern_str)
            result = func(*args, **kwargs)
            return result

        return wrapper

    if callable(pattern_str):
        func = pattern_str
        pattern_str = r'\$\{.*?\}'
        return decorator(func)

    return decorator


def tool_set_pydantic_default(func):
    """
    The default value from BaseModel Default.
    Set default values for parameters that are not input.
    """

    def wrapper(*args, **kwargs):
        tool: BaseTool = args[0]
        if not hasattr(tool, 'args') or not isinstance(tool.args, dict):
            raise ValueError("The first argument must be an instance of BaseTool with an 'args' attribute.")
        for key, value in tool.args.items():
            if key not in kwargs and 'default' in value:
                kwargs[key] = value.get("default")
        result = func(*args, **kwargs)
        return result

    return wrapper


# def _disable_row_call_fields(tool: BaseTool) -> List[str]:
#     """
#     disable_row_call参数为true的字段
#     """
#     fields = []
#     dat = tool.args_schema
#     for key, value in dat.model_fields.items():
#         json_schema_extra = getattr(value, 'json_schema_extra', {})
#         if json_schema_extra:
#             disable_row_call = next(iter(DISABLE_ROW_CALL.keys()), None)
#             if disable_row_call in json_schema_extra:
#                 if json_schema_extra[disable_row_call]:
#                     fields.append(key)
#     return fields

def kwargs_convert_df(dict: Dict, detect_disable_row_call: bool = False,
                      fill_non_list_row: bool = False, fields: List[str] = None) -> pd.DataFrame:
    """
    Convert dictionary to DataFrame.

    eg.fill_non_list_row=True
      code    date  value
    0    1  2024.0  200.0
    1    2     NaN    NaN
    2    3     NaN    NaN
    convert:
      code  date  value
    0    1  2024    200
    1    2  2024    200
    2    3  2024    200

    eg.detect_disable_row_call=True
      code    date  value
    0    1  2024.0  200.0
    1    2     NaN    NaN
    2    3     NaN    NaN
    convert:
        code    date  value
    0  [1, 2, 3]  2024.0  200.0

    eg.detect_disable_row_call=True,fill_non_list_row=True
      code    date  value
    0    1  2024.0  200.0
    1    2     NaN    NaN
    2    3     NaN    NaN
    convert:
            code  date  value
    0  [1, 2, 3]  2024    200
    """
    data = dict.copy()
    # Detect disable_row_call.
    if fields and detect_disable_row_call:
        for key, value in data.items():
            if key in fields and isinstance(value, list):
                data[key] = [value]

    # Convert non-list values to lists
    for key, value in data.items():
        if not isinstance(value, list):
            data[key] = [value]
    max_length = max(len(v) if isinstance(v, list) else 1 for v in data.values())

    # Check single-value field.
    if fill_non_list_row:
        for key, value in data.items():
            if len(value) == 1:
                data[key] = value * max_length

    for key in data:
        while len(data[key]) < max_length:
            data[key].append(np.nan)

    df = pd.DataFrame(data)
    return df


def merge_output(results: List[ActionOutput]) -> ActionOutput:
    """Merge action output."""
    results = [result for result in results if
               isinstance(result, ActionOutput) and not isinstance(result, ActionOutputError)]
    if not results:
        raise ValueError("The `ActionOutput` list object is found to be empty when performing the merge operation!")

    first_result = results[0]
    merged_any = []
    merged_msg = []
    merged_labels = []
    merged_source = []
    merged_dag_kwargs = {}

    for result in results:
        if result.any:
            merged_any.append(result.any)
        if result.msg and result.msg not in merged_msg:
            merged_msg.append(result.msg)
        if result.labels:
            merged_labels.extend(lb for lb in result.labels if lb not in merged_labels)
        if result.source:
            merged_source.extend(lb for lb in result.source if lb not in merged_source)
        if first_result.dag_kwargs.kwargs:
            for key, value in first_result.dag_kwargs.kwargs.items():
                if key in merged_dag_kwargs:
                    if isinstance(value, list):
                        merged_dag_kwargs[key].extend(value)
                    else:
                        merged_dag_kwargs[key].append(value)
                else:
                    merged_dag_kwargs[key] = (value if isinstance(value, list) else [value]).copy()

    return ActionOutput(
        status=first_result.status,
        any_to_prompt=first_result.any_to_prompt,
        any=merged_any,
        msg='. '.join(merged_msg) + '.' if merged_msg else '',
        labels=merged_labels,
        source=merged_source,
        dag_kwargs=DAGFlow(tool_name=first_result.dag_kwargs.tool_name, kwargs=merged_dag_kwargs,
                           desc=first_result.dag_kwargs.desc)
    )


def _has_disable_row_call_fields(dict: Dict[str, ResolvedArgs]) -> List[str]:
    """Filter out the fields with the DISABLE_ROW_CALL=True parameter in the upstream OUTPUTSCHEMA."""
    fields = []
    if dict is None:
        dict = {}
    for key_v, val in dict.items():
        if not isinstance(val, List):
            task: Task = val['dep_task']
            tool: BaseTool = task['tool']
            field = val['field']
            if isinstance(tool, CompilerBaseTool):
                for key, value in tool.output_model.model_fields.items():
                    json_schema_extra = getattr(value, 'json_schema_extra', {})
                    if json_schema_extra and key == field:
                        disable_row_call = next(iter(DISABLE_ROW_CALL.keys()), None)
                        if disable_row_call in json_schema_extra and json_schema_extra[disable_row_call]:
                            fields.append(key_v)
    return fields


def tool_call_by_row_pass_parameters(fill_non_list_row: bool = False, detect_disable_row_call: bool = False,
                                     limit: int = -1):
    """
    Pass parameters by row and call TOOL.
    Pad the LIST parameter bitwise, then call TOOL multiple times.
    Ensure that INPUT BASEMODEL can be validated through the LIST parameter.
    For example, use Union[str, List] to add LIST validation for single value parameters.
    Ensure that each parameter value in kwargs has the same number of rows.
    @detect_disable_row_call Ignore check if the parameter for detecting the upstream output results does not require checking the expanded columns (BASEMODEL USE DISABLE_ROW_CALL).
    @fill_non_list_row Does the single-value parameter need to be automatically populated into the Table.
    @limit Only perform the call on the first expanded LIMIT rows, with a default value of -1 indicating no limit.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            print('Parsing and executing multirow parameters...')
            tool: BaseTool = args[0]
            if tool.metadata is None:
                tool.metadata = {}
            tool_dep_var = tool.metadata.get(RESOLVED_RAGS_DEPENDENCY_VAR, None)
            disable_row_call_fields = _has_disable_row_call_fields(tool_dep_var)
            if tool_dep_var and disable_row_call_fields and detect_disable_row_call:
                df = kwargs_convert_df(kwargs, True, fill_non_list_row, disable_row_call_fields)
            else:
                df = kwargs_convert_df(kwargs, fill_non_list_row=fill_non_list_row)
            # Iterate through each row and print as a dictionary
            params = []
            if limit > 0:
                df = df.head(limit)
            for index, row in df.iterrows():
                row_dict = row.to_dict()
                params.append(row_dict)
                print(row_dict)
            with ThreadPoolExecutor(max_workers=max_worker()) as executor:
                results = list(executor.map(lambda x: func(*args, **x), params))

            output = merge_output(results)
            return output

        return wrapper

    if callable(fill_non_list_row):
        func = fill_non_list_row
        fill_non_list_row = False
        detect_disable_row_call = True
        return decorator(func)
    return decorator


def tool_set_default_value(**kwargs_v):
    """
    User-specified default values.
    Set default values for parameters that are not input.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not kwargs_v:
                raise ValueError("The user must define at least one default value.")
            for key, value in kwargs_v.items():
                if key not in kwargs:
                    kwargs[key] = value
            result = func(*args, **kwargs)
            return result

        return wrapper

    if callable(kwargs_v):
        func = kwargs_v
        kwargs_v = {}
        return decorator(func)

    return decorator


def tool_symbol_separated_string(fields: List[str], symbol: str = ','):
    """
    If the input is a list, convert it into a string separated by a specified character. If the input is any other type of value, return it as is.
    When the input parameter is a list of strings, this decorator will be useful.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            for field in fields:
                if field in kwargs:
                    value = kwargs[field]
                    if isinstance(value, List):
                        kwargs[field] = symbol.join(value)
            result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator


def tool_remove_suffix(fields: List[str], suffix: List[str]):
    """
    CN: 将指定字段的指定后缀全部移除，SUFFIX指定的后缀会被循环移除。
    EN: Remove all specified suffixes from the designated fields, where the SUFFIX will be iteratively removed.
    When the input parameter is a list of strings or string, this decorator will be useful.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            for field in fields:
                if field in kwargs:
                    kwargs[field] = remove_suffix(kwargs[field], suffix)
            result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator


def remove_suffix(value: Any, suffix: List[str]) -> Any:
    """Remove suffix."""
    if isinstance(value, List) and all(isinstance(item, str) for item in value):
        new_value = []
        for val in value:
            for sfx in suffix:
                val = str(val).removesuffix(sfx)
            new_value.append(val)
        return new_value
    elif isinstance(value, str):
        for sfx in suffix:
            value = str(value).removesuffix(sfx)
        return value
    else:
        return value


def tool_remove_prefix(fields: List[str], prefix: List[str]):
    """
    CN: 将指定字段的指定前缀全部移除，PREFIX指定的前缀会被循环移除。
    EN: Remove all specified prefixes from the designated fields, with the PREFIX specified being cyclically removed.
    When the input parameter is a list of strings or string, this decorator will be useful.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            for field in fields:
                if field in kwargs:
                    kwargs[field] = remove_prefix(kwargs[field], prefix)
            result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator


def remove_prefix(value: Any, prefix: List[str]) -> Any:
    """Remove suffix."""
    if isinstance(value, List) and all(isinstance(item, str) for item in value):
        new_value = []
        for val in value:
            for pre in prefix:
                val = str(val).removeprefix(pre)
            new_value.append(val)
        return new_value
    elif isinstance(value, str):
        for pre in prefix:
            value = str(value).removeprefix(pre)
        return value
    else:
        return value


def tool_string_spilt(fields: List[str], split: str, index: int = 0):
    """
    CN: 将指定字段的值使用指定字符进行分割，按照指定的INDEX值获取值。
    EN: Split the value of a specified field using a designated character, and then retrieve the value based on a specified index.
    When the input parameter is a list of strings or string, this decorator will be useful.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            for field in fields:
                if field in kwargs:
                    value = kwargs[field]
                    kwargs[field] = string_split(value, split, index)
            result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator


def string_split(value: Any, split: str, index: int):
    """INDEX START WITH `0`"""
    if isinstance(value, List) and all(isinstance(item, str) for item in value):
        new_value = []
        for val in value:
            vals = val.split(split)
            if len(vals) >= index + 1:
                idx = index
            else:
                idx = len(vals) - 1
            new_value.append(vals[idx])
        return new_value
    elif isinstance(value, str):
        vals = value.split(split)
        if len(vals) >= index + 1:
            idx = index
        else:
            idx = len(vals) - 1
        return vals[idx]
    else:
        return value


def tool_timeout(timeout: int):
    """
    This decorator is used to control the execution duration of a TOOL.
    @param timeout: Timeout duration, in seconds.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a list of tagged threads.
            result = [None]
            exception = [None]

            # Define the objective function.
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            # Create thread.
            thread = threading.Thread(target=target)
            thread.start()
            thread.join(timeout)

            # Check if the thread is still running.
            if thread.is_alive():
                tool: BaseTool = args[0]
                raise Exception(f"Tool '{tool.name}' exceeded timeout of {timeout} seconds")

            # Check if the target function throws an exception.
            if exception[0]:
                raise exception[0]

            return result[0]

        return wrapper

    return decorator


def tool_timeit(format_str: str = None):
    """
    Decorator to print the execution time of a function.

    Args:
    format_str (str, optional): A format string to customize the output of the execution time.
                                The format string can use the {time} placeholder to represent the execution time.
                                If format_str is not provided, the default format will be used.

    Examples:
    @tool_timeit()
    def my_function():
        time.sleep(1)

    @tool_timeit('Initialization function: {time:.4f} seconds')
    def another_function():
        time.sleep(2)

    Output:
    Function 'my_function' executed in 1.0010 seconds at example.py:10
    Initialization function: 2.0020 seconds
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            file_name = inspect.getfile(func)
            line_number = inspect.getsourcelines(func)[1]

            if format_str:
                formatted_time = format_str.format(time=execution_time)
                print(f'{formatted_time}, {file_name}:{line_number}')
            else:
                print(f"Function '{func.__name__}' executed in {execution_time:.4f} seconds "
                      f"at {file_name}:{line_number}")
            return result

        return wrapper

    return decorator
