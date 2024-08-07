# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : Tools Args Opr.
@Time    : 2024-08-05 20:08:10
"""
import re
from typing import List


def kwargs_clear(kwargs, invalid_value: List = None):
    """
    Remove empty values, 'None' strings, and None values from a dictionary.

    :param kwargs: Dictionary to be cleaned.
    :param invalid_value: Default invalid value.
    :return: Cleaned dictionary.
    """
    if invalid_value is None:
        invalid_value = ['', 'None', None]
    return {k: v for k, v in kwargs.items() if v not in invalid_value}


def contains_placeholder(text, pattern_str: str = None):
    """Detect if the pattern matches."""
    if pattern_str is None:
        pattern_str = r'\$\{.*?\}'
    pattern = re.compile(pattern_str)
    match = pattern.search(str(text))
    return match is not None


def kwargs_filter_placeholder(kwargs, pattern_str: str = None):
    """
    Filter kwargs placeholder.Does the string contain this pattern `${}`?

    :param kwargs: Dictionary to be cleaned.
    :param pattern_str: Pattern string.
    :return: Cleaned dictionary.
    """
    return {k: v for k, v in kwargs.items() if not contains_placeholder(v, pattern_str)}


def kwargs_filter(kwargs, invalid_value: List = None, pattern_str: str = None):
    kwargs = kwargs_clear(kwargs, invalid_value)
    kwargs = kwargs_filter_placeholder(kwargs, pattern_str)
    return kwargs


if __name__ == '__main__':
    print(contains_placeholder("${1}.name"))
