# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
TOOL_DESC_JOIN_EXAMPLES_MARK = "使用当前Tool生成Plan时可以参考下面的样例: "


def render_text_description(description: str) -> str:
    """
    去掉描述中的换行符号、空格符，并设置中文句号结尾
    """
    description = description.replace("\n", "").replace("  ", "").strip("。.")
    return f"{description}。"


def render_text_description_examples(description: str, example: str) -> str:
    """
    去掉描述中的换行符号、空格符，并设置中文句号结尾
    """
    description = description.replace("\n", "").replace("  ", "").strip("。.")
    example = example.replace("\n", "<br>").replace(" ", "").strip("。.")
    return f"{description}。{TOOL_DESC_JOIN_EXAMPLES_MARK}{example}。"


if __name__ == '__main__':
    description = render_text_description(
        "功能：通过指定时间词获取基金收益曲线数据，"
        "     例如近1月(query_month=1)、近3月(query_month=3)、近6月(query_month=6)、"
        "     近1年(query_month=12)、近3年(query_month=36)、近5年(query_month=60)等。"
        "输入参数：基金代码、开始时间、结束时间。"
        "返回值：基金收益率曲线与比较基准曲线数据。"
    )
    print(description)
