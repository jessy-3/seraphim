"""
Kraken Data Provider
Comprehensive Kraken API integration for Seraphim Trading System
"""

import hashlib
import hmac
import base64
import time
import urllib.parse
import requests
import websocket
import json
import threading
import logging
from typing import Dict, List, Optional, Any, Callable
from decimal import Decimal
from datetime import datetime, timezone
from django.conf import settings
import redis

logger = logging.getLogger(__name__)


class KrakenDataProvider:
    """
    Kraken API Data Provider
    
    Provides unified access to Kraken's public and private APIs,
    real-time WebSocket data, and standardized data formats.
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Initialize Kraken Data Provider
        
        Args:
            api_key: Kraken API Key (optional for public data only)
            api_secret: Kraken Private Key (optional for public data only)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        
        # API Endpoints
        self.api_url = "https://api.kraken.com"
        self.websocket_url = "wss://ws.kraken.com"
        
        # Redis connection for caching
        try:
            self.redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
        
        # WebSocket client
        self.ws_client = None
        self.ws_callbacks = {}
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
        
    def _get_kraken_signature(self, urlpath: str, data: Dict) -> str:
        """Generate Kraken API signature"""
        if not self.api_secret:
            raise ValueError("API Secret required for private endpoints")
            
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    
    def _make_request(self, uri_path: str, data: Dict = None, is_private: bool = False) -> Dict:
        """
        Make HTTP request to Kraken API with rate limiting
        """
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        
        headers = {'User-Agent': 'Seraphim Trading System 1.0'}
        url = self.api_url + uri_path
        
        try:
            if is_private:
                if not self.api_key or not self.api_secret:
                    raise ValueError("API credentials required for private endpoints")
                
                if data is None:
                    data = {}
                data['nonce'] = str(int(time.time() * 1000))
                
                headers.update({
                    'API-Key': self.api_key,
                    'API-Sign': self._get_kraken_signature(uri_path, data)
                })
                
                response = requests.post(url, headers=headers, data=data, timeout=30)
            else:
                response = requests.get(url, params=data, headers=headers, timeout=30)
            
            self.last_request_time = time.time()
            result = response.json()
            
            if result.get('error'):
                logger.error(f"Kraken API error: {result['error']}")
                raise Exception(f"Kraken API error: {result['error']}")
                
            return result['result']
            
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            raise Exception(f"Request failed: {e}")
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise
    
    # Public API Methods
    
    def get_server_time(self) -> Dict:
        """Get Kraken server time"""
        return self._make_request('/0/public/Time')
    
    def get_asset_info(self, assets: List[str] = None) -> Dict:
        """Get asset information"""
        params = {}
        if assets:
            params['asset'] = ','.join(assets)
        return self._make_request('/0/public/Assets', params)
    
    def get_trading_pairs(self, pairs: List[str] = None) -> Dict:
        """Get trading pair information"""
        params = {}
        if pairs:
            params['pair'] = ','.join(pairs)
        return self._make_request('/0/public/AssetPairs', params)
    
    def get_ticker(self, pairs: List[str]) -> Dict:
        """
        Get ticker information for trading pairs
        
        Args:
            pairs: List of trading pair symbols
            
        Returns:
            Dict containing ticker data
        """
        params = {'pair': ','.join(pairs)}
        result = self._make_request('/0/public/Ticker', params)
        
        # Cache ticker data in Redis
        if self.redis_client:
            for pair, data in result.items():
                cache_key = f"kraken_ticker:{pair}"
                cache_data = {
                    'price': float(data['c'][0]),  # Last price
                    'bid': float(data['b'][0]),    # Best bid
                    'ask': float(data['a'][0]),    # Best ask
                    'volume': float(data['v'][1]), # 24h volume
                    'timestamp': int(time.time()),
                    'source': 'kraken'
                }
                self.redis_client.setex(cache_key, 60, json.dumps(cache_data))
                
        return result
    
    def get_ohlc_data(self, pair: str, interval: int = 1440, since: int = None) -> Dict:
        """
        Get OHLC data for a trading pair
        
        Args:
            pair: Trading pair symbol
            interval: Time frame in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
            since: Return data since this timestamp
            
        Returns:
            Dict containing OHLC data
        """
        params = {'pair': pair, 'interval': interval}
        if since:
            params['since'] = since
            
        return self._make_request('/0/public/OHLC', params)
    
    def get_order_book(self, pair: str, count: int = 100) -> Dict:
        """Get order book for a trading pair"""
        params = {'pair': pair, 'count': count}
        return self._make_request('/0/public/Depth', params)
    
    def get_recent_trades(self, pair: str, since: int = None) -> Dict:
        """Get recent trades for a trading pair"""
        params = {'pair': pair}
        if since:
            params['since'] = since
        return self._make_request('/0/public/Trades', params)
    
    # Private API Methods (require authentication)
    
    def get_account_balance(self) -> Dict:
        """Get account balance"""
        return self._make_request('/0/private/Balance', is_private=True)
    
    def get_open_orders(self) -> Dict:
        """Get open orders"""
        return self._make_request('/0/private/OpenOrders', is_private=True)
    
    def get_closed_orders(self, start: int = None, end: int = None) -> Dict:
        """Get closed orders"""
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        return self._make_request('/0/private/ClosedOrders', params, is_private=True)
    
    def get_trades_history(self, start: int = None, end: int = None) -> Dict:
        """Get trades history"""
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        return self._make_request('/0/private/TradesHistory', params, is_private=True)
    
    def get_ledgers(self, asset: str = None, type: str = None) -> Dict:
        """Get ledger entries"""
        params = {}
        if asset:
            params['asset'] = asset
        if type:
            params['type'] = type
        return self._make_request('/0/private/Ledgers', params, is_private=True)
    
    def place_order(self, pair: str, type: str, ordertype: str, volume: str, 
                   price: str = None, **kwargs) -> Dict:
        """
        Place a new order
        
        Args:
            pair: Trading pair
            type: Order side ('buy' or 'sell')
            ordertype: Order type ('market', 'limit', 'stop-loss', etc.)
            volume: Order volume
            price: Order price (for limit orders)
            **kwargs: Additional order parameters
        """
        data = {
            'pair': pair,
            'type': type,
            'ordertype': ordertype,
            'volume': volume
        }
        
        if price:
            data['price'] = price
            
        data.update(kwargs)
        
        return self._make_request('/0/private/AddOrder', data, is_private=True)
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        data = {'txid': order_id}
        return self._make_request('/0/private/CancelOrder', data, is_private=True)
    
    # WebSocket Methods
    
    def start_websocket(self, subscriptions: List[Dict] = None):
        """
        Start WebSocket connection for real-time data
        
        Args:
            subscriptions: List of subscription dictionaries
        """
        if self.ws_client:
            logger.warning("WebSocket already running")
            return
            
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self._handle_websocket_message(data)
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket connection closed")
            self.ws_client = None
        
        def on_open(ws):
            logger.info("WebSocket connection opened")
            
            # Subscribe to default channels if none provided
            if not subscriptions:
                default_subs = [
                    {
                        "event": "subscribe",
                        "pair": ["XBT/USD", "ETH/USD", "ETH/XBT"],
                        "subscription": {"name": "ticker"}
                    },
                    {
                        "event": "subscribe", 
                        "pair": ["XBT/USD", "ETH/USD"],
                        "subscription": {"name": "trade"}
                    }
                ]
                for sub in default_subs:
                    ws.send(json.dumps(sub))
            else:
                for sub in subscriptions:
                    ws.send(json.dumps(sub))
        
        # Create WebSocket client
        self.ws_client = websocket.WebSocketApp(
            self.websocket_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Run in background thread
        ws_thread = threading.Thread(target=self.ws_client.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        logger.info("WebSocket client started in background")
    
    def _handle_websocket_message(self, data):
        """Handle incoming WebSocket messages"""
        if isinstance(data, dict):
            if data.get('event') == 'subscriptionStatus':
                logger.info(f"Subscription status: {data}")
                return
            elif data.get('event') == 'systemStatus':
                logger.info(f"System status: {data}")
                return
                
        # Handle ticker data
        if isinstance(data, list) and len(data) >= 4:
            channel_id = data[0]
            ticker_data = data[1]
            channel_name = data[2]
            pair = data[3]
            
            if 'ticker' in channel_name:
                self._handle_ticker_update(pair, ticker_data)
            elif 'trade' in channel_name:
                self._handle_trade_update(pair, ticker_data)
    
    def _handle_ticker_update(self, pair: str, ticker_data: Dict):
        """Handle ticker updates from WebSocket"""
        try:
            # Extract ticker information
            if 'c' in ticker_data:  # Last price
                price_data = {
                    'pair': pair,
                    'price': float(ticker_data['c'][0]),
                    'timestamp': int(time.time()),
                    'source': 'kraken_ws',
                    'bid': float(ticker_data.get('b', [0])[0]),
                    'ask': float(ticker_data.get('a', [0])[0]),
                    'volume': float(ticker_data.get('v', [0])[1])
                }
                
                # Store in Redis
                if self.redis_client:
                    cache_key = f"kraken_live_ticker:{pair}"
                    self.redis_client.setex(cache_key, 300, json.dumps(price_data))
                
                # Call registered callbacks
                for callback in self.ws_callbacks.get('ticker', []):
                    try:
                        callback(pair, price_data)
                    except Exception as e:
                        logger.error(f"Ticker callback error: {e}")
                        
        except Exception as e:
            logger.error(f"Ticker update error: {e}")
    
    def _handle_trade_update(self, pair: str, trade_data: List):
        """Handle trade updates from WebSocket"""
        try:
            for trade in trade_data:
                if isinstance(trade, list) and len(trade) >= 3:
                    trade_info = {
                        'pair': pair,
                        'price': float(trade[0]),
                        'volume': float(trade[1]), 
                        'timestamp': float(trade[2]),
                        'side': trade[3] if len(trade) > 3 else 'unknown',
                        'source': 'kraken_ws'
                    }
                    
                    # Call registered callbacks
                    for callback in self.ws_callbacks.get('trade', []):
                        try:
                            callback(pair, trade_info)
                        except Exception as e:
                            logger.error(f"Trade callback error: {e}")
                            
        except Exception as e:
            logger.error(f"Trade update error: {e}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for WebSocket events
        
        Args:
            event_type: 'ticker' or 'trade'
            callback: Function to call when event occurs
        """
        if event_type not in self.ws_callbacks:
            self.ws_callbacks[event_type] = []
        self.ws_callbacks[event_type].append(callback)
    
    def stop_websocket(self):
        """Stop WebSocket connection"""
        if self.ws_client:
            self.ws_client.close()
            self.ws_client = None
            logger.info("WebSocket client stopped")
    
    # Data Standardization Methods
    
    def normalize_symbol(self, kraken_symbol: str) -> str:
        """
        Convert Kraken symbol to standard format
        
        Args:
            kraken_symbol: Kraken pair symbol (e.g. 'XXBTZUSD')
            
        Returns:
            Standardized symbol (e.g. 'BTC/USD')
        """
        # Mapping for common symbols
        symbol_map = {
            'XXBTZUSD': 'BTC/USD',
            'XETHZUSD': 'ETH/USD', 
            'XETHXXBT': 'ETH/BTC',
            'XLTCZUSD': 'LTC/USD',
            'XLTCXXBT': 'LTC/BTC',
            'XXRPZUSD': 'XRP/USD'
        }
        
        return symbol_map.get(kraken_symbol, kraken_symbol)
    
    def get_standardized_ticker(self, pairs: List[str]) -> List[Dict]:
        """
        Get ticker data in standardized format
        
        Returns:
            List of standardized ticker dictionaries
        """
        raw_data = self.get_ticker(pairs)
        standardized = []
        
        for pair, data in raw_data.items():
            ticker = {
                'symbol': self.normalize_symbol(pair),
                'exchange': 'kraken',
                'price': float(data['c'][0]),
                'bid': float(data['b'][0]),
                'ask': float(data['a'][0]),
                'volume_24h': float(data['v'][1]),
                'high_24h': float(data['h'][1]),
                'low_24h': float(data['l'][1]),
                'change_24h': float(data['p'][1]),
                'timestamp': int(time.time()),
                'raw_data': data
            }
            standardized.append(ticker)
            
        return standardized
    
    def __del__(self):
        """Cleanup WebSocket connection on destruction"""
        if self.ws_client:
            self.stop_websocket()


# Convenience functions for easy usage

def get_kraken_provider() -> KrakenDataProvider:
    """Get configured Kraken provider instance"""
    api_key = getattr(settings, 'KRAKEN_API_KEY', None) 
    api_secret = getattr(settings, 'KRAKEN_API_SECRET', None)
    
    return KrakenDataProvider(api_key=api_key, api_secret=api_secret)


def get_live_prices(pairs: List[str]) -> Dict:
    """Quick function to get live prices"""
    provider = get_kraken_provider()
    return provider.get_ticker(pairs)
