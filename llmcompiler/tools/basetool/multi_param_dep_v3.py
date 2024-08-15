# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-14 10:14:16
"""
import random
import logging

from pydantic import Field, BaseModel
from datetime import datetime, timedelta
from typing import List, Optional, Type, Any, Union

from llmcompiler.tools.basic import CompilerBaseTool
from llmcompiler.tools.configure.pydantic_oper import field_descriptions_join
from llmcompiler.tools.configure.tool_decorator import tool_call_by_row_pass_parameters
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


class StockReturnFake(CompilerBaseTool):
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
    args_schema: Type[ReturnInputSchema] = ReturnInputSchema

    output_model: Type[BaseModel] = ReturnOutputSchema
    dag_flow_kwargs: List[str] = ['stock_return']

    @tool_call_by_row_pass_parameters(detect_disable_row_call=False)
    def _run(self, **kwargs: Any) -> ActionOutput:
        """
        Handles only single-value parameters; to support list parameters and multiple calls,
            use the @pass_parameters_by_row_and_call_tool annotation.
        """
        result = self.args_schema.model_validate(kwargs)
        code = result.code
        date_str = result.date
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        returns = []

        # Assuming there are 10 days of return data.
        for i in range(10):
            current_date = start_date + timedelta(days=i)
            # Simulate random fluctuations in returns ranging from -5% to 5%.
            daily_return = round(random.uniform(-0.05, 0.05), 4)
            returns.append(
                ReturnOutputSchema(code=code, date=current_date.strftime('%Y-%m-%d'), stock_return=daily_return))

        return ActionOutput(any=returns, msg='Test.', source=[Source(title='Test.')], labels=['Label'],
                            dag_kwargs=self.flow(returns))
