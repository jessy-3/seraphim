# 🏗️ Seraphim 技术架构详细设计

## 🔌 外部API集成方案

### Kraken API 集成
```python
# API配置
KRAKEN_CONFIG = {
    'base_url': 'https://api.kraken.com',
    'websocket_url': 'wss://ws.kraken.com',
    'rate_limit': {
        'public': 1,      # 1 req/sec
        'private': 1,     # 1 req/sec
        'orders': 0.33,   # 1 req/3sec
    }
}

# 实现示例
class KrakenDataProvider:
    def get_realtime_data(self, pairs):
        """WebSocket实时数据"""
        ws_url = "wss://ws.kraken.com"
        subscription = {
            "event": "subscribe",
            "pair": pairs,
            "subscription": {
                "name": "ticker"
            }
        }
        
    def get_historical_data(self, pair, interval, since):
        """REST API历史数据"""
        endpoint = f"/0/public/OHLC"
        params = {
            'pair': pair,
            'interval': interval,
            'since': since
        }
```

### IBKR API 集成
```python
# Interactive Brokers TWS API
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

class IBKRDataProvider(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.data_queue = queue.Queue()
        
    def get_stock_data(self, symbol):
        """获取股票实时数据"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        
        self.reqMktData(reqId=1, contract=contract, 
                       genericTickList="", snapshot=False, 
                       regulatorySnapshot=False, mktDataOptions=[])
```

---

## 📊 数据流架构

### 数据处理管道
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  External   │───→│   Data      │───→│   Data      │
│  Data APIs  │    │ Collector   │    │ Processor   │
└─────────────┘    └─────────────┘    └─────────────┘
                           │                    │
                           ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Redis     │◄───┤   Message   │───→│ PostgreSQL  │
│   Cache     │    │    Queue    │    │  Database   │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │  Strategy   │
                   │   Engine    │
                   └─────────────┘
```

### Celery任务设计
```python
# tasks.py
@shared_task
def collect_market_data(exchange, symbol):
    """市场数据采集任务"""
    provider = get_data_provider(exchange)
    data = provider.get_latest_data(symbol)
    
    # 存储到Redis
    cache_key = f"market_data:{exchange}:{symbol}"
    cache.set(cache_key, data, timeout=60)
    
    # 存储到数据库
    MarketData.objects.create(**data)
    
    # 触发策略计算
    run_strategies.delay(symbol, data)

@shared_task
def run_strategies(symbol, market_data):
    """运行交易策略"""
    active_strategies = Strategy.objects.filter(
        is_active=True, 
        symbols__contains=[symbol]
    )
    
    for strategy in active_strategies:
        strategy_engine = get_strategy_engine(strategy.name)
        signal = strategy_engine.process(market_data)
        
        if signal:
            execute_trade.delay(signal)

@shared_task
def execute_trade(signal):
    """执行交易信号"""
    # 风险检查
    if not risk_manager.check_signal(signal):
        logger.warning(f"Signal blocked by risk manager: {signal}")
        return
        
    # 执行交易
    exchange_adapter = get_exchange_adapter(signal.exchange)
    order = exchange_adapter.place_order(signal)
    
    # 记录交易
    Trade.objects.create(**order)
```

---

## 🧠 策略引擎架构

### 策略注册机制
```python
# strategy/registry.py
class StrategyRegistry:
    _strategies = {}
    
    @classmethod
    def register(cls, name, strategy_class):
        cls._strategies[name] = strategy_class
        
    @classmethod  
    def get_strategy(cls, name):
        return cls._strategies.get(name)
    
    @classmethod
    def list_strategies(cls):
        return list(cls._strategies.keys())

# 装饰器注册
def register_strategy(name):
    def decorator(strategy_class):
        StrategyRegistry.register(name, strategy_class)
        return strategy_class
    return decorator

# 使用示例
@register_strategy("moving_average_cross")
class MovingAverageCrossStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.short_window = config.get('short_window', 10)
        self.long_window = config.get('long_window', 30)
        
    def generate_signal(self, data):
        # 计算移动平均线
        short_ma = self.calculate_ma(data, self.short_window)
        long_ma = self.calculate_ma(data, self.long_window)
        
        # 生成交易信号
        if short_ma > long_ma and self.last_signal != 'buy':
            return TradingSignal('buy', data.symbol, data.price)
        elif short_ma < long_ma and self.last_signal != 'sell':
            return TradingSignal('sell', data.symbol, data.price)
            
        return None
```

### 技术指标库
```python
# indicators/technical.py
class TechnicalIndicators:
    @staticmethod
    def sma(prices, window):
        """简单移动平均"""
        return prices.rolling(window=window).mean()
        
    @staticmethod
    def ema(prices, window):
        """指数移动平均"""
        return prices.ewm(span=window).mean()
        
    @staticmethod
    def rsi(prices, window=14):
        """相对强弱指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
        
    @staticmethod
    def bollinger_bands(prices, window=20, num_std=2):
        """布林带"""
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)
        return upper, sma, lower
```

---

## 🛡️ 风险管理系统

### 多层风控架构
```python
# risk/manager.py
class RiskManager:
    def __init__(self):
        self.rules = [
            PositionSizeRule(),
            MaxDrawdownRule(),
            ConcentrationRule(),
            VolatilityRule(),
            LiquidityRule(),
        ]
        
    def check_signal(self, signal, portfolio):
        """检查交易信号"""
        for rule in self.rules:
            if not rule.validate(signal, portfolio):
                logger.warning(f"Signal rejected by {rule.__class__.__name__}")
                return False
        return True

class PositionSizeRule:
    def __init__(self, max_position_pct=0.05):
        self.max_position_pct = max_position_pct
        
    def validate(self, signal, portfolio):
        """单笔交易最大仓位限制"""
        position_value = signal.quantity * signal.price
        portfolio_value = portfolio.total_value
        position_pct = position_value / portfolio_value
        
        return position_pct <= self.max_position_pct

class MaxDrawdownRule:
    def __init__(self, max_drawdown=0.10):
        self.max_drawdown = max_drawdown
        
    def validate(self, signal, portfolio):
        """最大回撤限制"""
        current_drawdown = portfolio.calculate_drawdown()
        return current_drawdown < self.max_drawdown
```

### 实时监控系统
```python
# monitoring/alerts.py
class AlertManager:
    def __init__(self):
        self.alert_rules = {
            'high_drawdown': {'threshold': 0.05, 'action': 'email'},
            'connection_lost': {'threshold': 30, 'action': 'sms'},
            'large_loss': {'threshold': 1000, 'action': 'emergency_stop'},
        }
        
    def check_portfolio_health(self, portfolio):
        """检查投资组合健康状况"""
        drawdown = portfolio.calculate_drawdown()
        if drawdown > self.alert_rules['high_drawdown']['threshold']:
            self.send_alert('high_drawdown', f"Drawdown: {drawdown:.2%}")
            
    def send_alert(self, alert_type, message):
        """发送告警"""
        action = self.alert_rules[alert_type]['action']
        
        if action == 'email':
            self.send_email(message)
        elif action == 'sms':
            self.send_sms(message)
        elif action == 'emergency_stop':
            self.emergency_stop()
            self.send_email(f"EMERGENCY STOP: {message}")
```

---

## 🔄 回测系统设计

### 回测引擎
```python
# backtesting/engine.py
class BacktestEngine:
    def __init__(self, start_date, end_date, initial_capital=100000):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.portfolio = Portfolio(initial_capital)
        self.trades = []
        
    def run_backtest(self, strategy, data):
        """运行回测"""
        for timestamp, market_data in data.iterrows():
            # 更新投资组合价值
            self.portfolio.update_positions(market_data)
            
            # 生成交易信号
            signal = strategy.generate_signal(market_data)
            
            if signal:
                # 模拟交易执行
                trade = self.execute_trade(signal, market_data)
                if trade:
                    self.trades.append(trade)
                    
        return self.calculate_performance()
        
    def calculate_performance(self):
        """计算策略绩效"""
        returns = pd.Series([t.pnl for t in self.trades])
        
        metrics = {
            'total_return': self.portfolio.total_value / self.initial_capital - 1,
            'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252),
            'max_drawdown': self.calculate_max_drawdown(),
            'win_rate': len(returns[returns > 0]) / len(returns),
            'profit_factor': returns[returns > 0].sum() / abs(returns[returns < 0].sum()),
        }
        
        return metrics
```

---

## 📈 前端界面设计

### 交易控制面板
```javascript
// trading-panel.js
function tradingPanel() {
    return {
        selectedStrategy: '',
        strategies: [],
        positions: [],
        orders: [],
        
        init() {
            this.loadStrategies();
            this.loadPositions();
            this.loadOrders();
            this.initWebSocket();
        },
        
        startStrategy(strategyId) {
            fetch(`/api/strategies/${strategyId}/start/`, {
                method: 'POST',
            }).then(response => {
                if (response.ok) {
                    this.showNotification('Strategy started successfully');
                }
            });
        },
        
        stopStrategy(strategyId) {
            fetch(`/api/strategies/${strategyId}/stop/`, {
                method: 'POST',
            }).then(response => {
                if (response.ok) {
                    this.showNotification('Strategy stopped');
                }
            });
        },
        
        placeManualOrder() {
            const order = {
                symbol: this.orderForm.symbol,
                side: this.orderForm.side,
                quantity: this.orderForm.quantity,
                price: this.orderForm.price,
            };
            
            fetch('/api/orders/', {
                method: 'POST',
                body: JSON.stringify(order),
                headers: {'Content-Type': 'application/json'}
            }).then(response => {
                if (response.ok) {
                    this.loadOrders();
                    this.showNotification('Order placed');
                }
            });
        }
    }
}
```

### 实时监控仪表板
```html
<!-- dashboard/monitor.html -->
<div x-data="monitoringDashboard()">
    <!-- 系统状态 -->
    <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="bg-white p-4 rounded-lg shadow">
            <h3>System Status</h3>
            <div :class="systemHealth.status == 'healthy' ? 'text-green-500' : 'text-red-500'">
                <span x-text="systemHealth.status"></span>
            </div>
        </div>
        
        <div class="bg-white p-4 rounded-lg shadow">
            <h3>Active Strategies</h3>
            <div class="text-2xl font-bold" x-text="activeStrategies"></div>
        </div>
        
        <div class="bg-white p-4 rounded-lg shadow">
            <h3>Today's P&L</h3>
            <div class="text-2xl font-bold" 
                 :class="todayPnl >= 0 ? 'text-green-500' : 'text-red-500'"
                 x-text="'$' + todayPnl.toFixed(2)"></div>
        </div>
        
        <div class="bg-white p-4 rounded-lg shadow">
            <h3>Total Trades</h3>
            <div class="text-2xl font-bold" x-text="totalTrades"></div>
        </div>
    </div>
    
    <!-- 实时图表 -->
    <div class="grid grid-cols-2 gap-6">
        <div class="bg-white p-6 rounded-lg shadow">
            <canvas id="pnlChart"></canvas>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
            <canvas id="positionsChart"></canvas>
        </div>
    </div>
</div>
```

---

## 🚀 部署配置

### Docker Compose 生产配置
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - web

  web:
    build: ./web
    environment:
      - DJANGO_SETTINGS_MODULE=seraphim.settings.production
      - DATABASE_URL=postgresql://user:pass@postgres:5432/seraphim
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 2

  celery-worker:
    build: ./web
    command: celery -A seraphim worker -l info -Q default,data_collection,trading
    environment:
      - DJANGO_SETTINGS_MODULE=seraphim.settings.production
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 3

  celery-beat:
    build: ./web
    command: celery -A seraphim beat -l info
    environment:
      - DJANGO_SETTINGS_MODULE=seraphim.settings.production
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=seraphim
      - POSTGRES_USER=seraphim_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    sysctls:
      - net.core.somaxconn=511
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### 环境变量配置
```bash
# .env.production
DEBUG=False
SECRET_KEY=your-secret-key-here

# Database
POSTGRES_PASSWORD=secure-password
DATABASE_URL=postgresql://seraphim_user:${POSTGRES_PASSWORD}@postgres:5432/seraphim

# Redis
REDIS_URL=redis://redis:6379/0

# Trading APIs
KRAKEN_API_KEY=your-kraken-api-key
KRAKEN_API_SECRET=your-kraken-api-secret
IBKR_GATEWAY_HOST=127.0.0.1
IBKR_GATEWAY_PORT=7497

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-email-password
```

---

*🔧 这个技术架构为整个交易系统提供了坚实的基础。接下来我们可以开始实施第一个阶段的开发！*
