# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
import os
from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel, Field

from llmcompiler.few_shot.example import pack_exampl_variables
from llmcompiler.result.chat import generate_md5
from llmcompiler.utils.date.date import formatted_dt_now


class Result(BaseModel):
    total: str = Field(description="本次搜索相关总数，大于10000时显示`大于10000`")
    count: int = Field(description="当前结果集中包含的总量")
    data: list[dict] = Field(description="结果列表")


class BaseFewShot(ABC):
    """The base rewrite interface."""

    def __init__(self, cfi: str, type: str, limit: int = 200):
        """Few-shot,cfi/type/limit"""
        self.cfi = cfi
        self.type = type
        self.limit = limit

    @abstractmethod
    def add(self, md5: str, question: str, cfi: list[str], type: str, update_time: str):
        """pass"""

    @abstractmethod
    def get(self, question: str) -> Result:
        """pass"""

    @abstractmethod
    def delete(self, md5: str):
        """pass"""

    @abstractmethod
    def delete_by_cfi(self, cfi: List[str]):
        """pass"""


class DefaultBaseFewShot(BaseFewShot):

    def __init__(self):
        super().__init__("default", "default", 10)

    def add(self, md5: str, question: str, cfi: list[str], type: str, update_time: str):
        pass

    def get(self, question: str) -> Result:
        pass

    def delete(self, md5: str):
        pass

    def delete_by_cfi(self, cfi: List[str]):
        pass


if __name__ == '__main__':
    intent_recognition = DefaultBaseFewShot()
    # ========================添加样例========================
    examples = pack_exampl_variables()
    for example in examples:
        intent_recognition.add(
            md5=generate_md5("".join([example['var'], os.getenv("FEW_SHOT_TYPE"), os.getenv("FEW_SHOT_CFI")])),
            question=example['value'],
            cfi=[os.getenv("FEW_SHOT_CFI")],
            type=os.getenv("FEW_SHOT_TYPE"),
            update_time=formatted_dt_now()
        )

    # ========================查询样例========================
    result = intent_recognition.get(question="易方达")
    print(result)

    # ========================删除样例========================
    # intent_recognition.delete(md5="sadojwqeuncuwo")
