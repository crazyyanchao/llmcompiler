# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
from enum import Enum
from typing import Any, List, Dict, Tuple, Union

import pandas as pd
from pydantic import BaseModel, Field

"""
自定义Tool输出对象
"""


class ChartType(str, Enum):
    TABLE_WITH_LEFT_HEADERS = "table-with-left-headers"
    TABLE_DOUBLE_HEADERS = "table-double-headers"
    TABLE_WITH_HEADERS = "table-with-headers"
    LINE_HISTOGRAM_RATIO = "line-histogram-ratio"
    LINE_POLYLINE_RATIO = "line-polyline-ratio"
    OTHER = "other"


class Source(BaseModel):
    title: str = Field(description="数据源标题")
    content: str = Field(default="", description="数据源内容描述")
    url: str = Field(default="https://localhost.compiler.cn/#/asset/rdf", description="数据源链接")


class BaseChart(BaseModel):
    """
    BaseChart只包含数据标题和数据内容
    """
    title: str = Field(default="", description="标题")
    data: dict = Field(default={}, description="数据")


class Chart(BaseChart):
    """
    基于BaseChart扩展图表类型、数据来源、数据标签、以及其它需要在上下文中交互的内容
    """
    type: ChartType = Field(default="", description="图表类型")
    source: List[Source] = Field(default=[], description="数据来源")
    labels: List[str] = Field(default=[], description="数据标签")
    text_join_response: bool = Field(default=False, description="是否将模板`Text`拼接到最终响应的Response")
    text: str = Field(default="",
                      description="图表的文字描述：一般使用模板生成可用来制作PPT内容【可用来替换最终的Response内容】")


class DAGFlowKwargs(BaseModel):
    field_en: str = Field(description="字段英文名")
    field_cn: str = Field(description="字段中文名")
    description: str = Field(description="字段描述")


class DAGFlow(BaseModel):
    tool_name: str = Field(default="", description="当前Tool名称")
    kwargs: Dict[str, Any] = Field(default={}, description="可能会被其它Tools依赖的返回值")
    desc: List[DAGFlowKwargs] = Field(default=[], description="字段相关信息")


class ActionOutput(BaseModel):
    """
    自定义ActionOutput对象便于在AgentExecutorIterator对Steps进行更加灵活的控制
    """
    status: bool = Field(default=True, description="调用Action结果状态")
    any_to_prompt: bool = Field(default=True, description="是否将数据结果添加到下一步Prompt中")
    any: Any = Field(description="调用Action结果")
    msg: str = Field(default="", description="需要提供给LLM的额外的提示信息")
    labels: List[str] = Field(default=[], description="对Action的输出定义标签")
    source: List[Source] = Field(default=[], description="数据来源")
    dag_kwargs: DAGFlow = Field(default=DAGFlow(),
                                description="任务提取模块可能会依赖的参数：Task Fetching Unit")


class ActionOutputError(ActionOutput):
    status: bool = Field(default=False, description="调用Action结果状态")
    any: Any = Field(default="", description="调用Action结果")
    msg: str = Field(default="没有获取到任何有用信息，无法回答相关问题，请认真思考是否需要先调用其它工具！",
                     description="需要提供给LLM的额外的提示信息")


def action_output_charts_df_parse(
        results: List[Tuple[Union[Chart, List[Chart]], Union[pd.DataFrame, List[pd.DataFrame]]]]) -> Tuple[
    List[Chart], List[pd.DataFrame]]:
    """
    从结果中提取Charts和DataFrame
    """
    charts = []
    dfs = []
    for tp in results:
        if tp is not None:
            chart = tp[0]
            if chart is not None:
                if isinstance(chart, List):
                    for ct in chart:
                        charts.append(ct)
                else:
                    charts.append(chart)
            df = tp[1]
            if df is not None:
                if isinstance(df, List):
                    for d in df:
                        dfs.append(d)
                else:
                    dfs.append(df)
    return charts, dfs
