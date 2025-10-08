#!/usr/bin/env python3
"""
Fetch historical OHLC data for multiple symbols and timeframes
确保有足够的历史数据来计算所有技术指标
"""
import os
import sys
import django
import time
from datetime import datetime, timezone
from decimal import Decimal

# Add project root to Python path
sys.path.append('/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

from api.models import OhlcPrice, SymbolInfo
from api.providers.kraken_provider import KrakenDataProvider

# Kraken interval mapping (in minutes)
INTERVALS = {
    '1H': 60,      # 1 hour
    '4H': 240,     # 4 hours  
    '1D': 1440,    # 1 day
    '1W': 10080,   # 1 week
}

# Interval in seconds (for database storage)
INTERVAL_SECONDS = {
    '1H': 3600,
    '4H': 14400,
    '1D': 86400,
    '1W': 604800,
}

# Kraken pair names (different from display names)
KRAKEN_PAIRS = {
    'BTC/USD': 'XXBTZUSD',
    'ETH/USD': 'XETHZUSD',
    'SOL/USD': 'SOLUSD',
    'DOGE/USD': 'XDGUSD',
}

def fetch_ohlc_for_symbol(provider, symbol, display_name, interval_name, limit=200):
    """
    Fetch OHLC data for a specific symbol and interval
    
    Args:
        provider: KrakenDataProvider instance
        symbol: Kraken pair symbol (e.g., 'XXBTZUSD')
        display_name: Display name (e.g., 'BTC/USD')
        interval_name: Interval name (e.g., '1H', '4H', '1D', '1W')
        limit: Number of data points to fetch (default 200)
    """
    interval_minutes = INTERVALS[interval_name]
    interval_seconds = INTERVAL_SECONDS[interval_name]
    
    print(f"📊 Fetching {display_name} @ {interval_name} (last {limit} points)...")
    
    try:
        # Fetch OHLC data from Kraken
        result = provider.get_ohlc_data(symbol, interval=interval_minutes)
        
        if not result or symbol not in result:
            print(f"  ❌ No data returned from Kraken for {symbol}")
            return 0
        
        ohlc_data = result[symbol]
        
        if not ohlc_data:
            print(f"  ❌ Empty OHLC data for {symbol}")
            return 0
        
        # Take only the last 'limit' data points
        ohlc_data = ohlc_data[-limit:]
        
        print(f"  ✅ Received {len(ohlc_data)} data points")
        
        # Clear existing data for this symbol and interval
        deleted_count = OhlcPrice.objects.filter(
            symbol=display_name,
            interval=interval_seconds
        ).count()
        
        if deleted_count > 0:
            OhlcPrice.objects.filter(
                symbol=display_name,
                interval=interval_seconds
            ).delete()
            print(f"  🗑️  Deleted {deleted_count} existing records")
        
        # Prepare bulk insert
        ohlc_records = []
        for candle in ohlc_data:
            # Kraken OHLC format: [timestamp, open, high, low, close, vwap, volume, count]
            timestamp = int(candle[0])
            date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            ohlc_records.append(OhlcPrice(
                unix=date,  # UnixDateTimeField expects datetime object
                date=date,
                symbol=display_name,
                interval=interval_seconds,
                open=Decimal(str(candle[1])),
                high=Decimal(str(candle[2])),
                low=Decimal(str(candle[3])),
                close=Decimal(str(candle[4])),
                volume=Decimal(str(candle[6])),
                market_id=2  # Kraken
            ))
        
        # Bulk insert
        OhlcPrice.objects.bulk_create(ohlc_records, ignore_conflicts=True)
        print(f"  ✅ Saved {len(ohlc_records)} records to database")
        
        return len(ohlc_records)
        
    except Exception as e:
        print(f"  ❌ Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return 0

def ensure_symbol_info():
    """确保 SymbolInfo 表中有所有需要的品种"""
    print("\n📝 Ensuring SymbolInfo entries...")
    
    symbols = {
        'BTC/USD': {
            'description': 'Bitcoin / US Dollar',
            'url_symbol': 'btcusd',
            'base_decimals': 8,
            'counter_decimals': 2,
            'market_id': 2,  # Kraken
            'trading': 'Enabled'
        },
        'ETH/USD': {
            'description': 'Ethereum / US Dollar',
            'url_symbol': 'ethusd',
            'base_decimals': 8,
            'counter_decimals': 2,
            'market_id': 2,  # Kraken
            'trading': 'Enabled'
        },
        'SOL/USD': {
            'description': 'Solana / US Dollar',
            'url_symbol': 'solusd',
            'base_decimals': 8,
            'counter_decimals': 2,
            'market_id': 2,  # Kraken
            'trading': 'Enabled'
        },
        'DOGE/USD': {
            'description': 'Dogecoin / US Dollar',
            'url_symbol': 'dogeusd',
            'base_decimals': 8,
            'counter_decimals': 4,
            'market_id': 2,  # Kraken
            'trading': 'Enabled'
        },
    }
    
    for symbol, defaults in symbols.items():
        obj, created = SymbolInfo.objects.get_or_create(
            name=symbol,
            defaults=defaults
        )
        if created:
            print(f"  ✅ Created: {symbol}")
        else:
            print(f"  ℹ️  Exists: {symbol}")

def main():
    """Main function to fetch historical data"""
    print("=" * 70)
    print("🚀 Historical Data Fetcher")
    print("=" * 70)
    
    # Ensure symbol info exists
    ensure_symbol_info()
    
    # Initialize Kraken provider
    print("\n🔌 Connecting to Kraken API...")
    provider = KrakenDataProvider()
    
    # Total statistics
    total_fetched = 0
    total_errors = 0
    
    print("\n" + "=" * 70)
    print("📥 Fetching OHLC data...")
    print("=" * 70)
    
    # Fetch data for each symbol and interval
    for display_name, kraken_symbol in KRAKEN_PAIRS.items():
        print(f"\n{'='*70}")
        print(f"Symbol: {display_name} (Kraken: {kraken_symbol})")
        print(f"{'='*70}")
        
        for interval_name in ['1H', '4H', '1D', '1W']:
            count = fetch_ohlc_for_symbol(
                provider, 
                kraken_symbol, 
                display_name, 
                interval_name,
                limit=200  # Fetch 200 data points per interval
            )
            
            if count > 0:
                total_fetched += count
            else:
                total_errors += 1
            
            # Rate limiting (Kraken allows 1 request per second for public API)
            time.sleep(1.2)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"✅ Total OHLC records fetched: {total_fetched}")
    print(f"❌ Total errors: {total_errors}")
    
    # Show data statistics
    print("\n📈 Database Statistics:")
    for display_name in KRAKEN_PAIRS.keys():
        for interval_name in ['1H', '4H', '1D', '1W']:
            interval_seconds = INTERVAL_SECONDS[interval_name]
            count = OhlcPrice.objects.filter(
                symbol=display_name,
                interval=interval_seconds
            ).count()
            print(f"  {display_name} @ {interval_name}: {count} records")
    
    print("\n✅ Data fetch complete!")
    print("\n💡 Next steps:")
    print("  1. Run: docker exec seraphim-web-1 python scripts/calculate_indicators.py")
    print("  2. Run: docker exec seraphim-web-1 python scripts/calculate_ema_channel.py")
    print("  3. Test the dashboard at: http://localhost:8000/")

if __name__ == '__main__':
    main()

