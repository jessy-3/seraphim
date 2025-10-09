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

# ========================================
# Multi-Dimensional Analysis Functions
# ========================================

def calculate_channel_position(price, ema_low, ema_high):
    """
    Calculate price position within EMA channel
    Returns: percentage (0-100% = within channel, >100% = above channel)
    """
    if not ema_low or not ema_high or ema_high <= ema_low:
        return None
    
    position = (price - ema_low) / (ema_high - ema_low) * 100
    return round(position, 1)

def calculate_deviation(price, ema_high):
    """
    Calculate price deviation from EMA High
    Returns: percentage (positive = above EMA High)
    """
    if not ema_high or ema_high == 0:
        return None
    
    deviation = (price - ema_high) / ema_high * 100
    return round(deviation, 2)

def get_deviation_penalty(deviation):
    """
    Calculate confidence penalty based on price deviation
    """
    if deviation is None or deviation < 0:
        return 0  # No penalty if within channel
    
    if deviation < 3:
        return 5
    elif deviation < 5:
        return 15
    elif deviation < 10:
        return 25
    else:
        return 40

def calculate_recent_gain(current_price, historical_data, days=10):
    """
    Calculate recent price gain over N days
    Args:
        current_price: current closing price
        historical_data: list of OhlcPrice objects (newest first)
        days: lookback period
    Returns: gain percentage
    """
    if len(historical_data) <= days:
        return None
    
    past_price = float(historical_data[days].close)
    gain = (current_price - past_price) / past_price * 100
    
    return round(gain, 2)

def get_gain_penalty(gain_10d, gain_20d):
    """
    Calculate confidence penalty based on recent gains
    """
    penalty = 0
    warnings = []
    
    if gain_10d is not None:
        if gain_10d > 20:
            penalty += 20
            warnings.append(f"10日暴涨 {gain_10d:+.1f}%")
        elif gain_10d > 10:
            penalty += 10
            warnings.append(f"10日快涨 {gain_10d:+.1f}%")
        elif gain_10d > 7:
            penalty += 5
            warnings.append(f"10日上涨 {gain_10d:+.1f}%")
    
    if gain_20d is not None:
        if gain_20d > 40:
            penalty += 15
            warnings.append(f"20日涨幅过大 {gain_20d:+.1f}%")
        elif gain_20d > 20:
            penalty += 5
    
    return penalty, warnings

def calculate_historical_position(current_price, historical_data, lookback_days=365):
    """
    Calculate price position within historical range
    """
    if len(historical_data) < lookback_days:
        lookback_days = len(historical_data)
    
    if lookback_days == 0:
        return None
    
    prices = [float(p.close) for p in historical_data[:lookback_days]]
    
    if not prices:
        return None
    
    year_high = max(prices)
    year_low = min(prices)
    
    distance_from_high = (current_price - year_high) / year_high * 100
    distance_from_low = (current_price - year_low) / year_low * 100
    
    return {
        'year_high': year_high,
        'year_low': year_low,
        'distance_from_high': round(distance_from_high, 2),
        'distance_from_low': round(distance_from_low, 2),
        'position_pct': round((current_price - year_low) / (year_high - year_low) * 100, 1) if year_high != year_low else 50
    }

def get_historical_penalty(distance_from_high):
    """
    Calculate confidence penalty based on historical position
    """
    if distance_from_high is None:
        return 0, []
    
    if distance_from_high > -5:
        return 20, [f"接近年度高点 {distance_from_high:+.1f}%"]
    elif distance_from_high > -15:
        return 10, [f"中高位置 {distance_from_high:+.1f}%"]
    elif distance_from_high < -50:
        return -15, [f"✅ 低位机会 {distance_from_high:+.1f}%"]  # Negative = bonus
    else:
        return 0, []

def detect_volume_divergence(historical_data, window=5):
    """
    Detect volume divergence
    Returns: 'BEARISH_DIV' (price up, volume down) or 'BULLISH_DIV' or None
    """
    if len(historical_data) < window * 2:
        return None
    
    # Recent window
    recent_prices = [float(p.close) for p in historical_data[:window]]
    recent_volumes = [float(p.volume) if p.volume else 0 for p in historical_data[:window]]
    
    # Past window
    past_prices = [float(p.close) for p in historical_data[window:window*2]]
    past_volumes = [float(p.volume) if p.volume else 0 for p in historical_data[window:window*2]]
    
    if not recent_prices or not past_prices:
        return None
    
    recent_price_avg = sum(recent_prices) / len(recent_prices)
    recent_volume_avg = sum(recent_volumes) / len(recent_volumes) if sum(recent_volumes) > 0 else 0
    
    past_price_avg = sum(past_prices) / len(past_prices)
    past_volume_avg = sum(past_volumes) / len(past_volumes) if sum(past_volumes) > 0 else 0
    
    if past_price_avg == 0 or past_volume_avg == 0:
        return None
    
    price_change = (recent_price_avg - past_price_avg) / past_price_avg
    volume_change = (recent_volume_avg - past_volume_avg) / past_volume_avg
    
    # Bearish divergence: price up >5%, volume down >20%
    if price_change > 0.05 and volume_change < -0.2:
        return 'BEARISH_DIV'
    
    # Bullish divergence: price down >5%, volume down >20%
    elif price_change < -0.05 and volume_change < -0.2:
        return 'BULLISH_DIV'
    
    return None

# ========================================
# Strategy Functions
# ========================================

def generate_trend_following_signal(symbol, interval, latest_price, indicator, regime, historical_data):
    """
    Strategy 1: EMA Channel Breakout (Trend Following) with Multi-Dimensional Analysis
    - Prevents chasing tops and bottoms
    - Buy: Price breaks above EMA High (with safety checks)
    - Sell: Price breaks below EMA Low or back into channel
    """
    ema_high = float(indicator.ema_high_33) if indicator.ema_high_33 else None
    ema_low = float(indicator.ema_low_33) if indicator.ema_low_33 else None
    
    if not ema_high or not ema_low:
        return None
    
    close_price = float(latest_price)
    rsi = float(indicator.rsi) if indicator.rsi else None
    
    # === Multi-Dimensional Analysis ===
    channel_position = calculate_channel_position(close_price, ema_low, ema_high)
    deviation = calculate_deviation(close_price, ema_high)
    gain_10d = calculate_recent_gain(close_price, historical_data, 10)
    gain_20d = calculate_recent_gain(close_price, historical_data, 20)
    historical_pos = calculate_historical_position(close_price, historical_data, 365)
    volume_div = detect_volume_divergence(historical_data, 5)
    
    # Base confidence and warnings
    confidence = 50
    trigger_reasons = []
    
    # Initialize confidence breakdown tracker
    breakdown = {
        'base_score': 50,
        'adjustments': [],
        'final_score': 0,
        'metrics': {
            'channel_position': channel_position,
            'deviation': deviation,
            'rsi': rsi,
            'gain_10d': gain_10d,
            'gain_20d': gain_20d,
            'historical_distance': historical_pos['distance_from_high'] if historical_pos else None,
            'volume_divergence': volume_div
        }
    }
    
    # ========================================
    # BUY SIGNAL: Price above EMA High
    # ========================================
    if close_price > ema_high:
        signal_type = 'buy'
        trigger_reasons.append(f"突破EMA High ${ema_high:.2f}")
        
        # 1. Channel Position Analysis (HIGHEST WEIGHT)
        if channel_position is not None:
            if channel_position > 200:
                confidence -= 40
                breakdown['adjustments'].append({'factor': '通道位置', 'value': f'{channel_position:.0f}%', 'impact': -40, 'reason': '极度超买'})
                trigger_reasons.append(f"⚠️ 极度超买：通道位置 {channel_position:.0f}%")
            elif channel_position > 150:
                confidence -= 30
                breakdown['adjustments'].append({'factor': '通道位置', 'value': f'{channel_position:.0f}%', 'impact': -30, 'reason': '严重超买'})
                trigger_reasons.append(f"⚠️ 严重超买：通道位置 {channel_position:.0f}%")
            elif channel_position > 100:
                confidence -= 20
                breakdown['adjustments'].append({'factor': '通道位置', 'value': f'{channel_position:.0f}%', 'impact': -20, 'reason': '突破通道'})
                trigger_reasons.append(f"⚠️ 突破通道：位置 {channel_position:.0f}%")
            elif channel_position > 80:
                confidence -= 10
                breakdown['adjustments'].append({'factor': '通道位置', 'value': f'{channel_position:.0f}%', 'impact': -10, 'reason': '接近上轨'})
            elif channel_position < 40:
                confidence += 20
                breakdown['adjustments'].append({'factor': '通道位置', 'value': f'{channel_position:.0f}%', 'impact': +20, 'reason': '低位机会'})
        
        # 2. Deviation from EMA High
        deviation_penalty = get_deviation_penalty(deviation)
        if deviation_penalty > 0:
            confidence -= deviation_penalty
            breakdown['adjustments'].append({'factor': '乖离率', 'value': f'{deviation:+.1f}%', 'impact': -deviation_penalty, 'reason': '价格偏离EMA'})
            if deviation and deviation > 0:
                trigger_reasons.append(f"乖离率 {deviation:+.1f}%")
        
        # 3. RSI Overbought Check
        if rsi is not None:
            if rsi > 80:
                confidence -= 25
                breakdown['adjustments'].append({'factor': 'RSI', 'value': f'{rsi:.1f}', 'impact': -25, 'reason': 'RSI极度超买'})
                trigger_reasons.append(f"⚠️ RSI极度超买 {rsi:.1f}")
            elif rsi > 70:
                confidence -= 15
                breakdown['adjustments'].append({'factor': 'RSI', 'value': f'{rsi:.1f}', 'impact': -15, 'reason': 'RSI超买'})
                trigger_reasons.append(f"⚠️ RSI超买 {rsi:.1f}")
            elif rsi < 60:
                confidence += 10
                breakdown['adjustments'].append({'factor': 'RSI', 'value': f'{rsi:.1f}', 'impact': +10, 'reason': 'RSI健康'})
                trigger_reasons.append(f"✅ RSI健康 {rsi:.1f}")
        
        # 4. Recent Gain Check
        gain_penalty, gain_warnings = get_gain_penalty(gain_10d, gain_20d)
        if gain_penalty > 0:
            confidence -= gain_penalty
            breakdown['adjustments'].append({'factor': '近期涨幅', 'value': f'10d:{gain_10d:+.1f}%', 'impact': -gain_penalty, 'reason': '涨幅过快'})
            trigger_reasons.extend(gain_warnings)
        
        # 5. Historical Position Check
        if historical_pos:
            hist_penalty, hist_warnings = get_historical_penalty(historical_pos['distance_from_high'])
            if hist_penalty != 0:
                confidence -= hist_penalty
                breakdown['adjustments'].append({'factor': '历史位置', 'value': f"{historical_pos['distance_from_high']:+.1f}%", 'impact': -hist_penalty, 'reason': '距年度高点'})
                trigger_reasons.extend(hist_warnings)
        
        # 6. Volume Divergence
        if volume_div == 'BEARISH_DIV':
            confidence -= 15
            breakdown['adjustments'].append({'factor': '成交量背离', 'value': '顶背离', 'impact': -15, 'reason': '价涨量缩'})
            trigger_reasons.append("⚠️ 顶背离：价涨量缩")
        
        # 7. Trend Confirmation
        if regime.regime_type == 'trending':
            confidence += 15
            breakdown['adjustments'].append({'factor': '市场趋势', 'value': 'trending', 'impact': +15, 'reason': '趋势市场'})
            trigger_reasons.append("✅ 趋势市场")
        
        # 8. Volume Confirmation
        if regime.volume_ratio and regime.volume_ratio > 1.2:
            confidence += 10
            breakdown['adjustments'].append({'factor': '成交量确认', 'value': f'{regime.volume_ratio:.1f}x', 'impact': +10, 'reason': '成交量放大'})
            trigger_reasons.append(f"✅ 成交量 {regime.volume_ratio:.1f}x")
        
        # 9. MACD Confirmation
        if indicator.macd and indicator.signal_line:
            if float(indicator.macd) > float(indicator.signal_line):
                confidence += 10
                breakdown['adjustments'].append({'factor': 'MACD', 'value': '金叉', 'impact': +10, 'reason': 'MACD金叉'})
                trigger_reasons.append("✅ MACD金叉")
        
        # Adjust signal type based on final confidence
        confidence = max(0, min(100, confidence))
        breakdown['final_score'] = confidence
        
        if confidence < 30:
            signal_type = 'hold'  # Too risky, don't chase
            trigger_reasons.insert(0, "❌ 追高风险过大")
            breakdown['decision'] = '置信度 < 30%，改为 HOLD'
        elif confidence < 50:
            trigger_reasons.insert(0, "⚠️ 谨慎小仓")
            breakdown['decision'] = '置信度 < 50%，小仓试探'
        else:
            breakdown['decision'] = '置信度充足，可以买入'
        
        # Stop loss at EMA Low
        stop_loss = Decimal(str(ema_low))
        risk_pct = ((close_price - float(stop_loss)) / close_price) * 100
        
        return {
            'signal_type': signal_type,
            'strategy': 'trend_follow',
            'confidence': confidence,
            'entry_price': Decimal(str(close_price)),
            'stop_loss': stop_loss,
            'take_profit': None,
            'risk_pct': round(risk_pct, 2),
            'reward_pct': None,
            'trigger_reason': ' | '.join(trigger_reasons),
            'channel_position': channel_position,
            'deviation': deviation,
            'confidence_breakdown': breakdown,
        }
    
    # ========================================
    # SELL SIGNAL: Price below EMA Low
    # ========================================
    elif close_price < ema_low:
        signal_type = 'sell'
        trigger_reasons.append(f"跌破EMA Low ${ema_low:.2f}")
        
        # For sell signals, apply reverse logic
        # Avoid panic selling at bottoms
        if channel_position is not None and channel_position < 0:
            # Price is below channel - might be oversold
            confidence -= 20
            trigger_reasons.append(f"⚠️ 超卖：通道位置 {channel_position:.0f}%")
        
        if rsi is not None and rsi < 30:
            confidence -= 15
            trigger_reasons.append(f"⚠️ RSI超卖 {rsi:.1f}")
        elif rsi is not None and rsi < 40:
            confidence -= 10
        
        # Downtrend confirmation
        if regime.regime_type == 'trending' and regime.trend_direction == 'down':
            confidence += 15
            trigger_reasons.append("✅ 下跌趋势")
        
        # Volume confirmation
        if regime.volume_ratio and regime.volume_ratio > 1.2:
            confidence += 10
            trigger_reasons.append(f"✅ 成交量 {regime.volume_ratio:.1f}x")
        
        # MACD confirmation
        if indicator.macd and indicator.signal_line:
            if float(indicator.macd) < float(indicator.signal_line):
                confidence += 10
                trigger_reasons.append("✅ MACD死叉")
        
        # Volume divergence
        if volume_div == 'BULLISH_DIV':
            confidence -= 15
            trigger_reasons.append("⚠️ 底背离：不要杀跌")
        
        confidence = max(0, min(100, confidence))
        
        if confidence < 30:
            signal_type = 'hold'
            trigger_reasons.insert(0, "❌ 杀跌风险过大")
        
        # Stop loss at EMA High
        stop_loss = Decimal(str(ema_high))
        risk_pct = ((float(stop_loss) - close_price) / close_price) * 100
        
        return {
            'signal_type': signal_type,
            'strategy': 'trend_follow',
            'confidence': confidence,
            'entry_price': Decimal(str(close_price)),
            'stop_loss': stop_loss,
            'take_profit': None,
            'risk_pct': round(risk_pct, 2),
            'reward_pct': None,
            'trigger_reason': ' | '.join(trigger_reasons),
            'channel_position': channel_position,
            'deviation': deviation,
        }
    
    return None

def generate_mean_reversion_signal(symbol, interval, latest_price, indicator, regime, historical_data):
    """
    Strategy 2: Mean Reversion (for ranging markets) with Multi-Dimensional Analysis
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
    rsi = float(indicator.rsi) if indicator.rsi else None
    
    # Only generate signals in ranging markets
    if regime.regime_type != 'ranging':
        return None
    
    # Multi-dimensional analysis
    channel_position = calculate_channel_position(close_price, ema_low, ema_high)
    
    confidence = 45  # Base confidence (lower than trend following)
    trigger_reasons = []
    
    # Calculate distance from channel boundaries
    distance_to_low = abs(close_price - ema_low)
    distance_to_high = abs(close_price - ema_high)
    
    # Buy signal: Price near EMA Low (within 10% of channel width)
    if distance_to_low < (channel_width * 0.1):
        signal_type = 'buy'
        trigger_reasons.append(f"震荡市 - 接近EMA Low ${ema_low:.2f}")
        
        # Channel position bonus (lower = better for buy)
        if channel_position is not None and channel_position < 30:
            confidence += 15
            trigger_reasons.append(f"✅ 通道底部 {channel_position:.0f}%")
        
        # Check RSI oversold
        if rsi and rsi < 35:
            confidence += 20
            trigger_reasons.append(f"✅ RSI超卖 {rsi:.1f}")
        elif rsi and rsi < 45:
            confidence += 10
        
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
            'channel_position': channel_position,
        }
    
    # Sell signal: Price near EMA High
    elif distance_to_high < (channel_width * 0.1):
        signal_type = 'sell'
        trigger_reasons.append(f"震荡市 - 接近EMA High ${ema_high:.2f}")
        
        # Channel position check (higher = better for sell)
        if channel_position is not None and channel_position > 70:
            confidence += 15
            trigger_reasons.append(f"✅ 通道顶部 {channel_position:.0f}%")
        
        # Check RSI overbought
        if rsi and rsi > 65:
            confidence += 20
            trigger_reasons.append(f"✅ RSI超买 {rsi:.1f}")
        elif rsi and rsi > 55:
            confidence += 10
        
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
            'channel_position': channel_position,
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
    
    # Get historical data (last 400 periods for analysis)
    historical_data = list(OhlcPrice.objects.filter(
        symbol=symbol,
        interval=interval
    ).order_by('-date')[:400])
    
    if len(historical_data) < 30:
        print(f"  ❌ Insufficient historical data ({len(historical_data)} periods)")
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
        # Use trend following strategy with multi-dimensional analysis
        signal_data = generate_trend_following_signal(
            symbol, interval, latest_ohlc.close, latest_indicator, latest_regime, historical_data
        )
    else:
        # Use mean reversion strategy
        signal_data = generate_mean_reversion_signal(
            symbol, interval, latest_ohlc.close, latest_indicator, latest_regime, historical_data
        )
    
    # If no signal generated, create a "hold" signal
    if not signal_data:
        print(f"  ⏸️  HOLD - No clear signal")
        
        # Create basic confidence breakdown for HOLD signal
        confidence_breakdown = {
            'base_score': 0,
            'adjustments': {
                '市场状态': f"{latest_regime.regime_type} - 无明确方向",
            },
            'final_score': 0,
            'metrics': {
                'RSI': f"{float(latest_indicator.rsi):.1f}" if latest_indicator.rsi else '--',
                'MACD': f"{float(latest_indicator.macd):.4f}" if latest_indicator.macd else '--',
                '市场类型': latest_regime.regime_type,
                'ADX': f"{float(latest_regime.adx):.1f}" if latest_regime.adx else '--',
            }
        }
        
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
            'confidence_breakdown': confidence_breakdown,
        }
    else:
        emoji = "✅" if signal_data['signal_type'] == 'buy' else "🔴" if signal_data['signal_type'] == 'sell' else "⏸️"
        print(f"  {emoji} {signal_data['signal_type'].upper()} - Confidence: {signal_data['confidence']}%")
        print(f"     Strategy: {signal_data['strategy']}")
        print(f"     Entry: ${signal_data['entry_price']}")
        if signal_data['stop_loss']:
            print(f"     Stop Loss: ${signal_data['stop_loss']} (-{signal_data['risk_pct']}%)")
        # Print trigger reasons for detailed analysis
        if signal_data.get('trigger_reason'):
            reasons = signal_data['trigger_reason'].split(' | ')
            if len(reasons) > 2:  # Only print if there are multiple reasons
                print(f"     Reasons:")
                for reason in reasons[:5]:  # Show first 5 reasons
                    print(f"       • {reason}")
    
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
    
    # Always create new signal (for both BUY/SELL/HOLD)
    # This ensures HOLD signals are visible in the UI
    should_create = True
    
    print(f"  🔍 Debug: should_create={should_create}, signal_type={signal_data['signal_type']}")
    
    if should_create:
        print(f"  🔍 Debug: Creating signal object...")
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
            confidence_breakdown=signal_data.get('confidence_breakdown'),
            status='active'
        )
        print(f"  🔍 Debug: About to save signal...")
        signal.save()
        print(f"  💾 Saved new {signal_data['signal_type'].upper()} signal (ID: {signal.id})")

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

