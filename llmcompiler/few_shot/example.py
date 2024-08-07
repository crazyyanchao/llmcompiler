# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
"""
人工定义的Few-shot数据库

Few-shot内容可以是具体的DAG计划，也可以是文本描述的计划过程。定义好相关Few-shot数据以后运行few_shot.py即可。
"""

EXAMPLE_1 = """
<问题>
李丽管理的产品有哪些？其中易方达价值臻选最近60天、最近30天、最近3天的的业绩和比较基准情况
<执行计划>
1. 先使用`manager_info_1`获取谭丽在管的产品
2. 再使用`fund_info`获取易方达价值臻选的基金产品代码
3. 使用易方达价值臻选的产品代码通过`fund_return_2`获取最近60天的收益率和比较基准情况数据
4. 使用易方达价值臻选的产品代码通过`fund_return_2`获取最近30天的收益率和比较基准情况数据
5. 使用易方达价值臻选的产品代码通过`fund_return_2`获取最近3天的收益率和比较基准情况数据
"""

EXAMPLE_2 = """
<问题>
货币类基金七日年化收益大于1.5的基金有哪些？
<执行计划>
1. fund_info_filter(fundtype="HFM04", indicator="14", calculate="greater", value=1.5)
2. join() <END_OF_PLAN>
"""


def pack_exampl_variables():
    """打包样例"""
    examples = []
    global_vars = globals()

    for var_name, var_value in global_vars.items():
        if var_name.startswith('EX'):
            examples.append({'var': var_name, 'value': var_value})

    return examples


if __name__ == '__main__':
    # 获取以"EX"开头的变量值列表
    ex_variables_list = pack_exampl_variables()
    print(ex_variables_list)
