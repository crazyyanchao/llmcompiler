# LLMCompiler参数解析器可用配置介绍

&emsp;LLMCompiler对于Tool参数的解析和使用提供了一些可用配置，这些配置可以简化Tool的实现，同时支持更加健壮的参数解析运行过程。

&emsp;Tool的实现一般需要定义一个输入参数（InputSchema）和输出参数（OutputSchema），并且需要实现`_run`函数，该函数是Tool的运行逻辑。

## 输入参数`InputSchema`的可用配置

&emsp;输入参数的配置主要是在调用Tool执行输入参数解析到Tool的过程中使用的，这些配置只关注参数输入到Tool的过程。

- DISABLE_RESOLVED_ARGS

&emsp;定义TOOL中的输入参数是否执行参数解析，使用该设置表示为指定字段禁用参数解析（`$`符号等相关内容会被保留）。
例如输出参数为`code=${1}.code`，解析后为`code=${1}.code`（解析前解析后没有变化）。

```python
# 用法示例
class InputSchema(BaseModel):
    problem: str = Field(description="简单的数学问题", json_schema_extra=DISABLE_RESOLVED_ARGS)
    context: Optional[List] = Field(default=None, description="提供额外的上下文信息，帮助解决数学问题")
```

- PARTIAL_RESOLVED_ARGS_PARSE

&emsp;定义TOOL中的输入参数是否执行部分解析，使用该设置表示为指定字段启动参数部分解析（`$`符号等相关内容会被替换，完整的一个参数中其它内容将被保留）。
例如输出参数为`code=average of ${2}.stock_return`，解析后为`code=average of [1,2,3,4]`（解析后保留了除参数以外的其它部分）。

```python
class InputSchema(BaseModel):
    problem: str = Field(description="简单的数学问题", json_schema_extra=PARTIAL_RESOLVED_ARGS_PARSE)
    context: Optional[List] = Field(default=None, description="提供额外的上下文信息，帮助解决数学问题")
```

## 输出参数`OutputSchema`可用配置

&emsp;输出参数的配置主要是在Tool被依赖时使用，这些配置可以控制下游Tool该如何利用上游Tool输出的结果，当这些输出参数输入给其它Tool时，此时开始关注其它Tool的参数输入过程。

- DISABLE_ROW_CALL

&emsp;在使用`@tool_call_by_row_pass_parameters`注解（仅在使用这个注解时会生效），搭配这个参数时表示不执行自动转为DataFrame一列的过程，而是将原有值直接扩展到其它行。
`@tool_call_by_row_pass_parameters`注解的具体行为请参考注解的详细描述。

```python
# 用法示例
class InfoOutputSchema(BaseModel):
    name: Optional[str] = Field(default=None, description="stock name")
    code: Optional[str] = Field(default=None, description="stock code", json_schema_extra=DISABLE_ROW_CALL)
    date: Optional[str] = Field(default=None, description="establishment date")
```

## 作用于`_run`函数的Tool注解
