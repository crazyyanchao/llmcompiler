# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import math
import re
import logging
from typing import List, Optional, Type, Union

import numexpr
from langchain.chains.openai_functions import create_structured_output_runnable
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import Field, BaseModel
from langchain_core.pydantic_v1 import BaseModel as LangBaseModel
from langchain_core.pydantic_v1 import Field as LangField
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from llmcompiler.tools.basic import CompilerBaseTool
from llmcompiler.tools.dag.dag_flow_params import DISABLE_RESOLVED_ARGS, PARTIAL_RESOLVED_ARGS_PARSE
from llmcompiler.tools.generic.action_output import ActionOutput, ActionOutputError

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    raise ImportError(
        "The 'python-dotenv' package is required to use this class. Please install it using 'pip install python-dotenv'.")

_MATH_DESCRIPTION = (
    "math(problem: str, context: Optional[list[str]]) -> float:\n"
    " - Solves the provided math problem.\n"
    ' - `problem` can be either a simple math problem (e.g. "1 + 3") or a word problem (e.g. "how many apples are there if there are 3 apples and 2 apples").\n'
    " - You cannot calculate multiple expressions in one call. For instance, `math('1 + 3, 2 + 4')` does not work. "
    "If you need to calculate multiple expressions, you need to call them separately like `math('1 + 3')` and then `math('2 + 4')`\n"
    " - Minimize the number of `math` actions as much as possible. For instance, instead of calling "
    '2. math("what is the 10% of $1") and then call 3. math("$1 + $2"), '
    'you MUST call 2. math("what is the 110% of $1") instead, which will reduce the number of math actions.\n'
    # Context specific rules below
    " - You can optionally provide a list of strings as `context` to help the agent solve the problem. "
    "If there are multiple contexts you need to answer the question, you can provide them as a list of strings.\n"
    " - `math` action will not see the output of the previous actions unless you provide it as `context`. "
    "You MUST provide the output of the previous actions as `context` if you need to do math on it.\n"
    " - You MUST NEVER provide `search` type action's outputs as a variable in the `problem` argument. "
    "This is because `search` returns a text blob that contains the information about the entity, not a number or value. "
    "Therefore, when you need to provide an output of `search` action, you MUST provide it as a `context` argument to `math` action. "
    'For example, 1. search("Barack Obama") and then 2. math("age of $1") is NEVER allowed. '
    'Use 2. math("age of Barack Obama", context=["$1"]) instead.\n'
    " - When you ask a question about `context`, specify the units. "
    'For instance, "what is xx in height?" or "what is xx in millions?" instead of "what is xx?"\n'
)

_SYSTEM_PROMPT = """Translate a math problem into a expression that can be executed using Python's numexpr library. Use the output of running this code to answer the question.

Question: ${{Question with math problem.}}
```text
${{single line mathematical expression that solves the problem}}
```
...numexpr.evaluate(text)...
```output
${{Output of running the code}}
```
Answer: ${{Answer}}

Begin.

Question: What is 37593 * 67?
ExecuteCode({{code: "37593 * 67"}})
...numexpr.evaluate("37593 * 67")...
```output
2518731
```
Answer: 2518731

Question: 37593^(1/5)
ExecuteCode({{code: "37593**(1/5)"}})
...numexpr.evaluate("37593**(1/5)")...
```output
8.222831614237718
```
Answer: 8.222831614237718
"""

_ADDITIONAL_CONTEXT_PROMPT = """The following additional context is provided from other functions.\
    Use it to substitute into any ${{#}} variables or other words in the problem.\
    \n\n${context}\n\nNote that context variables are not defined in code yet.\
You must extract the relevant numbers and directly put them in code."""


class ExecuteCode(LangBaseModel):
    """The input to the numexpr.evaluate() function."""

    reasoning: str = LangField(
        ...,
        description="The reasoning behind the code expression, including how context is included, if applicable.",
    )

    code: str = LangField(
        ...,
        description="The simple code expression to execute by numexpr.evaluate().",
    )


def _evaluate_expression(expression: str) -> str:
    try:
        local_dict = {"pi": math.pi, "e": math.e}
        output = str(
            numexpr.evaluate(
                expression.strip(),
                global_dict={},  # restrict access to globals
                local_dict=local_dict,  # add common mathematical functions
            )
        )
    except Exception as e:
        raise ValueError(
            f'Failed to evaluate "{expression}". Raised error: {repr(e)}.'
            " Please try again with a valid numerical expression"
        )

    # Remove any leading and trailing brackets from the output
    return re.sub(r"^\[|\]$", "", output)


def get_math_tool(llm: BaseLanguageModel):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            ("user", "{problem}"),
            MessagesPlaceholder(variable_name="context", optional=True),
        ]
    )
    extractor = create_structured_output_runnable(ExecuteCode, llm, prompt)

    def calculate_expression(
            problem: str,
            context: Optional[List[str]] = None,
            config: Optional[RunnableConfig] = None,
    ):
        chain_input = {"problem": problem}
        if context:
            context_str = "\n".join(context)
            if context_str.strip():
                context_str = _ADDITIONAL_CONTEXT_PROMPT.format(
                    context=context_str.strip()
                )
                chain_input["context"] = [SystemMessage(content=context_str)]
        code_model = extractor.invoke(chain_input, config)
        try:
            return _evaluate_expression(code_model.code)
        except Exception as e:
            return repr(e)

    return StructuredTool.from_function(
        name="math",
        func=calculate_expression,
        description=_MATH_DESCRIPTION,
    )


# def get_math_tool_define() -> StructuredTool:
#     return get_math_tool(ChatOpenAI(model="gpt-4o", temperature=0, max_retries=3))


PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("user", "{problem}"),
        MessagesPlaceholder(variable_name="context", optional=True),
    ]
)
EXTRACTOR = create_structured_output_runnable(ExecuteCode,
                                              ChatOpenAI(model="gpt-4o", temperature=0, max_retries=3),
                                              PROMPT, enforce_function_usage=False, mode="openai-tools")


class InputSchema(BaseModel):
    # problem: str = Field(description="简单的数学问题", json_schema_extra=DISABLE_RESOLVED_ARGS)
    problem: str = Field(description="简单的数学问题", json_schema_extra=PARTIAL_RESOLVED_ARGS_PARSE)
    context: Optional[List] = Field(default=None, description="提供额外的上下文信息，帮助解决数学问题")


class OutputSchema(BaseModel):
    value: Union[int, float] = Field(default=None, description="计算结果")


class Math(CompilerBaseTool):
    name = "math"
    description = _MATH_DESCRIPTION
    args_schema: Type[BaseModel] = InputSchema

    output_model: Type[BaseModel] = OutputSchema
    dag_flow_kwargs: List[str] = ['value']

    def _run(self, problem: str, context: Optional[List] = None) -> ActionOutput:
        """Use the tool."""
        chain_input = {"problem": problem}
        if context:
            f_string = "\n"
            context_str = f_string.join([
                f'The output of the {index + 1} calculation: {f_string.join([str(xt) for xt in cxt]) if isinstance(cxt, list) else str(cxt)}'
                for index, cxt in enumerate(context)
            ])
            if context_str.strip():
                context_str = _ADDITIONAL_CONTEXT_PROMPT.format(
                    context=context_str.strip()
                )
                chain_input["context"] = [SystemMessage(content=context_str)]
        code_model = EXTRACTOR.invoke(chain_input)
        try:
            value = _evaluate_expression(code_model.code)
            output = OutputSchema(value=value)
            return ActionOutput(any=output, dag_kwargs=self.flow(output))
        except Exception as e:
            logger.error(str(e))
        return ActionOutputError()


if __name__ == '__main__':
    info = Math()
    print(info.name)
    print(info.description)
    print(info.args)
    print(info.dag_flow_paras())
    # print(info._run(problem='sum of $1 and $2', context=[[3307], [7.565011820330969]]))
    print(info._run(problem='average of [0.0088, -0.0494, -0.0311, 0.0181, -0.0134, -0.0463, -0.0202, 0.0391, 0.0433, 0.0204, 0.0354, 0.033, -0.0493, 0.007, -0.0354, -0.0482, -0.0306, 0.0121, -0.0147, -0.0159, -0.0478, 0.0451, 0.038, 0.0055, -0.0283, 0.0117, -0.041, -0.047, -0.03, -0.0409]'))
