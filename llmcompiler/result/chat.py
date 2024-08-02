# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import hashlib
import json
from typing import List, Dict
from pydantic import BaseModel, Field

from llmcompiler.tools.generic.action_output import Chart, Source


class ChatRequest(BaseModel):
    """
    对话接口封装请求对象
    """
    message: str = Field(default="message", description="对话消息")
    session_id: str = Field(default="session-id", description="会话UUID")
    localhost_message_key: str = Field(default="localhost-message-key", description="localhost消息服务ID")
    create_time: str = Field(default="yyyy-MM-dd HH:mm:ss", description="对话时间")


class ChatMessage(BaseModel):
    """
    对话工具传入对象
    """
    message: str = Field(default="message", description="对话消息")
    session_id: str = Field(default="session-id", description="会话UUID")
    localhost_message_key: str = Field(default="localhost-message-key", description="localhost消息服务ID")
    stream_kwargs: Dict = Field(default={}, description="流式传输的一些必要参数")


class ChatResponse(BaseModel):
    """
    对话接口的返回信息
    """
    response: str = Field(default="", description="纯文本或者带Markdown格式的文本")
    charts: List[Chart] = Field(default=[], description="图表：表格、折线图等等...")
    source: List[Source] = Field(default=[], description="数据来源")
    labels: List[str] = Field(default=[], description="数据标签")


def message_id(chat: ChatRequest):
    """     消息的唯一ID     """
    return generate_md5(chat.message + chat.create_time)


def generate_md5(text: str):
    """
    生成MD5哈希值
    :param text:
    :return:
    """
    md5_hash = hashlib.md5()
    md5_hash.update(text.encode('utf-8'))
    md5 = md5_hash.hexdigest()
    return md5


if __name__ == '__main__':
    charts = [Chart(), Chart()]
    print(json.dumps([item.dict() for item in charts]))
