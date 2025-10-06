#!/usr/bin/env python3
"""
Find correct Kraken symbol names for missing cryptocurrencies
"""

import os
import sys
import django

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

from api.providers.kraken_provider import get_kraken_provider

def test_kraken_symbols():
    """Test Kraken symbol names for USD cryptocurrencies"""
    print("🔍 查找加密货币的Kraken API名称")
    print("=" * 50)
    
    kraken = get_kraken_provider()
    
    # 已知映射
    known_mapping = {
        'BTC/USD': 'XXBTZUSD',
        'ETH/USD': 'XETHZUSD', 
        'LTC/USD': 'XLTCZUSD',
        'XRP/USD': 'XXRPZUSD'
    }
    
    # 需要查找的符号及其候选名称
    candidates = {
        'BCH/USD': ['BCHUSD', 'BCHUSDT', 'XBCHZUSD'],
        'LINK/USD': ['LINKUSD', 'LINKUSDT', 'XLINKZUSD'],
        'DOGE/USD': ['DOGEUSD', 'DOGEUSDT', 'XDOGZUSD']
    }
    
    print("1. 验证已知映射:")
    for db_symbol, kraken_symbol in known_mapping.items():
        try:
            ticker = kraken.get_ticker([kraken_symbol])
            if kraken_symbol in ticker:
                price = ticker[kraken_symbol]['c'][0]
                print(f"   ✅ {db_symbol} -> {kraken_symbol}: ${price}")
            else:
                print(f"   ❌ {db_symbol} -> {kraken_symbol}: 无数据")
        except Exception as e:
            print(f"   ❌ {db_symbol} -> {kraken_symbol}: {str(e)}")
    
    print("\n2. 查找缺失符号:")
    final_mapping = known_mapping.copy()
    
    for symbol, candidate_list in candidates.items():
        print(f"\n🔍 {symbol}:")
        found = False
        
        for candidate in candidate_list:
            try:
                ticker = kraken.get_ticker([candidate])
                if candidate in ticker and ticker[candidate]['c'][0]:
                    price = ticker[candidate]['c'][0]
                    print(f"   ✅ {candidate}: ${price}")
                    final_mapping[symbol] = candidate
                    found = True
                    break
                else:
                    print(f"   ⚠️  {candidate}: API响应但无价格数据")
            except Exception as e:
                print(f"   ❌ {candidate}: {str(e)[:50]}...")
        
        if not found:
            print(f"   😞 {symbol} 在Kraken上未找到有效交易对")
    
    print("\n" + "=" * 50)
    print("📋 最终的Kraken符号映射:")
    print("=" * 50)
    for db_symbol, kraken_symbol in final_mapping.items():
        print(f"    '{db_symbol}': '{kraken_symbol}',")
    
    return final_mapping

if __name__ == "__main__":
    test_kraken_symbols()
