# LLMCompiler

&emsp;本项目是LLMCompiler技术的最小示例演示程序，LLMCompiler是一种Agent框架旨在通过在有向无环图(DAG)
中快速执行任务来加快代理任务的执行速度。它还通过减少对LLM的调用次数来节省冗余令牌使用的成本，相关文档：[基于LLMCompiler的Tools并发调用](https://localhost.compiler.cn/#/asset/ai_api?doc_id=1528)。当前示例演示程序在[clab-data-bot](https://datalab.compiler.cn/datalab-model/ai-agents/clab-data-bot)
基础上去掉了Fastapi、YAML、Dockerfile等内容，只保留了LLMCompiler的核心内容，保留了Few-shot数据库使用入口。核心代码位于`src\application\graph`文件夹下。

![img.png](images/img.png)

## 程序使用

### `.env`配置修改

&emsp;在`.env`文件中定义项目运行所需的基础配置可以按需修改，如果只是进行代码测试也可以不修改直接运行。

### 运行入口

```
src\application\chat\completions.py
```

### 添加Few-shot

&emsp;Few-shot技术的应用旨在提高LLM执行规划时的准确率和稳定性，这是一个可选配置，对于Agent的运行是非必须的。

```
在src\lib\few_shot\example.py中定义Few-shot数据后，执行src\lib\few_shot\few_shot.py将数据存储到Elasticsearch中备用。
```

### 新增Tools

&emsp;Tools是提供给Agent调用的工具，可以是定义好的函数或者是嵌套的Agent，需要根据具体场景进行配置。推荐的用法是通过继承BaseTool实现自定义Tool，实现更加灵活的控制。

- Tools位置

```
src\lib\tools\basetool 文件夹中自定义Tools后在tools.py中`tools`方法定义引用即可。
```

- Tools参数依赖

```
当Tool的输出可能被其它Tool依赖时，需要在当前Tool继承`DAGFlowParams`类并实现`dag_flow_paras`抽象方法。
```

- Tool实现方式

```
Tools实现方法：
1. 使用注解，例如：src\lib\tools\basetool\tool_decorator.py中wd_a_desc函数
2. 用StructuredTool类提供的函数，例如：src\lib\tools\basetool\tool_decorator.py中wd_a_desc_2_tool函数
3. 继承BaseTool实现自定义方法，例如：src\lib\tools\basetool\fund_asset_portfolio.py
```

### 流式输出

&emsp;本项目支持流式输出，在程序的入口处预留了`ChatRequest`中的`localhost_message_key`参数，流式消息通过这个KEY来订阅，订阅接口的使用请参考[消息服务订阅接口](https://localhost.compiler.cn/#/asset/ai_api?doc_id=1495)。

## 其它

```shell
# 生成`requirements.txt`文件 
pip freeze > requirements.txt 

# 安装所有依赖项 
pip install -r requirements.txt 
```

