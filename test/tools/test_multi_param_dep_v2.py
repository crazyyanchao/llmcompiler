
# -*- coding: utf-8 -*-
"""
Test multi_param_dep_v2.py tool
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from llmcompiler.tools.basetool.multi_param_dep_v2 import StockReturnFake
from llmcompiler.tools.basetool.stock_info_fake import StockInfoFake
from llmcompiler.tools.generic.action_output import ActionOutput


def test_stock_return_fake_single():
    """Test single stock code call"""
    print("=== Test single stock code call ===")
    tool = StockReturnFake()
    
    # Test single parameter
    result = tool._run(code="AAPL", date="2023-01-01")
    print(f"Single parameter result: {result}")
    print(f"Result type: {type(result)}")
    if isinstance(result, ActionOutput):
        print(f"Return data count: {len(result.any) if result.any else 0}")
        for item in result.any[:3]:  # Show first 3 items
            print(f"  - {item}")


def test_stock_return_fake_list():
    """Test multiple stock codes call (list parameters)"""
    print("\n=== Test multiple stock codes call (list parameters) ===")
    tool = StockReturnFake()
    
    # Test list parameters - this is the case causing original error
    try:
        result = tool._run(code=["AAPL", "GOOGL", "MSFT"], date=["2023-01-01", "2023-01-02", "2023-01-03"])
        print(f"List parameter result: {result}")
        print(f"Result type: {type(result)}")
        if isinstance(result, ActionOutput):
            print(f"Return data count: {len(result.any) if result.any else 0}")
            for item in result.any[:5]:  # Show first 5 items
                print(f"  - {item}")
    except Exception as e:
        print(f"List parameter call failed: {e}")


def test_stock_info_fake():
    """Test stock info retrieval"""
    print("\n=== Test stock info retrieval ===")
    tool = StockInfoFake()
    
    # Simulate original query
    result = tool._run(type="Tech")
    print(f"Stock info result: {result}")
    print(f"Result type: {type(result)}")
    if isinstance(result, ActionOutput):
        print(f"Return data count: {len(result.any) if result.any else 0}")
        for item in result.any:
            print(f"  - {item}")
        
        # Check DAG flow parameters
        if hasattr(result, 'dag_kwargs') and result.dag_kwargs:
            print(f"DAG flow parameters: {result.dag_kwargs.kwargs}")


def test_dependency_simulation():
    """Simulate dependency relationship call"""
    print("\n=== Simulate dependency relationship call ===")
    
    # 1. First get stock info
    info_tool = StockInfoFake()
    info_result = info_tool._run(type="Tech")
    
    if isinstance(info_result, ActionOutput) and info_result.any:
        # 2. Extract stock codes (simulate dependency parsing)
        stock_codes = [item.code for item in info_result.any if hasattr(item, 'code')]
        stock_dates = [item.date for item in info_result.any if hasattr(item, 'date')]
        
        print(f"Extracted stock codes: {stock_codes}")
        print(f"Extracted dates: {stock_dates}")
        
        # 3. Try to call return tool with these parameters
        return_tool = StockReturnFake()
        try:
            return_result = return_tool._run(code=stock_codes, date=stock_dates)
            print(f"Dependency call result: {return_result}")
        except Exception as e:
            print(f"Dependency call failed: {e}")


if __name__ == "__main__":
    print("Starting multi_param_dep_v2.py tool test...")
    
    test_stock_return_fake_single()
    test_stock_return_fake_list()
    test_stock_info_fake()
    test_dependency_simulation()
    
    print("\n=== Test completed ===")
