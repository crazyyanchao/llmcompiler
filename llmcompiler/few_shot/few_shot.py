# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : LLMCompiler
@Time    : 2024-08-02 09:30:49
"""
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from llmcompiler.few_shot.example import pack_exampl_variables
from llmcompiler.utils.date.date import formatted_dt_now


class BaseFewShot(ABC):
    """The base Few-shot interface."""

    @abstractmethod
    def add(self, **kwargs):
        """pass"""

    @abstractmethod
    def get(self, **kwargs):
        """pass"""

    @abstractmethod
    def delete(self, **kwargs):
        """pass"""


class Result(BaseModel):
    total: str = Field(
        description="Total number of relevant results for this search; displays 'greater than 10000' if more than 10000")
    count: int = Field(description="Total number included in the current result set")
    data: list[dict] = Field(description="List of results")


class DefaultBaseFewShot(BaseFewShot):

    def __init__(self):
        self.storage = {}

    def add(self, id: str, question: str, update_time: str):
        self.storage[id] = {"question": question, "update_time": update_time}

    def _calculate_match_score(self, query: str, target: str) -> float:
        # Calculate character-based match score
        matches = sum(target.count(char) for char in query)
        return matches / len(target) if target else 0

    def get(self, question: str, topn: int = 5) -> Result:
        # Get all questions
        all_questions = [(k, v['question']) for k, v in self.storage.items()]

        # Calculate match scores
        scores = [(k, v, self._calculate_match_score(question, v)) for k, v in all_questions]

        # Sort by score in descending order and get topn
        top_matches = sorted(scores, key=lambda x: x[2], reverse=True)[:topn]

        # Find matched items
        matched_items = [self.storage[k] for k, v, score in top_matches]

        return Result(
            total=str(len(matched_items)),
            count=len(matched_items),
            data=matched_items
        )

    def delete(self, id: str):
        if id in self.storage:
            del self.storage[id]


if __name__ == '__main__':
    few_shot = DefaultBaseFewShot()
    # ========================添加样例========================
    examples = pack_exampl_variables()
    for example in examples:
        few_shot.add(
            id=example['var'],
            question=example['value'],
            update_time=formatted_dt_now()
        )

    # ========================查询样例========================
    result = few_shot.get(question="查找货币类基金")
    print(result)

    # ========================删除样例========================
    # intent_recognition.delete(id="sadojwqeuncuwo")
