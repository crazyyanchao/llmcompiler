# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : Remove invalid values from the dictionary kwargs.
@Time    : 2024-08-05 20:08:10
"""


def kwargs_clear(kwargs):
    """
    Remove empty values, 'None' strings, and None values from a dictionary.

    :param kwargs: Dictionary to be cleaned.
    :return: Cleaned dictionary.
    """
    return {k: v for k, v in kwargs.items() if v not in ('', 'None', None)}
