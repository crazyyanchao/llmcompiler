# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : Basic Tools.
@Time    : 2024-08-08 16:56:56
"""
import os
import inspect
import logging
import importlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional, Union

import pandas as pd
from langchain_core.tools import StructuredTool
from langchain_core.utils.pydantic import TypeBaseModel
from pydantic import BaseModel
from langchain.tools import BaseTool

from llmcompiler.tools.dag.dag_flow_params import DAGFlowParams
from llmcompiler.tools.generic.action_output import DAGFlow, DAGFlowKwargs, ActionOutput

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CompilerBaseTool(BaseTool, DAGFlowParams, ABC):
    output_model: Optional[TypeBaseModel] = None
    """Pydantic model class to validate and parse the tool's input arguments.

    Args schema should be either: 

    - A subclass of pydantic.BaseModel.
    or 
    - A subclass of pydantic.v1.BaseModel if accessing v1 namespace in pydantic 2
    """

    dag_flow_kwargs: List[str] = None
    """Parameters that may be relied upon by downstream interfaces."""

    def flow(self, data: Union[List[BaseModel], pd.DataFrame, BaseModel, Dict[str, Any]]) -> DAGFlow:
        """
        从Data封装DAGFlow对象.
        :param data:tool获取的结果，支持传入列表BaeModel、DataFrame、Dict.
        """
        params = {}
        if isinstance(data, List):
            for dat in data:
                for key, value in dat.dict().items():
                    if key in self.dag_flow_kwargs:
                        if key in params:
                            params[key].append(value)
                        else:
                            params[key] = [value]
        elif isinstance(data, pd.DataFrame):
            for key in self.dag_flow_kwargs:
                if key in data.columns:
                    params[key] = data[key].tolist()
        elif isinstance(data, BaseModel):
            for key, value in data.dict().items():
                if key in self.dag_flow_kwargs:
                    if key in params:
                        params[key].append(value)
                    else:
                        params[key] = [value]
        else:
            params = data
        dag_kwargs = self._dag_flow_params_pack(params, self.dag_flow_paras())
        return dag_kwargs

    def dag_flow_paras(self, **kwargs) -> List[DAGFlowKwargs]:
        """获取参数定义，封装DAGFlowKwargs参数，CompilerBaseTool实现类在被使用时可能会需要。"""
        flows = []
        if self.output_model is None:
            raise ValueError(
                "The `output_model` must be defined, please at least define the outputs that the DAG FLOW depends on.")
        for key, value in self.output_model.model_fields.items():
            if key in self.dag_flow_kwargs:
                flows.append(DAGFlowKwargs(field_en=key, field_cn='', description=value.description))
        return flows

    def _dag_flow_params_pack(self, kwargs: Dict[str, Any], desc: List[DAGFlowKwargs]) -> DAGFlow:
        """
        当返回值不存在BaseModel时，可单独定义DAGFlow参数；
        :param kwargs:下游依赖的参数名与参数值
        :param desc:被依赖参数的描述信息
        """
        for de in desc:
            if de.field_en not in kwargs:
                raise ValueError("Missing parameters required by Tools-DAG-Flow.")
        return DAGFlow(tool_name=self.name, kwargs=kwargs, desc=desc)

    @abstractmethod
    def _run(self, *args: Any, **kwargs: Any) -> ActionOutput:
        """Use the tool.

        Add run_manager: Optional[CallbackManagerForToolRun] = None
        to child implementations to enable tracing.
        """


class Tools(ABC):
    """
    Load Tools.
    """

    @staticmethod
    def load_tools(file_paths: Union[str, List[str]] = None) -> List[BaseTool]:
        """
        从指定的目录或者`.py`中自动加载Tools.
        :param file_paths: 传入需要加载Tools的路径，可以是多个，如果传入为空则从当前运行目录下的文件夹中自动检测Tools
        """
        define_tools = []
        if file_paths is None:
            directory = os.getcwd()
            file_paths = [os.path.join(directory, item) for item in os.listdir(directory) if
                          os.path.isdir(os.path.join(directory, item))]
        if isinstance(file_paths, str):
            file_paths = [file_paths]
        for file_path in file_paths:
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            tool_list = Tools.__detect_tools_in_path(file_path)
            define_tools.extend(tool_list)
        logger.info(f"A total of {len(define_tools)} Tools are configured.")
        return define_tools

    @staticmethod
    def __detect_tools_in_path(file_path: str) -> List[BaseTool]:
        define_tools = []

        if file_path.endswith('.py'):
            file_name = os.path.basename(file_path)
            if not file_name.startswith('__'):
                define_tools = Tools.__parse_tool(file_name, os.path.dirname(file_path))

        for root, _, files in os.walk(file_path):
            for file_name in files:
                if file_name.endswith('.py') and not file_name.startswith('__'):
                    tools = Tools.__parse_tool(file_name, root)
                    define_tools.extend(tools)
        return define_tools

    @staticmethod
    def __parse_tool(file_name: str, file_path: str) -> List[BaseTool]:
        define_tools = []
        module_name = file_name[:-3]
        module_path = os.path.join(file_path, file_name)
        logger.info(f"Loading module {module_name} at {module_path}")
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                logger.warning(f"Failed to load spec for module {module_name} at {module_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)

                if inspect.isclass(attribute):
                    if issubclass(attribute, BaseTool) or issubclass(attribute, CompilerBaseTool):
                        try:
                            if attribute() not in define_tools:
                                define_tools.append(attribute())
                                logger.info(f"Detected tools {attribute} under {module_name} at {module_path}.")
                        except:
                            pass
                else:
                    is_tool, is_structured_tool = Tools.check_method(attribute)
                    if is_tool and not is_structured_tool and attribute not in define_tools:
                        define_tools.append(attribute)
                        logger.info(f"Detected tools {attribute} under {module_name} at {module_path}.")
                    if is_tool and is_structured_tool and attribute() not in define_tools:
                        define_tools.append(attribute())
                        logger.info(f"Detected tools {attribute} under {module_name} at {module_path}.")
        except Exception as e:
            logger.error(f"Error loading module {module_name} at {module_path}: {e}")
        return define_tools

    @staticmethod
    def is_tool_annotated(func):
        """检查方法是否使用了@tool注解"""
        # 如果func是@tool装饰的结果，检查它是否具有特定的属性或类型
        return hasattr(func, "_tool_name") or isinstance(func, StructuredTool)

    @staticmethod
    def is_structured_tool_return(func):
        """检查方法的返回值是否是StructuredTool"""
        return_annotation = inspect.signature(func).return_annotation
        return return_annotation == StructuredTool

    @staticmethod
    def check_method(func) -> Tuple[bool, bool]:
        """
        判断方法是否使用了@tool注解或者返回值是StructuredTool.
        :return (是否使用了@tool注解或者返回值是StructuredTool，返回值是StructuredTool)
        """
        if inspect.isfunction(func) or isinstance(func, StructuredTool):
            if Tools.is_tool_annotated(func):
                return True, False
            elif Tools.is_structured_tool_return(func):
                return True, True
        return False, False
