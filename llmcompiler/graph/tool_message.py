# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : To be compatible with multiple models, wrap the TOOL's response as a HUMAN prompt response instead of a ToolMessage.
@Time    : 2024-08-02 14:09:26
"""

from langchain_core.messages import FunctionMessage


class ToolMessage(FunctionMessage):
    """FunctionMessage Rewrite."""
    pass
