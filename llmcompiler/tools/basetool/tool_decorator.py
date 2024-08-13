# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import os
from typing import List

import pandas as pd

from langchain_core.tools import tool, StructuredTool

# try:
#     from dotenv import load_dotenv
#
#     load_dotenv()
# except ImportError:
#     raise ImportError(
#         "The 'python-dotenv' package is required to use this class. Please install it using 'pip install python-dotenv'.")

try:
    import tushare as ts

    # from dotenv import load_dotenv
    #
    # load_dotenv()
    if "TUSHARE_TOKEN" not in os.environ:
        raise KeyError("Environment variable 'TUSHARE_TOKEN' is not set. Please set it in your .env file.")
    ts.set_token(os.environ["TUSHARE_TOKEN"])
    pro = ts.pro_api()
except ImportError:
    raise ImportError(
        "The 'tushare' package is required to use this class. Please install it using 'pip install tushare'.")


# ================================使用注解================================
@tool("stock_basic")
def stock_basic(name: str) -> List[str]:
    """输入公司简称，获取中国股票基本资料，输出股票代码、上市日期等信息"""
    df: pd.DataFrame = pro.stock_basic(name=name)
    return [df.to_json(force_ascii=False)]


# ================================使用注解================================
@tool("fund_portfolio")
def fund_portfolio(ts_code: str = "", symbol: str = "", ann_date: str = "", start_date: str = "", end_date: str = "") -> \
        List[str]:
    """
    功能：获取公募基金持仓数据，季度更新。
    输入参数：基金代码；股票代码；公告日期（YYYYMMDD格式）；报告期开始日期（YYYYMMDD格式）；报告期结束日期（YYYYMMDD格式）。
    返回值：TS基金代码；公告日期；截止日期；股票代码；持有股票市值(元)；持有股票数量（股）；占股票市值比；占流通股本比例。
    """
    df: pd.DataFrame = pro.stock_basic(ts_code=ts_code, symbol=symbol, ann_date=ann_date, start_date=start_date,
                                       end_date=end_date)
    return [df.to_json(force_ascii=False)]


# ================================使用StructuredTool提供的函数================================
def stock_basic_2(name: str) -> List[str]:
    df: pd.DataFrame = pro.stock_basic(name=name)
    return [df.to_json(force_ascii=False)]


def wd_a_desc_2_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=stock_basic_2,
        name="wd_a_desc_2_tool",
        description="使用公司简称获取A股基本资料信息，输出股票代码、上市日期等信息",
    )
