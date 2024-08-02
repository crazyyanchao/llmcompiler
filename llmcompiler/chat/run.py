# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import time
import logging
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph.graph import CompiledGraph
from langgraph.pregel import GraphRecursionError
from typing import List, Dict

from langgraph.graph import MessageGraph, END

from llmcompiler.chat.launch import Launch
from llmcompiler.graph.joiner import Joiner
from llmcompiler.result.chat import ChatResponse


class RunLLMCompiler(Launch):

    def init(self) -> CompiledGraph:
        """
        :param planer: 定义生成DAG时使用的LLM
        :param joiner: 定义数据处理时使用的LLM
        :param tools: 定义Tools，不传入使用默认函数获取Tools
        :param re_planer: 定义重新生成DAG时使用的LLM，不传入时默认会使用和`planer`一致的LLM（主要考虑模型的上下文Token限制时使用）
        """
        # -----------------------------------初始化工具集和Agent-----------------------------------
        start_time = time.time()
        graph_builder = MessageGraph()
        graph_builder.add_node("plan_and_schedule", self.plan_and_schedule.init)
        graph_builder.add_node("join", Joiner(self.swi_joiner, self.tools, self.chat.message).init)
        graph_builder.set_entry_point("plan_and_schedule")
        graph_builder.add_edge("plan_and_schedule", "join")
        graph_builder.add_conditional_edges(
            source="join",
            path=self.should_continue,
        )
        graph = graph_builder.compile()
        print(
            f"==========================初始化工具集和Agent：{round(time.time() - start_time, 2)}秒==========================")
        graph.get_graph().print_ascii()
        return graph

    def should_continue(self, state: List[BaseMessage]):
        if isinstance(state[-1], AIMessage):
            return END
        return "plan_and_schedule"

    def run(self) -> ChatResponse:
        """
        运行流程：数据提取Agent
        """
        run_start_time: float = time.time()
        logging.info(self.chat.message)

        # --- 编译 Graph Agent ---
        graph = self.init()

        # -----------------------------------LLMCompiler-Agent执行-----------------------------------
        start_time: float = time.time()
        charts: List = []
        source: List = []
        labels: List = []
        final_step: Dict = {}
        recursion_limit = 2 * 2 + 1  # (2*(dag+join))*(最大2次迭代)
        graph_stream = graph.stream(self.rewrite.info(self.chat.message), {'recursion_limit': recursion_limit})
        iteration = 1
        try:
            for step in graph_stream:
                print(
                    f"==========================Iteration {iteration}, {list(step.keys())}: {round(time.time() - start_time, 2)}秒==========================")
                if 'plan_and_schedule' in step:
                    chart_list = self.plan_and_schedule.charts
                    self.expand(chart_list, charts, source, labels)
                if 'join' in step:
                    # DAG - Task Fetching Unit Completed / Joiner Completed
                    iteration += 1
                final_step = step
                start_time: float = time.time()
        except GraphRecursionError as e:
            logging.error(f"{str(e)}")
        response = self.response_str(final_step, charts, iteration - 1)
        end_time = time.time()
        logging.info(f"===========AI-AGENT总和执行时间：{end_time - run_start_time} 秒~\n")
        return self.response(query=self.chat.message, response=response, charts=charts, source=source, labels=labels)