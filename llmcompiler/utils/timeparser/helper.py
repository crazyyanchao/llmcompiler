# -*- coding: utf-8 -*-
# @Author : Junhui Yu
# @File : helper.py
# @Time : 2022/10/25 11:16

import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler

_LEVELS = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARN': logging.WARNING,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET
}


def _logging_level_from_str(level):
    level = level.upper()
    if level in _LEVELS:
        return _LEVELS[level]
    return logging.INFO


def _refresh_logger(logger):
    # 清除 logger 中的 handler
    if len(logger.handlers) != 0:
        for i in range(len(logger.handlers)):
            logger.removeHandler(logger.handlers[0])

    return logger


def bracket(regular_expression):
    return ''.join([r'(', regular_expression, r')'])


def bracket_absence(regular_expression):
    return ''.join([r'(', regular_expression, r')?'])


def absence(regular_expression):
    return ''.join([regular_expression, r'?'])


def start_end(regular_expression):
    return ''.join([r'^', regular_expression, r'$'])


def set_logger(level='INFO', log_dir_name='.time_parrser_logs'):
    # 设置日志级别
    if level is None:
        logger = logging.getLogger(__name__)
        _refresh_logger(logger)
        return logger

    level = _logging_level_from_str(level)
    logger = logging.getLogger(__name__)
    # logger 为全局变量，因此须在申请前，先将日志清除
    _refresh_logger(logger)
    logger.setLevel(level)

    # 日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")

    # 输出流控制器
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    if log_dir_name is not None:
        # 日志写入文件 hanlder
        if log_dir_name.startswith("/"):
            filename_directory = log_dir_name
        else:
            filename_directory = os.path.join(os.path.expanduser('~'), log_dir_name)
        if not os.path.exists(filename_directory):
            os.makedirs(filename_directory)

        # 文件输出控制器
        file_handler = TimedRotatingFileHandler(
            os.path.join(filename_directory, "log.txt"),
            when="midnight", backupCount=30)

        file_handler.setLevel(level)
        file_handler.suffix = "%Y%m%d"
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    length = 20
    logger.log(level, "-" * length + " logging start " + "-" * length)
    logger.log(level, "LEVEL: {}".format(logging.getLevelName(level)))
    if log_dir_name is not None:
        logger.log(level, "PATH:  {}".format(filename_directory))
    logger.log(level, "-" * (length * 2 + 15))

    logger.addHandler(stream_handler)

    return logger
