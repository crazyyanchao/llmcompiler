# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-14 10:14:16
"""
import logging
import random

from pydantic import Field, BaseModel
from typing import List, Optional, Type, Any

from llmcompiler.tools.basic import CompilerBaseTool
from llmcompiler.tools.configure.pydantic_oper import field_descriptions_join
from llmcompiler.tools.dag.dag_flow_params import DISABLE_ROW_CALL, DISABLE_FILL_NON_LIST_ROW
from llmcompiler.tools.generic.action_output import ActionOutput, ActionOutputError
from llmcompiler.tools.generic.render_description import render_text_description

logger = logging.getLogger(__name__)

# Simulated stock data.
STOCK_DATA = {
    'AAPL': {'name': 'Apple', 'type': 'Tech', 'establishment_date': '1980-12-12'},
    'GOOGL': {'name': 'Google', 'type': 'Tech', 'establishment_date': '2004-08-19'},
    'MSFT': {'name': 'Microsoft', 'type': 'Tech', 'establishment_date': '1986-03-13'},
    'JPM': {'name': 'JPMorgan Chase', 'type': 'Finance', 'establishment_date': '1969-12-31'},
    'BRK.B': {'name': 'Berkshire Hathaway', 'type': 'Finance', 'establishment_date': '1980-11-20'},
}


class InfoInputSchema(BaseModel):
    name: Optional[str] = Field(default=None, description="stock name")
    code: Optional[str] = Field(default=None, description="stock code")
    type: Optional[str] = Field(default=None, description="stock type")


class InfoOutputSchema(BaseModel):
    name: Optional[str] = Field(default=None, description="stock name")
    code: Optional[str] = Field(default=None, description="stock code", json_schema_extra=DISABLE_ROW_CALL)
    date: Optional[str] = Field(default=None, description="establishment date")
    type: Optional[str] = Field(default=None, description="stock type", json_schema_extra=DISABLE_FILL_NON_LIST_ROW)


class StockInfoFake(CompilerBaseTool):
    """
    This tool for demonstration inherits from CompilerBaseTool
        because it needs to define parameters that downstream components can depend on.
    """
    name = "stock_info_fake"
    description = render_text_description(
        "Function: Retrieve basic stock information."
        f"Input parameters: {field_descriptions_join(InfoInputSchema)}"
        f"Return values: {field_descriptions_join(InfoOutputSchema)}"
    )
    args_schema: Type[BaseModel] = InfoInputSchema

    output_model: Type[BaseModel] = InfoOutputSchema
    dag_flow_kwargs: List[str] = ['code', 'date', 'stream']

    def _run(self, **kwargs: Any) -> ActionOutput:
        try:
            if not kwargs:
                raise ValueError('Not passing any parameters is not allowed.')
            results = []
            name = kwargs.get('name', '').lower()
            code = kwargs.get('code', '').lower()
            type = kwargs.get('type', '').lower()
            for key, info in STOCK_DATA.items():
                if info['name'].lower() == name or key.lower() == code or info['type'].lower() == type:
                    results.append(InfoOutputSchema(name=info['name'],
                                                    code=key,
                                                    date=info['establishment_date'],
                                                    type=random.choice(['China', 'USA', ''])))
            return ActionOutput(any=results, dag_kwargs=self.flow(results))
        except Exception as e:
            logger.error(str(e))
        return ActionOutputError()
