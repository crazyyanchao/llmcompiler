# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
from typing import List
from abc import ABC, abstractmethod
from llmcompiler.tools.generic.action_output import DAGFlowKwargs

# 该变量用于存储每个被解析的参数依赖的的上游工具，以及依赖字段的信息，在下游工具调用时可能会使用到
RESOLVED_RAGS_DEPENDENCY_VAR = "___RESOLVED_RAGS__"

# ====================🚀 INPUT SCHEMA KWARGS 🚀====================
# TOOL INPUT SCHEMA `json_schema_extra` **kwargs
# 定义TOOL中的输入参数是否执行参数解析，使用该设置表示为指定字段禁用参数解析（`$`符号等相关内容会被保留）
DISABLE_RESOLVED_ARGS = {"resolved_args": False}

# 定义TOOL中的输入参数是否执行部分解析，使用该设置表示为指定字段启动参数部分解析（`$`符号等相关内容会被替换，完整的一个参数中其它内容将被保留）
PARTIAL_RESOLVED_ARGS_PARSE = {"partial_parse_resolved_args": True}

# ====================🚀 OUTPUT SCHEMA KWARGS 🚀====================
# 在使用`@tool_call_by_row_pass_parameters`注解时，搭配这个参数时表示不执行自动转为DataFrame一列的过程，而是将原有值直接扩展到其它行。
DISABLE_ROW_CALL = {"disable_row_call": True}

# 在使用`@tool_call_by_row_pass_parameters`注解时，搭配这个参数时表示不执行字段列自动填充
DISABLE_FILL_NON_LIST_ROW = {"disable_fill_non_list_row": True}


class DAGFlowParams(ABC):
    """DAG参数依赖接口"""

    @abstractmethod
    def dag_flow_paras(self, **kwargs) -> List[DAGFlowKwargs]:
        """
        获取Tool中可能被其它Tools依赖的参数字段信息
        """
