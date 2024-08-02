# -*- coding: utf-8 -*-
from setuptools import setup

long_desc = """
LLMCompiler
===============

LLMCompiler Agent

LLMCompiler is an Agent Architecture designed to speed up the execution of agent tasks by executing them quickly in the DAG. It also saves the cost of redundant token use by reducing the number of calls to the LLM. The realization inspiration comes from An LLM Compiler for Parallel Function Calling.
"""

setup(
    name='-llmcompiler',
    version="1.0.0",
    description='LLMCompiler',
    long_description=long_desc,
    url='https://github.com/crazyyanchao',
    keywords='LLMCompiler Agent',
    classifiers=[
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: Apache License'
    ],
    packages=['llmcompiler'],
    package_dir={'llmcompiler': 'llmcompiler'},
    install_requires=[
        "langgraph>=0.1.19",
        "langchain>=0.2.12",
        "langchain-openai>=0.1.20",
        "pandas>=2.2.2",
        "grandalf"
    ],
    include_package_data=True,
    package_data={},
)
