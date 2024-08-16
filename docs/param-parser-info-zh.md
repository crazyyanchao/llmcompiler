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

&emsp;在使用`@tool_call_by_row_pass_parameters(detect_disable_row_call=True)`注解（仅在使用这个注解时会生效），搭配这个参数时表示不执行自动转为DataFrame一列的过程，而是将原有值直接扩展到其它行。
`@tool_call_by_row_pass_parameters`注解的具体行为请参考注解的详细描述。

```python
# 用法示例
class InfoOutputSchema(BaseModel):
    name: Optional[str] = Field(default=None, description="stock name")
    code: Optional[str] = Field(default=None, description="stock code", json_schema_extra=DISABLE_ROW_CALL)
    date: Optional[str] = Field(default=None, description="establishment date")
```

## 作用于`tool._run`函数的装饰器

### tool_kwargs_filter

- **含义**：过滤掉不合法的参数值，并可选地匹配特定的字符串模式。
- **入参**：
    - invalid_value（可选，类型：List[Any]）：需要过滤掉的无效参数值，默认值为['', 'None', None, [], {}]。
    - pattern_str（可选，类型：str）：用于匹配无效占位符的正则表达式，默认值为r'\$\{.*?\}'。
- **用法**：通过修饰函数来过滤kwargs中指定的无效值或符合指定正则表达式模式的值。
- **调用方式**：
```python
@tool_kwargs_filter(invalid_value=[None, '', []], pattern_str=r'\$\{.*?\}')
def _run(**kwargs):
    # 函数体
```

### tool_kwargs_clear

- **含义**：清除函数输入参数中包含特定无效值的键值对。
- **入参**：
  - invalid_value（可选，类型：List[Any]）：需要过滤掉的无效参数值，默认值为['', 'None', None, [], {}]。
- **用法**：在执行函数前，删除kwargs中与指定无效值匹配的键值对。
- **调用方式**：

```python
@tool_kwargs_clear(invalid_value=[None, '', []])
def _run(**kwargs):
    # 函数体
```

### tool_kwargs_filter_placeholder

- **含义**：根据指定的模式字符串清除参数中的占位符。
- **入参**：
  - pattern_str（类型：str）：用于匹配占位符的正则表达式模式，默认值为`r'\$\{.*?\}'`。
- **用法**：过滤掉kwargs中符合指定模式的占位符参数。
- **调用方式**：

```python
@tool_kwargs_filter_placeholder(pattern_str=r'\$\{.*?\}')
def _run(**kwargs):
    # 函数体
```

### tool_set_pydantic_default

- **含义**：为BaseTool实例的参数设置默认值。
- **入参**：无显式入参。
- **用法**：检查BaseTool实例的args参数字典，并为没有输入的参数设置默认值（如果定义了默认值）。
- **调用方式**：

```python
@tool_set_pydantic_default
def _run(**kwargs):
    # 函数体
```

### tool_call_by_row_pass_parameters

- **含义**：按行传递参数并调用工具函数，支持多行参数的并行处理。
- **入参**：
  - fill_non_list_row（可选，类型：bool）：是否自动填充单值参数至表的每一行，默认值为False。
  - detect_disable_row_call（可选，类型：bool）：是否检测上游输出的参数是否需要忽略行扩展，默认值为False。
  - limit（可选，类型：int）：仅对展开后的前LIMIT行参数执行调用，默认-1表示不限制。
- **用法**：将字典参数转换为DataFrame，逐行调用函数，使用多线程池并行执行这些调用，并合并结果。
- **调用方式**：

```python
@tool_call_by_row_pass_parameters(fill_non_list_row=True, detect_disable_row_call=True)
def _run(**kwargs):
    # 函数体
```

### tool_set_default_value

- **含义**：根据用户指定的默认值来填充函数的输入参数。
- **入参**：
  - **kwargs（类型：Dict[str, Any]）：指定的默认参数值字典，当参数未提供时使用这些默认值。
- **用法**：如果函数调用时未提供某些参数，则使用装饰器中指定的默认值。
- **调用方式**：

```python
@tool_set_default_value(param1='default_value1', param2=10)
def _run(**kwargs):
    # 函数体
```

### tool_symbol_separated_string

- **含义**：将指定字段转为用指定符号分割的字符串。
- **入参**：
  - fields（类型：List[str]）：指定字段。
  - symbol（类型：str）：指定符号。
- **用法**：传入如果是列表则转为指定字符分隔的字符串，传入如果是其他值则直接返回。
- **调用方式**：

```python
@tool_symbol_separated_string(fields=['code'])
def _run(**kwargs):
    # 函数体
```

### tool_remove_suffix

- **含义**：将指定字段的指定后缀全部移除，SUFFIX指定的后缀会被循环移除。
- **入参**：
  - fields（类型：List[str]）：指定字段。
  - suffix（类型：List[str]）：指定后缀。
- **用法**：传入如果是列表则移除指定字符后缀，对字符串循环移除，其他值则直接返回。
- **调用方式**：

```python
@tool_remove_suffix(fields=['code'], suffix=['PL', 'GL', 'FT'])
def _run(**kwargs):
    # 函数体
```

### tool_remove_prefix

- **含义**：将指定字段的指定前缀全部移除，PREFIX指定的前缀会被循环移除。
- **入参**：
  - fields（类型：List[str]）：指定字段。
  - prefix（类型：List[str]）：指定前缀。
- **用法**：传入如果是列表则移除指定字符前缀，对字符串循环移除，其他值则直接返回。
- **调用方式**：

```python
@tool_remove_prefix(fields=['code'], prefix=['AA', 'GO', 'MS'])
def _run(**kwargs):
    # 函数体
```

### tool_string_spilt

- **含义**：将指定字段的按照指定字符进行分割，获取指定索引位的参数。
- **入参**：
  - fields（类型：List[str]）：指定字段。
  - split（类型：str）：指定分割符。
  - index（类型：int）：元素索引。
- **用法**：将指定字段的按照指定字符进行分割，如果是列表则按每个元素处理，获取指定索引位的参数。
- **调用方式**：

```python
@tool_string_spilt(fields=['code'], split='O', index=2)
def _run(**kwargs):
    # 函数体
```

### tool_timeout

- **含义**：用于指定Tool最长运行时间。
- **入参**：
  - timeout（类型：int）：超时时间以秒为单位。
- **用法**：在需要对Tool最长响应时间进行控制时，该装饰器非常有用。
- **调用方式**：

```python
@tool_timeout(3)
def _run(**kwargs):
    # 函数体
```

