# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import re
import logging
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langchain_core.utils.json import parse_json_markdown
from langchain.chains.llm import LLMChain
from langchain_core.output_parsers import BaseLLMOutputParser
from langchain_core.output_parsers.base import T
from langchain_core.outputs import Generation
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import AIMessage, ChatMessage
from typing import List, Union, Sequence

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from llmcompiler.graph.prompt import JOINER_SYSTEM_PROMPT_1, JOINER_SYSTEM_PROMPT_2, JOINER_RESPONSE_HUMAN_TEMPLATE
from llmcompiler.utils.date.date import formatted_dt_now
from llmcompiler.utils.string.question_trim import extract_json_dict
from llmcompiler.graph.token_calculate import SwitchLLM, auto_switch_llm

PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate(
            prompt=PromptTemplate(input_variables=[], template=JOINER_SYSTEM_PROMPT_1)),
        MessagesPlaceholder(variable_name='messages'),
        SystemMessagePromptTemplate(
            prompt=PromptTemplate(input_variables=[], template=JOINER_SYSTEM_PROMPT_2)),
    ]
)


class FinalResponse(BaseModel):
    """The final response/answer."""
    response: str = Field(description="Final Answer")


class Replan(BaseModel):
    feedback: str = Field(
        description="Analysis of the previous attempts and recommendations on what needs to be fixed."
    )


class JoinOutputs(BaseModel):
    """Decide whether to replan or whether you can return the final response."""
    thought: str = Field(
        description="The chain of thought reasoning for the selected action"
    )
    action: Union[FinalResponse, Replan]


class Joiner:
    """
    Joiner: Responds to the user or triggers a second plan
    """

    def __init__(self, llm: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]], tools: Sequence[BaseTool], question: str):
        self.llm = llm
        self.tools = tools
        self.question = question

    def init(self, messages: list):
        # print(PROMPT.pretty_print())
        tool_descriptions = "\n".join(
            f"{i + 1}. {tool.name}: {tool.description} args: {str(tool.args)}\n"
            for
            i, tool in enumerate(self.tools)
            # +1 to offset the 0 starting index, we want it count normally from 1.
        )
        prompt = PROMPT.partial(
            tools=tool_descriptions,
            formatted_dt_now=formatted_dt_now()
        )  # You can optionally add examples
        messages = self.select_recent_messages(messages)
        llm = auto_switch_llm(self.llm, [prompt, messages])
        chain: LLMChain = LLMChain(llm=llm, prompt=prompt, output_parser=JoinerParser(self.tools), verbose=False)
        response = chain.invoke(input=messages)
        return response['text']

    def select_recent_messages(self, messages: list) -> dict:
        selected = []
        for msg in messages[::-1]:
            selected.append(msg)
            if isinstance(msg, HumanMessage):
                # 重置HumanMessage引导模型生成更贴合用户问题的回复文本
                msg.content = self.joiner_message_template()
                break
            # Chat Message是从Joiner决定Replan时加入的，再次进行Joiner时不需要保留额外信息所以重置content
            elif isinstance(msg, ChatMessage):
                msg.content = "Let’s think step by step!"
        return {"messages": selected[::-1]}

    def joiner_message_template(self):
        """
        指定Joiner阶段固定的用户消息模板
        """
        REWRITE_INFO_PROMPT = PromptTemplate.from_template(JOINER_RESPONSE_HUMAN_TEMPLATE)
        new_message = REWRITE_INFO_PROMPT.format(question=self.question)
        return new_message


class JoinerParser(BaseLLMOutputParser):

    def __init__(self, tools: Sequence[BaseTool] = None):
        self.tools = tools

    def parse_result(self, result: List[Generation], *, partial: bool = False) -> T:
        decision = self.parse_text_to_join_outputs(result[0].text)
        return self._parse_joiner_output(decision)

    def parse_text_to_join_outputs(self, text: str) -> JoinOutputs:
        """
        Thought & Action - 解析
        """
        try:
            print("================================ Joiner ================================")
            print(text)
            response = parse_json_markdown(text)
            thought = response.get('_thought_', 'Let’s think step by step!')
            if '_finish_' in response:
                response = response.get('_finish_', '')
                return JoinOutputs(thought=thought, action=FinalResponse(response=response))
            else:
                feedback = response.get('_replan_', '')
                return JoinOutputs(thought=thought, action=Replan(feedback=feedback))
        except:
            return self.parse_text(text)

    def parse_text(self, text: str) -> JoinOutputs:
        try:
            # 匹配
            json_dict = extract_json_dict(text)
            if json_dict is not None:
                if '_finish_' in json_dict:
                    return JoinOutputs(thought=json_dict.get('_thought_', ''),
                                       action=FinalResponse(response=json_dict.get('_finish_', '')))
                elif '_replan_' in json_dict:
                    return JoinOutputs(thought=json_dict.get('_thought_', ''),
                                       action=Replan(feedback=json_dict.get('_replan_', '')))
            # 字符串处理
            if "_finish_" in text:
                return self.parse_final_answer(text)
            elif "_replan_" in text:
                return self.parse_action(text)
            elif any(tool for tool in list(self.tools) if tool.name in text):
                return JoinOutputs(thought="Let’s think step by step!", action=Replan(feedback=text))
            elif '_thought_' not in text and '_finish_' not in text and '_replan_' not in text:
                return JoinOutputs(thought="Let’s think step by step!", action=FinalResponse(response=text))
        except Exception as e:
            logging.error(f"Could not parse LLM output: {text}\n{str(e)}")
        return JoinOutputs(thought="Let’s think step by step!", action=FinalResponse(response="Error Answer"))

    def parse_final_answer(self, text: str) -> JoinOutputs:
        """
        使用规则解析Final Answer
        """

        def escape_json_strings(text: str) -> JoinOutputs:
            response = text.split("_finish_")[1]
            response = re.sub(r'^[^a-zA-Z0-9\u4e00-\u9fa5]+|[^a-zA-Z0-9\u4e00-\u9fa5]+$', '', response)
            return JoinOutputs(thought="Let’s think step by step!", action=FinalResponse(response=response))

        json_texts = re.findall(r'json\n({.*?})\n', text, re.DOTALL)
        actions = [escape_json_strings(json_text) for json_text in json_texts]
        if actions:
            return actions[0]
        else:
            array = text.split('_finish_')

            _thought_ = ''
            for pie in array[0].split(':')[1:]:
                _thought_ += pie
            _thought_ = _thought_.strip('" \n{},，')

            _finish_ = ''
            for pie in array[1].split(':')[1:]:
                _finish_ += pie
            _finish_ = _finish_.strip('" \n{},，')
            return JoinOutputs(thought=_thought_, action=FinalResponse(response=_finish_))

    def parse_action(self, text: str) -> JoinOutputs:
        """
        使用规则解析Action
        """

        def escape_json_strings(text: str) -> JoinOutputs:
            feedback = text.split("_replan_")[1]
            feedback = re.sub(r'^[^a-zA-Z0-9\u4e00-\u9fa5]+|[^a-zA-Z0-9\u4e00-\u9fa5]+$', '', feedback)
            return JoinOutputs(thought="thinking...", action=Replan(feedback=feedback))

        json_texts = re.findall(r'json\n({.*?})\n', text, re.DOTALL)
        actions = [escape_json_strings(json_text) for json_text in json_texts]
        if actions:
            return actions[0]
        else:
            array = text.split('_replan_')

            _thought_ = ''
            for pie in array[0].split(':')[1:]:
                _thought_ += pie
            _thought_ = _thought_.strip('" \n{},，')

            _replan_ = ''
            for pie in array[1].split(':')[1:]:
                _replan_ += pie
            _replan_ = _replan_.strip('" \n{},，')
            return JoinOutputs(thought=_thought_, action=Replan(feedback=_replan_))

    def _parse_joiner_output(self, decision: JoinOutputs) -> List[BaseMessage]:
        response = [AIMessage(content=f"Thought: {decision.thought}")]
        if isinstance(decision.action, Replan):
            system_message = SystemMessage(content=f"\nContext from last attempt: {decision.action.feedback}\n\n")
            chat_message = ChatMessage(role="user", content="Let’s think step by step!")
            response.append(system_message)
            response.append(chat_message)
            return response
        else:
            return response + [AIMessage(content=decision.action.response)]


if __name__ == '__main__':
    parser = JoinerParser()
    text = """
    fund_nav_accumulated_1(code="000751.OF", query_month="36")
    """
    result = parser.parse_text_to_join_outputs(text=text)
    print(result.json(ensure_ascii=False))
