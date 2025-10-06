#!/usr/bin/env python3
"""
Simple IBKR data test without uvloop conflicts
"""
import asyncio
import sys
import os

# Avoid uvloop by setting event loop policy before importing ib_insync
if sys.platform == 'linux' or sys.platform == 'linux2':
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

try:
    from ib_insync import IB, Stock, Forex
    print("✅ ib_insync imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ib_insync: {e}")
    sys.exit(1)

async def test_ibkr_paper_data():
    """Test Paper Trading data availability"""
    
    ib = IB()
    try:
        print("🔌 Connecting to IB Gateway...")
        await ib.connectAsync('ib-gateway', 4002, clientId=3)
        print("✅ Connected to IBKR Paper Trading")
        
        # Test our 4 symbols
        test_contracts = [
            Stock('TSLA', 'SMART', 'USD'),    # Tesla
            Stock('IAU', 'SMART', 'USD'),     # Gold ETF  
            Stock('SPY', 'SMART', 'USD'),     # S&P 500 ETF
            Forex('XAU', 'USD')               # Gold/USD
        ]
        
        results = {}
        
        for contract in test_contracts:
            symbol = contract.symbol if hasattr(contract, 'symbol') else f"{contract.pair[:3]}/{contract.pair[3:]}"
            
            try:
                print(f"\\n📊 Testing {symbol}...")
                
                # Get contract details first
                details = await ib.reqContractDetailsAsync(contract)
                
                if details:
                    print(f"  ✅ Contract found: {details[0].contract}")
                    
                    # Request market data (paper trading should have basic data)
                    ib.reqMktData(details[0].contract, '', False, False)
                    
                    # Wait for data
                    await asyncio.sleep(3)
                    
                    ticker = ib.ticker(details[0].contract)
                    
                    if ticker:
                        price = ticker.last or ticker.bid or ticker.ask or ticker.close
                        if price and price > 0:
                            print(f"  📈 Price available: {price}")
                            print(f"      Bid: {ticker.bid}, Ask: {ticker.ask}, Last: {ticker.last}")
                            results[symbol] = {
                                'price': float(price),
                                'bid': float(ticker.bid) if ticker.bid else None,
                                'ask': float(ticker.ask) if ticker.ask else None,
                                'status': 'DATA_AVAILABLE'
                            }
                        else:
                            print(f"  ⚠️  No price data (all values 0 or None)")
                            results[symbol] = {'status': 'NO_PRICE_DATA'}
                    else:
                        print(f"  ❌ No ticker data")
                        results[symbol] = {'status': 'NO_TICKER'}
                        
                else:
                    print(f"  ❌ Contract not found")
                    results[symbol] = {'status': 'CONTRACT_NOT_FOUND'}
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                results[symbol] = {'status': f'ERROR: {str(e)}'}
        
        print("\\n" + "="*60)
        print("📋 Paper Trading Data Test Results:")
        print("="*60)
        
        available_data = 0
        for symbol, result in results.items():
            if result['status'] == 'DATA_AVAILABLE':
                available_data += 1
                print(f"✅ {symbol:<10} - Price: ${result['price']:.2f}")
            else:
                print(f"❌ {symbol:<10} - {result['status']}")
        
        print(f"\\n📊 Summary: {available_data}/4 symbols have data available")
        
        if available_data == 0:
            print("\\n💡 Possible reasons:")
            print("   1. Market data subscription not activated in IBKR")
            print("   2. Paper trading account needs data activation")  
            print("   3. Market is closed (some data may still be available)")
            print("   4. Need to accept market data agreements in Client Portal")
        elif available_data < 4:
            print("\\n💡 Partial success - some data requires subscription")
        else:
            print("\\n🎉 All data available! Paper Trading setup is working.")
            
        return results
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return {}
        
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("\\n🔌 Disconnected from IBKR")

def main():
    print("🧪 IBKR Paper Trading Data Test")
    print("="*60)
    
    try:
        # Use default asyncio event loop (not uvloop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(test_ibkr_paper_data())
        
        loop.close()
        
        return results
        
    except Exception as e:
        print(f"\\n❌ Test failed: {e}")
        return {}

if __name__ == '__main__':
    main()
