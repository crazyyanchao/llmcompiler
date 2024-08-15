# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-14 10:14:16
"""
import random
import logging
from concurrent.futures import ThreadPoolExecutor

from langchain_core.tools import BaseTool
from pydantic import Field, BaseModel
from datetime import datetime, timedelta
from typing import List, Optional, Type, Union

from llmcompiler.tools.configure.pydantic_oper import field_descriptions_join
from llmcompiler.tools.configure.tool_decorator import kwargs_convert_df
from llmcompiler.tools.generic.action_output import ActionOutput, Source
from llmcompiler.tools.generic.render_description import render_text_description
from llmcompiler.utils.thread.pool_executor import max_worker

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

    def _run(self, code: Union[str, List[str]], date: Union[str, List[str]]) -> ActionOutput:
        """Handle the LIST parameter separately in the input."""
        df = kwargs_convert_df({'code': code, 'date': date})
        # Iterate through each row and print as a dictionary
        params = []
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            params.append(row_dict)
            print(row_dict)

        with ThreadPoolExecutor(max_workers=max_worker()) as executor:
            results = list(executor.map(lambda x: self.data(**x), params))

        return ActionOutput(any=results, msg='Test.', source=[Source(title='Test.')], labels=['Label'])

    def data(self, **kwargs) -> List[ReturnOutputSchema]:
        """Fake: obtain the return using the code and date."""
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
        return returns
