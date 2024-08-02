# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import json
import re
import logging
from typing import List


def is_special_char(text):
    pattern = r"[^0-9a-zA-Z\u4e00-\u9fa5]$"
    match = re.search(pattern, text)
    return match is not None


def remove_trailing_chars(text):
    """
    移除字符串末尾的非数字、非字母、非中文的特殊符号
    :param text:
    :return:
    """
    while is_special_char(text):
        text = text[:-1]
    return text


def text_truncated_to_list(string):
    """
    # 问题列表做处理：每个问题使用'. '分隔，然后取第二个元素，去掉问题的编号数字
    :param string:
    :return:
    """
    ls = []
    if '\n' in string:
        array = string.split('\n')
        for ele in array:
            if ". " in ele:
                ls.append(ele.split('. ')[1])
            else:
                ls.append(ele)
    elif string == "":
        ls = []
    else:
        ls = [string]
    return ls


def extract_text_cn_en_num(string):
    # 提取中文、英文和数字
    text = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', string)
    return "".join(text)


def match_agent_final_answer(text: str):
    """
    提取包含Final Answer的JSON字符串
    """
    try:
        # 正则匹配模式
        pattern = r'\{[^}]*"action":\s*"Final Answer"[^}]*\}'

        # 执行正则匹配
        match = re.search(pattern, text)

        if match:
            # 提取匹配结果
            matched_json = match.group()
            return matched_json
        else:
            return text
    except:
        return text


def match_agent_action(text: str):
    """
    提取包含Final Answer的JSON字符串
    """
    try:
        # 正则表达式匹配模式
        pattern = r'{\s*"action":\s*"[^"]*"\s*,\s*"action_input":\s*{[^}]*}\s*}'

        # 执行正则匹配
        match = re.search(pattern, text)

        if match:
            # 提取匹配结果
            matched_json = match.group()
            return matched_json
        else:
            return text
    except:
        return text


def match_agent_action_thought(text: str) -> List:
    pattern = r'"action":\s*"([^"]*)"'
    matches = re.findall(pattern, text)

    return matches


def match_python_code(text: str) -> str:
    pt = "```([\w\W]*?)```"
    code = match_python(text, pt)
    if code.startswith("python"):
        pt = "```python([\w\W]*?)```"
        return match_python(text, pt)
    elif code.startswith("py\n"):
        pt = "```py([\w\W]*?)```"
        return match_python(text, pt)
    else:
        return code


def match_sql(text: str) -> str:
    pt = "```([\w\W]*?)```"
    code = match_python(text, pt)
    if code.startswith("sql"):
        pt = "```sql([\w\W]*?)```"
        return match_python(text, pt)
    else:
        return code


def match_python(text: str, pt: str):
    match = re.search(pt, text)
    if match is None:
        extracted_code = text
    else:
        extracted_code = match.group(1)
    return extracted_code


def match_uids_dataset(text: str) -> list[str]:
    pattern = r"HDATASET\d+"
    code = re.findall(pattern, text)
    return code


def get_uuid() -> str:
    import uuid
    return str(uuid.uuid4())


def extract_json_list(text: str) -> json:
    # 使用正则表达式匹配JSON列表
    pattern = r'\[.*?\]'
    try:
        text = text.replace("\n", "")
        json_list_all = re.findall(pattern, text)
        json_list_str = json_list_all[0]
        json_list = json.loads(json_list_str.replace('\'', '"'))
        return json_list
    except Exception as e:
        logging.error(e)


def match_uids_value_dataset(text: str) -> list[str]:
    pattern = r'[A-Za-z0-9]+'
    dataset_codes = re.findall(pattern, text)
    return dataset_codes


def extract_json_dict(text: str):
    pattern = r'\{[^{}]*\}'
    match = re.search(pattern, text)
    if match:
        json_str = match.group()
        try:
            json_dict = json.loads(json_str)
            return json_dict
        except json.JSONDecodeError:
            return None
    else:
        return None


def is_contains_chinese(text: str) -> bool:
    """判断字符串中是否包含中文字符"""
    pattern = re.compile(r'[\u4e00-\u9fa5]')  # 匹配中文字符的正则表达式
    return bool(pattern.search(str(text)))


def is_contains_chinese_en(text: str) -> bool:
    """判断字符串中是否包含中文、英文字符"""
    pattern = re.compile(r'[\u4e00-\u9fa5a-zA-Z]+')  # 匹配中文字符的正则表达式
    return bool(pattern.search(str(text)))


if __name__ == '__main__':
    print(is_contains_chinese_en("213"))
