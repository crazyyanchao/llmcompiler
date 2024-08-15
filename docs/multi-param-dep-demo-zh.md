# LLMCompiler参数依赖实现案例

&emsp;LLMCompiler支持对参数依赖的完全控制。在这个演示中，展示了参数依赖问题的多种解决方式。Tool实现时需要注意的是，当前的Tool不需要指定参数依赖时，可以继承`BaseTool`
来实现Tool；在需要指定参数依赖，可以继承 `CompilerBaseTool`。（需要注意的是案例中Tool的实现都是模拟接口）

## 案例一：在Tool实现中处理依赖参数

&emsp;在这个案例中`stock_info_fake.py`使用股票名称、股票代码、股票类型获取股票代码和成立日期等基本信息，`multi_param_dep_v1.py`通过股票代码、日期获取股票收益率数据。
因此`stock_info_fake.py`中需要定义参数依赖，它输出的股票代码和成立日期需要支持被`multi_param_dep_v1.py`使用，所以实现中继承了`CompilerBaseTool`，并在返回的`ActionOutput`中加入了`dag_kwargs`参数。
`dag_kwargs`参数的值由`self.flow`函数打包，这个函数支持将调取的接口结果以`BaseModel`、`DataFrame`、`Dict`等传入，并使用`dag_flow_kwargs`中定义的字段进行打包（包装后被依赖的参数值通常为列表格式，如果需要修改为其它格式需要自定义`dag_kwargs`
参数）。

&emsp;`multi_param_dep_v1.py`的实现中，`data`函数每次只支持处理一组`code,date`参数，因此在上游依赖为列表格式时，需要单独在`tool`的`_run`函数中实现列表参数的处理。

- 代码实现调用案例

```python
from llmcompiler.tools.basic import Tools
from llmcompiler.result.chat import ChatRequest
from langchain_openai.chat_models.base import ChatOpenAI
from llmcompiler.chat.run import RunLLMCompiler

chat = ChatRequest(message="How has the return been for Tech stocks since their inception?")

tools = Tools.load_tools(["../llmcompiler/tools/basetool/stock_info_fake.py",
                          "../llmcompiler/tools/basetool/multi_param_dep_v1.py"])
print(tools)

llm = ChatOpenAI(model="gpt-4o", temperature=0, max_retries=3)

llm_compiler = RunLLMCompiler(chat, tools, llm)
print(llm_compiler())
```

- `stock_info_fake.py`源码
```python
import logging
from pydantic import Field, BaseModel
from typing import List, Optional, Type, Any

from llmcompiler.tools.basic import CompilerBaseTool
from llmcompiler.tools.configure.pydantic_oper import field_descriptions_join
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
    code: Optional[str] = Field(default=None, description="stock code")
    date: Optional[str] = Field(default=None, description="establishment date")


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
    dag_flow_kwargs: List[str] = ['code', 'date']

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
                    results.append(InfoOutputSchema(name=info['name'], code=key, date=info['establishment_date']))
            return ActionOutput(any=results, dag_kwargs=self.flow(results))
        except Exception as e:
            logger.error(str(e))
        return ActionOutputError()
```

- `multi_param_dep_v1.py`源码
```python
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
```

## 案例二：使用`@tool_call_by_row_pass_parameters`注解

&emsp;在这个案例中同样使用了`stock_info_fake.py`文件，与案例一相同不再赘述。

&emsp;`multi_param_dep_v2.py`的实现中，使用了`@tool_call_by_row_pass_parameters`注解，该注解负责将上游参数打包为一个表格然后按行执行Tool调用，并将多个结果进行自动合并。（这个用法默认当前这个Tool只支持单参数调用）

- `multi_param_dep_v2.py`源码
```python
import random
import logging

from langchain_core.tools import BaseTool
from pydantic import Field, BaseModel
from datetime import datetime, timedelta
from typing import List, Optional, Type, Any, Union

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

    @tool_call_by_row_pass_parameters
    def _run(self, **kwargs: Any) -> ActionOutput:
        """
        Handles only single-value parameters; to support list parameters and multiple calls,
            use the @pass_parameters_by_row_and_call_tool annotation.
        """
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
```



## 案例三：使用`json_schema_extra:DISABLE_ROW_CALL`参数禁用按行调用 【未实现】

## 案例四：使用`json_schema_extra:DISABLE_RESOLVED_ARGS`参数禁用参数解析【已实现】

## 案例五：使用`json_schema_extra:PARTIAL_RESOLVED_ARGS_PARSE`执行部分参数解析【已实现】


