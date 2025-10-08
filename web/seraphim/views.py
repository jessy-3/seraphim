from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from api.wsclient import ws_client
from api.models import SymbolInfo, OhlcPrice, Indicator
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
                
                # Convert to our format
                for symbol_name, kraken_pair in kraken_symbol_map.items():
                    if kraken_pair in live_ticker:
                        ticker_data = live_ticker[kraken_pair]
                        kraken_live_data[symbol_name] = {
                            'price': float(ticker_data['c'][0]),
                            'bid': float(ticker_data['b'][0]),
                            'ask': float(ticker_data['a'][0]),
                            'volume_24h': float(ticker_data['v'][1]),
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
            
            # Priority 1: Kraken live data (crypto)
            if symbol.name in kraken_live_data:
                kraken_data = kraken_live_data[symbol.name]
                symbol_data.update({
                    'price': kraken_data['price'],
                    'price_source': 'Kraken Live',
                    'bid': kraken_data.get('bid'),
                    'ask': kraken_data.get('ask'),
                    'volume_24h': kraken_data.get('volume_24h')
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
            
            symbols_with_prices.append(symbol_data)

        context = {
            'symbols': symbols,
            'symbols_with_prices': symbols_with_prices,
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