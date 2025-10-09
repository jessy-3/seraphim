# 量化交易策略与市场状态识别

## 目录
- [交易策略概述](#交易策略概述)
- [六大交易策略](#六大交易策略)
- [市场状态识别方法](#市场状态识别方法)
- [推荐组合方案](#推荐组合方案)
- [实施路线图](#实施路线图)

---

## 交易策略概述

### 当前可用指标
系统已实现以下技术指标：
- **EMA Channel**: 上轨 (EMA High 33) + 下轨 (EMA Low 33)
- **RSI (14)**: Relative Strength Index，相对强弱指标
- **MACD**: Moving Average Convergence Divergence，指数平滑移动平均线
- **SMA (20)**: Simple Moving Average，简单移动平均
- **EMA (12, 26)**: Exponential Moving Average，指数移动平均
- **Volume**: 成交量
- **OHLC**: Open-High-Low-Close，开高低收

### 核心挑战
**如何同时处理两种市场环境：**
1. **趋势市场 (Trending Market)**: 需要趋势跟随策略
2. **震荡市场 (Ranging Market)**: 需要均值回归策略

---

## 六大交易策略

### 策略 1: EMA Channel 突破策略 (Trend Following)

#### 基本逻辑
```
买入信号 (Long Entry):
  价格突破 EMA High 33 (向上突破上轨)
  → 强势确认，追涨

卖出信号 (Short Entry / Exit):
  价格跌破 EMA Low 33 (向下突破下轨)
  → 弱势确认，离场

持有 (Hold):
  价格在轨道内震荡
  → 观望，容忍磨损
```

#### 适用场景
- **大周期趋势市场** (如 BTC 从 $20k → $100k)
- 波动剧烈的加密货币市场
- 长线持仓

#### 改进方向
1. **突破确认机制**: 
   - 突破后收盘价仍在轨道外
   - 突破幅度 > 0.5%
   
2. **止损设置**:
   - 买入后设止损于下轨
   - 卖出后设止盈于上轨

3. **时间过滤**:
   - 突破后持续 2-3 根 K 线才有效

#### 优势与劣势
**优势**:
- 能抓住大波段行情
- 避免在大趋势中踏空

**劣势**:
- 震荡市会有频繁的假突破（磨损）
- 需要忍受回撤

---

### 策略 2: RSI + EMA Channel 组合 (Reversal Confirmation)

#### 基本逻辑
```
买入信号:
  条件 1: 价格 <= EMA Low 33 (下轨支撑)
  条件 2: RSI < 30 (超卖确认)
  → 双重确认，提高准确率

卖出信号:
  条件 1: 价格 >= EMA High 33 (上轨压力)
  条件 2: RSI > 70 (超买确认)
  → 双重确认
```

#### 参数说明
- **RSI 超卖阈值**: 20-30 (激进 20, 保守 30)
- **RSI 超买阈值**: 70-80 (保守 70, 激进 80)
- **EMA 周期**: 33 (可优化)

#### 适用场景
- 震荡市场
- 区间交易
- 抄底摸顶

#### 优势与劣势
**优势**:
- RSI 过滤假突破
- 提高信号可靠性
- 更保守，适合风险厌恶型

**劣势**:
- 可能错过趋势初期（RSI 不够极端）
- 在强趋势中 RSI 可能长期超买/超卖

---

### 策略 3: MACD 趋势 + EMA Channel 突破 (Trend + Momentum)

#### 基本逻辑
```
买入信号:
  条件 1: 价格突破 EMA Low 33 (从下往上)
  条件 2: MACD > 0 OR MACD 金叉 (上升趋势)
  → 顺势而为，避免逆势抄底

卖出信号:
  条件 1: 价格跌破 EMA High 33 (从上往下)
  条件 2: MACD < 0 OR MACD 死叉 (下降趋势)
  → 顺势离场
```

#### MACD 信号定义
- **金叉 (Golden Cross)**: MACD 线上穿 Signal 线
- **死叉 (Death Cross)**: MACD 线下穿 Signal 线
- **零轴**: MACD > 0 表示短期 EMA > 长期 EMA

#### 适用场景
- 明确的趋势市场
- 避免"接飞刀"（下跌途中抄底）

#### 优势与劣势
**优势**:
- 趋势确认，减少逆势交易
- 降低震荡市假信号

**劣势**:
- MACD 滞后性，可能错过最佳入场点
- 震荡市会产生频繁的金叉死叉

---

### 策略 4: EMA 金叉死叉 + 轨道位置 (Classic Crossover)

#### 基本逻辑
```
买入信号:
  条件 1: EMA(12) 上穿 EMA(26) (金叉)
  条件 2: 价格在轨道下半部 (接近 EMA Low 33)
  → 低位启动，风险回报比高

卖出信号:
  条件 1: EMA(12) 下穿 EMA(26) (死叉)
  条件 2: 价格在轨道上半部 (接近 EMA High 33)
  → 高位离场，锁定利润
```

#### 轨道位置计算
```python
channel_position = (price - ema_low_33) / (ema_high_33 - ema_low_33)
# 0.0 = 下轨, 0.5 = 中轨, 1.0 = 上轨

下半部: channel_position < 0.4
上半部: channel_position > 0.6
```

#### 适用场景
- 中期波段交易
- 趋势跟随

#### 优势与劣势
**优势**:
- 经典信号，容易理解和执行
- 轨道位置判断提高风险收益比

**劣势**:
- 金叉死叉滞后
- 震荡市频繁交叉

---

### 策略 5: 成交量确认突破 (Volume Confirmation)

#### 基本逻辑
```
买入信号:
  条件 1: 价格突破 EMA Low 33 (向上)
  条件 2: 成交量 > 平均成交量 * 1.5
  → 真突破，有资金推动

卖出信号:
  条件 1: 价格突破 EMA High 33 (向上但放量)
  条件 2: 成交量 > 平均成交量 * 1.5
  → 放量滞涨，警惕顶部
```

#### 成交量分析
```python
avg_volume = mean(volume[-20:])  # 20 根 K 线平均成交量

放量标准:
  - 1.5x: 温和放量
  - 2.0x: 明显放量
  - 3.0x: 极度放量（警惕反转）

缩量标准:
  - < 0.5x: 极度缩量（观望）
```

#### 适用场景
- 关键支撑/阻力位突破确认
- 过滤假突破

#### 优势与劣势
**优势**:
- 成交量是"真金白银"，不易作假
- 有效过滤无量假突破
- 识别市场参与度

**劣势**:
- 加密货币市场成交量可能被操纵
- 盘整后的放量突破有时是陷阱

---

### 策略 6: 多时间框架确认 (Multi-Timeframe Analysis)

#### 基本逻辑
```
三层确认机制:

第一层 - 大周期趋势 (1D / 1W):
  价格 > 1D EMA High 33 → 大趋势向上
  价格 < 1D EMA Low 33  → 大趋势向下
  价格在轨道内        → 震荡/观望

第二层 - 中周期时机 (4H):
  大趋势向上 + 4H 回调到下轨 → 买入时机
  大趋势向下 + 4H 反弹到上轨 → 卖出时机

第三层 - 小周期入场 (1H):
  等待 1H RSI 反转信号
  或 1H K 线形态确认（锤子线、十字星等）
```

#### 示例：BTC/USD 买入流程
```
1. 检查 1W 图表: 价格在 EMA High 33 之上
   → 确认长期上升趋势

2. 检查 1D 图表: 价格回调接近 1D EMA Low 33
   → 找到潜在支撑位

3. 检查 4H 图表: RSI 跌至 30 以下
   → 确认短期超卖

4. 检查 1H 图表: 出现反转锤子线 + 成交量放大
   → 精确入场点

5. 执行买入
```

#### 适用场景
- 所有市场环境
- 提高胜率的通用方法

#### 优势与劣势
**优势**:
- 大幅提高胜率
- 减少假信号
- 清晰的风险管理层次

**劣势**:
- 分析复杂，需要经验
- 可能错过快速突破行情
- 对初学者要求高

---

## 市场状态识别方法

### 核心问题
**如何判断当前是趋势市场还是震荡市场？**
量化交易中的经典问题：市场状态识别（Market Regime Detection）
🎯 核心矛盾总结
大波段市场 (Trending Market):
  策略：趋势跟随
  → 突破上轨买入（追涨）
  → 跌破下轨卖出（止损）
  → 容忍通道内磨损，抓住大波段

小震荡市场 (Ranging Market):
  策略：均值回归  
  → 接近下轨买入（抄底）
  → 接近上轨卖出（高抛）
  → 赚取震荡差价，避免追高杀跌
  
问题：如何判断当前处于哪种市场状态？

这决定了使用"趋势跟随"还是"均值回归"策略。

---

### 方法 1: ADX (Average Directional Index) ⭐⭐⭐⭐⭐

#### 指标说明
ADX 是专门用来衡量**趋势强度**的指标（不判断方向，只判断强弱）。

#### 计算逻辑
```
1. 计算 +DI (Positive Directional Indicator, 上升动向指标)
2. 计算 -DI (Negative Directional Indicator, 下降动向指标)
3. 计算 DX = |+DI - -DI| / (+DI + -DI) * 100
4. ADX = DX 的 14 期平滑移动平均
```

#### 判断标准
```
ADX < 20:     无趋势/弱趋势 → 震荡市
ADX 20-25:    开始形成趋势 → 观察
ADX 25-40:    强趋势 → 趋势跟随策略
ADX > 40:     极强趋势 → 警惕趋势衰竭
ADX 回落:     趋势减弱 → 准备离场
```

#### 策略应用
```python
if adx < 25:
    # 震荡市：均值回归
    if price < ema_low_33:
        signal = 'BUY'  # 抄底
    elif price > ema_high_33:
        signal = 'SELL'  # 高抛
        
elif adx >= 25:
    # 趋势市：趋势跟随
    if price > ema_high_33 and +DI > -DI:
        signal = 'BUY'  # 追涨
    elif price < ema_low_33 and -DI > +DI:
        signal = 'SELL'  # 止损
```

#### 优势与劣势
**优势**:
- 专业的趋势强度指标
- 被广泛验证和使用
- 结合 +DI/-DI 可判断趋势方向

**劣势**:
- 计算相对复杂
- 需要新增数据库字段
- 滞后性（基于历史数据）

---

### 方法 2: 价格在轨道内的时间比例 ⭐⭐⭐⭐

#### 核心思想
利用现有的 EMA Channel，统计价格停留在轨道内的时间。

#### 计算方法
```python
def calculate_in_channel_ratio(symbol, interval, lookback=20):
    """
    计算过去 N 根 K 线中，价格在轨道内的比例
    """
    prices = get_recent_ohlc(symbol, interval, lookback)
    indicators = get_recent_indicators(symbol, interval, lookback)
    
    in_channel_count = 0
    for price, ind in zip(prices, indicators):
        if ind.ema_low_33 < price.close < ind.ema_high_33:
            in_channel_count += 1
    
    ratio = in_channel_count / lookback
    return ratio
```

#### 判断标准
```
比例 > 75%:  强震荡市 → 均值回归策略
比例 60-75%: 温和震荡 → 谨慎操作
比例 40-60%: 过渡期 → 观望
比例 < 40%:  趋势市 → 趋势跟随策略
```

#### 策略应用
```python
in_channel_ratio = calculate_in_channel_ratio('BTC/USD', '1D', 20)

if in_channel_ratio > 0.7:
    # 震荡市
    strategy = 'mean_reversion'
    print("震荡市：低买高卖")
    
elif in_channel_ratio < 0.4:
    # 趋势市
    strategy = 'trend_following'
    print("趋势市：突破跟随")
    
else:
    # 不确定
    strategy = 'wait'
    print("市场不明朗：观望")
```

#### 优势与劣势
**优势**:
- **不需要新指标**，利用现有 EMA Channel
- 直观易懂
- 计算简单，性能好

**劣势**:
- lookback 参数需要优化
- 对市场转折反应较慢

---

### 方法 3: 轨道宽度变化 (Channel Width Volatility) ⭐⭐⭐⭐

#### 核心思想
轨道宽度反映市场波动率，类似 Bollinger Bands 的"挤压"理论。

#### 计算方法
```python
def calculate_channel_width(indicator):
    """
    计算 EMA Channel 宽度（标准化）
    """
    width = (indicator.ema_high_33 - indicator.ema_low_33)
    width_percent = width / indicator.ema_low_33 * 100
    return width_percent

def channel_width_trend(symbol, interval, lookback=20):
    """
    判断轨道是在扩张还是收缩
    """
    indicators = get_recent_indicators(symbol, interval, lookback)
    widths = [calculate_channel_width(ind) for ind in indicators]
    
    recent_avg = mean(widths[-5:])   # 最近 5 根
    earlier_avg = mean(widths[-20:-5])  # 之前 15 根
    
    change = (recent_avg - earlier_avg) / earlier_avg * 100
    return change, widths[-1]
```

#### 判断标准
```
轨道变窄 (宽度 < 历史平均 * 0.8):
  → 波动率收敛
  → 震荡市，等待突破
  → "暴风雨前的宁静"

轨道变宽 (宽度 > 历史平均 * 1.2):
  → 波动率扩张
  → 趋势可能形成或加速
  → 高度关注方向

轨道稳定 (接近历史平均):
  → 正常波动
```

#### 策略应用
```python
width_change, current_width = channel_width_trend('BTC/USD', '1D')

if width_change < -15:  # 轨道收窄 15%
    print("轨道收窄，等待突破")
    strategy = 'wait_for_breakout'
    
elif width_change > 15:  # 轨道扩张 15%
    print("波动率上升，趋势可能形成")
    if price > ema_high_33:
        strategy = 'trend_following_long'
    elif price < ema_low_33:
        strategy = 'trend_following_short'
```

#### 优势与劣势
**优势**:
- 提前识别市场变化
- 结合突破方向效果更好
- 符合"挤压后突破"的经典理论

**劣势**:
- 不能单独使用，需结合价格位置
- 需要定义"历史平均"的周期

---

### 方法 4: 波峰波谷计数 (Peak & Trough Analysis) ⭐⭐⭐

#### 核心思想
通过识别局部高点和低点的模式，判断市场结构。

#### 定义
```python
def identify_peaks_troughs(prices, window=5):
    """
    识别波峰和波谷
    window: 左右窗口大小
    """
    peaks = []
    troughs = []
    
    for i in range(window, len(prices) - window):
        # 波峰：左右都低于中心
        if all(prices[i] > prices[i-j] for j in range(1, window+1)) and \
           all(prices[i] > prices[i+j] for j in range(1, window+1)):
            peaks.append((i, prices[i]))
        
        # 波谷：左右都高于中心
        if all(prices[i] < prices[i-j] for j in range(1, window+1)) and \
           all(prices[i] < prices[i+j] for j in range(1, window+1)):
            troughs.append((i, prices[i]))
    
    return peaks, troughs
```

#### 判断标准
```
震荡市特征:
  - 波峰高度相近（横盘）
  - 波谷高度相近
  - 波峰/波谷交替密集
  - 形成"矩形"或"三角形"整理

上升趋势特征:
  - 连续更高的波峰 (Higher Highs, HH)
  - 连续更高的波谷 (Higher Lows, HL)
  - 波峰间隔拉长

下降趋势特征:
  - 连续更低的波峰 (Lower Highs, LH)
  - 连续更低的波谷 (Lower Lows, LL)
  - 波谷间隔拉长
```

#### 艾略特波浪理论 (Elliott Wave Theory)
```
推动浪 (Impulse Wave):
  5 波结构：1-2-3-4-5
  → 第 3 波通常最强
  → 第 5 波可能衰竭

调整浪 (Corrective Wave):
  3 波结构：A-B-C
  → 调整后可能继续原趋势

应用：
  - 如果识别到 5 波推动浪完成 → 警惕反转
  - 如果在 ABC 调整中 → 震荡市，等待方向
```

#### 策略应用
```python
peaks, troughs = identify_peaks_troughs(prices)

# 判断趋势
if len(peaks) >= 2:
    if peaks[-1][1] > peaks[-2][1]:  # 更高的波峰
        if len(troughs) >= 2 and troughs[-1][1] > troughs[-2][1]:
            print("上升趋势：HH + HL")
            strategy = 'trend_following_long'

# 判断震荡
peak_heights = [p[1] for p in peaks[-3:]]
if max(peak_heights) - min(peak_heights) < mean(peak_heights) * 0.05:
    print("横盘震荡：波峰高度相近")
    strategy = 'mean_reversion'
```

#### 优势与劣势
**优势**:
- 经典技术分析方法
- 符合交易者思维习惯
- 可结合形态学（头肩顶、双底等）

**劣势**:
- 主观性较强（如何定义"局部"？）
- 计算复杂
- 实时判断困难（波峰波谷需要后续确认）

---

### 方法 5: 突破成功率统计 (Breakout Success Rate) ⭐⭐⭐⭐

#### 核心思想
记录历史突破后的表现，评估当前市场对突破的"接受度"。

#### 定义突破成功
```python
def evaluate_breakout_success(symbol, interval, lookback=50):
    """
    统计过去 N 次突破的成功率
    """
    data = get_historical_data(symbol, interval, lookback)
    
    breakouts = []
    for i in range(len(data) - 5):  # 留 5 根 K 线验证
        price = data[i]['close']
        ema_high = data[i]['ema_high_33']
        ema_low = data[i]['ema_low_33']
        
        # 突破上轨
        if price > ema_high:
            # 检查后续 5 根 K 线
            future_prices = [data[i+j]['close'] for j in range(1, 6)]
            max_future = max(future_prices)
            
            if max_future > price * 1.02:  # 继续上涨 2%
                breakouts.append({'type': 'up', 'success': True})
            else:
                breakouts.append({'type': 'up', 'success': False})
        
        # 突破下轨（类似逻辑）
        elif price < ema_low:
            future_prices = [data[i+j]['close'] for j in range(1, 6)]
            min_future = min(future_prices)
            
            if min_future < price * 0.98:  # 继续下跌 2%
                breakouts.append({'type': 'down', 'success': True})
            else:
                breakouts.append({'type': 'down', 'success': False})
    
    success_count = sum(1 for b in breakouts if b['success'])
    success_rate = success_count / len(breakouts) if breakouts else 0.5
    
    return success_rate, len(breakouts)
```

#### 判断标准
```
成功率 > 60%:  趋势市环境
  → 突破大概率成功
  → 使用趋势跟随策略

成功率 40-60%: 过渡期/不确定
  → 突破成功率接近随机
  → 观望或小仓位测试

成功率 < 40%:  震荡市环境
  → 突破大概率失败（假突破）
  → 使用均值回归策略（反向操作）
```

#### 策略应用
```python
success_rate, sample_size = evaluate_breakout_success('BTC/USD', '1D', 50)

print(f"过去 {sample_size} 次突破，成功率：{success_rate:.1%}")

if success_rate > 0.6:
    print("高成功率 → 趋势市")
    if current_price > ema_high_33:
        signal = 'BUY'  # 突破跟随
        
elif success_rate < 0.4:
    print("低成功率 → 震荡市")
    if current_price > ema_high_33:
        signal = 'SELL'  # 反向操作（高抛）
```

#### 优势与劣势
**优势**:
- 自适应市场环境
- 基于实际历史表现
- 可量化评估

**劣势**:
- 需要足够的样本量
- 滞后性（基于历史）
- 需要定义"成功"的标准（2%? 5%?）

---

### 方法 6: 多周期确认 (Multi-Timeframe Regime Detection) ⭐⭐⭐⭐⭐

#### 核心思想
**大周期判断趋势，小周期寻找入场**，这是最稳健的方法。

#### 三层分析框架
```
第一层 - 宏观趋势 (1W / 1M):
  目的：确定长期方向
  
  价格 > 1W EMA High 33:
    → 长期牛市，主要做多
  
  价格 < 1W EMA Low 33:
    → 长期熊市，主要做空或空仓
  
  价格在轨道内:
    → 长期震荡，灵活操作

第二层 - 中期趋势 (1D):
  目的：确定当前市场状态
  
  in_channel_ratio_1d = calculate_in_channel_ratio('BTC/USD', '1D', 20)
  
  if in_channel_ratio_1d > 0.7:
    → 日线震荡市
  else:
    → 日线趋势市

第三层 - 短期时机 (4H / 1H):
  目的：寻找精确入场点
  
  结合 RSI、成交量等指标
  等待回调或突破确认
```

#### 决策矩阵
```
┌─────────────┬──────────────────┬──────────────────┐
│  1W 趋势    │   1D 状态        │   操作策略       │
├─────────────┼──────────────────┼──────────────────┤
│  向上       │   趋势           │   激进做多       │
│  向上       │   震荡           │   回调买入       │
│  向上       │   向下           │   观望/小仓位    │
├─────────────┼──────────────────┼──────────────────┤
│  震荡       │   向上           │   波段做多       │
│  震荡       │   震荡           │   高抛低吸       │
│  震荡       │   向下           │   波段做空       │
├─────────────┼──────────────────┼──────────────────┤
│  向下       │   向上           │   反弹出货       │
│  向下       │   震荡           │   空仓观望       │
│  向下       │   向下           │   趋势做空       │
└─────────────┴──────────────────┴──────────────────┘
```

#### 完整示例
```python
def multi_timeframe_analysis(symbol):
    """
    多周期分析
    """
    # 1. 周线趋势
    week_data = get_latest_data(symbol, '1W')
    if week_data.close > week_data.ema_high_33:
        week_trend = 'UP'
    elif week_data.close < week_data.ema_low_33:
        week_trend = 'DOWN'
    else:
        week_trend = 'RANGING'
    
    # 2. 日线状态
    day_ratio = calculate_in_channel_ratio(symbol, '1D', 20)
    if day_ratio > 0.7:
        day_regime = 'RANGING'
    else:
        day_data = get_latest_data(symbol, '1D')
        if day_data.close > day_data.ema_high_33:
            day_regime = 'TRENDING_UP'
        else:
            day_regime = 'TRENDING_DOWN'
    
    # 3. 4小时入场时机
    hour4_data = get_latest_data(symbol, '4H')
    hour4_rsi = hour4_data.rsi
    
    # 决策矩阵
    if week_trend == 'UP' and day_regime == 'RANGING':
        if hour4_data.close < hour4_data.ema_low_33 and hour4_rsi < 30:
            return 'BUY', 'week_up_day_ranging_hour_oversold'
    
    elif week_trend == 'UP' and day_regime == 'TRENDING_UP':
        if hour4_data.close > hour4_data.ema_high_33:
            return 'BUY', 'strong_uptrend_breakout'
    
    # ... 其他组合
    
    return 'HOLD', 'no_clear_signal'
```

#### 优势与劣势
**优势**:
- **最稳健的方法**
- 大幅降低假信号
- 清晰的风险分层
- 适合各种交易周期

**劣势**:
- 分析复杂，需要经验
- 需要监控多个周期
- 可能错过快速行情
- 对初学者门槛高

---

## 推荐组合方案

### 设计原则
基于你的需求（BTC 大周期 + 容忍磨损 + 识别震荡），推荐以下组合：

1. **简单但有效**
2. **利用现有指标**，最小化新开发
3. **可快速验证**
4. **可迭代优化**

---

### 阶段 1: 快速实现 MVP (1-2 周)

#### 核心组合
**方法 2 (轨道内时间) + 方法 6 (多周期确认)**

#### 实现代码框架
```python
# 文件: api/services/signal_generator.py

from api.models import OhlcPrice, Indicator
from datetime import datetime, timedelta

class SignalGenerator:
    """
    交易信号生成器
    """
    
    def __init__(self, symbol='BTC/USD'):
        self.symbol = symbol
    
    def calculate_in_channel_ratio(self, interval='1D', lookback=20):
        """
        计算价格在轨道内的时间比例
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback * 2)  # 预留空间
        
        prices = OhlcPrice.objects.filter(
            symbol=self.symbol,
            interval=self._interval_to_seconds(interval),
            date__gte=start_date
        ).order_by('-date')[:lookback]
        
        indicators = Indicator.objects.filter(
            symbol=self.symbol,
            interval=self._interval_to_seconds(interval),
            timestamp__gte=start_date
        ).order_by('-timestamp')[:lookback]
        
        if len(prices) < lookback or len(indicators) < lookback:
            return 0.5  # 数据不足，返回中性值
        
        in_channel_count = 0
        for price, ind in zip(prices, indicators):
            if ind.ema_low_33 and ind.ema_high_33:
                if ind.ema_low_33 < price.close < ind.ema_high_33:
                    in_channel_count += 1
        
        ratio = in_channel_count / lookback
        return ratio
    
    def get_trend_direction(self, interval='1D'):
        """
        判断趋势方向
        """
        latest = self._get_latest_data(interval)
        
        if not latest or not latest['indicator']:
            return 'UNKNOWN'
        
        price = latest['price'].close
        ema_high = latest['indicator'].ema_high_33
        ema_low = latest['indicator'].ema_low_33
        
        if price > ema_high:
            return 'UPTREND'
        elif price < ema_low:
            return 'DOWNTREND'
        else:
            return 'RANGING'
    
    def generate_signal(self):
        """
        生成交易信号
        """
        # 1. 判断大周期趋势 (1D)
        trend_1d = self.get_trend_direction('1D')
        is_ranging = self.calculate_in_channel_ratio('1D', 20) > 0.7
        
        # 2. 获取当前数据 (4H)
        current_4h = self._get_latest_data('4H')
        if not current_4h:
            return {
                'signal': 'HOLD',
                'reason': 'insufficient_data',
                'confidence': 0
            }
        
        price = current_4h['price'].close
        ema_high = current_4h['indicator'].ema_high_33
        ema_low = current_4h['indicator'].ema_low_33
        rsi = current_4h['indicator'].rsi
        
        # 3. 决策逻辑
        if is_ranging:
            # 震荡市：均值回归策略
            if price < ema_low * 1.01 and rsi < 35:
                return {
                    'signal': 'BUY',
                    'strategy': 'mean_reversion',
                    'reason': 'oversold_in_ranging_market',
                    'confidence': 0.7,
                    'entry_price': price,
                    'stop_loss': ema_low * 0.98,
                    'take_profit': ema_high
                }
            elif price > ema_high * 0.99 and rsi > 65:
                return {
                    'signal': 'SELL',
                    'strategy': 'mean_reversion',
                    'reason': 'overbought_in_ranging_market',
                    'confidence': 0.7,
                    'entry_price': price,
                    'stop_loss': ema_high * 1.02,
                    'take_profit': ema_low
                }
        else:
            # 趋势市：突破跟随策略
            if trend_1d == 'UPTREND':
                if price > ema_high:
                    return {
                        'signal': 'BUY',
                        'strategy': 'trend_following',
                        'reason': 'breakout_in_uptrend',
                        'confidence': 0.8,
                        'entry_price': price,
                        'stop_loss': ema_low,
                        'take_profit': None  # 趋势跟随，不设固定止盈
                    }
            elif trend_1d == 'DOWNTREND':
                if price < ema_low:
                    return {
                        'signal': 'SELL',
                        'strategy': 'trend_following',
                        'reason': 'breakdown_in_downtrend',
                        'confidence': 0.8,
                        'entry_price': price,
                        'stop_loss': ema_high,
                        'take_profit': None
                    }
        
        return {
            'signal': 'HOLD',
            'reason': 'no_clear_signal',
            'confidence': 0
        }
    
    def _get_latest_data(self, interval):
        """
        获取最新数据
        """
        interval_seconds = self._interval_to_seconds(interval)
        
        price = OhlcPrice.objects.filter(
            symbol=self.symbol,
            interval=interval_seconds
        ).order_by('-date').first()
        
        indicator = Indicator.objects.filter(
            symbol=self.symbol,
            interval=interval_seconds
        ).order_by('-timestamp').first()
        
        if not price or not indicator:
            return None
        
        return {
            'price': price,
            'indicator': indicator
        }
    
    def _interval_to_seconds(self, interval):
        """
        时间周期转换为秒
        """
        mapping = {
            '1H': 3600,
            '4H': 14400,
            '1D': 86400,
            '1W': 604800
        }
        return mapping.get(interval, 86400)


# 使用示例
if __name__ == "__main__":
    import os, django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')
    django.setup()
    
    generator = SignalGenerator('BTC/USD')
    signal = generator.generate_signal()
    
    print(f"信号: {signal['signal']}")
    print(f"策略: {signal.get('strategy', 'N/A')}")
    print(f"原因: {signal['reason']}")
    print(f"置信度: {signal['confidence']:.0%}")
```

#### 数据库扩展
```python
# 文件: api/models.py (新增)

class TradingSignal(models.Model):
    """
    交易信号记录
    """
    symbol = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)
    interval = models.IntegerField()  # 信号生成周期
    
    signal_type = models.CharField(max_length=10)  # BUY, SELL, HOLD
    strategy = models.CharField(max_length=50)  # trend_following, mean_reversion
    reason = models.CharField(max_length=200)
    confidence = models.DecimalField(max_digits=3, decimal_places=2)  # 0-1
    
    entry_price = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    stop_loss = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    take_profit = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    
    # 市场状态记录
    market_regime = models.CharField(max_length=20)  # TRENDING, RANGING, UNKNOWN
    in_channel_ratio = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    
    class Meta:
        db_table = 'qt_trading_signal'
        indexes = [
            models.Index(fields=['symbol', '-timestamp']),
        ]
```

---

### 阶段 2: 增加复杂度 (2-3 周)

#### 新增功能
1. **ADX 计算** (方法 1)
   - 新增 Indicator 字段：`adx`, `plus_di`, `minus_di`
   - 提高趋势判断精度

2. **轨道宽度分析** (方法 3)
   - 识别"挤压后突破"模式

3. **成交量确认** (策略 5)
   - 过滤假突破

4. **突破成功率统计** (方法 5)
   - 自适应市场环境

#### 增强版信号生成器
```python
class EnhancedSignalGenerator(SignalGenerator):
    """
    增强版信号生成器
    """
    
    def calculate_adx(self, interval='1D', period=14):
        """
        计算 ADX (简化版本，完整版需要更复杂的逻辑)
        """
        # TODO: 实现 ADX 计算
        pass
    
    def evaluate_volume_confirmation(self, interval='4H'):
        """
        成交量确认
        """
        data = self._get_historical_data(interval, lookback=20)
        
        avg_volume = mean([d['price'].volume for d in data[:-1]])
        current_volume = data[-1]['price'].volume
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        return {
            'is_high_volume': volume_ratio > 1.5,
            'volume_ratio': volume_ratio
        }
    
    def generate_enhanced_signal(self):
        """
        增强版信号生成
        """
        basic_signal = self.generate_signal()
        
        # 成交量确认
        volume_info = self.evaluate_volume_confirmation('4H')
        
        # 调整置信度
        if basic_signal['signal'] in ['BUY', 'SELL']:
            if volume_info['is_high_volume']:
                basic_signal['confidence'] *= 1.2  # 提升 20%
                basic_signal['reason'] += '_with_volume_confirmation'
            else:
                basic_signal['confidence'] *= 0.8  # 降低 20%
        
        basic_signal['confidence'] = min(basic_signal['confidence'], 1.0)
        
        return basic_signal
```

---

### 阶段 3: 回测与优化 (持续)

#### 回测框架
```python
# 文件: scripts/backtest.py

class Backtester:
    """
    策略回测引擎
    """
    
    def __init__(self, strategy, symbol, start_date, end_date):
        self.strategy = strategy
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        
        self.trades = []
        self.equity_curve = []
        self.initial_capital = 10000  # 初始资金
        self.current_capital = self.initial_capital
        self.position = None  # 当前持仓
    
    def run(self):
        """
        运行回测
        """
        # 获取历史数据
        data = self._load_historical_data()
        
        for i in range(len(data)):
            timestamp = data[i]['timestamp']
            price = data[i]['close']
            
            # 生成信号
            signal = self.strategy.generate_signal_at_time(timestamp)
            
            # 执行交易
            if signal['signal'] == 'BUY' and self.position is None:
                self._open_position('LONG', price, signal)
            elif signal['signal'] == 'SELL' and self.position is not None:
                self._close_position(price)
            
            # 更新权益曲线
            equity = self._calculate_equity(price)
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': equity
            })
        
        # 关闭剩余持仓
        if self.position:
            self._close_position(data[-1]['close'])
        
        return self._calculate_metrics()
    
    def _calculate_metrics(self):
        """
        计算回测指标
        """
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        avg_win = mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = mean([abs(t['pnl']) for t in losing_trades]) if losing_trades else 0
        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        
        # 最大回撤
        peak = self.initial_capital
        max_drawdown = 0
        for point in self.equity_curve:
            if point['equity'] > peak:
                peak = point['equity']
            drawdown = (peak - point['equity']) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'final_capital': self.current_capital,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
    
    # ... 其他辅助方法


# 使用示例
if __name__ == "__main__":
    strategy = SignalGenerator('BTC/USD')
    
    backtester = Backtester(
        strategy=strategy,
        symbol='BTC/USD',
        start_date='2023-01-01',
        end_date='2024-12-31'
    )
    
    results = backtester.run()
    
    print(f"总交易次数: {results['total_trades']}")
    print(f"胜率: {results['win_rate']:.1%}")
    print(f"盈亏比: {results['profit_factor']:.2f}")
    print(f"总收益率: {results['total_return']:.1%}")
    print(f"最大回撤: {results['max_drawdown']:.1%}")
```

---

## 实施路线图

### Week 1-2: MVP 开发
- [ ] 创建 `SignalGenerator` 类
- [ ] 实现轨道内时间比例计算
- [ ] 实现多周期趋势判断
- [ ] 创建 `TradingSignal` 数据模型
- [ ] 在 Dashboard 显示实时信号

### Week 3-4: 功能增强
- [ ] 添加 ADX 计算
- [ ] 实现轨道宽度分析
- [ ] 集成成交量确认
- [ ] 优化信号置信度算法

### Week 5-6: 回测系统
- [ ] 开发回测引擎
- [ ] 加载历史数据
- [ ] 计算回测指标
- [ ] 可视化权益曲线

### Week 7-8: 优化与部署
- [ ] 参数优化（EMA 周期、RSI 阈值等）
- [ ] A/B 测试不同策略
- [ ] 添加信号推送（邮件/Telegram）
- [ ] 性能监控与日志

---

## 参考资料

### 书籍
1. **《Technical Analysis of the Financial Markets》** - John Murphy
   - 技术分析经典，涵盖所有基础指标

2. **《Evidence-Based Technical Analysis》** - David Aronson
   - 量化视角看技术分析

3. **《Algorithmic Trading》** - Ernest Chan
   - 算法交易实战

### 在线资源
1. **TradingView**: 图表分析和策略测试
2. **QuantConnect**: 开源量化回测平台
3. **Investopedia**: 技术指标详解

### 论文
1. **"Trend Following Strategies in Commodity Futures"** - Moskowitz et al. (2012)
2. **"Market Microstructure and Algorithmic Trading"** - Hendershott & Riordan (2013)

---

## 总结

本文档涵盖了：
1. **6 种交易策略**：从简单到复杂，从单一指标到多指标组合
2. **6 种市场状态识别方法**：解决"趋势 vs 震荡"的核心问题
3. **完整实施方案**：从 MVP 到优化的渐进式路线图
4. **代码框架**：可直接使用的 Python 实现

**核心原则**：
- 从简单开始，逐步优化
- 回测验证，数据驱动
- 组合使用，相互确认
- 风险管理，严格执行

祝交易顺利！📈

