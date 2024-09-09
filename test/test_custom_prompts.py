from dotenv import load_dotenv

load_dotenv()

from llmcompiler.tools.basic import Tools
from llmcompiler.result.chat import ChatRequest
from langchain_openai.chat_models.base import ChatOpenAI
from llmcompiler.chat.run import RunLLMCompiler
from langchain.prompts import PromptTemplate

# chat = ChatRequest(message="How has the return been for Tech stocks since their inception?")
# tools = Tools.load_tools(["../llmcompiler/tools/basetool/stock_info_fake.py",
#                           "../llmcompiler/tools/basetool/multi_param_dep_v1.py"])

chat = ChatRequest(
    message="How has the return been for Tech stocks since their inception?"
)
tools = Tools.load_tools(
    [
        "../llmcompiler/tools/basetool/stock_info_fake.py",
        "../llmcompiler/tools/basetool/multi_param_dep_v2.py",
    ]
)

# chat = ChatRequest(
#     message="How has the return been for Tech stocks since their inception? Calculate the average return of tech stocks.")
# tools = Tools.load_tools(["../llmcompiler/tools/math",
#                           "../llmcompiler/tools/basetool/stock_info_fake.py",
#                           "../llmcompiler/tools/basetool/multi_param_dep_v3.py"])

print(tools)

llm = ChatOpenAI(model="gpt-4o", temperature=0, max_retries=3)

custom_prompts = {
    "JOINER_RESPONSE_HUMAN_TEMPLATE": """Please generate the Final Answer that the user needs based on the user's question and the provided data, ensuring it is logical and rigorous.

When generating the Final Answer, it's important to carefully check the accuracy of any numerical content and ensure that the data provided is relevant to the user's question. The Final Answer can be a few concise summary sentences, but it must fully address the user's question. If numerical analysis is required in the Final Answer, try to analyze information such as the maximum value, minimum value, and data trends after carefully understanding the data fields.

The Final Answer should not contain any formatting or large blocks of numerical content. Remember, the final response to the user should follow one of the options in the RESPONSE FORMAT INSTRUCTIONS, and the output should comply with those requirements.

**User Question**
{question}

Let’s think step by step!""",
    "HUMAN_MESSAGE_TEMPLATE": """Please generate a professional and concise minimum execution plan based on the user's question, along with the relevant information and reference plans.

The relevant information may contain some related data that can be used as "constants." When generating the "Plan," please carefully check the information provided. However, remember not to create any "constant" information not provided in the user's question or the relevant information. For example, if a fund code is not provided, it must be queried using a Tool—this is important.

**User Question**
{question}

**Relevant Information**
{info}

**Reference Plan**
{examples}

Let’s think step by step!
""",
    "JOINER_SYSTEM_PROMPT_2": """Using the above previous actions, decide whether to replan or finish. If all the required information is present. You may finish. If you have made many attempts to find the information without success, admit so and respond with whatever information you have gathered so the user can work well with you.The response should be in English.""",
}

# llm_compiler = RunLLMCompiler(chat, tools, llm, custom_prompts)
llm_compiler = RunLLMCompiler(chat=chat, tools=tools, llm=llm, custom_prompts=custom_prompts)
print(llm_compiler())

# llm_compiler.runWithoutJoiner()