# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
from dotenv import load_dotenv

load_dotenv()

from llmcompiler.chat.run import RunLLMCompiler
from llmcompiler.custom_llms.claude import Claude3LLM
from llmcompiler.graph.token_calculate import SwitchLLM

from llmcompiler.result.chat import ChatRequest, ChatResponse
from llmcompiler.tools.tools import DefineTools
from llmcompiler.utils.date.date import formatted_dt_now
from langchain_openai.chat_models.base import ChatOpenAI

"""
1. 关于Message处理：LLM对于Message的支持方式不同，使用时如果遇到`ChatHarvestAI`报错，则可以考虑切换到自定义LLM模式。
2. 传入Tools时，继承`DefineTools`类，并重写`tools`方法即可。
3. 使用Few-shot
"""


def run(chat: ChatRequest) -> ChatResponse:
    """
    Run test.
    """
    c3_sonnet: Claude3LLM = Claude3LLM(model="anthropic.claude-3-sonnet-20240229-v1:0")
    swi_c3_sonnet = SwitchLLM(llm=c3_sonnet, max_token=200 * 1024, out_token=4 * 1024, order=3)
    default_tools = DefineTools().tools()

    compiler = RunLLMCompiler(chat, default_tools, swi_c3_sonnet, swi_c3_sonnet, c3_sonnet)

    return compiler()


if __name__ == '__main__':
    # message = "宁德时代的股票代码是什么？"
    message = "501062.SH这支基金的管理人是谁？"
    # message = "501062.SH这支基金的成立日期之后的第二年四季度，持仓情况怎么样？"
    # message = "场内发行中的基金有哪些？"
    chat = ChatRequest(message=message, session_id="session-id0", create_time=formatted_dt_now())

    tools = DefineTools().tools()
    llm = ChatOpenAI(model="gpt-4o", temperature=0, max_retries=3)
    llm_compiler = RunLLMCompiler(chat, tools, llm)

    result = llm_compiler()
    # result = run(chat)

    print(result)
