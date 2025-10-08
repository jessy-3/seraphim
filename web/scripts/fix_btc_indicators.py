#!/usr/bin/env python3
"""
Simple script to fix BTC/USD indicators
"""
import os
import sys
import django
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# Add project root to Python path
sys.path.append('/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

from api.models import OhlcPrice, Indicator

def calculate_rsi(data, window=14):
    """Relative Strength Index"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_sma(data, window):
    """Simple Moving Average"""
    return data.rolling(window=window).mean()

def calculate_ema(data, window):
    """Exponential Moving Average"""
    return data.ewm(span=window).mean()

def calculate_macd(data, fast=12, slow=26, signal=9):
    """MACD (Moving Average Convergence Divergence)"""
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def fix_btc_indicators():
    print("🧮 Fixing BTC/USD indicators...")
    
    # Get BTC/USD OHLC data
    ohlc_data = OhlcPrice.objects.filter(
        symbol='BTC/USD',
        interval=86400  # Daily
    ).order_by('date').values('date', 'open', 'high', 'low', 'close', 'volume')
    
    if not ohlc_data:
        print("❌ No OHLC data found for BTC/USD")
        return
    
    df = pd.DataFrame(list(ohlc_data))
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    
    print(f"📊 Processing {len(df)} OHLC records")
    
    # Calculate indicators
    df['sma_20'] = calculate_sma(df['close'], 20)
    df['ema_12'] = calculate_ema(df['close'], 12) 
    df['ema_26'] = calculate_ema(df['close'], 26)
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    # Calculate MACD
    macd, signal, histogram = calculate_macd(df['close'])
    df['macd'] = macd
    
    # Remove NaN values
    df = df.dropna()
    
    print(f"📈 Generated {len(df)} indicator records")
    
    # Clear existing indicators
    deleted_count = Indicator.objects.filter(symbol='BTC/USD', interval=86400).count()
    Indicator.objects.filter(symbol='BTC/USD', interval=86400).delete()
    print(f"🗑️  Deleted {deleted_count} existing indicators")
    
    # Create indicators one by one for better error handling
    created_count = 0
    for index, row in df.tail(100).iterrows():  # Only recent 100 records
        try:
            # Ensure timestamp is a proper datetime
            if isinstance(index, pd.Timestamp):
                timestamp = index.to_pydatetime()
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=pytz.UTC)
            else:
                timestamp = pd.to_datetime(index).to_pydatetime().replace(tzinfo=pytz.UTC)
            
            unix_timestamp = int(timestamp.timestamp())
            
            print(f"Creating indicator for {timestamp} (unix: {unix_timestamp})")
            
            indicator = Indicator.objects.create(
                symbol='BTC/USD',
                unix=timestamp,  # UnixDateTimeField expects datetime, not int
                timestamp=timestamp,
                interval=86400,
                ma_20=round(float(row['sma_20']), 2) if not pd.isna(row['sma_20']) else None,
                ema=round(float(row['ema_12']), 2) if not pd.isna(row['ema_12']) else None,
                upper_ema=round(float(row['ema_26']), 2) if not pd.isna(row['ema_26']) else None,
                macd=round(float(row['macd']), 4) if not pd.isna(row['macd']) else None,
                rsi=round(float(row['rsi']), 2) if not pd.isna(row['rsi']) else None,
            )
            created_count += 1
            
        except Exception as e:
            print(f"❌ Error creating indicator for {index}: {e}")
            continue
    
    print(f"✅ Created {created_count} indicators for BTC/USD")

if __name__ == '__main__':
    fix_btc_indicators()
