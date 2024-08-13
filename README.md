# LLMCompiler

[![English](https://img.shields.io/badge/English-Click-yellow)](README.md)
[![中文文档](https://img.shields.io/badge/中文文档-点击查看-orange)](README-zh.md)

&emsp;LLMCompiler is an Agent Architecture designed to speed up the execution of agent tasks by executing them quickly
in the DAG. It also saves the cost of redundant token use by reducing the number of calls to the LLM. The realization
inspiration comes from An LLM Compiler for Parallel Function Calling.

&emsp;Here is an example of using SQL to query data to illustrate the core role of the framework. The core process of generating an execution plan for SQL includes syntax parsing, semantic analysis, optimizer intervention, and generation of an execution plan. When LLMCompiler executes tool calls based on user instructions, it can actually be understood that LLM helps users do a process similar to SQL to generate execution plans, but the generated plan here is a DAG, and the DAG describes the call relationship between tools and the parameter dependency passing logic.

&emsp;This implementation is useful when the agent needs to call a large number of tools. If the tool you need exceeds
the context limit of the LLM, you can extend the agent node based on this tool.Divide the tool into different
agent and assemble them to create a more powerful LLMCompiler. Another case has been
proven in a production-level application, when about 60 Tools were configured, and the accuracy rate was more than 90%
when paired with few-shot.

## LLMCompiler Frame Diagram

![LLMCompiler Frame Diagram](images/frame.png)

## Task Fetching Unit

![Task Fetching Unit](images/task-fetch.png)

## How To Use

```shell
pip install llmcompiler
```

```py
from llmcompiler.result.chat import ChatRequest
from llmcompiler.tools.tools import Tools
from langchain_openai.chat_models.base import ChatOpenAI
from llmcompiler.chat.run import RunLLMCompiler

chat = ChatRequest(message="<YOUR_MESSAGE>")

# `tools` is a list based on Langchain BaseTool, `Tools.load_tools` can automatically load Tools from specified directories or `.py` files.
# The default configuration is only for demonstration purposes, it is recommended to inherit `BaseTool` or `CompilerBaseTool` to implement Tool, which can better control some details.
# No parameter dependencies are required, you can inherit `BaseTool` to implement Tool, with the implementation reference being `llmcompiler/tools/basetool/fund_basic_v1.py`.
# Parameter dependencies are required, you can inherit `CompilerBaseTool`, with the implementation references being `llmcompiler/tools/math/math_tools.py, llmcompiler/tools/basetool/fund_basic_v2.py`.
tools = Tools.load_tools("../llmcompiler/tools/math")

# The implementation class of BaseLanguageModel is supported.
llm = ChatOpenAI(model="gpt-4o", temperature=0, max_retries=3)

llm_compiler = RunLLMCompiler(chat, tools, llm)
# Run the full LLMCompiler process.
print(llm_compiler())

# Ignore the joiner process and return the task and execution result directly.
print(llm_compiler.runWithoutJoiner())

# More ways to use it can be discussed in the issue, and I will continue to improve the documentation in the future.
```

## Case

[Example of Performing Complex Mathematical Calculations](docs/dag-demo.md)

## Reference Linking

- [Paper: An LLM Compiler for Parallel Function Calling](https://arxiv.org/abs/2312.04511)
- [Partial Code: LLMCompiler From Github](https://github.com/langchain-ai/langgraph/blob/main/examples/llm-compiler/LLMCompiler.ipynb)
- [ICML 2024 LLMCompiler: An LLM Compiler for Parallel Function Calling](https://github.com/SqueezeAILab/LLMCompiler)
