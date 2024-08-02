# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import json
import os
from abc import ABC, abstractmethod
from typing import List, Dict
from typing import Sequence
from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, \
    HumanMessagePromptTemplate

from llmcompiler.few_shot.few_shot import BaseFewShot
from llmcompiler.graph.prompt import HUMAN_MESSAGE_TEMPLATE
from llmcompiler.utils.date.date import formatted_dt_now
from llmcompiler.utils.timeparser import TimeExtractor


class BaseRewrite(ABC):
    """The base rewrite interface."""

    @abstractmethod
    def info(self, text: str) -> List[BaseMessage]:
        """Rewrite user input and outputs a list of messages."""


SYSTEM_TEMPLATE = f"""你是由易方达基金创造的金融领域专家同时精通自然语言处理NLP技术，而且非常擅长使用工具解决问题。
你可以基于用户问题、相关信息、参考计划、可选工具、备注说明，生成一个专业且简洁的找数据的最少执行计划。
你的目标是遵循备注说明的内容，在不改变原有用户问题含义的情况下对用户问题生成执行计划。
"""

HUMAN_TEMPLATE = f"""**用户问题**
{{question}}

**相关信息**
{{info}}

**参考计划**
{{examples}}

**可选工具**
{{tools}}

**备注说明**
生成计划时需要详细列出要查找哪些数据，每个计划的开头一般都是`查找`，结尾一般需要列出可以使用的工具，备选工具已经在**可选工具**中列出，使用工具时可能需要一些必要参数请将这些参数列出来。
生成计划时请充分参考相关信息中列出的内容，确保每个计划都补充了上下文信息，不要有冗余的执行计划。
特别要注意如果相关信息中有基金代码需要补充到生成的执行计划中。
现在的时间是：{formatted_dt_now()}，执行计划中的时间词注意替换为具体时间。
相关信息中可能包含除了时间信息外一些其它重要内容，你可以充分利用。
闲聊类问题不需要给出执行计划。
不要说出需要使用哪些找数据工具、数据源、第三方平台工具、查找官网等等信息。
不要说出任何抱歉、对不起、根据提供的信息等等与找数据没关系的语句。
不需要尝试回答问题，也不要给出任何分析后的结果。
最终的响应内容包含<用户问题>、<执行计划>两项即可。
去掉用户问题中关于结果形式的描述。

Let’s think step by step!"""


def examples(text: str, few_shot: BaseFewShot) -> str:
    """
    基于用户问题获取样例计划
    """
    if few_shot:
        result = few_shot.get(question=text)
        re_list = result.data
        text_info = ""
        size = len(re_list)
        for index, re in enumerate(re_list):
            example = str(re["question"]).strip("\n ")
            if index + 1 == size:
                text_info += example
            else:
                text_info += example + "\n"
        return text_info
    else:
        return ""


def inputs_format_message(text: str, few_shot: BaseFewShot, time_parser: bool = True) -> Dict:
    """
    Extract time information and obtain example plan.
    """
    info = []
    if time_parser:
        time_info_1 = time_info_time_parser(text)
        time_info = f"Time information related to user questions: {json.dumps(time_info_1, ensure_ascii=False)}" if time_info_1 else ""
        info.append(time_info)
    few_shot = examples(text, few_shot)
    inputs = {"question": text,
              "info": "\n".join(info),
              "examples": few_shot
              }
    return inputs


def time_info_time_parser(text: str) -> List:
    """从文本抽取时间信息"""
    time_info_1 = []
    time_info_2 = []
    temp_time_words = []
    extract_time = TimeExtractor()
    res = extract_time("\n".join([text]))
    for re in res:
        txt = re["text"]
        type = re["type"]
        time = re["detail"]["time"]
        dat = {"text": txt, "type": type, "time": time}
        if txt not in temp_time_words:
            if txt in text and dat not in time_info_1:
                time_info_1.append(dat)
            else:
                time_info_2.append(dat)
            temp_time_words.append(txt)
    return time_info_1


# RESPONSE_PLAN_FORMAT_PREFIX = """下面列出了用户问题以及解决问题需要的执行计划，请充分参考执行计划的步骤解决用户问题，执行计划中列出的工具至少需要调用一次，解析Action时请认真检查。
# """

RESPONSE_PLAN_FORMAT_PREFIX = """下面列出了解决用户问题需要参考的执行计划，请充分参考执行计划的步骤生成`Plan`。
"""

RESPONSE_PLAN_FORMAT_SUFFIX = """\nLet’s think step by step!"""

# RESPONSE_PLAN_FORMAT = f"""{RESPONSE_PLAN_FORMAT_PREFIX}
# **用户问题**
# {{question}}
#
# **执行计划**
# {{plan}}
# """

REWRITE_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate(
            prompt=PromptTemplate(input_variables=[], template=SYSTEM_TEMPLATE)),
        HumanMessagePromptTemplate(
            prompt=PromptTemplate(input_variables=["date", "question"],
                                  template=HUMAN_TEMPLATE)
        )
    ]
)

REWRITE_INFO_PROMPT = PromptTemplate.from_template(HUMAN_MESSAGE_TEMPLATE)


class Rewrite(BaseRewrite):

    def __init__(self, few_shot: BaseFewShot, llm: BaseLanguageModel = None, tools: Sequence[BaseTool] = None):
        self.llm = llm
        self.tools = tools
        self.few_shot = few_shot

    def info(self, message) -> List[HumanMessage]:
        """
        User questions Add more background information.
        """
        print("================================ Rewriter Without LLM ================================")
        try:
            kwargs = inputs_format_message(text=message, few_shot=self.few_shot, time_parser=True)
            new_message = REWRITE_INFO_PROMPT.format(info=kwargs['info'], examples=kwargs['examples'], question=message)
            print(new_message)
            return [HumanMessage(content=new_message)]
        except ValueError:
            return [HumanMessage(content=message)]

    # def info(self, message) -> List[BaseMessage]:
    #     """
    #     添加多轮消息
    #     USER: Q
    #     ASSISTANT: A
    #     USER: Q
    #     ASSISTANT: A
    #     USER: Q
    #     """
    #     try:
    #         messages = []
    #         kwargs = inputs_format_message(message, self.examples_num)
    #         messages.append(HumanMessage(content=f"{message}"))
    #         messages.append(AIMessage(
    #             content="与用户问题相关的信息有哪些？请列出时间相关信息、实体以及关联信息，生成`Plan`时这些内容可能会作为常量使用。"))
    #         messages.append(HumanMessage(content=kwargs['info']))
    #         messages.append(
    #             AIMessage(content="与用户问题相关的参考计划有哪些？请列出这些参考计划，在生成`Plan`时需要参考。"))
    #         messages.append(HumanMessage(content=kwargs['examples']))
    #         return messages
    #     except ValueError:
    #         return [HumanMessage(content=message)]
