#!/usr/bin/env python
"""
计算EMA Channel (轨道当值) 指标
- 上轨当值: EMA(High, 33)
- 下轨当值: EMA(Low, 33)

基于Pine Script:
stLong=ta.ema(high,33)   // 上轨当值
stShort=ta.ema(low,33)   // 下轨当值
"""

import os
import sys
import django
from decimal import Decimal
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
django.setup()

from api.models import OhlcPrice, Indicator

def calculate_ema(prices, period):
    """计算指数移动平均线 (EMA)"""
    if len(prices) < period:
        return [None] * len(prices)
    
    # Convert to pandas series for EMA calculation
    series = pd.Series(prices)
    ema = series.ewm(span=period, adjust=False).mean()
    return ema.tolist()

def calculate_ema_channel_for_symbol(symbol='BTC/USD', interval=86400, limit=100):
    """
    为指定符号计算EMA Channel指标
    
    Args:
        symbol: 交易对符号
        interval: 时间间隔 (秒)
        limit: 计算的数据点数量
    """
    print(f"🧮 计算 {symbol} 的EMA Channel指标 (轨道当值)...")
    
    # 获取OHLC数据
    ohlc_data = OhlcPrice.objects.filter(
        symbol=symbol,
        interval=interval
    ).order_by('-date')[:limit]
    
    if not ohlc_data:
        print(f"❌ 没有找到 {symbol} 的OHLC数据")
        return
    
    print(f"📊 找到 {len(ohlc_data)} 条OHLC记录")
    
    # 转换为列表并反转顺序 (最旧的在前)
    ohlc_list = list(reversed(ohlc_data))
    
    # 提取High和Low价格
    high_prices = [float(item.high) for item in ohlc_list]
    low_prices = [float(item.low) for item in ohlc_list]
    
    print(f"💹 价格范围: High {min(high_prices):.2f} - {max(high_prices):.2f}")
    print(f"💹 价格范围: Low {min(low_prices):.2f} - {max(low_prices):.2f}")
    
    # 计算EMA Channel
    ema_high_33 = calculate_ema(high_prices, 33)  # 上轨当值
    ema_low_33 = calculate_ema(low_prices, 33)    # 下轨当值
    
    print(f"🔄 计算完成，开始保存到数据库...")
    
    # 保存到数据库
    saved_count = 0
    updated_count = 0
    
    for i, ohlc in enumerate(ohlc_list):
        ema_high_val = ema_high_33[i]
        ema_low_val = ema_low_33[i]
        
        # 跳过EMA还未稳定的数据点
        if ema_high_val is None or ema_low_val is None:
            continue
            
        # 查找或创建指标记录
        indicator, created = Indicator.objects.get_or_create(
            symbol=symbol,
            interval=interval,
            unix=ohlc.unix,
            defaults={
                'timestamp': ohlc.date,
                'volume': ohlc.volume,
                'ema_high_33': Decimal(str(ema_high_val)),
                'ema_low_33': Decimal(str(ema_low_val)),
            }
        )
        
        if created:
            saved_count += 1
        else:
            # 更新现有记录的EMA Channel值
            indicator.ema_high_33 = Decimal(str(ema_high_val))
            indicator.ema_low_33 = Decimal(str(ema_low_val))
            indicator.save()
            updated_count += 1
    
    print(f"✅ EMA Channel指标计算完成:")
    print(f"   📝 新增记录: {saved_count}")
    print(f"   🔄 更新记录: {updated_count}")
    
    # 显示最新的几个计算结果
    recent_indicators = Indicator.objects.filter(
        symbol=symbol,
        interval=interval,
        ema_high_33__isnull=False,
        ema_low_33__isnull=False
    ).order_by('-timestamp')[:5]
    
    print(f"\n📊 最新的EMA Channel值:")
    for ind in recent_indicators:
        print(f"   {ind.timestamp.strftime('%Y-%m-%d')} | "
              f"上轨: {ind.ema_high_33:.2f} | "
              f"下轨: {ind.ema_low_33:.2f}")

def main():
    """主函数"""
    symbols = ['BTC/USD', 'ETH/USD']  # 可以扩展更多符号
    interval = 86400  # 1天
    
    for symbol in symbols:
        try:
            calculate_ema_channel_for_symbol(symbol, interval)
            print()
        except Exception as e:
            print(f"❌ 计算 {symbol} 时出错: {e}")
            continue

if __name__ == "__main__":
    main()
