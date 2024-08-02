# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import multiprocessing


def max_worker(crt_num: int = 32) -> int:
    """
    获取最大可并发线程数
    """
    cpu_count = multiprocessing.cpu_count()
    max = cpu_count * 2
    if crt_num > max:
        return max
    else:
        return crt_num
