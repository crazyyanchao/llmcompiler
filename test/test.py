from dotenv import load_dotenv

load_dotenv()

from llmcompiler.tools.basic import Tools
from llmcompiler.result.chat import ChatRequest
from langchain_openai.chat_models.base import ChatOpenAI
from llmcompiler.chat.run import RunLLMCompiler

# chat = ChatRequest(message="How has the return been for Tech stocks since their inception?")
# tools = Tools.load_tools(["../llmcompiler/tools/basetool/stock_info_fake.py",
#                           "../llmcompiler/tools/basetool/multi_param_dep_v1.py"])

chat = ChatRequest(message="How has the return been for Tech stocks since their inception?")
tools = Tools.load_tools(["../llmcompiler/tools/basetool/stock_info_fake.py",
                          "../llmcompiler/tools/basetool/multi_param_dep_v2.py"])

# chat = ChatRequest(
#     message="How has the return been for Tech stocks since their inception? Calculate the average return of tech stocks.")
# tools = Tools.load_tools(["../llmcompiler/tools/math",
#                           "../llmcompiler/tools/basetool/stock_info_fake.py",
#                           "../llmcompiler/tools/basetool/multi_param_dep_v3.py"])

print(tools)

llm = ChatOpenAI(model="gpt-4o", temperature=0, max_retries=3)

llm_compiler = RunLLMCompiler(chat, tools, llm)
print(llm_compiler())

# llm_compiler.runWithoutJoiner()
