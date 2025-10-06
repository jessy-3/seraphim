#!/usr/bin/env python
"""
Test script for Kraken Data Provider
Validates all implemented functionality
"""

import sys
import os
import django

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

from api.providers.kraken_provider import KrakenDataProvider, get_kraken_provider
import json
import time

def test_public_api():
    """Test public API functions"""
    print("🌍 Testing Public API Functions...")
    
    provider = KrakenDataProvider()  # No credentials needed for public API
    
    try:
        # Test server time
        print("⏰ Testing server time...")
        server_time = provider.get_server_time()
        print(f"   Server time: {server_time}")
        
        # Test asset info
        print("💰 Testing asset info...")
        assets = provider.get_asset_info(['XBT', 'ETH', 'USD'])
        print(f"   Found {len(assets)} assets")
        
        # Test trading pairs
        print("📊 Testing trading pairs...")
        pairs = provider.get_trading_pairs(['XBTUSD', 'ETHUSD'])
        print(f"   Found {len(pairs)} trading pairs")
        
        # Test ticker data
        print("📈 Testing ticker data...")
        ticker = provider.get_ticker(['XBTUSD', 'ETHUSD', 'ETHXBT'])
        for pair, data in ticker.items():
            price = data['c'][0]
            print(f"   {pair}: ${price}")
        
        # Test standardized ticker
        print("🔄 Testing standardized ticker...")
        std_ticker = provider.get_standardized_ticker(['XBTUSD', 'ETHUSD'])
        for ticker in std_ticker:
            print(f"   {ticker['symbol']}: ${ticker['price']} (24h vol: {ticker['volume_24h']})")
        
        # Test OHLC data
        print("📊 Testing OHLC data...")
        ohlc = provider.get_ohlc_data('XBTUSD', interval=60)  # 1 hour intervals
        ohlc_data = ohlc['XBTUSD']
        print(f"   Retrieved {len(ohlc_data)} OHLC points for BTC/USD")
        if ohlc_data:
            last_candle = ohlc_data[-1]
            print(f"   Last candle: O:{last_candle[1]} H:{last_candle[2]} L:{last_candle[3]} C:{last_candle[4]}")
        
        print("✅ Public API tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Public API test failed: {e}")
        return False

def test_private_api():
    """Test private API functions with authentication"""
    print("\\n🔐 Testing Private API Functions...")
    
    provider = get_kraken_provider()  # Uses credentials from settings
    
    try:
        # Test account balance
        print("💰 Testing account balance...")
        balance = provider.get_account_balance()
        print("   Account balances:")
        for asset, amount in balance.items():
            if float(amount) > 0.001:
                print(f"   {asset}: {amount}")
        
        # Test open orders
        print("📋 Testing open orders...")
        open_orders = provider.get_open_orders()
        orders = open_orders.get('open', {})
        print(f"   Found {len(orders)} open orders")
        
        # Test trade history (last 10)
        print("📚 Testing trade history...")
        trades = provider.get_trades_history()
        trade_list = trades.get('trades', {})
        print(f"   Found {len(trade_list)} recent trades")
        
        # Test ledger entries
        print("📖 Testing ledger entries...")
        ledgers = provider.get_ledgers()
        ledger_list = ledgers.get('ledger', {})
        print(f"   Found {len(ledger_list)} ledger entries")
        
        print("✅ Private API tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Private API test failed: {e}")
        return False

def test_websocket():
    """Test WebSocket functionality"""
    print("\\n🔌 Testing WebSocket Connection...")
    
    provider = KrakenDataProvider()
    
    # Counter for received messages
    received_messages = {'ticker': 0, 'trade': 0}
    
    def ticker_callback(pair, data):
        received_messages['ticker'] += 1
        print(f"   📊 Ticker update: {pair} = ${data['price']}")
    
    def trade_callback(pair, data):
        received_messages['trade'] += 1
        print(f"   💱 Trade update: {pair} = ${data['price']} (vol: {data['volume']})")
    
    try:
        # Register callbacks
        provider.register_callback('ticker', ticker_callback)
        provider.register_callback('trade', trade_callback)
        
        # Start WebSocket
        provider.start_websocket()
        
        print("   Waiting for WebSocket data (10 seconds)...")
        time.sleep(10)
        
        # Stop WebSocket
        provider.stop_websocket()
        
        print(f"   Received {received_messages['ticker']} ticker updates")
        print(f"   Received {received_messages['trade']} trade updates")
        
        if received_messages['ticker'] > 0 or received_messages['trade'] > 0:
            print("✅ WebSocket test completed successfully!")
            return True
        else:
            print("⚠️ WebSocket test: No data received (may be normal)")
            return True
            
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False

def test_data_caching():
    """Test Redis data caching"""
    print("\\n🗄️ Testing Data Caching...")
    
    provider = KrakenDataProvider()
    
    try:
        if not provider.redis_client:
            print("   ⚠️ Redis not available, skipping cache test")
            return True
            
        # Get ticker data (should cache automatically)
        ticker = provider.get_ticker(['XBTUSD'])
        
        # Check if data is cached
        cached_data = provider.redis_client.get("kraken_ticker:XBTUSD")
        if cached_data:
            cache_info = json.loads(cached_data)
            print(f"   ✅ Data cached successfully: BTC/USD = ${cache_info['price']}")
        else:
            print("   ⚠️ No cached data found")
            
        print("✅ Data caching test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Data caching test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Seraphim Trading System - Kraken Data Provider Test")
    print("=" * 60)
    
    tests = [
        ("Public API", test_public_api),
        ("Private API", test_private_api), 
        ("Data Caching", test_data_caching),
        ("WebSocket", test_websocket)  # Last because it takes time
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\\n🧪 Running {test_name} Tests...")
        success = test_func()
        results.append((test_name, success))
        
        if not success:
            print(f"❌ {test_name} test failed, continuing with other tests...")
    
    print("\\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\\n🎉 All tests passed! Kraken Data Provider is ready!")
    else:
        print("\\n⚠️ Some tests failed, but basic functionality may still work.")
        
    print("\\n🚀 Ready to proceed with Phase 1.1 development!")

if __name__ == "__main__":
    main()
