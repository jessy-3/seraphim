#!/usr/bin/env python3
"""
Fetch comprehensive historical OHLC data from Kraken
This script downloads as much historical data as available without deleting existing data.

Recommended data ranges:
- BTC/USD, ETH/USD: From earliest available (2013/2015+) for 10+ years of data
- Other major pairs: From 2020 or when trading started
"""
import os
import sys
import django
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
    '1H': 60,
    '4H': 240,
    '1D': 1440,
    '1W': 10080
}

INTERVAL_SECONDS = {
    '1H': 3600,
    '4H': 14400,
    '1D': 86400,
    '1W': 604800
}

# Kraken symbols mapping
KRAKEN_PAIRS = {
    'BTC/USD': 'XXBTZUSD',
    'ETH/USD': 'XETHZUSD',
    'SOL/USD': 'SOLUSD',
    'DOGE/USD': 'XDGUSD',
    'BCH/USD': 'BCHUSD',
    'LTC/USD': 'XLTCZUSD',
    'XRP/USD': 'XXRPZUSD',
    'LINK/USD': 'LINKUSD',
    'ETH/BTC': 'XETHXXBT',
}

def fetch_historical_data_batch(provider, symbol, display_name, interval_name, since_timestamp=None):
    """
    Fetch a batch of historical OHLC data starting from since_timestamp
    
    Args:
        provider: KrakenDataProvider instance
        symbol: Kraken pair symbol
        display_name: Display name (e.g., 'BTC/USD')
        interval_name: Interval name (e.g., '1D')
        since_timestamp: Unix timestamp to start from (None = earliest available)
    
    Returns:
        (num_records_saved, last_timestamp)
    """
    interval_minutes = INTERVALS[interval_name]
    interval_seconds = INTERVAL_SECONDS[interval_name]
    
    try:
        # Fetch data from Kraken with 'since' parameter
        result = provider.get_ohlc_data(symbol, interval=interval_minutes, since=since_timestamp)
        
        if not result or symbol not in result:
            return 0, None
        
        ohlc_data = result[symbol]
        
        if not ohlc_data:
            return 0, None
        
        # Prepare bulk insert (only insert records that don't exist)
        ohlc_records = []
        last_timestamp = None
        
        for candle in ohlc_data:
            timestamp = int(candle[0])
            date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            last_timestamp = timestamp
            
            # Check if this record already exists
            exists = OhlcPrice.objects.filter(
                symbol=display_name,
                interval=interval_seconds,
                unix=date
            ).exists()
            
            if not exists:
                ohlc_records.append(OhlcPrice(
                    unix=date,
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
        if ohlc_records:
            OhlcPrice.objects.bulk_create(ohlc_records, ignore_conflicts=True)
        
        return len(ohlc_records), last_timestamp
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return 0, None

def fetch_full_history_for_symbol(provider, symbol, display_name, interval_name, target_years=None):
    """
    Fetch complete historical data for a symbol by making multiple batched requests
    
    Args:
        provider: KrakenDataProvider instance
        symbol: Kraken pair symbol
        display_name: Display name
        interval_name: Interval name
        target_years: Target number of years to fetch (None = all available)
    """
    print(f"\n{'='*80}")
    print(f"📊 Fetching full history: {display_name} @ {interval_name}")
    if target_years:
        print(f"   Target: {target_years} years of data")
    print(f"{'='*80}")
    
    interval_seconds = INTERVAL_SECONDS[interval_name]
    
    # Check existing data
    existing_count = OhlcPrice.objects.filter(
        symbol=display_name,
        interval=interval_seconds
    ).count()
    
    existing_earliest = OhlcPrice.objects.filter(
        symbol=display_name,
        interval=interval_seconds
    ).order_by('date').first()
    
    existing_latest = OhlcPrice.objects.filter(
        symbol=display_name,
        interval=interval_seconds
    ).order_by('-date').first()
    
    if existing_count > 0:
        print(f"📚 Existing data: {existing_count} records")
        print(f"   From: {existing_earliest.date.strftime('%Y-%m-%d')}")
        print(f"   To:   {existing_latest.date.strftime('%Y-%m-%d')}")
    else:
        print(f"📚 No existing data")
    
    # Start fetching from earliest available (or from where we left off)
    since_timestamp = None
    total_saved = 0
    batch_count = 0
    max_batches = 50  # Prevent infinite loops
    
    print(f"\n🔄 Starting data fetch...")
    
    while batch_count < max_batches:
        batch_count += 1
        
        saved, last_timestamp = fetch_historical_data_batch(
            provider, symbol, display_name, interval_name, since_timestamp
        )
        
        total_saved += saved
        
        if saved > 0:
            # Show progress
            date_str = datetime.fromtimestamp(last_timestamp, tz=timezone.utc).strftime('%Y-%m-%d')
            print(f"  Batch {batch_count}: +{saved} records (up to {date_str})")
        
        # If we got less than 720 records (typical Kraken limit), we've reached the end
        if last_timestamp is None or saved < 500:
            break
        
        # Continue from the last timestamp
        since_timestamp = last_timestamp
        
        # Small delay to respect API rate limits
        import time
        time.sleep(0.5)
    
    # Final statistics
    final_count = OhlcPrice.objects.filter(
        symbol=display_name,
        interval=interval_seconds
    ).count()
    
    final_earliest = OhlcPrice.objects.filter(
        symbol=display_name,
        interval=interval_seconds
    ).order_by('date').first()
    
    final_latest = OhlcPrice.objects.filter(
        symbol=display_name,
        interval=interval_seconds
    ).order_by('-date').first()
    
    print(f"\n✅ Fetch complete:")
    print(f"   New records saved: {total_saved}")
    print(f"   Total records now: {final_count}")
    if final_earliest and final_latest:
        days_span = (final_latest.date - final_earliest.date).days
        years_span = days_span / 365.25
        print(f"   Date range: {final_earliest.date.strftime('%Y-%m-%d')} to {final_latest.date.strftime('%Y-%m-%d')}")
        print(f"   Span: {days_span} days ({years_span:.2f} years)")

def main():
    """Main function to fetch comprehensive historical data"""
    print("="*80)
    print("🏦 Kraken Historical Data Downloader")
    print("="*80)
    
    provider = KrakenDataProvider()
    
    # Priority 1: Core pairs with maximum history
    print("\n" + "="*80)
    print("📈 PRIORITY 1: Core Trading Pairs (Maximum History)")
    print("="*80)
    
    core_pairs = {
        'BTC/USD': ['1D', '1W', '4H', '1H'],  # All timeframes
        'ETH/USD': ['1D', '1W', '4H', '1H'],  # All timeframes
    }
    
    for display_name, intervals in core_pairs.items():
        kraken_symbol = KRAKEN_PAIRS[display_name]
        for interval in intervals:
            fetch_full_history_for_symbol(
                provider, kraken_symbol, display_name, interval
            )
    
    # Priority 2: Major altcoins - daily and weekly data
    print("\n" + "="*80)
    print("📊 PRIORITY 2: Major Altcoins (Multi-year History)")
    print("="*80)
    
    major_altcoins = {
        'SOL/USD': ['1D', '1W'],
        'DOGE/USD': ['1D', '1W'],
        'LTC/USD': ['1D', '1W'],
        'XRP/USD': ['1D', '1W'],
        'LINK/USD': ['1D', '1W'],
        'BCH/USD': ['1D', '1W'],
    }
    
    for display_name, intervals in major_altcoins.items():
        kraken_symbol = KRAKEN_PAIRS[display_name]
        for interval in intervals:
            fetch_full_history_for_symbol(
                provider, kraken_symbol, display_name, interval
            )
    
    # Priority 3: Additional pairs and shorter timeframes
    print("\n" + "="*80)
    print("📉 PRIORITY 3: Additional Timeframes")
    print("="*80)
    
    additional = {
        'ETH/BTC': ['1D', '1W'],
        'SOL/USD': ['4H'],
        'DOGE/USD': ['4H'],
    }
    
    for display_name, intervals in additional.items():
        kraken_symbol = KRAKEN_PAIRS[display_name]
        for interval in intervals:
            fetch_full_history_for_symbol(
                provider, kraken_symbol, display_name, interval
            )
    
    # Final summary
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80)
    
    for display_name in ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD']:
        print(f"\n{display_name}:")
        for interval_name, interval_seconds in INTERVAL_SECONDS.items():
            count = OhlcPrice.objects.filter(
                symbol=display_name,
                interval=interval_seconds
            ).count()
            if count > 0:
                earliest = OhlcPrice.objects.filter(
                    symbol=display_name,
                    interval=interval_seconds
                ).order_by('date').first()
                latest = OhlcPrice.objects.filter(
                    symbol=display_name,
                    interval=interval_seconds
                ).order_by('-date').first()
                years = (latest.date - earliest.date).days / 365.25
                print(f"  {interval_name}: {count:,} records ({earliest.date.strftime('%Y-%m-%d')} to {latest.date.strftime('%Y-%m-%d')}, {years:.1f} years)")
    
    print("\n" + "="*80)
    print("✅ Historical data fetch complete!")
    print("="*80)

if __name__ == '__main__':
    main()

