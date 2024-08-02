# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, PromptTemplate, \
    HumanMessagePromptTemplate

FILTER_TOOLS_SYSTEM_TEMPLATE = """你可以基于用户问题将给出的工具列表按照和问题的相关性进行排序。
给出的工具列表可以用以解决用户问题，请仔细分析问题然后按照指定的输出格式输出一个排序后的工具列表。

**用户问题**
{question}

**工具列表**
{tool_descriptions}

**输出格式**
```json
[{{
        "tool": string,\ 工具名称
        "score": float,\ 相关性得分
    }}
]
```

Let’s think step by step!"""

FILTER_TOOLS_USER_TEMPLATE = """
请输出排序后的(TOP-N)前`{top_k}`个工具列表：
"""

FILTER_TOOLS_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate(
            prompt=PromptTemplate(input_variables=["question", "tool_descriptions"],
                                  template=FILTER_TOOLS_SYSTEM_TEMPLATE)),
        HumanMessagePromptTemplate(
            prompt=PromptTemplate(input_variables=['top_k'], template=FILTER_TOOLS_USER_TEMPLATE)
        )
    ]
)
