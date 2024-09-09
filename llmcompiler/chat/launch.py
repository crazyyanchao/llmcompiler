# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import os
from abc import abstractmethod, ABC
from typing import List, Union, Dict, Tuple, Any

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import ChatMessage
from langchain_core.tools import BaseTool
from langgraph.constants import END
from langgraph.graph.graph import CompiledGraph
from langchain.prompts import PromptTemplate

from llmcompiler.few_shot.few_shot import BaseFewShot
from llmcompiler.graph.output_parser import Task
from llmcompiler.graph.plan_and_schedule import PlanAndSchedule
from llmcompiler.graph.rewrite import Rewrite
from llmcompiler.graph.token_calculate import SwitchLLM
from llmcompiler.result.chat import ChatResponse, ChatRequest
from llmcompiler.tools.generic.action_output import Chart, Source

OUTPUT_TEMPLATE = "I've considered {iteration} times and still don't fully understand your question. Could you ask the question in another way? If there are relevant charts or data you can refer to temporarily."


class Launch(ABC):
    """
    初始化：定义planer、joiner、re_planer可以使用的候选模型，定义tools列表，定义Few-shot库ID
    init：初始化图
    run：运行图，传入Request对象，额外需要携带的流式参数stream_kwargs
    """

    def __init__(self, chat: ChatRequest, tools: List[BaseTool],
                 llm: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]] = None,
                 planer: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]] = None,
                 joiner: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]] = None,
                 re_planer: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]] = None,
                 multi_dialogue: bool = False, debug_prompt: bool = False, few_shot: BaseFewShot = None,
                 print_graph: bool = True, print_dag: bool = True,
                 custom_prompts: dict[str, str] = None):
        """
        初始化必要参数。
        :param chat: 请求对象
        :param planer: 可供planer使用的LLM。
        :param joiner: 可供joiner使用的LLM。
        :param tools: 可供LLM调用的Tools。
        :param re_planer: 可供re_planer使用的LLM。
        :param multi_dialogue: 支持多轮默认关闭<预留参数>。
        :param debug_prompt: DEBUG提示词预留参数。
        :param few_shot: Few-shot对象。
        :param print_graph: LLMCompiler的LangGrap结构可视化语法是否打印。
        :param print_dag: 任务的有向无环图可视化语法是否打印。
        :param custom_prompts: 自定义提示词。
        """
        self.few_shot = few_shot
        self.chat = chat
        self.multi_dialogue = multi_dialogue
        self.debug_prompt = debug_prompt
        self.custom_prompts = custom_prompts

        self.swi_re_planer = None
        self.swi_joiner = None
        self.swi_planer = None
        self.init_llm(llm, planer, joiner, re_planer)

        if tools is None:
            from llmcompiler.tools.tools import DefineTools
            self.tools = DefineTools().tools()
        else:
            self.tools = tools

        self.print_graph = print_graph
        self.print_dag = print_dag

        self.rewrite = Rewrite(llm=llm, tools=tools, few_shot=few_shot, custom_prompts=custom_prompts)
        if self.swi_planer:
            self.plan_and_schedule = PlanAndSchedule(self.swi_planer, self.tools, self.swi_re_planer, self.print_dag, self.custom_prompts)
        else:
            raise Exception("Planer is not initialized!")

    def __call__(self, recursion_limit: int = 2) -> ChatResponse:
        """
        :param recursion_limit: Agent的迭代次数，例如设置为2表示迭代思考2次。
        """
        return self.run(recursion_limit)

    def init_llm(self, llm: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]] = None,
                 planer: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]] = None,
                 joiner: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]] = None,
                 re_planer: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]] = None):
        """
        Initialized LLMs.
        """
        if planer:
            self.swi_planer = planer
        else:
            self.swi_planer = llm

        if joiner:
            self.swi_joiner = joiner
        else:
            self.swi_joiner = llm

        if re_planer:
            self.swi_re_planer = re_planer
        else:
            if planer:
                self.swi_re_planer = planer
            else:
                self.swi_re_planer = llm

        if not self.swi_planer:
            raise Exception("Planer is not initialized!")
        if not self.swi_joiner:
            raise Exception("Joiner is not initialized!")
        if not self.swi_re_planer:
            raise Exception("RePlaner is not initialized!")

    @abstractmethod
    def init(self, *args: Any, **kwargs: Any) -> CompiledGraph:
        """
        Initialize the graph and define the graph structure.
        """

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> ChatResponse:
        """Run graph."""

    @abstractmethod
    def initWithoutJoiner(self, *args: Any, **kwargs: Any) -> CompiledGraph:
        """
        Initialize the graph and define the graph structure.
        """

    @abstractmethod
    def runWithoutJoiner(self) -> List[Tuple[Task, Any]]:
        """Run graph without joiner,returns the task and task execution result."""

    def response_str(self, final_step: Dict, charts: List[Chart], iteration: int) -> str:
        if 'join' in final_step:
            message = final_step['join'][-1]
            if 'Error Answer' == final_step['join'][-1].content or \
                    'API request failed after maximum retries' == message.content:
                return OUTPUT_TEMPLATE.format(iteration=iteration)
            elif isinstance(message, ChatMessage):
                return OUTPUT_TEMPLATE.format(iteration=iteration)
            else:
                output = final_step['join'][-1].content
                return self.reset_output(self.response_str_check_tool(output), charts)
        elif END in final_step:
            output = final_step[END][-1].content
            return self.reset_output(self.response_str_check_tool(output), charts)
        else:
            return OUTPUT_TEMPLATE.format(iteration=iteration)

    def response_str_check_tool(self, output: str) -> str:
        """
        输出中如果包含工具名称重置输出
        """
        for tool in self.tools:
            if tool.name in output:
                return OUTPUT_TEMPLATE
        return output

    def response(self, query: str, response: str, charts: List[Chart], source: List[Source], labels: List[str]):
        """
        最终响应内容处理
        TODO
        """
        return ChatResponse(response=response, charts=charts, source=source, labels=labels)

    def reset_output(self, output: str, charts: List[Chart]) -> str:
        """
        重置输出结果：如果返回的图表对象中存在定义的模板描述，则按照模板描述返回最终响应
        """
        chart_texts = [chart.text for chart in charts if chart.text and chart.text_join_response]
        if chart_texts:
            return "".join(set(chart_texts))
        else:
            return output

    def expand(self, value: List[Chart], charts: List[Chart], source: List[Source], labels: List[str]):
        """
        处理中间结果
        """
        # Action返回结果
        if isinstance(value, Chart):
            self.expand_ele(value, charts, source, labels)
        elif isinstance(value, List):
            for chart in value:
                if isinstance(chart, Chart):
                    self.expand_ele(chart, charts, source, labels)

    def expand_ele(self, value: Chart, charts: List[Chart], source: List[Source], labels: List[str]):
        """
        处理中间结果
        """
        if value not in charts:
            charts.append(value)
        for sor in value.source:
            if sor not in source:
                source.append(sor)
        for lb in value.labels:
            if lb not in labels:
                labels.append(lb)
