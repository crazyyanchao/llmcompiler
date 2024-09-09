# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import json
from typing import Sequence, List, Union

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableBranch
from langchain_core.tools import BaseTool
from langchain_core.messages import (
    SystemMessage, ToolMessage, BaseMessage, HumanMessage,
)
from llmcompiler.graph.output_parser import LLMCompilerPlanParser
from llmcompiler.graph.prompt import PLANER_SYSTEM_PROMPT_1, PLANER_SYSTEM_PROMPT_2
from llmcompiler.tools.dag.dag_flow_params import DAGFlowParams
from llmcompiler.utils.date.date import formatted_dt_now
from llmcompiler.graph.token_calculate import SwitchLLM, auto_switch_llm
from llmcompiler.utils.prompt.prompt import get_custom_or_default


class Planer:
    """
    Planner accepts the input question and generates a task list to execute.
    """

    def __init__(self, llm: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]],
                 tools: Sequence[BaseTool],
                 re_llm: Union[SwitchLLM, List[SwitchLLM]] = None,
                 custom_prompts: dict[str, str] = None):
        self.llm = llm
        self.re_llm = re_llm
        if re_llm is None:
            self.re_llm = llm
        self.tools = tools
        self.custom_prompts = custom_prompts

    def init(self):
        base_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate(
                    prompt=PromptTemplate(input_variables=[''], template=get_custom_or_default(self.custom_prompts, "PLANER_SYSTEM_PROMPT_1", PLANER_SYSTEM_PROMPT_1))),
                MessagesPlaceholder(variable_name='messages'),
                SystemMessagePromptTemplate(
                    prompt=PromptTemplate(input_variables=['examples'], template=get_custom_or_default(self.custom_prompts, "PLANER_SYSTEM_PROMPT_2", PLANER_SYSTEM_PROMPT_2))),
            ]
        )
        # print(base_prompt.pretty_print())
        tool_desc_list = []
        for i, tool in enumerate(self.tools):
            tool_desc = "\n"
            tool_desc += f"{i + 1}. **Tool Name**: `{tool.name}`\n"
            tool_desc += f"**Description**:\n {tool.description} args: {str(tool.args)}"
            if isinstance(tool, DAGFlowParams) and tool.dag_flow_paras():
                tool_desc += f"\n**Output Parameters that can be used by other tools**:\n{json.dumps([flow.dict() for flow in tool.dag_flow_paras()], ensure_ascii=False)}"
            tool_desc_list.append(tool_desc)
        tool_descriptions = "\n".join(tool_desc_list)

        dt_now = formatted_dt_now()
        planner_prompt = base_prompt.partial(
            replan="",
            num_tools=len(self.tools) + 1,  # Add one because we're adding the join() tool at the end.
            tool_descriptions=tool_descriptions,
            formatted_dt_now=dt_now,
        )
        replanner_prompt = base_prompt.partial(
            replan=' - You are given "Previous Plan" which is the plan that the previous agent created along with the execution results '
                   "(given as Observation) of each plan and a general thought (given as Thought) about the executed results."
                   'You MUST use these information to create the next plan under "Current Plan".\n'
                   ' - When starting the Current Plan, you should start with "Thought" that outlines the strategy for the next plan.\n'
                   " - In the Current Plan, you should NEVER repeat the actions that are already executed in the Previous Plan.\n"
                   " - You must continue the task index from the end of the previous one. Do not repeat task indices.",
            num_tools=len(self.tools) + 1,
            tool_descriptions=tool_descriptions,
            formatted_dt_now=dt_now,
        )

        def should_replan(state: list):
            """
            Context is passed as a system message
            state中倒数第一个或者第二个信息是SystemMessage时，说明是由Joiner处理过的信息，一般需要通过`replanner`分支处理
            """
            if len(state) == 1:
                return isinstance(state[-1], SystemMessage)
            elif len(state) > 1:
                return isinstance(state[-2], SystemMessage)
            else:
                return False

        def wrap_messages(state: list):
            return {"messages": state}

        def wrap_and_get_last_index(state: list):
            next_task = 0
            for message in state[::-1]:
                if isinstance(message, ToolMessage):
                    next_task = message.additional_kwargs["idx"] + 1
                    break
            state[-1].content = state[-1].content + f" - Begin counting at : {next_task}\n"
            return {"messages": state}

        def select_llm(prompt: PromptValue):
            messages = prompt.to_messages()
            if should_replan_llm(messages):
                llm = auto_switch_llm(self.llm, messages)
                return llm
            else:
                re_llm = auto_switch_llm(self.re_llm, messages)
                return re_llm

        def should_replan_llm(messages: List[BaseMessage]):
            """
            判断消息中倒数第一条或者第二条是否为`HumanMessage`
            """
            if len(messages) == 1:
                return isinstance(messages[-1], HumanMessage)
            elif len(messages) > 1:
                return isinstance(messages[-2], HumanMessage)
            else:
                return False

        return (
                RunnableBranch(
                    (should_replan, wrap_and_get_last_index | replanner_prompt),
                    wrap_messages | planner_prompt,
                )
                | select_llm
                | LLMCompilerPlanParser(tools=self.tools)
        )
