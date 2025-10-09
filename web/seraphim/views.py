from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from api.wsclient import ws_client
from api.models import SymbolInfo, OhlcPrice, Indicator, MarketRegime, TradingSignal
from api.providers.kraken_provider import get_kraken_provider
# Delay IBKR import to avoid uvloop conflicts during Django startup
# from api.providers.ibkr_socket_provider import get_ibkr_socket_provider
from api.providers.ibkr_simple_provider import get_ibkr_simple_provider
import redis
import json
import logging

logger = logging.getLogger(__name__)


class DashboardView(View):
    """Main dashboard view for Seraphim Trading System"""
    
    def get(self, request):
        # Start market websocket client for real-time data
        ws_client('start')
        
        # Get basic market data with custom ordering
        symbols = SymbolInfo.objects.all()
        
        # Custom ordering: crypto first (market_id=1), then stocks (market_id=2)
        # Within crypto: BTC/USD, ETH/USD, ETH/BTC, then others alphabetically
        def symbol_sort_key(symbol):
            if symbol.market_id == 1:  # Crypto
                if symbol.name == 'BTC/USD':
                    return (0, 0)
                elif symbol.name == 'ETH/USD':
                    return (0, 1)  
                elif symbol.name == 'ETH/BTC':
                    return (0, 2)  # Right after ETH/USD
                else:
                    return (0, 10, symbol.name)  # Other cryptos alphabetically
            else:  # Stocks (market_id=2)
                return (1, symbol.name)
        
        symbols = sorted(symbols, key=symbol_sort_key)
        
        # Initialize Kraken provider for live data
        kraken_live_data = {}
        try:
            kraken_provider = get_kraken_provider()
            
            # Map database symbols to Kraken pairs (Kraken uses extended names)
            kraken_symbol_map = {
                'BTC/USD': 'XXBTZUSD',
                'ETH/USD': 'XETHZUSD', 
                'SOL/USD': 'SOLUSD',
                'LTC/USD': 'XLTCZUSD',
                'XRP/USD': 'XXRPZUSD',
                'BCH/USD': 'BCHUSD',
                'LINK/USD': 'LINKUSD',
                'DOGE/USD': 'XDGUSD',
                'ETH/BTC': 'XETHXXBT'
            }
            
            # Get live prices from Kraken for mapped symbols
            kraken_pairs = [pair for pair in kraken_symbol_map.values()]
            try:
                live_ticker = kraken_provider.get_ticker(kraken_pairs)
                logger.info(f"Retrieved live data for {len(live_ticker)} pairs from Kraken")
                
                # Convert to our format (keep string precision for prices)
                from decimal import Decimal
                for symbol_name, kraken_pair in kraken_symbol_map.items():
                    if kraken_pair in live_ticker:
                        ticker_data = live_ticker[kraken_pair]
                        kraken_live_data[symbol_name] = {
                            'price': Decimal(ticker_data['c'][0]),  # Keep full precision
                            'bid': Decimal(ticker_data['b'][0]),
                            'ask': Decimal(ticker_data['a'][0]),
                            'volume_24h': Decimal(ticker_data['v'][1]),
                            'source': 'Kraken Live'
                        }
                        
            except Exception as e:
                logger.warning(f"Failed to get live Kraken data: {e}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Kraken provider: {e}")
        
        # Initialize IBKR provider for stock data  
        ibkr_stock_data = {}
        try:
            ibkr_provider = get_ibkr_simple_provider()
            
            # Get stock symbols from database (market_id=2 for IBKR stocks)
            stock_symbols_in_db = [s.name for s in symbols if s.market_id == 2]
            logger.info(f"Found {len(stock_symbols_in_db)} IBKR stock symbols in database")
            
            if stock_symbols_in_db:
                # Get market data using simple provider (avoids uvloop conflicts)
                ibkr_stock_data = ibkr_provider.get_market_data(stock_symbols_in_db)
                logger.info(f"IBKR data provider initialized for {len(stock_symbols_in_db)} symbols")
            
        except Exception as e:
            logger.error(f"Failed to initialize IBKR simple provider: {e}")
            # Fallback to placeholder
            stock_symbols_in_db = [s for s in symbols if s.market_id == 2]
            for symbol in stock_symbols_in_db:
                ibkr_stock_data[symbol.name] = {
                    'price': 0.0,
                    'source': 'IBKR (Error)',
                    'status': 'error'
                }
        
        # Get Redis connection for fallback prices  
        live_prices = {}
        try:
            r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
            for symbol in symbols:
                price_key = f"live_price_{symbol.name.replace('/', '')}"
                price_data = r.get(price_key)
                if price_data:
                    live_prices[symbol.name] = json.loads(price_data)
                else:
                    # Fallback to latest database price
                    latest_price = OhlcPrice.objects.filter(symbol=symbol.name).order_by('-date').first()
                    if latest_price and latest_price.close:
                        live_prices[symbol.name] = {
                            'price': float(latest_price.close),
                            'timestamp': latest_price.date.isoformat(),
                            'source': 'database'
                        }
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            # Fallback to database prices for all symbols
            for symbol in symbols:
                latest_price = OhlcPrice.objects.filter(symbol=symbol.name).order_by('-date').first()
                if latest_price and latest_price.close:
                    live_prices[symbol.name] = {
                        'price': float(latest_price.close),
                        'timestamp': latest_price.date.isoformat(),
                        'source': 'database'
                    }
        
        # Create symbols with embedded price data
        symbols_with_prices = []
        for symbol in symbols:
            symbol_data = {
                'name': symbol.name,
                'description': symbol.description,
                'price': None,
                'price_source': 'none'
            }
            
            # Priority 1: For crypto, use database OHLC (full precision), but show Kraken Live badge
            # WebSocket will update to real-time prices immediately after page load
            if symbol.name in kraken_live_data:
                # Use database OHLC close for initial display (preserves full decimal precision)
                latest_ohlc = OhlcPrice.objects.filter(symbol=symbol.name).order_by('-date').first()
                if latest_ohlc and latest_ohlc.close:
                    symbol_data.update({
                        'price': latest_ohlc.close,  # Use DB for full precision
                        'price_source': 'Kraken Live',  # Show Kraken Live badge (WebSocket is active)
                    })
                else:
                    # Fallback to Kraken ticker if no DB data
                    kraken_data = kraken_live_data[symbol.name]
                    symbol_data.update({
                        'price': kraken_data['price'],
                        'price_source': 'Kraken Live',
                    })
            
            # Priority 2: IBKR live data (stocks)
            elif symbol.name in ibkr_stock_data:
                ibkr_data = ibkr_stock_data[symbol.name]
                symbol_data.update({
                    'price': ibkr_data['price'],
                    'price_source': ibkr_data['source'],
                    'bid': ibkr_data.get('bid'),
                    'ask': ibkr_data.get('ask'),
                    'timestamp': ibkr_data.get('timestamp')
                })
                
            # Priority 3: Redis cache or database
            elif symbol.name in live_prices:
                price_info = live_prices[symbol.name]
                symbol_data['price'] = price_info['price']
                symbol_data['price_source'] = price_info.get('source', 'live')
                symbol_data['timestamp'] = price_info.get('timestamp', '')
            
            # If still no price, use latest OHLC close from database (highest precision)
            if symbol_data['price'] is None or symbol_data['price'] == 0:
                latest_ohlc = OhlcPrice.objects.filter(symbol=symbol.name).order_by('-date').first()
                if latest_ohlc and latest_ohlc.close:
                    symbol_data['price'] = latest_ohlc.close
                    symbol_data['price_source'] = 'database (latest OHLC)'
            
            symbols_with_prices.append(symbol_data)

        # Create symbol config for frontend (counter_decimals for price formatting)
        symbols_config = {}
        initial_prices = {}
        for symbol in symbols:
            symbols_config[symbol.name] = {
                'counter_decimals': symbol.counter_decimals,
                'base_decimals': symbol.base_decimals
            }
            # Prepare initial prices as strings to preserve precision
            for sym_data in symbols_with_prices:
                if sym_data['name'] == symbol.name and sym_data['price'] is not None:
                    # Convert to string to preserve full precision in JSON
                    initial_prices[symbol.name] = str(sym_data['price'])
                    break
        
        context = {
            'symbols': symbols,
            'symbols_with_prices': symbols_with_prices,
            'symbols_config': mark_safe(json.dumps(symbols_config)),  # Serialize to JSON for frontend
            'initial_prices': mark_safe(json.dumps(initial_prices)),  # Serialize prices to preserve precision
            'live_prices': live_prices,
            'kraken_integration': True,
            'kraken_live_count': len(kraken_live_data),
            'ibkr_integration': True,
            'ibkr_live_count': len(ibkr_stock_data),
            'is_authenticated': request.user.is_authenticated,
            'app_name': 'Seraphim Trading System',
        }
        
        return render(request, 'seraphim/dashboard.html', context)


class MarketDataView(View):
    """API view for market data"""
    
    def get(self, request):
        symbol = request.GET.get('symbol', 'BTC/USD')
        interval_seconds = int(request.GET.get('interval', '86400'))  # Default to 1D (86400 seconds)
        
        # Get OHLC data for the specific interval
        ohlc_data = OhlcPrice.objects.filter(
            symbol=symbol,
            interval=interval_seconds
        ).order_by('-date')[:100]
        
        # Get indicators for the specific interval (if available)
        # Note: Current Indicator model doesn't have interval field, using all for now
        indicators = Indicator.objects.filter(
            symbol=symbol,
            interval=interval_seconds
        ).order_by('-timestamp')[:100]
        
        # Add debug info
        logger.info(f"MarketDataView: symbol={symbol}, interval={interval_seconds}, ohlc_count={ohlc_data.count()}, indicators_count={indicators.count()}")
        
        data = {
            'ohlc': [
                {
                    'timestamp': item.date.isoformat(),
                    'open': float(item.open) if item.open else 0,
                    'high': float(item.high) if item.high else 0,
                    'low': float(item.low) if item.low else 0,
                    'close': float(item.close) if item.close else 0,
                    'volume': float(item.volume) if item.volume else 0,
                } for item in ohlc_data
            ],
            'indicators': [
                {
                    'timestamp': item.timestamp.isoformat(),
                    'sma_20': float(item.ma_20) if item.ma_20 else None,
                    'ema_12': float(item.ema) if item.ema else None,
                    'ema_26': float(item.upper_ema) if item.upper_ema else None,
                    'macd': float(item.macd) if item.macd else None,
                    'rsi': float(item.rsi) if item.rsi else None,
                    # EMA Channel (轨道当值) indicators
                    'ema_high_33': float(item.ema_high_33) if item.ema_high_33 else None,  # 上轨当值
                    'ema_low_33': float(item.ema_low_33) if item.ema_low_33 else None,    # 下轨当值
                } for item in indicators
            ]
        }
        
        return JsonResponse(data)


class MarketRegimeView(View):
    """API view for market regime detection data"""
    
    def get(self, request):
        symbol = request.GET.get('symbol', 'BTC/USD')
        interval_seconds = int(request.GET.get('interval', '86400'))  # Default to 1D
        
        # Get latest market regime
        latest_regime = MarketRegime.objects.filter(
            symbol=symbol,
            interval=interval_seconds
        ).order_by('-timestamp').first()
        
        if not latest_regime:
            return JsonResponse({
                'error': 'No market regime data found',
                'symbol': symbol,
                'interval': interval_seconds
            }, status=404)
        
        # Get higher timeframe regime for context
        higher_interval = {3600: 14400, 14400: 86400, 86400: 604800, 604800: 604800}.get(interval_seconds, interval_seconds)
        higher_regime = None
        if higher_interval != interval_seconds:
            higher_regime = MarketRegime.objects.filter(
                symbol=symbol,
                interval=higher_interval
            ).order_by('-timestamp').first()
        
        data = {
            'symbol': symbol,
            'interval': interval_seconds,
            'timestamp': latest_regime.timestamp.isoformat(),
            'regime_type': latest_regime.regime_type,
            'trend_direction': latest_regime.trend_direction,
            'adx': float(latest_regime.adx) if latest_regime.adx else None,
            'channel_in_pct': float(latest_regime.channel_in_pct) if latest_regime.channel_in_pct else None,
            'channel_width_pct': float(latest_regime.channel_width_pct) if latest_regime.channel_width_pct else None,
            'volume_ratio': float(latest_regime.volume_ratio) if latest_regime.volume_ratio else None,
            'higher_tf_trend': latest_regime.higher_tf_trend,
        }
        
        # Add higher timeframe data if available
        if higher_regime:
            data['higher_timeframe'] = {
                'interval': higher_interval,
                'regime_type': higher_regime.regime_type,
                'trend_direction': higher_regime.trend_direction,
                'adx': float(higher_regime.adx) if higher_regime.adx else None,
            }
        
        return JsonResponse(data)


class TradingSignalsView(View):
    """API view for trading signals"""
    
    def get(self, request):
        symbol = request.GET.get('symbol', None)  # Optional filter by symbol
        interval_seconds = request.GET.get('interval', None)  # Optional filter by interval
        status = request.GET.get('status', 'active')  # Default to active signals
        limit = int(request.GET.get('limit', '50'))  # Limit number of results
        
        # Build query
        query = TradingSignal.objects.all()
        
        if symbol:
            query = query.filter(symbol=symbol)
        
        if interval_seconds:
            query = query.filter(interval=int(interval_seconds))
        
        if status:
            query = query.filter(status=status)
        
        # Order by timestamp (latest first) and limit
        signals = query.order_by('-timestamp')[:limit]
        
        data = {
            'signals': [
                {
                    'id': signal.id,
                    'symbol': signal.symbol,
                    'interval': signal.interval,
                    'timestamp': signal.timestamp.isoformat(),
                    'signal_type': signal.signal_type,
                    'strategy': signal.strategy,
                    'market_regime': signal.market_regime,
                    'confidence': float(signal.confidence),
                    'entry_price': float(signal.entry_price),
                    'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                    'take_profit': float(signal.take_profit) if signal.take_profit else None,
                    'risk_pct': float(signal.risk_pct) if signal.risk_pct else None,
                    'reward_pct': float(signal.reward_pct) if signal.reward_pct else None,
                    'trigger_reason': signal.trigger_reason,
                    'rsi_value': float(signal.rsi_value) if signal.rsi_value else None,
                    'macd_value': float(signal.macd_value) if signal.macd_value else None,
                    'volume_ratio': float(signal.volume_ratio) if signal.volume_ratio else None,
                    'status': signal.status,
                    'exit_price': float(signal.exit_price) if signal.exit_price else None,
                    'exit_timestamp': signal.exit_timestamp.isoformat() if signal.exit_timestamp else None,
                    'pnl_pct': float(signal.pnl_pct) if signal.pnl_pct else None,
                    'created_at': signal.created_at.isoformat(),
                    'updated_at': signal.updated_at.isoformat(),
                } for signal in signals
            ],
            'count': signals.count(),
            'filters': {
                'symbol': symbol,
                'interval': interval_seconds,
                'status': status,
                'limit': limit
            }
        }
        
        return JsonResponse(data)


class TradingSignalDetailView(View):
    """API view for a single trading signal detail"""
    
    def get(self, request, signal_id):
        try:
            signal = TradingSignal.objects.get(id=signal_id)
        except TradingSignal.DoesNotExist:
            return JsonResponse({'error': 'Signal not found'}, status=404)
        
        data = {
            'id': signal.id,
            'symbol': signal.symbol,
            'interval': signal.interval,
            'timestamp': signal.timestamp.isoformat(),
            'signal_type': signal.signal_type,
            'strategy': signal.strategy,
            'market_regime': signal.market_regime,
            'confidence': float(signal.confidence),
            'entry_price': float(signal.entry_price),
            'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
            'take_profit': float(signal.take_profit) if signal.take_profit else None,
            'risk_pct': float(signal.risk_pct) if signal.risk_pct else None,
            'reward_pct': float(signal.reward_pct) if signal.reward_pct else None,
            'trigger_reason': signal.trigger_reason,
            'rsi_value': float(signal.rsi_value) if signal.rsi_value else None,
            'macd_value': float(signal.macd_value) if signal.macd_value else None,
            'volume_ratio': float(signal.volume_ratio) if signal.volume_ratio else None,
            'status': signal.status,
            'exit_price': float(signal.exit_price) if signal.exit_price else None,
            'exit_timestamp': signal.exit_timestamp.isoformat() if signal.exit_timestamp else None,
            'pnl_pct': float(signal.pnl_pct) if signal.pnl_pct else None,
            'created_at': signal.created_at.isoformat(),
            'updated_at': signal.updated_at.isoformat(),
        }
        
        return JsonResponse(data)


class ManualDataUpdateView(View):
    """
    Manual trigger for data updates
    Endpoint: /api/manual-update/
    """
    
    def post(self, request):
        """
        Trigger manual data update
        Optional query parameters:
        - task: specific task to run (ohlc, indicators, ema, regime, signals, all)
        """
        from api.tasks import (
            fetch_ohlc_data, 
            calculate_indicators, 
            calculate_ema_channel,
            calculate_market_regime,
            generate_trading_signals,
            manual_update_all
        )
        
        task_param = request.GET.get('task', 'all').lower()
        
        try:
            if task_param == 'ohlc':
                result = fetch_ohlc_data.delay()
                task_id = result.id
                message = "OHLC data fetch started"
                
            elif task_param == 'indicators':
                result = calculate_indicators.delay()
                task_id = result.id
                message = "Indicator calculations started"
                
            elif task_param == 'ema':
                result = calculate_ema_channel.delay()
                task_id = result.id
                message = "EMA channel calculations started"
                
            elif task_param == 'regime':
                result = calculate_market_regime.delay()
                task_id = result.id
                message = "Market regime calculations started"
                
            elif task_param == 'signals':
                result = generate_trading_signals.delay()
                task_id = result.id
                message = "Trading signal generation started"
                
            elif task_param == 'all':
                result = manual_update_all.delay()
                task_id = result.id
                message = "Full data update started (all tasks)"
                
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Invalid task parameter: {task_param}',
                    'valid_tasks': ['ohlc', 'indicators', 'ema', 'regime', 'signals', 'all']
                }, status=400)
            
            return JsonResponse({
                'status': 'success',
                'message': message,
                'task_id': task_id,
                'task_type': task_param
            })
            
        except Exception as e:
            logger.error(f"Manual update failed: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    def get(self, request):
        """
        Get task status
        Query parameter: task_id
        """
        from celery.result import AsyncResult
        
        task_id = request.GET.get('task_id')
        
        if not task_id:
            return JsonResponse({
                'status': 'error',
                'message': 'task_id parameter is required'
            }, status=400)
        
        result = AsyncResult(task_id)
        
        return JsonResponse({
            'task_id': task_id,
            'status': result.status,
            'ready': result.ready(),
            'successful': result.successful() if result.ready() else None,
            'result': result.result if result.ready() and result.successful() else None,
            'error': str(result.info) if result.failed() else None
        })