# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import os
import logging
import pandas as pd
from langchain_core.tools import BaseTool
from pydantic import Field, BaseModel
from typing import Type, List, Union, Tuple, Optional

from llmcompiler.tools.configure.tool_decorator import tool_kwargs_filter, tool_set_pydantic_default
from llmcompiler.tools.generic.action_output import ChartType, Chart, \
    action_output_charts_df_parse, Source
from llmcompiler.tools.generic.action_output import ActionOutput, ActionOutputError
from llmcompiler.tools.generic.render_description import render_text_description

logger = logging.getLogger(__name__)

# try:
#     from dotenv import load_dotenv
#
#     load_dotenv()
# except ImportError:
#     raise ImportError(
#         "The 'python-dotenv' package is required to use this class. Please install it using 'pip install python-dotenv'.")

try:
    import tushare as ts

    if "TUSHARE_TOKEN" not in os.environ:
        raise KeyError("Environment variable 'TUSHARE_TOKEN' is not set. Please set it in your .env file.")
    ts.set_token(os.environ["TUSHARE_TOKEN"])
    pro = ts.pro_api()
except ImportError:
    raise ImportError(
        "The 'tushare' package is required to use this class. Please install it using 'pip install tushare'.")


class InputSchema(BaseModel):
    ts_code: Union[str, List[str]] = Field(default=[], description="基金代码")
    market: str = Field(default="E", description="交易市场: E场内 O场外（默认E）")
    status: str = Field(default="L", description="存续状态 D摘牌 I发行 L上市中")
    offset: Optional[int] = Field(default=0, description="开始行数（分页提取时使用）")
    limit: Optional[int] = Field(default=200, description="每页行数")


class FundBasicV1(BaseTool):
    name = "fund_basic_v1"
    description = render_text_description(
        "功能：获取公募基金数据列表，包括场内和场外基金。"
        "输入参数：基金代码；交易市场: E场内 O场外（默认E）；存续状态 D摘牌 I发行 L上市中。"
        "返回值：基金代码；简称；管理人；托管人；投资类型；成立日期；到期日期；上市时间；发行日期；退市日期；发行份额(亿)；"
        "管理费；托管费；存续期；面值；起点金额(万元)；预期收益率；业绩比较基准；存续状态D摘牌 I发行 L已上市；投资风格；"
        "基金类型；受托人；日常申购起始日；日常赎回起始日；E场内O场外。"
    )
    args_schema: Type[BaseModel] = InputSchema

    @tool_set_pydantic_default
    @tool_kwargs_filter
    def _run(self, **kwargs) -> ActionOutput:
        """Use the tool."""
        try:
            result = self.chart(**kwargs)
            tuple = action_output_charts_df_parse([result])
            charts = tuple[0]
            if charts:
                return ActionOutput(any=charts)
        except Exception as e:
            logging.error(str(e))
        return ActionOutputError(
            msg="Did not get the basic information of the fund, please directly tell the user that the public data has not been updated, in addition, do not say and any information unrelated to the user problem!")

    def chart(self, **kwargs) -> Tuple[Chart, pd.DataFrame]:
        try:
            df = pro.fund_basic(**kwargs)
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
            logger.error(str(e))


if __name__ == '__main__':
    info = FundBasicV1()
    print(info.name)
    print(info.description)
    print(info.args)
    print(info.dag_flow_paras())
    print(info._run(limit=10))
