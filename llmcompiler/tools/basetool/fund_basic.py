# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import os
from concurrent.futures import ThreadPoolExecutor

import logging
import pandas as pd

from langchain.callbacks.manager import (
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from pydantic import Field, BaseModel
from typing import Optional, Type, List, Union, Tuple

from llmcompiler.tools.dag.dag_flow_params import DAGFlowParams
from llmcompiler.tools.generic.action_output import ChartType, Chart, dag_flow_params_pack, DAGFlowKwargs, \
    action_output_charts_df_parse, Source
from llmcompiler.tools.generic.action_input import action_input_list_str_multi
from llmcompiler.tools.generic.action_output import ActionOutput, ActionOutputError
from llmcompiler.tools.generic.render_description import render_text_description
from llmcompiler.utils.thread.pool_executor import max_worker

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    raise ImportError(
        "The 'python-dotenv' package is required to use this class. Please install it using 'pip install python-dotenv'.")

try:
    import tushare as ts
    from dotenv import load_dotenv

    load_dotenv()
    ts.set_token(os.environ["TUSHARE_TOKEN"])
    pro = ts.pro_api()
except ImportError:
    raise ImportError(
        "The 'tushare' package is required to use this class. Please install it using 'pip install tushare'.")


class FundInfoSchema(BaseModel):
    ts_code: Union[str, List[str]] = Field(default=[], description="基金代码")
    market: str = Field(default="E", description="交易市场: E场内 O场外（默认E）")
    status: str = Field(default=None, description="存续状态 D摘牌 I发行 L上市中")


class FundBasic(BaseTool, DAGFlowParams):
    name = "fund_basic"
    description = render_text_description(
        "功能：获取公募基金数据列表，包括场内和场外基金。"
        "输入参数：基金代码；交易市场: E场内 O场外（默认E）；存续状态 D摘牌 I发行 L上市中。"
        "返回值：基金代码；简称；管理人；托管人；投资类型；成立日期；到期日期；上市时间；发行日期；退市日期；发行份额(亿)；"
        "管理费；托管费；存续期；面值；起点金额(万元)；预期收益率；业绩比较基准；存续状态D摘牌 I发行 L已上市；投资风格；"
        "基金类型；受托人；日常申购起始日；日常赎回起始日；E场内O场外。"
    )
    args_schema: Type[BaseModel] = FundInfoSchema

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _run(
            self, ts_code: Union[str, List[str]] = None, market: str = None, status: str = None,
            run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> ActionOutput:
        """Use the tool."""
        try:
            params = action_input_list_str_multi([ts_code, market, status])
            with ThreadPoolExecutor(max_workers=max_worker()) as executor:
                results = list(executor.map(lambda x: self.chart(x), params))
            tuple = action_output_charts_df_parse(results)
            charts = tuple[0]
            df = pd.concat(tuple[1])
            if charts:
                _params_ = {
                    'ts_code': df['ts_code'].drop_duplicates().tolist(),
                    'found_date': df['found_date'].drop_duplicates().min()
                }
                return ActionOutput(any=charts,
                                    dag_kwargs=dag_flow_params_pack(self.name, _params_, self.dag_flow_paras()))
        except Exception as e:
            logging.error(str(e))
        return ActionOutputError(
            msg="Did not get the basic information of the fund, please directly tell the user that the public data has not been updated, in addition, do not say and any information unrelated to the user problem!")

    def dag_flow_paras(self) -> List[DAGFlowKwargs]:
        """
        定义DAG可能依赖的参数
        """
        return [
            DAGFlowKwargs(field_en='ts_code', field_cn='基金代码', description=''),
            DAGFlowKwargs(field_en='found_date', field_cn='基金成立日期', description='')
        ]

    def chart(self, ts_code: str = None, market: str = None, status: str = None) -> Tuple[Chart, pd.DataFrame]:
        try:
            df = pro.fund_basic(ts_code=ts_code, market=market, status=status)
            if not df.empty:
                columns = df.columns.values.tolist()
                result = {"labels": columns, "data": df.values.tolist()}
                return Chart(
                    type=ChartType.TABLE_WITH_HEADERS.value,
                    title="公募基金基础信息",
                    data=result,
                    source=[Source(title="公募基金列表", content="公募基金数据列表，包括场内和场外基金",
                                   url="https://tushare.pro/document/2?doc_id=19")],
                    labels=["公募基金基础信息"]
                ), df
        except Exception as e:
            logging.error(str(e))


if __name__ == '__main__':
    info = FundBasic()
    print(info.name)
    print(info.description)
    print(info.args)
    print(info._run(ts_code="['000751.OF', '020857.OF']"))
