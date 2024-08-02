# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
from typing import List, Union, Any

from pydantic import BaseModel

from llmcompiler.utils.date.date import convert_date_format_str, scroll_date_backward, recently_quarter_cleaner, \
    get_last_quarter_date, get_past_date_tuple, formatted_dt_now
from llmcompiler.utils.string.question_trim import extract_json_list

"""
标准化Tool输入参数解析
"""


def action_input_list_str(para: Union[Any, List[Any]]) -> List[Any]:
    """
    Tool输入同时支持`str`或者`List[str]`
    字符串中如果包含列表则解析为列表格式
    """
    if para is None:
        para = []
    re_paras = []
    if isinstance(para, List):
        for ele in para:
            if isinstance(ele, List):
                re_paras.extend(ele)
            else:
                re_paras.append(ele)
        return re_paras
    elif isinstance(para, str):
        if '[' in para and ']' in para:
            json = extract_json_list(para)
            if json is not None:
                return json
        else:
            re_paras.append(para)
            return re_paras
    return [para]


def action_input_list_str_multi(paras: List[Union[Any, List[Any]]]) -> List[Any]:
    """
    Tool输入同时支持`str`或者`List[str]`，多个入参拼接到一个列表
    """
    para_list = []
    for para in paras:
        para_list.extend(action_input_list_str(para))
    return para_list


def action_input_list_str_int(para: Union[str, int, List[str], List[int]]) -> List[str]:
    """
    Tool输入同时支持str, int, List[str], List[int]
    """
    paras = []
    if isinstance(para, str) or isinstance(para, int):
        paras.append(para)
    else:
        paras = para
    return paras


class DateZone(BaseModel):
    start_date: str
    end_date: str


def action_input_dates(start_date: Union[str, int, List[str], List[int]],
                       end_date: Union[str, int, List[str], List[int]], strftime: str = None,
                       expand_time: bool = True) -> List[DateZone]:
    """
    组合时间区间
    """
    dates = []
    start_date = set(action_input_list_str_int(start_date))
    end_date = set(action_input_list_str_int(end_date))
    if strftime is not None:
        start_date = [convert_date_format_str(dt, strftime) for dt in start_date]
        end_date = [convert_date_format_str(dt, strftime) for dt in end_date]
    for st in start_date:
        for et in end_date:
            if expand_time and st == et:
                # 默认扩展时间
                st = scroll_date_backward(et, 365, strftime, strftime)
            dates.append(DateZone(start_date=st, end_date=et))
    return dates


def action_input_date_list(date: Union[str, int, List[str], List[int]], strftime: str = None) -> List[str]:
    """
    组合时间区间
    """
    if date is None:
        if strftime is not None:
            date = formatted_dt_now(fmt="%Y%m%d")
        else:
            date = formatted_dt_now(fmt=strftime)
    dates = set(action_input_list_str_int(date))
    if strftime is not None:
        dates = [convert_date_format_str(dt, strftime) for dt in dates]
    return dates


def action_input_date_quarter(dates: List[str], format: str = '%Y%m%d', out_format: str = '%Y%m%d',
                              set_default: bool = True):
    """
    将日期映射到季度日期，如果传入日期不是季度日期则获取最近上一季度日期
    """
    if dates:
        return [recently_quarter_cleaner(date, format, out_format) for date in dates]
    elif set_default:
        return [get_last_quarter_date(out_format)]
    else:
        return dates


def action_input_dates_recent_days(days: Union[int, List[int]], format: str = '%Y%m%d') -> List[DateZone]:
    """
    指定天数解析为时间区间
    """
    if isinstance(days, int) or isinstance(days, str):
        days = [days]
    dates = []
    for day in days:
        tuple = get_past_date_tuple(int(day), format)
        dates.append(DateZone(start_date=tuple[0], end_date=tuple[1]))
    return dates
