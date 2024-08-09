# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : Basic Tools.
@Time    : 2024-08-08 16:56:56
"""
import importlib
import inspect
import os
import logging
from abc import ABC
from typing import List, Type

import pandas as pd
from langchain.tools import BaseTool
from pydantic import BaseModel

from llmcompiler.tools.dag.dag_flow_params import DAGFlowParams
from llmcompiler.tools.generic.action_output import DAGFlow, dag_flow_params_pack, DAGFlowKwargs

logger = logging.getLogger(__name__)


class CompilerBaseTool(BaseTool, DAGFlowParams, ABC):

    def flow(self, df: pd.DataFrame, cls: Type[BaseModel], *args) -> DAGFlow:
        _dag_fields = self._args_list(args)
        _params_ = {}
        for field in _dag_fields:
            if field in df.columns:
                _params_[field] = df[field].tolist()
        dag_kwargs = dag_flow_params_pack(self.name, _params_, self.dag_flow_paras(_dag_fields, cls))
        return dag_kwargs

    def dag_flow_paras(self, _dag_fields: List[str], cls: Type[BaseModel]) -> List[DAGFlowKwargs]:
        flows = []
        for key, value in cls.model_fields.items():
            if key in _dag_fields:
                flows.append(DAGFlowKwargs(field_en=key, field_cn='', description=value.description))
        return flows

    def _args_list(self, *args):
        args = args[0]
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, str):
                if ',' in arg:
                    return arg.split(',')
                else:
                    return [arg]
            elif isinstance(arg, list):
                return arg
        elif len(args) > 1:
            return list(args)
        else:
            return []


class Tools(ABC):
    """
    Load Tools.
    """

    @staticmethod
    def dynamic_load_tools() -> List[BaseTool]:
        define_tools = []
        file_paths = [os.getcwd()]
        for file_path in file_paths:
            tool_list = Tools.detect_tools_in_path(file_path)
            define_tools.extend(tool_list)
        return define_tools

    @staticmethod
    def load_tools(file_paths: List[str]) -> List[BaseTool]:
        define_tools = []
        for file_path in file_paths:
            tool_list = Tools.detect_tools_in_path(file_path)
            define_tools.extend(tool_list)
        return define_tools

    @staticmethod
    def detect_tools_in_path(file_path: str) -> List[BaseTool]:
        define_tools = []
        for root, _, files in os.walk(file_path):
            for file_name in files:
                if file_name.endswith('.py') and not file_name.startswith('__'):
                    module_name = file_name[:-3]
                    module_path = os.path.join(root, file_name)
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, module_path)
                        if spec is None or spec.loader is None:
                            logger.warning(f"Failed to load spec for module {module_name} at {module_path}")
                            continue
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        for attribute_name in dir(module):
                            attribute = getattr(module, attribute_name)
                            if (inspect.isclass(attribute) and
                                    (issubclass(attribute, BaseTool) or issubclass(attribute, CompilerBaseTool))):
                                try:
                                    if attribute() not in define_tools:
                                        define_tools.append(attribute())
                                except:
                                    pass
                    except Exception as e:
                        logger.error(f"Error loading module {module_name} at {module_path}: {e}")

        logger.info(f"A total of {len(define_tools)} Tools are configured.")
        return define_tools
