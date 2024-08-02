# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import time
from datetime import datetime, timedelta
from typing import Union, Tuple

from llmcompiler.utils.timeparser import TimeExtractor


def formatted_dt_now(fmt="%Y-%m-%d %H:%M:%S"):
    """
    获取当前时间戳
    :return:
    """
    timestamp = time.time()
    dt = datetime.fromtimestamp(timestamp)
    formatted_dt = dt.strftime(fmt)
    return formatted_dt


def get_past_date_tuple(days: int, format: str = '%Y%m%d'):
    """
    获取最近N天的日期
    """
    current_date = datetime.now()
    past_date = current_date - timedelta(days=days)
    formatted_date = past_date.strftime(format)
    return formatted_date, formatted_dt_now(format)


def scroll_date_backward(date: str, scroll_days: int, input_format: str = '%Y%m%d', output_format: str = '%Y%m%d'):
    """
    日期向前滚动
    """
    date_obj = datetime.strptime(date, input_format)
    scrolled_date_obj = date_obj - timedelta(days=scroll_days)
    scrolled_date_str = scrolled_date_obj.strftime(output_format)
    return scrolled_date_str


DATE_FORMATS = ['%Y-%m-%d %H:%M:%S', '%Y%m%d %H%M%S', '%Y%m%d%H%M%S',
                '%Y-%m-%d', '%Y-%m', '%Y',
                '%Y%m%d', '%Y%m']


def convert_date_format(string: Union[str, int], source_format: str = '%Y%m%d', target_format: str = '%Y-%m-%d'):
    """
    按照指定的SOURCE和TARGET格式转换时间
    """
    date_object = datetime.strptime(str(string), source_format)
    new_date_string = date_object.strftime(target_format)
    return new_date_string


def check_date_format(string: Union[str, int]):
    """
    检查字符串符合哪个格式
    """
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(str(string), fmt)
            return fmt
        except ValueError:
            continue
    return None


def convert_date_format_str(string: Union[str, int], target_format: str = '%Y%m%d') -> str:
    """
    检查时间格式然后转换为指定的TARGET_FORMAT格式
    """
    source_format = check_date_format(string)
    date_time = convert_date_format(string, source_format, target_format)
    return date_time


def get_last_quarter_date(format: str = '%Y%m%d'):
    """
    返回当前最近一个季度
    """
    today = datetime.today()
    quarter = (today.month - 1) // 3  # 计算当前季度
    first_day_of_current_quarter = datetime(today.year, quarter * 3 + 1, 1)  # 当前季度的第一天
    last_day_of_last_quarter = first_day_of_current_quarter - timedelta(days=1)  # 上一个季度的最后一天
    last_quarter_date = last_day_of_last_quarter.strftime(format)
    return last_quarter_date


def get_last_quarter_date_back(quarters_back: int = 1, format: str = '%Y%m%d'):
    """
    当前时间向前滚动N个季度
    季度滚动：0表示最近一个季度，-1表示最新季度，1表示上一季度，N表示滚动几个季度
    """
    today = datetime.today()
    quarter = (today.month - 1) // 3  # 计算当前季度
    # 计算向前滚动的季度数
    target_quarter = quarter - quarters_back
    target_year = today.year
    # 调整年份和季度
    while target_quarter < 0:
        target_year -= 1
        target_quarter += 4

    target_month = target_quarter * 3 + 1
    # 计算上一个季度的最后一天
    last_day_of_last_quarter = datetime(target_year, target_month, 1) - timedelta(days=1)
    last_quarter_date = last_day_of_last_quarter.strftime(format)
    return last_quarter_date


def get_last_quarter_date_back_dt(date: str, quarters_back: int = 1, in_format: str = '%Y%m%d', format: str = '%Y%m%d'):
    """
    指定时间向前滚动N个季度
    季度滚动：0表示最近一个季度，-1表示最新季度，1表示上一季度，N表示滚动几个季度
    """
    date_time = datetime.strptime(date, in_format)
    quarter = (date_time.month - 1) // 3  # 计算当前季度
    # 计算向前滚动的季度数
    target_quarter = quarter - quarters_back
    target_year = date_time.year
    # 调整年份和季度
    while target_quarter < 0:
        target_year -= 1
        target_quarter += 4

    target_month = target_quarter * 3 + 1
    # 计算上一个季度的最后一天
    last_day_of_last_quarter = datetime(target_year, target_month, 1) - timedelta(days=1)
    last_quarter_date = last_day_of_last_quarter.strftime(format)
    return last_quarter_date


def get_last_quarter_date_guar():
    """
    当前日期与最靠近的一个季度相差小于30天则返回上一级的，否则返回最靠近的一个季度
    """
    today = datetime.today()
    input_date = datetime.strptime(get_last_quarter_date_back(0), "%Y%m%d")
    time_difference = today - input_date
    days_difference = time_difference.days
    if days_difference > 30:
        return get_last_quarter_date_back(0)
    else:
        return get_last_quarter_date_back(1)


def recently_quarter_date(date: str, format: str = '%Y%m%d', out_format: str = '%Y%m%d'):
    """
    获取当前日期的最近上一季度
    """
    date = datetime.strptime(date, format)
    quarter_start_month = (date.month - 1) // 3 * 3 + 1
    if quarter_start_month == 1:
        last_quarter_start = datetime(date.year - 1, 10, 1)
    else:
        last_quarter_start = datetime(date.year, quarter_start_month - 3, 1)

    last_quarter_end = last_quarter_start + timedelta(days=89)
    last_quarter_end = datetime(last_quarter_end.year, last_quarter_end.month, 31)
    return last_quarter_start.strftime(out_format), last_quarter_end.strftime(out_format)


def is_system_year(date: str, format: str = '%Y%m%d'):
    """
    判断是否为系统年份
    """
    try:
        date_obj = datetime.strptime(date, format)
        current_year = datetime.now().year
        if date_obj.year == current_year:
            return True
        else:
            return False
    except ValueError:
        return False


def is_quarter(date: str, format: str = '%Y%m%d'):
    try:
        date_obj = datetime.strptime(date, format)
        formatted_date = date_obj.strftime('%m%d')
        quarters = ['0331', '0630', '0930', '1231']
        if formatted_date in quarters:
            return True
        else:
            return False
    except ValueError:
        return False


def is_quarter_text(date: str):
    """返回季度日期的描述文本"""
    try:
        prefix = '%Y'
        format = check_date_format(date)
        if '%Y-%m-%d' == format:
            suffix_fmt = '%m-%d'
        else:
            suffix_fmt = '%m%d'
        date_obj = datetime.strptime(date, format)
        year = date_obj.strftime(prefix)
        formatted_date = date_obj.strftime(suffix_fmt)
        if '-' in formatted_date:
            formatted_date = formatted_date.replace('-', '')
        quarters = {'0331': '第一季度', '0630': '第二季度', '0930': '第三季度', '1231': '第四季度'}
        suffix = quarters.get(formatted_date, '')
        return f"{year}年{suffix}"
    except ValueError:
        return None


def get_last_quarter_date_guar_input(date: str, format="%Y%m%d"):
    """
    与当前日期最靠近的一个季度相差小于30天则返回上一级的，否则返回最靠近的一个季度
    """
    today = datetime.strptime(date, format)
    # 与当前日期最近的一个季度
    recently_date = get_last_quarter_date_back_dt(date, 0)
    input_date = datetime.strptime(recently_date, "%Y%m%d")
    time_difference = today - input_date
    days_difference = time_difference.days
    # 当前年份
    if is_system_year(date):
        if is_quarter(date):
            curt_quarter = datetime.strptime(get_last_quarter_date_back(0), format)
            t_dif = today - curt_quarter
            d_dif = t_dif.days
            if d_dif < 30:
                return get_last_quarter_date_back_dt(date, 0)
            else:
                return recently_date
        elif days_difference < 30:
            # 如果是当前系统年份，且差距小于30天，则返回向前滚动的一个季度
            return get_last_quarter_date_back_dt(date, 1)
    # 非当前年份
    else:
        if is_quarter(date):
            return date
    # 否则返回当前时间最近的一个季度
    return recently_date


def date_zone_move(st_date: str, en_date: str, st_format: str = '%Y%m%d', ed_format: str = '%Y%m%d', days: int = 1) -> \
        Tuple[str, str]:
    """
    时间窗口滑动，整体向前滑动N天
    :param st_date: 开始日期
    :param en_date: 结束日期
    :param st_format: 开始日期格式，默认为'%Y%m%d'
    :param ed_format: 结束日期格式，默认为'%Y%m%d'
    :param days: 向前滑动的天数，默认为1天
    :return: 向前滑动后的开始日期和结束日期
    """
    # 将字符串日期转换为datetime对象
    start_date_obj = datetime.strptime(st_date, st_format)
    end_date_obj = datetime.strptime(en_date, ed_format)
    # 向前滑动N天
    mv_st_date_obj = start_date_obj - timedelta(days=days)
    mv_en_date_obj = end_date_obj - timedelta(days=days)
    # 将datetime对象转换回字符串日期
    mv_st_date = mv_st_date_obj.strftime(st_format)
    mv_en_date = mv_en_date_obj.strftime(ed_format)
    return mv_st_date, mv_en_date


def recently_quarter_cleaner(date: str, format: str = '%Y%m%d', out_format: str = '%Y%m%d'):
    """
    当前日期如果不是一个表示季度的日期，则返回最近上一季度；否则返回原来日期
    """
    if is_quarter(date, format):
        return date
    else:
        return recently_quarter_date(date, format, out_format)[1]


def text_has_time_info(text: str) -> bool:
    """判断文本中是否包含时间词，包含返回True，否则返回False"""
    extract_time = TimeExtractor()
    res = extract_time(text)
    if res:
        return True
    else:
        return False
