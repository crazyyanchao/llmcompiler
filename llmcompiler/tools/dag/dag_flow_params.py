# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
from typing import List
from abc import ABC, abstractmethod
from llmcompiler.tools.generic.action_output import DAGFlowKwargs

# TOOL INPUT SCHEMA `json_schema_extra` **kwargs
# 定义TOOL中的输入参数是否执行参数解析，使用该设置表示为指定字段禁用参数解析
DISABLE_RESOLVED_ARGS = {"resolved_args": False}


class DAGFlowParams(ABC):
    """DAG参数依赖接口"""

    @abstractmethod
    def dag_flow_paras(self, **kwargs) -> List[DAGFlowKwargs]:
        """
        获取Tool中可能被其它Tools依赖的参数字段信息
        """
