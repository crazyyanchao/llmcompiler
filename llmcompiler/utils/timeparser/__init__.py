# -*- coding: utf-8 -*-
# @Author : Junhui Yu
# @File : __init__.py.py
# @Time : 2022/10/25 10:44


from .helper import set_logger

logging = set_logger(level='INFO', log_dir_name='.timeparser_logs')


from .time_parser import *
from .extractor import *


from .time_extractor import TimeExtractor

parse_time = TimeParser()
extract_time = TimeExtractor()


extractor = Extractor()
extract_parentheses = extractor.extract_parentheses
remove_parentheses = extractor.remove_parentheses
