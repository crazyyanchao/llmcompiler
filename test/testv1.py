from llmcompiler.result.chat import ChatRequest
from llmcompiler.tools.tools import DefineTools
from langchain_openai.chat_models.base import ChatOpenAI
from llmcompiler.chat.run import RunLLMCompiler

chat = ChatRequest(message="<YOUR_MESSAGE>")

# tools 是基于 Langchain BaseTool 的列表。
# 默认配置仅用于演示，建议继承BaseTool来实现Tool，这样可以更好地控制一些细节。
# 对于多参数依赖，可以继承 DAGFlowParams，实现参考为`llmcompiler/tools/basetool/fund_basic.py`。 
tools = DefineTools().tools()

# 支持BaseLanguageModel的实现类。
llm = ChatOpenAI(model="gpt-4o", temperature=0, max_retries=3)

llm_compiler = RunLLMCompiler(chat, tools, llm)
# 运行完整的LLMCompiler过程
print(llm_compiler())

# 忽略Joiner过程，将Task与执行结果直接返回
print(llm_compiler.runWithoutJoiner())

# 更多使用方式可以在`issue`中讨论，后续还会继续完善文档。
