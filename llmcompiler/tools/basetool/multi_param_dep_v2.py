# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-14 10:14:16
"""
import random
import logging

from langchain_core.tools import BaseTool
from pydantic import Field, BaseModel
from datetime import datetime, timedelta
from typing import List, Optional, Type, Any, Union

from llmcompiler.tools.configure.pydantic_oper import field_descriptions_join
from llmcompiler.tools.configure.tool_decorator import tool_call_by_row_pass_parameters, \
    tool_symbol_separated_string, tool_remove_suffix, tool_remove_prefix, tool_string_spilt, tool_timeout
from llmcompiler.tools.generic.action_output import ActionOutput, Source
from llmcompiler.tools.generic.render_description import render_text_description

logger = logging.getLogger(__name__)


class ReturnInputSchema(BaseModel):
    """If the upstream dependency parameter is a list, LIST validation needs to be supported here."""
    code: Union[str, List[str]] = Field(description="stock code")
    date: Union[str, List[str]] = Field(description="date,format `%Y-%m-%d`")


class ReturnOutputSchema(BaseModel):
    code: Optional[str] = Field(default=None, description="stock code")
    date: Optional[str] = Field(default=None, description="date")
    stock_return: Optional[float] = Field(default=None, description="stock return")


class StockReturnFake(BaseTool):
    """
    This tool for demonstration inherits from BaseTool
        because it does not need to define parameters that downstream components can depend on.
    """
    name = "stock_return_fake"
    description = render_text_description(
        "Function: Retrieve stock return."
        f"Input parameters: {field_descriptions_join(ReturnInputSchema)}"
        f"Return values: {field_descriptions_join(ReturnOutputSchema)}"
    )
    args_schema: Type[BaseModel] = ReturnInputSchema

    # @tool_call_by_row_pass_parameters(detect_disable_row_call=False, fill_non_list_row=True, limit=2)
    # @tool_symbol_separated_string(fields=['code'])
    # @tool_remove_suffix(fields=['code'], suffix=['PL', 'GL', 'FT'])
    # @tool_remove_prefix(fields=['code'], prefix=['AA', 'GO', 'MS'])
    # @tool_string_spilt(fields=['code'], split='O', index=2)
    @tool_timeout(4)
    def _run(self, **kwargs: Any) -> ActionOutput:
        """
        Handles only single-value parameters; to support list parameters and multiple calls,
            use the @pass_parameters_by_row_and_call_tool annotation.
        """
        import time
        time.sleep(3)
        code = kwargs.get('code', '')
        date_str = kwargs.get('date', '')
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        returns = []

        # Assuming there are 10 days of return data.
        for i in range(10):
            current_date = start_date + timedelta(days=i)
            # Simulate random fluctuations in returns ranging from -5% to 5%.
            daily_return = round(random.uniform(-0.05, 0.05), 4)
            returns.append(
                ReturnOutputSchema(code=code, date=current_date.strftime('%Y-%m-%d'), stock_return=daily_return))

        return ActionOutput(any=returns, msg='Test.', source=[Source(title='Test.')], labels=['Label'])
