"""
Simple IBKR provider that avoids uvloop conflicts
"""
import asyncio
import logging
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class IBKRSimpleProvider:
    """Simplified IBKR provider for basic market data"""
    
    def __init__(self):
        self.data_cache = {}
        self.last_update = None
        self.connection_status = 'disconnected'
        
    def get_market_data(self, symbols: list) -> Dict:
        """
        Get market data for given symbols
        Returns cached data or attempts to fetch new data
        """
        result = {}
        
        for symbol in symbols:
            # For now, return placeholder that indicates connection attempt
            result[symbol] = {
                'price': 0.0,
                'source': 'IBKR (Connecting...)',
                'status': 'connecting',
                'timestamp': None
            }
        
        # Try to get real data in background
        self._try_fetch_data_background(symbols)
        
        return result
    
    def _try_fetch_data_background(self, symbols: list):
        """Attempt to fetch data in background thread to avoid uvloop conflicts"""
        def fetch_thread():
            try:
                # This would run the actual IBKR connection in a separate thread
                # avoiding the main Django/uvloop event loop
                self._fetch_real_data(symbols)
            except Exception as e:
                logger.warning(f"Background data fetch failed: {e}")
        
        # Start background thread
        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()
    
    def _fetch_real_data(self, symbols: list):
        """Fetch real data from IBKR (placeholder for now)"""
        # This is where we would implement the actual IBKR connection
        # using a separate event loop to avoid conflicts
        
        try:
            # For debugging - check if we can connect
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('ib-gateway', 4002))
            sock.close()
            
            if result == 0:
                self.connection_status = 'connected'
                logger.info("IBKR Gateway connection test successful")
                
                # Update cache to show connection success
                for symbol in symbols:
                    self.data_cache[symbol] = {
                        'price': 0.0,
                        'source': 'IBKR (Connected - Need Data Subscription)',
                        'status': 'connected_no_data',
                        'timestamp': None
                    }
            else:
                self.connection_status = 'connection_failed'
                logger.warning("IBKR Gateway connection test failed")
                
        except Exception as e:
            logger.error(f"IBKR connection test error: {e}")
            self.connection_status = 'error'

# Global instance
_ibkr_provider = None

def get_ibkr_simple_provider():
    """Get singleton IBKR provider instance"""
    global _ibkr_provider
    if _ibkr_provider is None:
        _ibkr_provider = IBKRSimpleProvider()
    return _ibkr_provider
