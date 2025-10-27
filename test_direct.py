#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from metrics import get_detailed_data
from pydantic import BaseModel
from typing import Optional, Dict, Any

class TestRequest(BaseModel):
    start_date: str
    end_date: str
    table_name: str
    attribution_model: Optional[str] = "Último Clique Não Direto"

class TestToken:
    def __init__(self, email):
        self.email = email

async def test_detailed_data():
    print("Testing detailed-data function directly...")
    
    request = TestRequest(
        start_date="2025-08-02",
        end_date="2025-08-02",
        table_name="wtennis",
        attribution_model="Último Clique Não Direto"
    )
    
    token = TestToken("accounts@mymetric.com.br")
    
    try:
        result = await get_detailed_data(request, token)
        print("✅ Function executed successfully")
        print(f"Summary: {result.summary}")
        
        if result.summary['total_revenue'] > 0:
            print("🎉 SUCCESS: Revenue is showing correctly!")
            print(f"Revenue: {result.summary['total_revenue']}")
        else:
            print("❌ ISSUE: Revenue is still 0")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_detailed_data()) 