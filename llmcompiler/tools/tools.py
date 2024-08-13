# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple

import numpy as np
from langchain.chains.llm import LLMChain
from langchain_core.language_models import BaseLanguageModel
from langchain.tools import BaseTool
from langchain_openai import OpenAIEmbeddings
from pydantic import Field, BaseModel

from llmcompiler.graph.token_calculate import openai_gpt_model_token
from llmcompiler.custom_llms.claude import Claude3LLM
from llmcompiler.result.chat import ChatRequest
from llmcompiler.tools.basetool.fund_basic_v1 import FundBasicV1
from llmcompiler.tools.basetool.tool_decorator import stock_basic, fund_portfolio
from llmcompiler.tools.basic import Tools
from llmcompiler.tools.dag.dag_flow_params import DAGFlowParams
from llmcompiler.tools.generic.render_description import TOOL_DESC_JOIN_EXAMPLES_MARK
from llmcompiler.tools.prompt import FILTER_TOOLS_PROMPT
from llmcompiler.utils.thread.pool_executor import max_worker

logger = logging.getLogger(__name__)


class ToolEmbedding(BaseModel):
    tool: BaseTool = Field(description="Tool")
    embedding: List[float] = Field(description="向量表示")
    similarity: float = Field(default=0.0, description="与Query计算的相似度数值")
    dag_flow: bool = Field(default=False, description="当前Tool是否定义了依赖参数")


class DefineTools(Tools):
    """
    自定义工具列表
    """

    def __init__(self, chat: ChatRequest = None):
        if chat is None:
            chat = ChatRequest()
        self.chat = chat

    def tools(self) -> List[BaseTool]:
        """可使用的Tools列表"""
        define_tools = [
            # FundBasic(),
            FundBasicV1(),
            fund_portfolio,
            stock_basic
        ]
        logger.info(f"A total of {len(define_tools)} Tools are configured.")
        return define_tools

    def filter(self, top_k: int = 15, top_k_percent: float = None,
               filter_out_dag_flow_tools: bool = False, resort_top_k: bool = False) -> List[BaseTool]:
        """
        基于问题获取过滤后Tools
        :param top_k: 定义需要过滤的Top-K
        :param top_k_percent: 定义需要过滤的Tools百分比，如果定义该参数则Top-k则会被覆盖
        :param filter_out_dag_flow_tools: 是否将具有参数依赖的Tools默认添加到最终结果中，不参与过滤
        :param resort_top_k: 是否重排序合并后的结果
        """
        # Tools计算嵌入后动态排序
        EMBD = OpenAIEmbeddings(model="text-embedding-3-small", max_retries=2)
        emb_query = EMBD.embed_query(self.chat.message)
        tools_emb = self.tools_embedding()
        top_k = self.top_k(tool_size=len(tools_emb), top_k=top_k, top_k_percent=top_k_percent)
        with ThreadPoolExecutor(max_workers=max_worker()) as executor:
            results = list(executor.map(lambda x: self.cal_query_similarity(x, emb_query), tools_emb))
        # 排序后先获取Top-K，然后再基于dag_flow参数判断是否添加模型的Tool
        sorted_tools = sorted(results, key=lambda x: x.similarity, reverse=True)
        top_k_tools_emb = [x for x in sorted_tools[:top_k]]
        if filter_out_dag_flow_tools:
            for tool in tools_emb:
                if tool.dag_flow and tool not in top_k_tools_emb:
                    top_k_tools_emb.insert(0, tool)
            # 重排序Tools
            if resort_top_k:
                top_k_tools = [x.tool for x in sorted(top_k_tools_emb, key=lambda x: x.similarity, reverse=True)]
            else:
                top_k_tools = [x.tool for x in top_k_tools_emb]
        else:
            top_k_tools = [x.tool for x in top_k_tools_emb]
        logger.info("\n".join(
            [f"The Result Filtered From {len(self.tools())} Tools:"] +
            [f"{index + 1}. {tool.name}" for index, tool in enumerate(top_k_tools)] + ["---"]))
        return top_k_tools

    def llm_filter(self, llm: BaseLanguageModel, top_k: int = 15, top_k_percent: float = None):
        """使用大模型排序Tools"""
        start_time = time.time()
        desc, tools = self.tools_desc()
        top_k = self.top_k(tool_size=len(tools), top_k=top_k, top_k_percent=top_k_percent)
        print(FILTER_TOOLS_PROMPT.pretty_print())
        chain: LLMChain = LLMChain(llm=llm, prompt=FILTER_TOOLS_PROMPT, verbose=False)
        inputs = {"question": self.chat.message, "tool_descriptions": desc, "top_k": top_k}
        response = chain.invoke(input=inputs)
        print(
            f"==========================过滤Tools：{round(time.time() - start_time, 2)}秒==========================")
        # print("================================ Rewriter ================================")
        print(response['text'])

    def top_k(self, tool_size: int, top_k: int, top_k_percent: float) -> int:
        """计算Top-K数量"""
        if top_k_percent is not None:
            if top_k_percent > 1:
                logger.error("Top-K percent must be less than or equal to 1.")
            else:
                top_k = round(tool_size * top_k_percent)
        return top_k

    def tools_embedding(self) -> List[ToolEmbedding]:
        """所有Tools计算Embedding"""
        texts = [f"{self.tool_description(tool.description)} {self.tool_args(tool.args)}" for tool in self.tools()]
        EMBD = OpenAIEmbeddings(model="text-embedding-3-small", max_retries=2)
        embeddings = EMBD.embed_documents(texts)
        return [ToolEmbedding(tool=tool, embedding=embeddings[index], dag_flow=isinstance(tool, DAGFlowParams))
                for index, tool in enumerate(self.tools())]

    def tool_description(self, description: str) -> str:
        """Tools描述信息处理"""
        if TOOL_DESC_JOIN_EXAMPLES_MARK in description:
            return description.split(TOOL_DESC_JOIN_EXAMPLES_MARK)[0]
        else:
            return description

    def tool_args(self, kwargs: Dict[str, Dict]) -> str:
        """Tools入参描述信息处理"""
        text = ""
        for key, value in kwargs.items():
            text += f"Parameter:{key},meaning:{value.get('description', '')}."
        return text

    def cal_query_similarity(self, tool: ToolEmbedding, emb_query: List[float]) -> ToolEmbedding:
        """计算相似度"""
        # tool_text = f"{tool.name}: {tool.description} args: {str(tool.args)}"
        similarity = np.dot(tool.embedding, emb_query)
        tool.similarity = similarity
        return tool

    def print(self, tools: List[BaseTool]) -> None:
        for index, tool in enumerate(tools):
            print(f"--- {index}. {tool.name}")
            print(f"--- {index}. {tool.description}")
            print(f"--- {index}. {tool.args}")

    def tools_desc(self) -> Tuple[str, List[BaseTool]]:
        """获取所有Tools的描述信息"""
        tool_desc_list = []
        tools = self.tools()
        for i, tool in enumerate(tools):
            tool_desc = "\n"
            tool_desc += f"{i + 1}. **Tool Name**: `{tool.name}`\n"
            tool_desc += f"**Description**:\n {tool.description} args: {str(tool.args)}"
            if isinstance(tool, DAGFlowParams):
                tool_desc += f"\n**Output Parameters that can be used by other tools**:\n{json.dumps([flow.dict() for flow in tool.dag_flow_paras()], ensure_ascii=False)}"
            tool_desc_list.append(tool_desc)
        tool_descriptions = "\n".join(tool_desc_list)
        return tool_descriptions, tools

    def token(self) -> int:
        """估算Tools占有的Token数量"""
        token = openai_gpt_model_token(self.tools_desc()[0], 'gpt-4')[0]
        logger.warning(f"Tokens: {token}")
        return token


if __name__ == '__main__':
    # tools = DefineTools()
    # 查找定义过DAG FLOW参数的Tools
    # tls = tools.tools()
    # for tl in tls:
    #     if isinstance(tl, DAGFlowParams) and isinstance(tl, BaseTool):
    #         print(f"--- {tl.name}")
    # tls = DefineTools(ChatRequest(message='易方达汇鑫的产品信息')) \
    #     .filter(top_k_percent=0.6, filter_out_dag_flow_tools=True)
    # tools.print(tls)
    # tools.token()

    tools = DefineTools(
        ChatRequest(message='汇鑫中短债成立以来单位净值、累计净值情况；易方达新兴产业最近三年收益率和单位净值'))
    c3_sonnet: Claude3LLM = Claude3LLM(model="anthropic.claude-3-sonnet-20240229-v1:0")
    c3_opus: Claude3LLM = Claude3LLM(model="anthropic.claude-3-opus-20240229-v1:0")
    # tools.llm_filter(gpt4_32K)
    tools.tools_embedding()
