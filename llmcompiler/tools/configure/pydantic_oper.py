# -*- coding: utf-8 -*-
"""
@Author  : Yc-Ma
@Desc    : Pydantic Opr.
@Time    : 2024-08-05 17:25:41
"""
from typing import Type

from pydantic import BaseModel


def field_descriptions_join(model: Type[BaseModel], delimiter: str = ';', suffix: str = '.') -> str:
    """Concatenate the field descriptions of BaseModel into a single sentence."""
    descriptions = []
    for field_name, field in model.model_fields.items():
        descriptions.append(field.description)
    return delimiter.join(descriptions) + suffix
