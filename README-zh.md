# LLMCompiler

[![English](https://img.shields.io/badge/English-Click-yellow)](README.md)
[![中文文档](https://img.shields.io/badge/中文文档-点击查看-orange)](README-zh.md)

&emsp;LLMCompiler 是一种 Agent 架构，旨在通过在DAG中快速执行任务来加快 Agent 任务的执行速度。它还通过减少对 LLM 的调用次数来节省 Tokens 使用的成本。实现
灵感来自《An LLM Compiler for Parallel Function Calling》。

&emsp;这里以使用 SQL 查询数据为例，介绍该框架的核心作用。生成 SQL 执行计划的核心流程包括语法解析、语义分析、优化器介入、生成执行计划。LLMCompiler 基于用户指令执行工具调用时其实可以理解为 LLM 帮用户做了类似 SQL 生成执行计划的过程，只不过这里生成的计划是一个 DAG，DAG描述了工具之间的调用关系和参数依赖传递逻辑。

&emsp;当 Agent 需要调用大量工具时，此实现非常有用。如果您需要的工具超过 LLM 的上下文限制，您可以基于此工具扩展Agent节点。将工具分为不同的
Agent并组装它们以创建更强大的 LLMCompiler。另外已经有案例是在生产级应用中得到验证的，这个案例中配置了大约 60 种工具，与 Few-shot 搭配时准确率超过
90%。

## LLMCompiler 框架图

![LLMCompiler Frame Diagram](images/frame.png)

&emsp;这张图片展示了LLMCompiler的系统架构，描述了用户请求如何在系统内被处理、规划、执行和反馈的全过程。以下是对图中各部分内容的详细描述：

1. 用户请求 (User Request)：

&emsp;在左边展示了一个用户头像，代表系统的终端用户。用户通过界面或其他输入方式向系统发出请求，这是整个流程的起点。

2. 规划器 (Planner)：

&emsp;用户请求首先进入“规划器”模块，这个模块的图标是一个大脑，象征着智能和决策能力（LLM）。规划器的主要职责是解析用户请求，理解其意图，并基于此生成一系列可执行的任务计划。这个计划被组织成一个有向无环图 (
DAG)，代表任务的顺序与依赖关系。

3. 任务DAG流 (Stream Task DAG)：

&emsp;规划器生成的任务DAG流被传递给“任务获取单元” (Task Fetching Unit)
。任务DAG流是一种表示任务间关系的结构，确保任务可以根据其依赖性正确地被执行。DAG流中的每个节点代表一个具体的任务，边表示任务之间的依赖关系。

4. 任务获取单元 (Task Fetching Unit)：

&emsp;任务获取单元是系统的核心执行模块。它负责从DAG中提取任务，并根据任务之间的依赖关系进行调度。任务被尽可能并行地执行，以提高效率。图中用字母A、B、C、D表示任务，并用箭头表示任务的依赖关系与执行顺序。工具图标（如锤子）表示这个模块不仅调度任务，还实际执行它们。

5. 状态更新 (Update State with Task Results)：

&emsp;任务执行完成后，任务结果被用来更新系统的内部状态。状态更新是系统确保所有任务正确执行并记录进展的关键步骤。

6. 合并器（重规划器）(Joiner, Replanner)：

&emsp;更新后的状态被传递到“合并器”模块，该模块同样用大脑图标表示，表明它具备复杂的决策能力。合并器的作用是根据更新后的状态进行评估，如果任务结果不足以满足用户请求，它会重新规划更多任务，并将这些任务再次提交给任务获取单元进行执行。如果任务结果已足够满足用户请求，合并器则会准备向用户反馈最终的结果。

7. 向用户反馈 (Respond to User)：

&emsp;最终的任务结果通过合并器生成，并反馈给用户。这是整个流程的闭环，用户通过系统获得了请求的结果或信息。

&emsp;总的来说，这张图展示了一个复杂的任务调度与执行系统，强调了从用户请求到任务规划、并行执行，再到状态更新与反馈的全流程，体现了系统的智能化与高效性。大脑图标象征了系统中的智能决策模块（LLM），而箭头和任务节点则展示了任务流转和依赖关系的专业处理方式。

## 任务提取单元

![Task Fetching Unit](images/task-fetch.png)

&emsp;这张图片描述了LLMCompiler框架的工作流程图，该框架旨在通过并行调用LLM（大语言模型）来高效执行任务。图片分为几个主要部分，具体描述如下：

1. 用户输入（User Input）：

&emsp;在左侧，用户通过自然语言输入一个问题，例如“微软的市值需要增加多少才能超过苹果的市值？”

2. LLM Planner（LLM 规划器）：

&emsp;用户的输入会被传递到LLM规划器中，该规划器将用户的请求解析为一系列任务（DAG of Tasks）。例如：

- $1 = search(Microsoft Market Cap)：查找微软的市值。
- $2 = search(Apple Market Cap)：查找苹果的市值。
- $3 = math($1 / $2)：进行计算，比较两者的市值。
- $4 = llm($3)：将结果传递给大语言模型进一步处理。

3. 任务获取单元（Task Fetching Unit）：

&emsp;任务获取单元负责从LLM Planner中获取任务，并解析任务之间的依赖关系。这个单元通过一个图示（圆圈和箭头）表示，显示任务是如何通过顺序或并行的方式来执行的。

4. 执行器（Executor）：

&emsp;执行器包含多个“Function Calling Units”（功能调用单元），每个单元都配备了一个工具（Tool）和内存（Memory），工具的所有调用都会在内存中暂存以供后续解析器的使用。
执行器的各个单元负责具体执行任务，例如调用搜索引擎、执行数学运算或调用LLM。

5. 工具栏（Tools）：

&emsp;底部显示了一些工具的图标，包括搜索工具（search）、数学运算工具（math）和大语言模型（LLM）等。这些工具用于执行用户请求中的不同部分。

&emsp;LLMCompiler框架的主要功能是通过自动识别哪些任务可以并行执行，以及哪些任务是相互依赖的，从而实现高效和有效的并行函数调用。

&emsp;总的来说，这张图片展示了LLMCompiler框架如何从用户输入开始，通过规划任务、解析任务依赖关系，最终调用各种工具来完成任务的全过程。

## 使用方式

```shell
pip install llmcompiler
```

```py
from llmcompiler.result.chat import ChatRequest
from llmcompiler.tools.basic import Tools
from langchain_openai.chat_models.base import ChatOpenAI
from llmcompiler.chat.run import RunLLMCompiler

chat = ChatRequest(message="<YOUR_MESSAGE>")

# `tools`是基于Langchain BaseTool的列表，`Tools.load_tools`可以从指定的目录或者`.py`中自动加载Tools.
# 默认配置仅用于演示，建议继承`BaseTool`或`CompilerBaseTool`来实现Tool，这样可以更好地控制一些细节。
# 不需要指定参数依赖，可以继承`BaseTool`来实现Tool，实现参考为`llmcompiler/tools/basetool/fund_basic_v1.py`。
# 需要指定参数依赖，可以继承 `CompilerBaseTool`，实现参考为`llmcompiler/tools/math/math_tools.py,llmcompiler/tools/basetool/fund_basic_v2.py`。 
tools = Tools.load_tools("../llmcompiler/tools/math")

# 支持BaseLanguageModel的实现类。
llm = ChatOpenAI(model="gpt-4o", temperature=0, max_retries=3)

llm_compiler = RunLLMCompiler(chat, tools, llm)
# 运行完整的LLMCompiler过程
print(llm_compiler())

# 忽略Joiner过程，将Task与执行结果直接返回
print(llm_compiler.runWithoutJoiner())

# 更多使用方式可以在`issue`中讨论，后续还会继续完善文档。
```

## 案例

[执行复杂数学计算的案例](docs/dag-demo.md)

## 参考链接

- [论文: An LLM Compiler for Parallel Function Calling](https://arxiv.org/abs/2312.04511)
- [部分参考代码: LLMCompiler From Github](https://github.com/langchain-ai/langgraph/blob/main/examples/llm-compiler/LLMCompiler.ipynb)
- [ICML 2024 LLMCompiler：一种用于并行函数调用的LLM编译器](https://github.com/SqueezeAILab/LLMCompiler)

