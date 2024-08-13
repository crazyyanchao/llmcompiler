from dotenv import load_dotenv

from llmcompiler.tools.basic import Tools

load_dotenv()

from llmcompiler.result.chat import ChatRequest
from langchain_openai.chat_models.base import ChatOpenAI
from llmcompiler.chat.run import RunLLMCompiler

# chat = ChatRequest(message="宁德时代的股票代码是什么？")
# chat = ChatRequest(message="场内基金有哪些列出20支！")
# chat = ChatRequest(message="520990.SH持仓情况")
# chat = ChatRequest(message="What's ((3*(4+5)/0.5)+3245) + 8? What's 32/4.23? What's the sum of those two values?")
# chat = ChatRequest(message=" ((3*(4+5)/0.5)+3245)加8等于多少？32除以4.23是多少？他们乘积除以二是多少？")
chat = ChatRequest(
    message="1. What is the result of ((3*(4+5)/0.5)+3245) plus 8, and what is the result when divided by 100? Calculate the results of the two values separately, then find their average."
            "2. What is 32 divided by 4.23, and what is their product? Calculate their average!"
            "3. What is the product of all the averages divided by two?")

# chat = ChatRequest(message=" ((3*(4+5)/0.5)+3245)加8等于多少？他们乘积除以二是多少？")

# tools 是基于 Langchain BaseTool 的列表。
# 默认配置仅用于演示，建议继承BaseTool来实现Tool，这样可以更好地控制一些细节。
# 对于多参数依赖，可以继承 DAGFlowParams，实现参考为`llmcompiler/tools/basetool/fund_basic.py`。
# tools = Tools.load_tools("../llmcompiler/tools/basetool/fund_basic_v1.py")
tools = Tools.load_tools("../llmcompiler/tools/math")
print(tools)

# 支持BaseLanguageModel的实现类。
llm = ChatOpenAI(model="gpt-4o", temperature=0, max_retries=3)

llm_compiler = RunLLMCompiler(chat, tools, llm)
# 运行完整的LLMCompiler过程
print(llm_compiler())

# 忽略Joiner过程，将Task与执行结果直接返回
# print(llm_compiler.runWithoutJoiner())

