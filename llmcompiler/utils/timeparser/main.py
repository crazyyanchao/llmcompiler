# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
from datetime import datetime
import pandas as pd
from llmcompiler.utils.timeparser import TimeExtractor

if __name__ == '__main__':
    # word = sys.argv[1]
    word = "最近一个月GDP增速"

    # extract_time = TimeExtractor()
    # res = extract_time(reset_text(word))
    # print(res)

    extract_time = TimeExtractor()
    res = extract_time(word)
    print(res)

    time = res[0]['detail']['time']
    start_date = datetime.strptime(time[0], "%Y-%m-%d %H:%M:%S")
    current_date = datetime.strptime(time[1], "%Y-%m-%d %H:%M:%S")

    start_date_str = start_date.strftime("%Y%m%d")
    current_date_str = current_date.strftime("%Y%m%d")

    start_time_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    current_time_str = current_date.strftime("%Y-%m-%d %H:%M:%S")

    df1 = pd.DataFrame({'start': [start_date_str], 'end': [current_date_str]})
    df2 = pd.DataFrame({'start_time': [start_time_str], 'end_time': [current_time_str]})
    print(df1.to_markdown() + "\n")
    print(df2.to_markdown() + "\n")
