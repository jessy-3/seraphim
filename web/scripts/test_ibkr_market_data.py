#!/usr/bin/env python3
"""
Test IBKR market data availability for our symbols
"""
import os
import sys
import django
import asyncio
from datetime import datetime

# Add project root to Python path
sys.path.append('/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

async def test_market_data():
    """Test what market data we can get from IBKR"""
    
    try:
        from ib_insync import IB, Stock, Index, Forex
        
        print("🔌 连接IBKR...")
        ib = IB()
        
        # Connect to IB Gateway
        await ib.connectAsync('ib-gateway', 4002, clientId=2)
        print("✅ IBKR连接成功！")
        
        # Test symbols from our database
        test_symbols = [
            ('TSLA', 'STK', 'SMART', 'USD'),  # Tesla stock
            ('IAU', 'STK', 'SMART', 'USD'),   # Gold ETF
            ('DJI', 'IND', 'CME', 'USD'),     # Dow Jones Index
            ('XAUUSD', 'CASH', 'IDEALPRO', 'USD') # Gold Forex
        ]
        
        results = {}
        
        for symbol, sec_type, exchange, currency in test_symbols:
            try:
                print(f"\n📊 测试 {symbol}...")
                
                # Create contract
                if sec_type == 'STK':
                    contract = Stock(symbol, exchange, currency)
                elif sec_type == 'IND':
                    contract = Index(symbol, exchange, currency)
                elif sec_type == 'CASH':
                    contract = Forex(symbol[:3], symbol[3:])
                
                # Get contract details
                details = await ib.reqContractDetailsAsync(contract)
                if details:
                    print(f"  ✅ 合约找到: {details[0].contract.localSymbol}")
                    
                    # Request market data
                    ib.reqMktData(details[0].contract, '', False, False)
                    await asyncio.sleep(2)  # Wait for data
                    
                    ticker = ib.ticker(details[0].contract)
                    if ticker and (ticker.bid or ticker.ask or ticker.last):
                        print(f"  📈 实时数据: Bid={ticker.bid}, Ask={ticker.ask}, Last={ticker.last}")
                        results[symbol] = 'LIVE_DATA_AVAILABLE'
                    else:
                        print(f"  ⚠️  无实时数据 (可能需要订阅)")
                        results[symbol] = 'NO_LIVE_DATA'
                        
                else:
                    print(f"  ❌ 合约未找到")
                    results[symbol] = 'CONTRACT_NOT_FOUND'
                    
            except Exception as e:
                print(f"  ❌ 错误: {e}")
                results[symbol] = f'ERROR: {str(e)}'
        
        print("\n" + "="*50)
        print("📋 测试结果汇总:")
        print("="*50)
        
        for symbol, result in results.items():
            status_icon = {
                'LIVE_DATA_AVAILABLE': '✅',
                'NO_LIVE_DATA': '⚠️',
                'CONTRACT_NOT_FOUND': '❌',
            }.get(result.split(':')[0], '❌')
            
            print(f"{status_icon} {symbol}: {result}")
        
        # Data subscription recommendations
        print("\n" + "="*50)
        print("💡 数据订阅建议:")
        print("="*50)
        
        no_data_count = sum(1 for r in results.values() if 'NO_LIVE_DATA' in r)
        if no_data_count > 0:
            print(f"⚠️  {no_data_count} 个符号需要市场数据订阅")
            print("💰 建议订阅:")
            print("   - US Securities Bundle (免费)")
            print("   - US Index Data (~$4/月)")
            print("   - IDEALPRO Forex (免费)")
        else:
            print("🎉 所有数据都可用！Paper Trading账户数据充足。")
            
        ib.disconnect()
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("💡 请确保:")
        print("   1. IB Gateway正在运行")
        print("   2. 网络连接正常")
        print("   3. IBKR账户已登录")
        
        return False
    
    return True

if __name__ == '__main__':
    print("🧪 IBKR市场数据可用性测试")
    print("="*50)
    
    try:
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(test_market_data())
        loop.close()
        
        if success:
            print("\n✅ 测试完成！请根据结果决定数据订阅。")
        else:
            print("\n❌ 测试失败，请检查连接设置。")
            
    except Exception as e:
        print(f"\n❌ 测试运行错误: {e}")
