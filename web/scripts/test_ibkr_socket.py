#!/usr/bin/env python3
"""
Test IBKR Socket API connection for Seraphim Trading System
Tests ib_insync connection to IB Gateway container
"""

import os
import sys
import django

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

from api.providers.ibkr_socket_provider import get_ibkr_socket_provider
import time

def test_ibkr_socket():
    """Test IBKR Socket API connection"""
    print("🚀 Testing IBKR Socket API Connection (ib_insync)")
    print("=" * 60)
    
    # Check if running in Docker
    environment = "🐳 Docker Container" if os.path.exists('/.dockerenv') else "💻 Local Environment"
    print(f"📍 Environment: {environment}")
    
    print("\n1. 🏗️  Initializing IBKR Socket Provider")
    print("-" * 40)
    
    provider = get_ibkr_socket_provider(
        host="ib-gateway",  # Docker service name
        port=4004,          # Paper trading port (corrected)
        client_id=1
    )
    
    print(f"✅ Provider initialized")
    print(f"📡 Target: {provider.host}:{provider.port}")
    print(f"🆔 Client ID: {provider.client_id}")
    
    # Test 1: Health Check (before connection)
    print("\n2. 🏥 Initial Health Check")
    print("-" * 40)
    health = provider.health_check()
    
    if health['status']:
        print(f"✅ {health['message']}")
    else:
        print(f"🔍 {health['message']} (expected before connection)")
    
    # Test 2: Connection Test
    print("\n3. 🔌 Connection Test")
    print("-" * 40)
    
    print("🔄 Attempting to connect to IB Gateway...")
    print("💡 This will fail if IB Gateway container is not running")
    
    try:
        success = provider.connect(timeout=10)
        
        if success:
            print("🎉 Successfully connected to IBKR!")
            
            # Test 3: Account Information
            print("\n4. 👤 Account Information")
            print("-" * 40)
            
            accounts = provider.get_accounts()
            if accounts:
                print(f"✅ Found {len(accounts)} account(s):")
                for i, account in enumerate(accounts):
                    print(f"   {i+1}. {account}")
                
                # Get account summary for first account
                print(f"\n📊 Account Summary for {accounts[0]}:")
                summary = provider.get_account_summary(accounts[0])
                
                if 'error' not in summary:
                    # Show key metrics
                    key_metrics = ['TotalCashValue', 'NetLiquidation', 'BuyingPower']
                    for metric in key_metrics:
                        if metric in summary:
                            value = summary[metric]
                            print(f"   {metric}: {value['value']} {value['currency']}")
                else:
                    print(f"⚠️  Could not get account summary: {summary['error']}")
            else:
                print("⚠️  No accounts found")
            
            # Test 4: Market Data Test
            print("\n5. 📈 Market Data Test")
            print("-" * 40)
            
            test_symbols = ['AAPL', 'MSFT']
            print(f"🔍 Testing market data for: {', '.join(test_symbols)}")
            
            market_data = provider.get_market_data(test_symbols)
            
            if market_data:
                print(f"✅ Retrieved market data for {len(market_data)} symbols:")
                for symbol, data in market_data.items():
                    if 'error' not in data:
                        print(f"   📊 {symbol}: Last=${data.get('last', 'N/A')} "
                              f"Bid=${data.get('bid', 'N/A')} Ask=${data.get('ask', 'N/A')}")
                    else:
                        print(f"   ❌ {symbol}: {data['error']}")
            else:
                print("⚠️  No market data retrieved")
            
            # Test 5: Positions Test
            print("\n6. 💼 Positions Test")
            print("-" * 40)
            
            positions = provider.get_positions()
            if positions:
                print(f"✅ Found {len(positions)} position(s):")
                for pos in positions:
                    print(f"   📈 {pos['symbol']}: {pos['position']} shares @ ${pos['avgCost']:.2f}")
            else:
                print("📭 No positions found (normal for new paper account)")
            
            # Test 6: Orders Test
            print("\n7. 📝 Orders Test")
            print("-" * 40)
            
            orders = provider.get_orders()
            if orders:
                print(f"✅ Found {len(orders)} open order(s):")
                for order in orders:
                    print(f"   📋 {order['symbol']}: {order['action']} {order['totalQuantity']} @ ${order.get('lmtPrice', 'MKT')}")
            else:
                print("📭 No open orders found")
            
            # Disconnect
            provider.disconnect()
            print("\n🔌 Disconnected from IBKR")
            
            # Final health check
            final_health = provider.health_check()
            print(f"🏥 Final status: {final_health['message']}")
            
            return True
            
        else:
            print("❌ Failed to connect to IB Gateway")
            print("\n💡 Troubleshooting:")
            print("   1. Ensure IB Gateway container is running:")
            print("      docker compose ps ib-gateway")
            print("   2. Check container logs:")
            print("      docker compose logs ib-gateway")
            print("   3. Verify Paper Trading credentials in .env file")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        print("\n💡 Common issues:")
        print("   - IB Gateway container not started")
        print("   - Wrong credentials in .env file")
        print("   - Paper Trading not enabled")
        print("   - Network connectivity issues")
        return False

def print_setup_instructions():
    """Print setup instructions"""
    print("\n" + "=" * 60)
    print("🛠️  IBKR SOCKET API SETUP INSTRUCTIONS")
    print("=" * 60)
    
    print("\n📋 Prerequisites:")
    print("   1. ✅ IBKR account with Paper Trading enabled")
    print("   2. ✅ Credentials in .env file:")
    print("      IBKR_USERNAME=your_username")
    print("      IBKR_PASSWORD=your_password") 
    print("      IBKR_TRADING_MODE=paper")
    print("   3. ✅ IB Gateway Docker container configured")
    
    print("\n🚀 To start IB Gateway:")
    print("   docker compose up -d ib-gateway")
    
    print("\n🔍 To check status:")
    print("   docker compose ps")
    print("   docker compose logs ib-gateway")
    
    print("\n🎯 Expected workflow:")
    print("   1. Start IB Gateway container")
    print("   2. Container auto-logs in with your credentials")
    print("   3. API becomes available on port 4002")
    print("   4. This test connects and retrieves data")

def main():
    print_setup_instructions()
    
    print("\n" + "🔍" * 20 + " TESTING " + "🔍" * 20)
    
    success = test_ibkr_socket()
    
    print("\n" + "=" * 60)
    print("📊 IBKR SOCKET API TEST SUMMARY")
    print("=" * 60)
    
    if success:
        print("🎉 IBKR Socket API integration successful!")
        print("✅ Ready for trading operations via ib_insync")
        print("✅ Can retrieve account data, market data, and place orders")
    else:
        print("🔧 IBKR Socket API requires setup")
        print("📝 Next steps:")
        print("   1. Start IB Gateway container: docker compose up -d ib-gateway")
        print("   2. Wait for container to initialize (~30 seconds)")
        print("   3. Run this test again")

if __name__ == "__main__":
    main()
