# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
def split_string(text: str) -> list:
    """
    用于分割字符串并生成一个列表。
    字符串中包含换行符和中英文句号，请使用换行符分割字符串，但是如果被分割的字符串不是以句号结尾时，请不要分割，作为完整的一句字符串。
    :param s:
    :return:
    """
    lines = text.split('\n')
    result = []
    temp = ''
    for line in lines:
        if temp != '':
            line = temp + line
            temp = ''
        if line.endswith('。') or line.endswith('.'):
            result.append(line)
        else:
            temp = line
    if temp != '':
        result.append(temp)
    return result
