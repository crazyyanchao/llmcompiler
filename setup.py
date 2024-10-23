# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='llmcompiler',
    version="1.2.14",
    author="Yc-Ma",
    author_email="yanchaoma@foxmail.com",
    description='LLMCompiler',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/crazyyanchao/llmcompiler',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',  # 添加开发状态分类器
        'Intended Audience :: Developers',  # 添加目标受众分类器
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent'
    ],
    python_requires='>=3.9',
    install_requires=[
        "langgraph>=0.1.19",
        "langchain>=0.2.12",
        "langchain-openai>=0.1.20",
        "pandas>=2.2.2",
        "grandalf"
    ],
    keywords=['LLMCompiler', 'Agent', 'Natural Language Processing', 'LLM', 'Machine Learning', 'AI', 'Compiler'],
    include_package_data=True,
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst', '.csv']
    },
)
