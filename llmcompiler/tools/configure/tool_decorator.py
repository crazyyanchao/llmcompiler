# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : Decorator.
@Time    : 2024-08-06 19:31:00
"""
from langchain_core.tools import BaseTool

from llmcompiler.tools.configure.kwargs_clear import kwargs_filter_placeholder, kwargs_clear


def tool_kwargs_clear(invalid_value):
    """
    Remove invalid values.
    Remove empty values, 'None' strings, and None values from a dictionary.
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


def tool_kwargs_filter_placeholder(pattern_str):
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


def tool_set_default_value(**kwargs_v):
    """
    Set default values for parameters that are not passed.
    @tool_set_default_value() The default value from BaseModel Default.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not kwargs_v:
                tool: BaseTool = args[0]
                for key, value in tool.args.items():
                    kwargs_v[key] = value.get("default", None)
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
