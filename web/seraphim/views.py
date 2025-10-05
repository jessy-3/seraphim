from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from api.wsclient import ws_client
from api.models import SymbolInfo, OhlcPrice, Indicator
import redis
import json


class DashboardView(View):
    """Main dashboard view for Seraphim Trading System"""
    
    def get(self, request):
        # Start market websocket client for real-time data
        ws_client('start')
        
        # Get basic market data
        symbols = SymbolInfo.objects.all()  # Show all symbols for now
        
        # Get Redis connection for real-time prices, fallback to database
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
            if symbol.name in live_prices:
                price_info = live_prices[symbol.name]
                symbol_data['price'] = price_info['price']
                symbol_data['price_source'] = price_info.get('source', 'live')
                symbol_data['timestamp'] = price_info.get('timestamp', '')
            
            symbols_with_prices.append(symbol_data)

        context = {
            'symbols': symbols,
            'symbols_with_prices': symbols_with_prices,
            'live_prices': live_prices,
            'is_authenticated': request.user.is_authenticated,
            'app_name': 'Seraphim Trading System',
        }
        
        return render(request, 'seraphim/dashboard.html', context)


class SimpleDashboardView(View):
    """Simple dashboard for testing price display"""
    
    def get(self, request):
        # Get basic market data
        symbols = SymbolInfo.objects.all()
        
        # Get prices with database fallback
        symbols_with_prices = []
        for symbol in symbols:
            latest_price = OhlcPrice.objects.filter(symbol=symbol.name).order_by('-date').first()
            symbol_data = {
                'name': symbol.name,
                'description': symbol.description,
                'price': float(latest_price.close) if latest_price and latest_price.close else None,
                'price_source': 'database' if latest_price else 'none'
            }
            symbols_with_prices.append(symbol_data)

        context = {
            'symbols': symbols,
            'symbols_with_prices': symbols_with_prices,
            'app_name': 'Seraphim Trading System',
        }
        
        return render(request, 'seraphim/simple_dashboard.html', context)


class MarketDataView(View):
    """API view for market data"""
    
    def get(self, request):
        symbol = request.GET.get('symbol', 'BTC/USD')
        interval = request.GET.get('interval', '1d')
        
        # Get OHLC data
        ohlc_data = OhlcPrice.objects.filter(
            symbol=symbol
        ).order_by('-date')[:100]
        
        # Get indicators if user is logged in
        indicators = Indicator.objects.filter(
            symbol=symbol
        ).order_by('-timestamp')[:100]
        
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
                } for item in indicators
            ]
        }
        
        return JsonResponse(data)