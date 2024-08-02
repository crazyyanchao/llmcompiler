# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import math
import re
from typing import List, Optional

import numexpr
from langchain.chains.openai_functions import create_structured_output_runnable
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool

from llmcompiler.custom_llms.openai_compiler import OpenaicompilerLLM

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


class ExecuteCode(BaseModel):
    """The input to the numexpr.evaluate() function."""

    reasoning: str = Field(
        ...,
        description="The reasoning behind the code expression, including how context is included, if applicable.",
    )

    code: str = Field(
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


if __name__ == '__main__':
    gpt4o: OpenaicompilerLLM = \
        OpenaicompilerLLM(temperature=0, type="compiler-gpt-4o", model="gpt-4o", model_name="compiler-gpt-4o",
                        max_retries=3)
    get_math_tool(gpt4o).invoke(
        input={"problem": "What's ((3*(4+5)/0.5)+3245) + 8? What's 32/4.23? What's the sum of those two values?"})
