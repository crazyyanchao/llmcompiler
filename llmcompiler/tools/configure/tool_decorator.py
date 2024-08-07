# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : Decorator.
@Time    : 2024-08-06 19:31:00
"""
from typing import List, Optional, Any

from langchain_core.tools import BaseTool

from llmcompiler.tools.configure.kwargs_clear import kwargs_filter_placeholder, kwargs_clear, kwargs_filter


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
    Tool input is filtered out if it is any value in the list. By default, the list is `[" ', 'None', None]`.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            kwargs = kwargs_clear(kwargs, invalid_value)
            result = func(*args, **kwargs)
            return result

        return wrapper

    if callable(invalid_value):
        func = invalid_value
        invalid_value = ['', 'None', None]
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
