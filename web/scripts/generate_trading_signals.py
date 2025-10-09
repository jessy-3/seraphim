#!/usr/bin/env python3
"""
Trading Signal Generation - generates buy/sell/hold signals based on market regime and indicators
"""
import os
import sys
import django
import pandas as pd
from datetime import datetime, timezone
from decimal import Decimal

# Add project root to Python path
sys.path.append('/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

from api.models import OhlcPrice, Indicator, MarketRegime, TradingSignal

def generate_trend_following_signal(symbol, interval, latest_price, indicator, regime):
    """
    Strategy 1: EMA Channel Breakout (Trend Following)
    - Buy: Price breaks above EMA High in trending market
    - Sell: Price breaks below EMA Low or back into channel
    """
    ema_high = float(indicator.ema_high_33) if indicator.ema_high_33 else None
    ema_low = float(indicator.ema_low_33) if indicator.ema_low_33 else None
    
    if not ema_high or not ema_low:
        return None
    
    close_price = float(latest_price)
    
    # Calculate confidence based on multiple factors
    confidence = 50  # Base confidence
    trigger_reasons = []
    
    # Buy signal: Price above EMA High
    if close_price > ema_high:
        signal_type = 'buy'
        trigger_reasons.append(f"Price ${close_price:.2f} above EMA High ${ema_high:.2f}")
        
        # Higher confidence if in trending market
        if regime.regime_type == 'trending':
            confidence += 15
            trigger_reasons.append("Strong trending market (ADX)")
        
        # Check volume confirmation
        if regime.volume_ratio and regime.volume_ratio > 1.2:
            confidence += 10
            trigger_reasons.append(f"Volume increased {regime.volume_ratio:.1f}x")
        
        # Check MACD confirmation
        if indicator.macd and indicator.signal_line:
            if float(indicator.macd) > float(indicator.signal_line):
                confidence += 10
                trigger_reasons.append("MACD golden cross")
        
        # Check RSI (not overbought)
        if indicator.rsi and float(indicator.rsi) < 70:
            confidence += 5
        elif indicator.rsi and float(indicator.rsi) > 75:
            confidence -= 10
            trigger_reasons.append(f"Warning: RSI overbought ({float(indicator.rsi):.1f})")
        
        # Stop loss at EMA Low
        stop_loss = Decimal(str(ema_low))
        risk_pct = ((close_price - float(stop_loss)) / close_price) * 100
        
        return {
            'signal_type': signal_type,
            'strategy': 'trend_follow',
            'confidence': min(max(confidence, 0), 100),
            'entry_price': Decimal(str(close_price)),
            'stop_loss': stop_loss,
            'take_profit': None,  # Trend following: no fixed target
            'risk_pct': round(risk_pct, 2),
            'reward_pct': None,
            'trigger_reason': ' | '.join(trigger_reasons),
        }
    
    # Sell signal: Price below EMA Low
    elif close_price < ema_low:
        signal_type = 'sell'
        trigger_reasons.append(f"Price ${close_price:.2f} below EMA Low ${ema_low:.2f}")
        
        if regime.regime_type == 'trending' and regime.trend_direction == 'down':
            confidence += 15
            trigger_reasons.append("Strong downtrend (ADX)")
        
        # Check volume
        if regime.volume_ratio and regime.volume_ratio > 1.2:
            confidence += 10
            trigger_reasons.append(f"Volume increased {regime.volume_ratio:.1f}x")
        
        # Check MACD
        if indicator.macd and indicator.signal_line:
            if float(indicator.macd) < float(indicator.signal_line):
                confidence += 10
                trigger_reasons.append("MACD death cross")
        
        # Stop loss at EMA High
        stop_loss = Decimal(str(ema_high))
        risk_pct = ((float(stop_loss) - close_price) / close_price) * 100
        
        return {
            'signal_type': signal_type,
            'strategy': 'trend_follow',
            'confidence': min(max(confidence, 0), 100),
            'entry_price': Decimal(str(close_price)),
            'stop_loss': stop_loss,
            'take_profit': None,
            'risk_pct': round(risk_pct, 2),
            'reward_pct': None,
            'trigger_reason': ' | '.join(trigger_reasons),
        }
    
    return None

def generate_mean_reversion_signal(symbol, interval, latest_price, indicator, regime):
    """
    Strategy 2: Mean Reversion (for ranging markets)
    - Buy: Price near EMA Low in ranging market
    - Sell: Price near EMA High in ranging market
    """
    ema_high = float(indicator.ema_high_33) if indicator.ema_high_33 else None
    ema_low = float(indicator.ema_low_33) if indicator.ema_low_33 else None
    
    if not ema_high or not ema_low:
        return None
    
    close_price = float(latest_price)
    channel_mid = (ema_high + ema_low) / 2
    channel_width = ema_high - ema_low
    
    # Only generate signals in ranging markets
    if regime.regime_type != 'ranging':
        return None
    
    confidence = 45  # Base confidence (lower than trend following)
    trigger_reasons = []
    
    # Calculate distance from channel boundaries
    distance_to_low = abs(close_price - ema_low)
    distance_to_high = abs(close_price - ema_high)
    
    # Buy signal: Price near EMA Low (within 10% of channel width)
    if distance_to_low < (channel_width * 0.1):
        signal_type = 'buy'
        trigger_reasons.append(f"Price ${close_price:.2f} near EMA Low ${ema_low:.2f}")
        trigger_reasons.append("Ranging market - mean reversion expected")
        
        # Check RSI oversold
        if indicator.rsi and float(indicator.rsi) < 35:
            confidence += 20
            trigger_reasons.append(f"RSI oversold ({float(indicator.rsi):.1f})")
        
        # Target is channel mid or high
        take_profit = Decimal(str(channel_mid))
        stop_loss = Decimal(str(ema_low * 0.98))  # 2% below EMA Low
        
        risk_pct = ((close_price - float(stop_loss)) / close_price) * 100
        reward_pct = ((float(take_profit) - close_price) / close_price) * 100
        
        return {
            'signal_type': signal_type,
            'strategy': 'mean_reversion',
            'confidence': min(max(confidence, 0), 100),
            'entry_price': Decimal(str(close_price)),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_pct': round(risk_pct, 2),
            'reward_pct': round(reward_pct, 2),
            'trigger_reason': ' | '.join(trigger_reasons),
        }
    
    # Sell signal: Price near EMA High
    elif distance_to_high < (channel_width * 0.1):
        signal_type = 'sell'
        trigger_reasons.append(f"Price ${close_price:.2f} near EMA High ${ema_high:.2f}")
        trigger_reasons.append("Ranging market - mean reversion expected")
        
        # Check RSI overbought
        if indicator.rsi and float(indicator.rsi) > 65:
            confidence += 20
            trigger_reasons.append(f"RSI overbought ({float(indicator.rsi):.1f})")
        
        take_profit = Decimal(str(channel_mid))
        stop_loss = Decimal(str(ema_high * 1.02))  # 2% above EMA High
        
        risk_pct = ((float(stop_loss) - close_price) / close_price) * 100
        reward_pct = ((close_price - float(take_profit)) / close_price) * 100
        
        return {
            'signal_type': signal_type,
            'strategy': 'mean_reversion',
            'confidence': min(max(confidence, 0), 100),
            'entry_price': Decimal(str(close_price)),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_pct': round(risk_pct, 2),
            'reward_pct': round(reward_pct, 2),
            'trigger_reason': ' | '.join(trigger_reasons),
        }
    
    return None

def generate_signal_for_symbol(symbol, interval=86400):
    """
    Generate trading signal for a specific symbol and interval
    """
    interval_name = {3600: '1H', 14400: '4H', 86400: '1D', 604800: '1W'}.get(interval, f'{interval}s')
    print(f"📡 Generating signal for {symbol} @ {interval_name}...")
    
    # Get latest price
    latest_ohlc = OhlcPrice.objects.filter(
        symbol=symbol,
        interval=interval
    ).order_by('-date').first()
    
    if not latest_ohlc:
        print(f"  ❌ No OHLC data found")
        return
    
    # Get latest indicator
    latest_indicator = Indicator.objects.filter(
        symbol=symbol,
        interval=interval
    ).order_by('-timestamp').first()
    
    if not latest_indicator:
        print(f"  ❌ No indicator data found")
        return
    
    # Get latest market regime
    latest_regime = MarketRegime.objects.filter(
        symbol=symbol,
        interval=interval
    ).order_by('-timestamp').first()
    
    if not latest_regime:
        print(f"  ❌ No market regime data found")
        return
    
    # Generate signal based on market regime
    signal_data = None
    
    if latest_regime.regime_type == 'trending':
        # Use trend following strategy
        signal_data = generate_trend_following_signal(
            symbol, interval, latest_ohlc.close, latest_indicator, latest_regime
        )
    else:
        # Use mean reversion strategy
        signal_data = generate_mean_reversion_signal(
            symbol, interval, latest_ohlc.close, latest_indicator, latest_regime
        )
    
    # If no signal generated, create a "hold" signal
    if not signal_data:
        print(f"  ⏸️  HOLD - No clear signal")
        signal_data = {
            'signal_type': 'hold',
            'strategy': 'none',
            'confidence': 0,
            'entry_price': latest_ohlc.close,
            'stop_loss': None,
            'take_profit': None,
            'risk_pct': None,
            'reward_pct': None,
            'trigger_reason': f"Price in channel ({latest_regime.regime_type} market)",
        }
    else:
        emoji = "✅" if signal_data['signal_type'] == 'buy' else "🔴"
        print(f"  {emoji} {signal_data['signal_type'].upper()} - Confidence: {signal_data['confidence']}%")
        print(f"     Strategy: {signal_data['strategy']}")
        print(f"     Entry: ${signal_data['entry_price']}")
        if signal_data['stop_loss']:
            print(f"     Stop Loss: ${signal_data['stop_loss']} (-{signal_data['risk_pct']}%)")
    
    # Save signal to database
    timestamp = latest_ohlc.date
    unix_timestamp = int(pd.to_datetime(timestamp).timestamp())
    unix_dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    
    # Check if there's already an active signal for this symbol/interval
    existing_signal = TradingSignal.objects.filter(
        symbol=symbol,
        interval=interval,
        status='active'
    ).order_by('-timestamp').first()
    
    # If signal changed, close the old one
    if existing_signal and existing_signal.signal_type != signal_data['signal_type']:
        existing_signal.status = 'closed'
        existing_signal.exit_price = latest_ohlc.close
        existing_signal.exit_timestamp = timestamp
        # Calculate P&L
        if existing_signal.signal_type == 'buy':
            pnl = ((float(latest_ohlc.close) - float(existing_signal.entry_price)) / float(existing_signal.entry_price)) * 100
        else:
            pnl = ((float(existing_signal.entry_price) - float(latest_ohlc.close)) / float(existing_signal.entry_price)) * 100
        existing_signal.pnl_pct = round(pnl, 2)
        existing_signal.save()
        print(f"  📊 Closed previous signal: {existing_signal.signal_type.upper()} (P&L: {existing_signal.pnl_pct:+.2f}%)")
    
    # Only create new signal if it's not "hold" or if it's different from existing
    if signal_data['signal_type'] != 'hold' and (not existing_signal or existing_signal.signal_type != signal_data['signal_type']):
        signal = TradingSignal(
            symbol=symbol,
            unix=unix_dt,
            timestamp=timestamp,
            interval=interval,
            signal_type=signal_data['signal_type'],
            strategy=signal_data['strategy'],
            market_regime=latest_regime.regime_type,
            confidence=signal_data['confidence'],
            entry_price=signal_data['entry_price'],
            stop_loss=signal_data['stop_loss'],
            take_profit=signal_data['take_profit'],
            risk_pct=signal_data['risk_pct'],
            reward_pct=signal_data['reward_pct'],
            trigger_reason=signal_data['trigger_reason'],
            rsi_value=round(float(latest_indicator.rsi), 2) if latest_indicator.rsi else None,
            macd_value=latest_indicator.macd,
            volume_ratio=latest_regime.volume_ratio,
            status='active'
        )
        signal.save()
        print(f"  💾 Saved new signal")

def main():
    """Main function to generate trading signals for all symbols and intervals"""
    print("📡 Trading Signal Generation")
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
    
    for interval_name, interval in intervals.items():
        print(f"\n📊 Processing {interval_name} timeframe...")
        
        for symbol in symbols:
            try:
                generate_signal_for_symbol(symbol, interval)
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
    
    # Show active signals
    print("\n📡 Active Trading Signals:")
    active_signals = TradingSignal.objects.filter(status='active').order_by('-confidence')
    
    for signal in active_signals[:20]:  # Show top 20
        interval_name = {3600: '1H', 14400: '4H', 86400: '1D', 604800: '1W'}.get(signal.interval, f'{signal.interval}s')
        emoji = "✅" if signal.signal_type == 'buy' else "🔴" if signal.signal_type == 'sell' else "⏸️"
        print(f"  {emoji} {signal.symbol} @ {interval_name}: {signal.signal_type.upper()} "
              f"({signal.confidence}% confidence, {signal.strategy})")
    
    print(f"\n📈 Total active signals: {active_signals.count()}")
    print("\n✅ Signal generation complete!")

if __name__ == '__main__':
    main()

