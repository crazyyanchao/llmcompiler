# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
from typing import Tuple, List, Union, Any

import tiktoken
import logging
from langchain_core.language_models import BaseLanguageModel
from pydantic import BaseModel, Field

from llmcompiler.utils.string.question_trim import extract_text_cn_en_num


class SwitchLLM(BaseModel):
    """
    候选切换模型
    """
    llm: BaseLanguageModel = Field(description='模型')
    max_token: int = Field(description='最大Token限制')
    out_token: int = Field(description='输出Token限制，一般可设置为1024、2048、4096...等值')
    order: int = Field(default=1, description='模型切换排序顺序')


def auto_switch_llm(switch_llms: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]],
                    input_message: Any) -> BaseLanguageModel:
    """
    自动切换LLM
    :param switch_llms: 模型列表，按照列表传入的顺序进行切换，例如如果LLM1不满足Token长度限制，则切换到LLM2依次类推
    :param input_message: 需要计算Token的文本
    TODO:目前仅支持通过计算GPT4和GPT35的Token然后判断是否切换到其它模型，不支持其它模型的Token计算
    """
    llm = auto_switch_llm_select(switch_llms, input_message)
    return llm


def auto_switch_llm_select(switch_llms: Union[BaseLanguageModel, List[BaseLanguageModel], SwitchLLM, List[SwitchLLM]],
                           input_message: Any) -> BaseLanguageModel:
    if isinstance(switch_llms, SwitchLLM):
        return switch_llms.llm
    elif isinstance(switch_llms, BaseLanguageModel):
        return switch_llms
    elif isinstance(switch_llms, List):
        if all(isinstance(obj, SwitchLLM) for obj in switch_llms):
            sort_switch_llms = sorted(switch_llms, key=lambda x: x.order)
            try:
                for switch_llm in sort_switch_llms:
                    llm = switch_llm.llm
                    # 计算GPT4和GPT35的Token是否超过限制，如果没有超过限制则使用GPT模型，否则默认获取最后一个可切换模型
                    token = openai_gpt_model_token(str(input_message), llm.model)
                    if token[1]:
                        token_num = token[0]
                        if token_num + switch_llm.out_token < switch_llm.max_token:
                            logging.info("Switch to the gpt-models!")
                            return switch_llm.llm
                    else:
                        logging.warning("Unable to switch gpt-models!")
                        # 无法自动切换模型则默认获取列表中最后一个模型
                        return sort_switch_llms[-1].llm
            except Exception:
                logging.error("There was an error switching models!")
                # 切换出错则获取列表中最后一个模型
                return sort_switch_llms[-1].llm
        else:
            non_switch_llms = [obj for obj in switch_llms if isinstance(obj, BaseLanguageModel)]
            if not non_switch_llms:
                raise ValueError("No BaseLanguageModel objects found in the list")
            return non_switch_llms[-1]
    else:
        raise ValueError("No BaseLanguageModel objects found in the list")


def openai_gpt_model_token(text: str, model: str) -> Tuple[int, bool]:
    """
    使用模型名称获取文本的Token数量，返回Token长度和是否支持当前模型计算Token的标记
    :param text: 文本
    :param model: GPT模型名称，例如`gpt-4`、`gpt-3.5-turbo`、`gpt-3.5`
    """
    model = extract_text_cn_en_num(model)
    if model.startswith('gpt4') or model.startswith('gpt35'):
        encoding = tiktoken.get_encoding("cl100k_base")
        # encoding = tiktoken.encoding_for_model(model)
        num_tokens = len(encoding.encode(text))
        return num_tokens, True
    else:
        return 0, False


