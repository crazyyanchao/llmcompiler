# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : Basic Tools.
@Time    : 2024-08-08 16:56:56
"""
import importlib
import os
import logging
from abc import ABC
from typing import List
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


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
                            if (isinstance(attribute, type) and
                                issubclass(attribute,
                                           BaseTool) and attribute != BaseTool) and attribute() not in define_tools:
                                define_tools.append(attribute())
                    except Exception as e:
                        logger.error(f"Error loading module {module_name} at {module_path}: {e}")

        logger.info(f"A total of {len(define_tools)} Tools are configured.")
        return define_tools
