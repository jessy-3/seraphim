#!/usr/bin/env python3
"""
Fetch extended daily historical data by making multiple batched requests
Specifically targets BTC/USD and ETH/USD from 2015-01-01 onwards
"""
import os
import sys
import django
from datetime import datetime, timezone
from decimal import Decimal
import time

sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

from api.models import OhlcPrice
from api.providers.kraken_provider import KrakenDataProvider

def fetch_daily_history_from_date(provider, kraken_symbol, display_name, start_date_str):
    """
    Fetch daily data starting from a specific date by making multiple requests
    
    Args:
        provider: KrakenDataProvider instance
        kraken_symbol: Kraken pair symbol (e.g., 'XXBTZUSD')
        display_name: Display name (e.g., 'BTC/USD')
        start_date_str: Start date in 'YYYY-MM-DD' format
    """
    print(f"\n{'='*80}")
    print(f"📊 Fetching extended daily history: {display_name}")
    print(f"   Target start date: {start_date_str}")
    print(f"{'='*80}")
    
    interval_seconds = 86400  # 1 Day
    interval_minutes = 1440
    
    # Check existing data
    existing = OhlcPrice.objects.filter(
        symbol=display_name,
        interval=interval_seconds
    )
    existing_count = existing.count()
    
    if existing_count > 0:
        earliest = existing.order_by('date').first()
        latest = existing.order_by('-date').first()
        print(f"\n📚 Current data in database:")
        print(f"   Records: {existing_count:,}")
        print(f"   From: {earliest.date.date()}")
        print(f"   To:   {latest.date.date()}")
    else:
        print(f"\n📚 No existing data")
    
    # Parse start date
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    start_timestamp = int(start_date.replace(tzinfo=timezone.utc).timestamp())
    
    print(f"\n🔄 Starting data fetch from {start_date_str}...")
    
    total_saved = 0
    batch_count = 0
    max_batches = 100  # Allow more batches for historical data
    since_timestamp = start_timestamp
    
    while batch_count < max_batches:
        batch_count += 1
        
        try:
            # Fetch data from Kraken
            result = provider.get_ohlc_data(kraken_symbol, interval=interval_minutes, since=since_timestamp)
            
            if not result or kraken_symbol not in result:
                print(f"  ⚠️  Batch {batch_count}: No data returned")
                break
            
            ohlc_data = result[kraken_symbol]
            
            if not ohlc_data or len(ohlc_data) == 0:
                print(f"  ⚠️  Batch {batch_count}: Empty data")
                break
            
            # Prepare records
            new_records = []
            last_timestamp = None
            
            for candle in ohlc_data:
                timestamp = int(candle[0])
                date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                last_timestamp = timestamp
                
                # Check if exists
                exists = OhlcPrice.objects.filter(
                    symbol=display_name,
                    interval=interval_seconds,
                    unix=date
                ).exists()
                
                if not exists:
                    new_records.append(OhlcPrice(
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
            
            # Save new records
            if new_records:
                OhlcPrice.objects.bulk_create(new_records, ignore_conflicts=True)
                total_saved += len(new_records)
                date_str = datetime.fromtimestamp(last_timestamp, tz=timezone.utc).strftime('%Y-%m-%d')
                print(f"  Batch {batch_count}: +{len(new_records)} records (up to {date_str})")
            else:
                print(f"  Batch {batch_count}: No new records (all exist)")
            
            # Check if we've reached the present
            now = datetime.now(timezone.utc)
            if last_timestamp and datetime.fromtimestamp(last_timestamp, tz=timezone.utc) >= now:
                print(f"  ✅ Reached current date")
                break
            
            # If we got less than 500 records, might be at the end
            if len(ohlc_data) < 500:
                print(f"  ✅ Received less than 500 records, likely at end")
                break
            
            # Continue from last timestamp
            since_timestamp = last_timestamp
            
            # Rate limiting
            time.sleep(1.0)  # Be more conservative with rate limiting
            
        except Exception as e:
            print(f"  ❌ Error in batch {batch_count}: {e}")
            import traceback
            traceback.print_exc()
            break
    
    # Final statistics
    print(f"\n{'='*80}")
    print(f"✅ Fetch complete for {display_name}")
    print(f"{'='*80}")
    print(f"   New records saved: {total_saved:,}")
    print(f"   Total batches: {batch_count}")
    
    # Show final state
    final = OhlcPrice.objects.filter(
        symbol=display_name,
        interval=interval_seconds
    )
    final_count = final.count()
    
    if final_count > 0:
        final_earliest = final.order_by('date').first()
        final_latest = final.order_by('-date').first()
        days_span = (final_latest.date - final_earliest.date).days
        years_span = days_span / 365.25
        
        print(f"\n📊 Final statistics:")
        print(f"   Total records: {final_count:,}")
        print(f"   Date range: {final_earliest.date.date()} to {final_latest.date.date()}")
        print(f"   Span: {days_span} days ({years_span:.2f} years)")
        print(f"   Price range: ${float(final_earliest.close):,.2f} to ${float(final_latest.close):,.2f}")
        
        # Show some sample data
        print(f"\n   Sample data (first 5 days):")
        for record in final.order_by('date')[:5]:
            print(f"     {record.date.date()}: ${float(record.close):,.2f}")
        print(f"   ...")
        print(f"   Sample data (latest 3 days):")
        for record in final.order_by('-date')[:3]:
            print(f"     {record.date.date()}: ${float(record.close):,.2f}")

def main():
    """Main function"""
    print("="*80)
    print("🏦 Extended Daily Historical Data Fetcher")
    print("="*80)
    
    provider = KrakenDataProvider()
    
    # BTC/USD from 2015-01-01
    print("\n" + "="*80)
    print("📈 Fetching BTC/USD daily data from 2015-01-01")
    print("="*80)
    fetch_daily_history_from_date(
        provider,
        'XXBTZUSD',
        'BTC/USD',
        '2015-01-01'
    )
    
    # ETH/USD from 2015-08-07 (Ethereum launch date)
    print("\n" + "="*80)
    print("📈 Fetching ETH/USD daily data from 2015-08-07")
    print("="*80)
    fetch_daily_history_from_date(
        provider,
        'XETHZUSD',
        'ETH/USD',
        '2015-08-07'
    )
    
    print("\n" + "="*80)
    print("✅ All extended daily data fetch complete!")
    print("="*80)

if __name__ == '__main__':
    main()

