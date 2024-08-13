# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import os
import logging
from pydantic import Field, BaseModel
from typing import List, Union, Optional, Type

from llmcompiler.tools.basic import CompilerBaseTool
from llmcompiler.tools.configure.tool_decorator import tool_kwargs_filter, tool_set_pydantic_default
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


class OutputSchema(BaseModel):
    ts_code: Optional[str] = Field(default=None, description="基金代码")
    name: Optional[str] = Field(default=None, description="简称")
    management: Optional[str] = Field(default=None, description="管理人")
    custodian: Optional[str] = Field(default=None, description="托管人")
    fund_type: Optional[str] = Field(default=None, description="投资类型")
    found_date: Optional[str] = Field(default=None, description="成立日期")
    due_date: Optional[str] = Field(default=None, description="到期日期")
    list_date: Optional[str] = Field(default=None, description="上市时间")
    issue_date: Optional[str] = Field(default=None, description="发行日期")
    delist_date: Optional[str] = Field(default=None, description="退市日期")
    issue_amount: Optional[float] = Field(default=None, description="发行份额(亿)")
    m_fee: Optional[float] = Field(default=None, description="管理费")
    c_fee: Optional[float] = Field(default=None, description="托管费")
    duration_year: Optional[float] = Field(default=None, description="存续期")
    p_value: Optional[float] = Field(default=None, description="面值")
    min_amount: Optional[float] = Field(default=None, description="起点金额(万元)")
    exp_return: Optional[float] = Field(default=None, description="预期收益率")
    benchmark: Optional[str] = Field(default=None, description="业绩比较基准")
    status: Optional[str] = Field(default=None, description="存续状态D摘牌 I发行 L已上市")
    invest_type: Optional[str] = Field(default=None, description="投资风格")
    type: Optional[str] = Field(default=None, description="基金类型")
    trustee: Optional[str] = Field(default=None, description="受托人")
    purc_startdate: Optional[str] = Field(default=None, description="日常申购起始日")
    redm_startdate: Optional[str] = Field(default=None, description="日常赎回起始日")
    market: Optional[str] = Field(default=None, description="E场内O场外")


class FundBasicV2(CompilerBaseTool):
    name = "fund_basic_v2"
    description = render_text_description(
        "功能：获取公募基金数据列表，包括场内和场外基金。"
        "输入参数：基金代码；交易市场: E场内 O场外（默认E）；存续状态 D摘牌 I发行 L上市中。"
        "返回值：基金代码；简称；管理人；托管人；投资类型；成立日期；到期日期；上市时间；发行日期；退市日期；发行份额(亿)；"
        "管理费；托管费；存续期；面值；起点金额(万元)；预期收益率；业绩比较基准；存续状态D摘牌 I发行 L已上市；投资风格；"
        "基金类型；受托人；日常申购起始日；日常赎回起始日；E场内O场外。"
    )
    args_schema: Type[BaseModel] = InputSchema

    output_model: Type[BaseModel] = OutputSchema
    dag_flow_kwargs: List[str] = ['ts_code', 'found_date']

    @tool_set_pydantic_default
    @tool_kwargs_filter
    def _run(self, **kwargs) -> ActionOutput:
        """Use the tool."""
        try:
            df = pro.fund_basic(**kwargs)
            reports = df.apply(lambda row: OutputSchema(**row.to_dict()), axis=1).tolist()
            return ActionOutput(any=reports, dag_kwargs=self.flow(reports))
        except Exception as e:
            logger.error(str(e))
        return ActionOutputError(
            msg="Did not get the basic information of the fund, please directly tell the user that the public data has not been updated, in addition, do not say and any information unrelated to the user problem!")


if __name__ == '__main__':
    info = FundBasicV2()
    print(info.name)
    print(info.description)
    print(info.args)
    print(info.dag_flow_paras())
    print(info._run(limit=10))
