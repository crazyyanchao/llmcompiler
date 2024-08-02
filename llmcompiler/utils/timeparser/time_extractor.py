# -*- coding: utf-8 -*-
# @Author : Junhui Yu
# @File : time_extractor.py
# @Time : 2022/10/26 11:13

import re
import time

from .rule_pattern import TIME_CHAR_STRING, \
    FAKE_POSITIVE_START_STRING, FAKE_POSITIVE_END_STRING
from .chinese_parser import extract_parentheses, remove_parentheses
from .time_parser import TimeParser


class TimeExtractor(object):
    """ 贪心算法，时间实体抽取器。"""


    def __init__(self):
        self.parse_time = None

    def _prepare(self):
        self.parse_time = TimeParser()
        self.time_string_pattern = re.compile(TIME_CHAR_STRING)  # 该正则存在假阴风险

        self.fake_positive_start_pattern = re.compile(FAKE_POSITIVE_START_STRING)
        self.fake_positive_end_pattern = re.compile(FAKE_POSITIVE_END_STRING)

        # 此类表达虽然可按时间解析，但是文本中很大概率并非表示时间，故以大概率进行排除，
        # 并设参数 ret_all，即返回所有进行控制，默认为 False，即根据词典进行删除
        self.non_time_string_list = [
            '一点', '0时', '一日', '黎明', '十分', '百分', '万分']
        # 一点也不大方、一日之计在于晨、黎明主演电影、

        self.num_pattern = re.compile(r'[０-９0-9]')
        self.four_num_year_pattern = re.compile(r'^[\d]{4}$')
        self.unit_pattern = re.compile(r'(多)?[万亿元]')  # 四数字后接单位，说明非年份

        self.single_char_time = set(['春', '夏', '秋', '冬'])

    def __call__(self, text, time_base=time.time(), with_parsing=True, ret_all=False,
                 ret_type='str', ret_future=False, period_results_num=None):
        if self.parse_time is None:
            self._prepare()

        candidates_list = self.extract_time_candidates(text)

        time_entity_list = list()
        for candidate in candidates_list:
            offset = [0, 0]
            bias = 0
            while candidate['offset'][0] + offset[1] < candidate['offset'][1]:
                # 此循环意在找出同一个 candidate 中包含的多个 time_entity

                true_string, result, offset = self.grid_search(
                    candidate['time_candidate'][bias:], time_base=time_base,
                    ret_type=ret_type, ret_future=ret_future,
                    period_results_num=period_results_num)

                if true_string is not None:

                    # rule 1: 判断字符串是否为大概率非时间语义
                    if (true_string in self.non_time_string_list) and (not ret_all):
                        bias += offset[1]
                        continue

                    # rule 2: 判断四数字 ”2033“ 是否后接货币、非年份量词
                    if self.four_num_year_pattern.search(true_string):
                        back_start = candidate['offset'][0] + bias + offset[1]
                        if self.unit_pattern.search(text[back_start: back_start + 2]):
                            # 说明非真实年份，跳回
                            bias += offset[1]
                            continue

                    if with_parsing:
                        time_entity_list.append(
                            {'text': true_string,
                             'offset': [candidate['offset'][0] + bias + offset[0],
                                        candidate['offset'][0] + bias + offset[1]],
                             'type': result['type'],
                             'detail': result})
                    else:
                        time_entity_list.append(
                            {'text': true_string,
                             'offset': [candidate['offset'][0] + bias + offset[0],
                                        candidate['offset'][0] + bias + offset[1]],
                             'type': result['type']})
                    bias += offset[1]
                else:
                    break

        # for item in time_entity_list:
        #     assert item['text'] == text[item['offset'][0]: item['offset'][1]]
        #     print(item)
        return time_entity_list

    def _filter(self, sub_string):
        """ 对某些易造成实体错误的字符进行过滤。
        此问题产生的原因在于，parse_time 工具对某些不符合要求的字符串也能成功解析，造成假阳性。
        """
        if self.fake_positive_start_pattern.search(sub_string[0]):
            return False

        if self.fake_positive_end_pattern.search(sub_string[-1]):
            return False

        if len(sub_string) != len(sub_string.strip()):
            return False

        # 的 不可以在句首或句尾
        if '的' in sub_string[0] or '的' in sub_string[-1]:
            return False

        # 括号造成的边界错误
        if sub_string[0] in ')）' or sub_string[-1] in '(（':
            return False

        return True

    def _grid_search_1(self, time_candidate):
        """ 取消 parse_time 中 strict 限制，从长至短，先左后右依次缩短 time_candidate，
        直到解析错误或解析结果出错
        """

    def grid_search(self, time_candidate, time_base=time.time(),
                    ret_type='str', ret_future=False, period_results_num=None):
        """ 全面搜索候选时间字符串，从长至短，较优 """
        length = len(time_candidate)
        for i in range(length):  # 控制总长，若想控制单字符的串也被返回考察，此时改为 length + 1
            for j in range(i):  # 控制偏移
                try:
                    offset = [j, length - i + j + 1]
                    sub_string = time_candidate[j: offset[1]]

                    # 处理假阳性。检查子串，对某些产生歧义的内容进行过滤。
                    # 原因在于，parse_time 会对某些不符合要求的字符串做正确解析.
                    if not self._filter(sub_string):
                        continue

                    # rule 3: 若子串中包含 ”的“ 字会对结果产生影响，则先将 ”的“ 字删除后再进行解析。
                    sub_string_for_parse = sub_string.replace('的', '')

                    # rule 4: 字符串中若包含空格，会对结果产生影响，则先将 “ ” 删除后解析。
                    sub_string_for_parse = sub_string_for_parse.replace(' ', '')

                    # rule 5: 对于一些特殊的补充性时间字符串，也需要特殊对待，将括号去除后再进行解析。
                    # 一般为 周 对 日的补充，如“2021年11月1日（下周一晚）19:30-20:30”
                    # 该规则依然简陋，稳定性不够好
                    sub_parentheses = extract_parentheses(sub_string_for_parse, parentheses='()（）')
                    if '周' in ''.join(sub_parentheses) or '星期' in ''.join(sub_parentheses):
                        sub_string_for_parse = remove_parentheses(sub_string_for_parse, parentheses='()（）')

                    # rule 6: 对于数字为起始或结尾的字符串，过滤之。
                    # 如：342127197212178212 将 2017 和 1972 抽取为年份
                    if self.num_pattern.search(sub_string_for_parse[0]):
                        if j - 1 >= 0:
                            if self.num_pattern.search(time_candidate[j - 1]):
                                continue
                    if self.num_pattern.search(sub_string_for_parse[-1]):
                        if offset[1] < length:
                            if self.num_pattern.search(time_candidate[offset[1]]):
                                continue

                    result = self.parse_time(
                        sub_string_for_parse, time_base=time_base, strict=True,
                        ret_type=ret_type, ret_future=ret_future,
                        period_results_num=period_results_num)

                    return sub_string, result, offset
                except (ValueError, Exception):
                    continue

        return None, None, None

    def _grid_search_2(self, time_candidate):
        """ 全面搜索候选时间字符串，从前至后，从长至短 """
        print(time_candidate)
        length = len(time_candidate)
        for i in range(length - 1):  # 控制起始点
            for j in range(length, i, -1):  # 控制终止点
                try:
                    offset = [i, j]
                    sub_string = time_candidate[i: j]
                    print(sub_string)
                    # 处理假阳性。检查子串，对某些产生歧义的内容进行过滤。
                    # 原因在于，parse_time 会对某些不符合要求的字符串做正确解析.
                    if not TimeExtractor._filter(sub_string):
                        continue

                    result = self.parse_time(sub_string, strict=True)

                    return sub_string, result, offset
                except (ValueError, Exception):
                    continue

        return None, None, None

    def extract_time_candidates(self, text):
        """ 获取所有的候选时间字符串，其中包含了时间实体 """
        text_length = len(text)
        idx_count = 0
        time_candidates_list = list()
        while idx_count < text_length:
            matched_res = self.time_string_pattern.search(text[idx_count:])
            # print(matched_res)
            if matched_res is not None:
                if len(matched_res.group()) > 1:
                    time_candidates_list.append(
                        {'time_candidate': matched_res.group(),
                         'offset': [idx_count + matched_res.span()[0],
                                    idx_count + matched_res.span()[1]]})
                elif matched_res.group() in self.single_char_time:
                    # 可能误打 “春”、“夏” 等单字符时间表达，故在此加入
                    time_candidates_list.append(
                        {'time_candidate': matched_res.group(),
                         'offset': [idx_count + matched_res.span()[0],
                                    idx_count + matched_res.span()[1]]})
                idx_count += matched_res.span()[1]
            else:
                break

        return time_candidates_list


if __name__ == '__main__':
    text = '''
        过去5天涨幅小于-15%'''

    extract_time = TimeExtractor()
    res = extract_time(text, with_parsing=False)
    print(res)
