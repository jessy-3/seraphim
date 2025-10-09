#!/usr/bin/env python3
"""
Market Regime Detection - identifies if market is trending or ranging
"""
import os
import sys
import django
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# Add project root to Python path
sys.path.append('/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

from api.models import OhlcPrice, Indicator, MarketRegime

def calculate_channel_metrics(df, ema_high, ema_low):
    """
    Calculate channel-related metrics
    Returns: (in_channel_pct, channel_width_pct)
    """
    # How many bars are inside the channel (last 20 bars)
    recent_df = df.tail(20)
    inside_channel = ((recent_df['close'] >= ema_low) & (recent_df['close'] <= ema_high)).sum()
    in_channel_pct = (inside_channel / len(recent_df)) * 100
    
    # Channel width as percentage of price
    channel_width_pct = ((ema_high - ema_low) / ema_low) * 100
    
    return in_channel_pct, channel_width_pct

def detect_trend_direction(df, ema_high, ema_low):
    """
    Detect trend direction based on price position relative to channel
    Returns: 'up', 'down', or 'neutral'
    """
    close = df['close'].iloc[-1]
    
    if close > ema_high:
        return 'up'
    elif close < ema_low:
        return 'down'
    else:
        return 'neutral'

def calculate_volume_ratio(df):
    """Calculate current volume vs 20-period average"""
    if len(df) < 20:
        return None
    
    recent_volume = df['volume'].tail(20).mean()
    current_volume = df['volume'].iloc[-1]
    
    if recent_volume > 0:
        return float(current_volume / recent_volume)
    return None

def get_higher_timeframe_trend(symbol, current_interval):
    """
    Get trend from higher timeframe for multi-timeframe analysis
    """
    # Map to higher timeframe
    higher_tf_map = {
        3600: 14400,    # 1H -> 4H
        14400: 86400,   # 4H -> 1D
        86400: 604800,  # 1D -> 1W
        604800: 604800  # 1W -> 1W (no higher TF)
    }
    
    higher_interval = higher_tf_map.get(current_interval, current_interval)
    
    # Get latest market regime from higher timeframe
    try:
        higher_regime = MarketRegime.objects.filter(
            symbol=symbol,
            interval=higher_interval
        ).order_by('-timestamp').first()
        
        if higher_regime:
            return higher_regime.trend_direction
    except:
        pass
    
    return None

def detect_market_regime(symbol, interval=86400, lookback=50):
    """
    Detect market regime for a specific symbol and interval
    """
    interval_name = {3600: '1H', 14400: '4H', 86400: '1D', 604800: '1W'}.get(interval, f'{interval}s')
    print(f"🔍 Detecting market regime for {symbol} @ {interval_name}...")
    
    # Get OHLC data
    ohlc_data = OhlcPrice.objects.filter(
        symbol=symbol,
        interval=interval
    ).order_by('-date')[:lookback]
    
    if not ohlc_data:
        print(f"  ❌ No OHLC data found")
        return
    
    # Convert to DataFrame and reverse (oldest first)
    df = pd.DataFrame(list(ohlc_data.values('date', 'open', 'high', 'low', 'close', 'volume')))
    df = df.iloc[::-1].reset_index(drop=True)
    
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    if len(df) < 20:
        print(f"  ⚠️  Insufficient data (only {len(df)} records)")
        return
    
    # Get latest indicator data (includes ADX and EMA Channel)
    latest_indicator = Indicator.objects.filter(
        symbol=symbol,
        interval=interval
    ).order_by('-timestamp').first()
    
    if not latest_indicator:
        print(f"  ❌ No indicator data found")
        return
    
    # Get ADX value
    adx = float(latest_indicator.adx) if latest_indicator.adx else None
    
    # Get EMA Channel values
    ema_high = float(latest_indicator.ema_high_33) if latest_indicator.ema_high_33 else None
    ema_low = float(latest_indicator.ema_low_33) if latest_indicator.ema_low_33 else None
    
    if not adx or not ema_high or not ema_low:
        print(f"  ⚠️  Missing ADX or EMA Channel data")
        return
    
    # Calculate channel metrics
    in_channel_pct, channel_width_pct = calculate_channel_metrics(df, ema_high, ema_low)
    
    # Detect trend direction
    trend_direction = detect_trend_direction(df, ema_high, ema_low)
    
    # Calculate volume ratio
    volume_ratio = calculate_volume_ratio(df)
    
    # Get higher timeframe trend
    higher_tf_trend = get_higher_timeframe_trend(symbol, interval)
    
    # === REGIME DETECTION LOGIC ===
    
    # Method 1: ADX threshold (ADX > 25 = trending, ADX < 20 = ranging)
    adx_trending = adx > 25
    adx_ranging = adx < 20
    
    # Method 2: Channel breakout (price outside channel = trending)
    price_outside_channel = in_channel_pct < 55  # If < 55% time inside = trending
    
    # Combined decision
    if adx_trending and price_outside_channel:
        regime_type = 'trending'
    elif adx_ranging and in_channel_pct > 70:
        regime_type = 'ranging'
    else:
        # Mixed signals - use ADX as tie-breaker
        regime_type = 'trending' if adx > 22 else 'ranging'
    
    print(f"  📊 Regime: {regime_type.upper()}")
    print(f"     ADX: {adx:.2f}")
    print(f"     Channel In: {in_channel_pct:.1f}%")
    print(f"     Trend: {trend_direction}")
    print(f"     Volume Ratio: {volume_ratio:.2f}" if volume_ratio else "     Volume Ratio: N/A")
    
    # Save to database
    timestamp = df['date'].iloc[-1]
    unix_timestamp = int(pd.to_datetime(timestamp).timestamp())
    unix_dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    
    # Delete existing regime for this timestamp (update)
    MarketRegime.objects.filter(
        symbol=symbol,
        interval=interval,
        unix=unix_dt
    ).delete()
    
    # Create new regime record
    regime = MarketRegime(
        symbol=symbol,
        unix=unix_dt,
        timestamp=timestamp,
        interval=interval,
        regime_type=regime_type,
        trend_direction=trend_direction,
        adx=round(adx, 2),
        channel_in_pct=round(in_channel_pct, 2),
        channel_width_pct=round(channel_width_pct, 2),
        higher_tf_trend=higher_tf_trend,
        volume_ratio=round(volume_ratio, 2) if volume_ratio else None
    )
    regime.save()
    
    print(f"  💾 Saved market regime")

def main():
    """Main function to detect market regime for all symbols and intervals"""
    print("🔍 Market Regime Detection")
    print("="*50)
    
    # Define symbols and intervals to process
    symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD',
               'BCH/USD', 'LTC/USD', 'XRP/USD', 'LINK/USD', 'ETH/BTC']
    
    intervals = {
        '1H': 3600,
        '4H': 14400,
        '1D': 86400,
        '1W': 604800
    }
    
    success_count = 0
    error_count = 0
    
    # Process from highest to lowest timeframe (for multi-TF analysis)
    for interval_name in ['1W', '1D', '4H', '1H']:
        interval = intervals[interval_name]
        print(f"\n📊 Processing {interval_name} timeframe...")
        
        for symbol in symbols:
            try:
                detect_market_regime(symbol, interval, lookback=50)
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"  ❌ Error for {symbol} @ {interval_name}: {e}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "="*50)
    print("📊 Summary:")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {error_count}")
    
    # Show latest regimes
    print("\n🔍 Latest Market Regimes:")
    for symbol in symbols:
        for interval_name, interval in [('1D', 86400), ('1W', 604800)]:
            regime = MarketRegime.objects.filter(
                symbol=symbol,
                interval=interval
            ).order_by('-timestamp').first()
            
            if regime:
                emoji = "📈" if regime.regime_type == "trending" else "📊"
                print(f"  {emoji} {symbol} @ {interval_name}: {regime.regime_type.upper()} "
                      f"({regime.trend_direction}, ADX={regime.adx})")
    
    print("\n✅ Market regime detection complete!")

if __name__ == '__main__':
    main()

