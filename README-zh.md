# LLMCompiler

[![English](https://img.shields.io/badge/English-Click-yellow)](README.md)
[![中文文档](https://img.shields.io/badge/中文文档-点击查看-orange)](README-zh.md)

&emsp;LLMCompiler 是一种 Agent 架构，旨在通过在DAG中快速执行任务来加快 Agent 任务的执行速度。它还通过减少对 LLM 的调用次数来节省 Tokens 使用的成本。实现
灵感来自《An LLM Compiler for Parallel Function Calling》。

&emsp;这里以使用 SQL 查询数据为例，介绍该框架的核心作用。生成 SQL 执行计划的核心流程包括语法解析、语义分析、优化器介入、生成执行计划。LLMCompiler 基于用户指令执行工具调用时其实可以理解为 LLM 帮用户做了类似 SQL 生成执行计划的过程，只不过这里生成的计划是一个 DAG，DAG描述了工具之间的调用关系和参数依赖传递逻辑。

&emsp;当 Agent 需要调用大量工具时，此实现非常有用。如果您需要的工具超过 LLM 的上下文限制，您可以基于此工具扩展代理节点。将工具分为不同的
代理并组装它们以创建更强大的 LLMCompiler。另外已经有案例是在生产级应用中得到验证的，这个案例中配置了大约 60 种工具，与 Few-shot 搭配时准确率超过
90%。

## LLMCompiler 框架图

![LLMCompiler Frame Diagram](images/frame.png)

## 任务提取单元

![Task Fetching Unit](images/task-fetch.png)

## 使用方式

```shell
pip install llmcompiler
```

```py
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
```

## 参考链接

- [论文: An LLM Compiler for Parallel Function Calling](https://arxiv.org/abs/2312.04511)
- [部分参考代码: LLMCompiler From Github](https://github.com/langchain-ai/langgraph/blob/main/examples/llm-compiler/LLMCompiler.ipynb)
- [ICML 2024 LLMCompiler：一种用于并行函数调用的LLM编译器](https://github.com/SqueezeAILab/LLMCompiler)

