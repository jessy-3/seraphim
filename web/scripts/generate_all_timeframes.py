#!/usr/bin/env python
"""
生成所有时间周期的OHLC数据和轨道当值指标
- 从1H数据生成4H数据
- 从1D数据生成1W数据  
- 为1H, 4H, 1D, 1W计算轨道当值
"""

import os
import sys
import django
from decimal import Decimal
import pandas as pd
from datetime import datetime, timezone, timedelta

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
    
    series = pd.Series(prices)
    ema = series.ewm(span=period, adjust=False).mean()
    return ema.tolist()

def aggregate_ohlc_data(source_interval, target_interval, limit=1000):
    """
    从小时间周期聚合为大时间周期
    source_interval: 源时间周期(秒)
    target_interval: 目标时间周期(秒)  
    """
    print(f"🔄 从 {source_interval}s 聚合到 {target_interval}s...")
    
    # 获取源数据
    source_data = OhlcPrice.objects.filter(
        symbol='BTC/USD',
        interval=source_interval
    ).order_by('date')[:limit * (target_interval // source_interval)]
    
    if not source_data:
        print(f"❌ 没有找到源数据 ({source_interval}s)")
        return
    
    print(f"📊 找到 {len(source_data)} 条源数据")
    
    # 计算聚合倍数
    ratio = target_interval // source_interval
    aggregated_count = 0
    
    # 按组聚合
    for i in range(0, len(source_data), ratio):
        group = source_data[i:i+ratio]
        if len(group) < ratio:
            continue  # 跳过不完整的组
            
        # 聚合OHLC
        agg_open = group[0].open
        agg_close = group[-1].close
        agg_high = max(item.high for item in group)
        agg_low = min(item.low for item in group)
        agg_volume = sum(item.volume for item in group)
        agg_date = group[0].date
        
        # 检查是否已存在
        existing = OhlcPrice.objects.filter(
            symbol='BTC/USD',
            interval=target_interval,
            date=agg_date
        ).first()
        
        if not existing:
            OhlcPrice.objects.create(
                symbol='BTC/USD',
                interval=target_interval,
                date=agg_date,
                open=agg_open,
                high=agg_high,
                low=agg_low,
                close=agg_close,
                volume=agg_volume,
                market_id=1
            )
            aggregated_count += 1
    
    print(f"✅ 聚合完成: 新增 {aggregated_count} 条记录")

def calculate_ema_channel_for_interval(interval_seconds, symbol='BTC/USD', limit=500):
    """为指定时间周期计算轨道当值"""
    
    interval_desc = {
        3600: '1小时',
        14400: '4小时', 
        86400: '1天',
        604800: '1周'
    }.get(interval_seconds, f'{interval_seconds}秒')
    
    print(f"🧮 计算 {symbol} {interval_desc} 的轨道当值...")
    
    # 获取OHLC数据
    ohlc_data = OhlcPrice.objects.filter(
        symbol=symbol,
        interval=interval_seconds
    ).order_by('-date')[:limit]
    
    if not ohlc_data:
        print(f"❌ 没有找到 {symbol} {interval_desc} 的OHLC数据")
        return
    
    print(f"📊 找到 {len(ohlc_data)} 条OHLC记录")
    
    # 转换为列表并反转顺序 (最旧的在前)
    ohlc_list = list(reversed(ohlc_data))
    
    # 提取High和Low价格
    high_prices = [float(item.high) for item in ohlc_list]
    low_prices = [float(item.low) for item in ohlc_list]
    
    # 计算EMA Channel (33期)
    ema_high_33 = calculate_ema(high_prices, 33)
    ema_low_33 = calculate_ema(low_prices, 33)
    
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
            interval=interval_seconds,
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
    
    print(f"✅ {interval_desc} 轨道当值计算完成:")
    print(f"   📝 新增记录: {saved_count}")
    print(f"   🔄 更新记录: {updated_count}")

def main():
    print("🚀 开始生成所有时间周期数据...\n")
    
    # 1. 从1H数据生成4H数据
    try:
        aggregate_ohlc_data(3600, 14400, limit=2000)  # 生成约500条4H数据
        print()
    except Exception as e:
        print(f"❌ 生成4H数据失败: {e}\n")
    
    # 2. 从1D数据生成1W数据
    try:
        aggregate_ohlc_data(86400, 604800, limit=1400)  # 生成约200条1W数据
        print()
    except Exception as e:
        print(f"❌ 生成1W数据失败: {e}\n")
    
    # 3. 为所有时间周期计算轨道当值
    intervals = [3600, 14400, 86400, 604800]  # 1H, 4H, 1D, 1W
    
    for interval in intervals:
        try:
            calculate_ema_channel_for_interval(interval)
            print()
        except Exception as e:
            interval_desc = {
                3600: '1小时',
                14400: '4小时', 
                86400: '1天',
                604800: '1周'
            }.get(interval, f'{interval}秒')
            print(f"❌ 计算 {interval_desc} 轨道当值失败: {e}\n")
    
    print("🎉 所有时间周期数据生成完成!")

if __name__ == "__main__":
    main()
