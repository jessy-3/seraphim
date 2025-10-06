#!/usr/bin/env python3
"""
Calculate technical indicators from OHLC data
"""
import os
import sys
import django
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to Python path
sys.path.append('/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

from api.models import OhlcPrice, Indicator

def calculate_sma(data, window):
    """Simple Moving Average"""
    return data.rolling(window=window).mean()

def calculate_ema(data, window):
    """Exponential Moving Average"""
    return data.ewm(span=window).mean()

def calculate_rsi(data, window=14):
    """Relative Strength Index"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """MACD (Moving Average Convergence Divergence)"""
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_indicators_for_symbol(symbol, limit=100):
    """Calculate indicators for a specific symbol"""
    
    print(f"📊 Calculating indicators for {symbol}...")
    
    # Get OHLC data
    ohlc_data = OhlcPrice.objects.filter(
        symbol=symbol
    ).order_by('date').values('date', 'open', 'high', 'low', 'close', 'volume')
    
    if not ohlc_data:
        print(f"  ❌ No OHLC data found for {symbol}")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(list(ohlc_data))
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['open'] = df['open'].astype(float)
    
    if len(df) < 50:
        print(f"  ⚠️  Insufficient data for {symbol} (only {len(df)} records)")
        return
    
    print(f"  ✅ Processing {len(df)} OHLC records")
    
    # Calculate indicators
    df['sma_20'] = calculate_sma(df['close'], 20)
    df['ema_12'] = calculate_ema(df['close'], 12)
    df['ema_26'] = calculate_ema(df['close'], 26)
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    macd, signal, histogram = calculate_macd(df['close'])
    df['macd'] = macd
    df['macd_signal'] = signal
    df['macd_histogram'] = histogram
    
    # Remove rows with NaN values (insufficient data for calculation)
    df = df.dropna()
    
    print(f"  📈 Generated {len(df)} indicator records")
    
    # Clear existing indicators for this symbol
    Indicator.objects.filter(symbol=symbol).delete()
    
    # Save indicators to database (limit to recent data to avoid too much data)
    indicators_to_create = []
    recent_df = df.tail(limit)  # Only keep recent data
    
    for _, row in recent_df.iterrows():
        indicator = Indicator(
            symbol=symbol,
            timestamp=row['date'],
            ma_20=round(float(row['sma_20']), 2) if not pd.isna(row['sma_20']) else None,
            ema=round(float(row['ema_12']), 2) if not pd.isna(row['ema_12']) else None,
            upper_ema=round(float(row['ema_26']), 2) if not pd.isna(row['ema_26']) else None,
            macd=round(float(row['macd']), 4) if not pd.isna(row['macd']) else None,
            rsi=round(float(row['rsi']), 2) if not pd.isna(row['rsi']) else None,
        )
        indicators_to_create.append(indicator)
    
    # Bulk create
    if indicators_to_create:
        Indicator.objects.bulk_create(indicators_to_create, batch_size=1000)
        print(f"  💾 Saved {len(indicators_to_create)} indicators to database")
    else:
        print(f"  ⚠️  No valid indicators to save")

def main():
    """Main function to calculate indicators for all symbols with OHLC data"""
    print("🧮 Technical Indicators Calculator")
    print("="*50)
    
    # Get symbols that have OHLC data
    symbols_with_data = OhlcPrice.objects.values_list('symbol', flat=True).distinct()
    
    print(f"Found {len(symbols_with_data)} symbols with OHLC data:")
    for symbol in symbols_with_data:
        print(f"  - {symbol}")
    
    print("\n" + "="*50)
    
    # Calculate indicators for each symbol
    for symbol in symbols_with_data:
        try:
            calculate_indicators_for_symbol(symbol, limit=100)
        except Exception as e:
            print(f"  ❌ Error calculating indicators for {symbol}: {e}")
    
    print("\n" + "="*50)
    print("📊 Summary:")
    
    # Show final statistics
    total_indicators = Indicator.objects.count()
    symbols_with_indicators = Indicator.objects.values_list('symbol', flat=True).distinct()
    
    print(f"Total indicators calculated: {total_indicators}")
    print(f"Symbols with indicators: {len(symbols_with_indicators)}")
    
    # Show latest indicator for each symbol
    print("\n📈 Latest indicators:")
    for symbol in symbols_with_indicators:
        latest = Indicator.objects.filter(symbol=symbol).order_by('-timestamp').first()
        if latest:
            print(f"  {symbol}: RSI={latest.rsi}, MACD={latest.macd}, SMA20={latest.ma_20}")
    
    print("\n✅ Indicator calculation complete!")

if __name__ == '__main__':
    main()
