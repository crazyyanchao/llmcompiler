# -*- coding: utf-8 -*-
# @Author : Junhui Yu
# @File : extractor.py
# @Time : 2022/10/25 12:20

import re

from .rule_pattern import *

__all__ = ['Extractor']


class Extractor(object):
    """ 规则抽取器 """

    def __init__(self):
        self.money_pattern = None
        self.email_pattern = None
        self.email_domain_pattern = None
        self.email_prefix_pattern = None
        self.url_pattern = None
        self.phone_number_pattern = None
        self.ip_address_pattern = None
        self.id_card_pattern = None
        self.html_tag_pattern = None
        self.qq_pattern = None
        self.strict_qq_pattern = None
        self.wechat_id_pattern = None
        self.strict_wechat_id_pattern = None
        self.cell_phone_pattern = None
        self.landline_phone_pattern = None
        self.phone_prefix_pattern = None
        self.extract_parentheses_pattern = None
        self.remove_parentheses_pattern = None
        self.parentheses_pattern = PARENTHESES_PATTERN
        self.parentheses_dict = None
        self.redundant_pattern = None
        self.exception_pattern = None
        self.full_angle_pattern = None
        self.chinese_char_pattern = None
        self.chinese_chars_pattern = None

    @staticmethod
    def _extract_base(pattern, text, with_offset=False):
        if with_offset:
            results = [{'text': item.group(1),
                        'offset': (item.span()[0] - 1, item.span()[1] - 1)}
                       for item in pattern.finditer(text)]
        else:
            results = [item.group(1) for item in pattern.finditer(text)]

        return results

    def remove_redundant_char(self, text, redundant_chars=None):
        if self.redundant_pattern is None:
            pattern_list = list()
            if redundant_chars is None:
                redundant_chars = REDUNDANT_PATTERN

            for char in redundant_chars:
                pattern_tmp = '(?<={char}){char}+'.format(
                    char=re.escape(char))
                pattern_list.append(pattern_tmp)

            redundant_pattern = '|'.join(pattern_list)
            self.redundant_pattern = re.compile(redundant_pattern)

        return self.redundant_pattern.sub('', text)

    def clean_text(self, text, remove_html_tag=True,
                   convert_full2half=True,
                   remove_exception_char=True, remove_url=True,
                   remove_redundant_char=True, remove_parentheses=True,
                   remove_email=True, remove_phone_number=True,
                   delete_prefix=False, redundant_chars=None):

        if remove_redundant_char:
            text = self.remove_redundant_char(
                text, redundant_chars=redundant_chars)
        if remove_parentheses:
            text = self.remove_parentheses(text)

        return text

    def remove_parentheses(self, text, parentheses=PARENTHESES_PATTERN):
        if self.remove_parentheses_pattern is None or self.parentheses_pattern != parentheses:
            self.parentheses_pattern = parentheses

            p_length = len(self.parentheses_pattern)
            remove_pattern_list = list()
            remove_pattern_format = '{left}[^{left}{right}]*{right}'

            for i in range(0, p_length, 2):
                left = re.escape(self.parentheses_pattern[i])
                right = re.escape(self.parentheses_pattern[i + 1])
                remove_pattern_list.append(
                    remove_pattern_format.format(left=left, right=right))

            remove_pattern = '|'.join(remove_pattern_list)
            remove_pattern = re.compile(remove_pattern)

            self.remove_parentheses_pattern = remove_pattern

        length = len(text)
        while True:
            text = self.remove_parentheses_pattern.sub('', text)
            if len(text) == length:
                return text
            length = len(text)

    def extract_parentheses(self, text, parentheses=PARENTHESES_PATTERN, detail=False):
        if self.extract_parentheses_pattern is None or self.parentheses_pattern != parentheses:
            self.parentheses_pattern = parentheses

            extract_pattern = '[' + re.escape(self.parentheses_pattern) + ']'
            extract_pattern = re.compile(extract_pattern)

            p_length = len(self.parentheses_pattern)

            parentheses_dict = dict()
            for i in range(0, p_length, 2):
                value = self.parentheses_pattern[i]
                key = self.parentheses_pattern[i + 1]
                parentheses_dict.update({key: value})

            self.parentheses_dict = parentheses_dict
            self.extract_parentheses_pattern = extract_pattern

        content_list = list()
        parentheses_list = list()
        idx_list = list()
        finditer = self.extract_parentheses_pattern.finditer(text)
        for i in finditer:
            idx = i.start()
            parentheses = text[idx]

            if parentheses in self.parentheses_dict.keys():
                if len(parentheses_list) > 0:
                    if parentheses_list[-1] == self.parentheses_dict[parentheses]:
                        parentheses_list.pop()
                        if detail:
                            start_idx = idx_list.pop()
                            end_idx = idx + 1
                            content_list.append(
                                {'content': text[start_idx: end_idx],
                                 'offset': (start_idx, end_idx)})
                        else:
                            content_list.append(text[idx_list.pop(): idx + 1])
            else:
                parentheses_list.append(parentheses)
                idx_list.append(idx)

        return content_list
