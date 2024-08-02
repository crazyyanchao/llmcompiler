# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
from typing import List, Sequence

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class ToolCallStatus(BaseModel):
    tool_name: str = Field(description="工具名称")
    status: bool = Field(default=False, description="工具调用状态")
    text: str = Field(default="", description="工具相关的文本信息")


class ToolsCall(BaseModel):
    call_status: List[ToolCallStatus] = Field(description="工具调用状态列表")

    def not_call(self) -> List[ToolCallStatus]:
        """
        未调用工具列表
        """
        return [tool for tool in self.call_status if not tool.status]

    def update(self, tool_name: str):
        """
        更新工具调用状态
        """
        for tool in self.call_status:
            if tool.tool_name == tool_name:
                tool.status = True
                break

    def next_call(self) -> str:
        """
        没有被调用的工具作为提示添加到Prompt
        """
        cls = self.not_call()
        if cls:
            return f"The next action may require invoking the `{cls[0].tool_name}` tool.Task is:<{cls[0].text}>"
        return ""

    def complete_call(self):
        """
        工具是否被全部调用
        """
        call = [call for call in self.call_status if not call.status]
        if call:
            return False
        else:
            return True

    def count(self) -> int:
        return len(self.call_status)


def init_base_call_tools(text: str, tools: Sequence[BaseTool]) -> ToolsCall:
    """
    初始化需要调用的工具列表
    """
    call = []
    text_split = text.split('\n')
    for txt in text_split:
        if txt is not None and '' != txt:
            base_call = long_match_tool(txt, tools)
            if base_call is not None:
                call.append(base_call)
    return ToolsCall(call_status=call)


def long_match_tool(text: str, tools: Sequence[BaseTool]) -> ToolCallStatus:
    """
    匹配Tool-Name按照Tool-Name长度降序排序拿First
    """
    call = []
    for tool in tools:
        if tool.name in text:
            call.append(ToolCallStatus(tool_name=tool.name, text=text))
    sorted_contents = sorted(call, key=lambda x: len(x.tool_name), reverse=True)
    if sorted_contents:
        return sorted_contents[0]
