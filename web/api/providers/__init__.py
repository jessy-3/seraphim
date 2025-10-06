"""
Data Providers for Seraphim Trading System
Provides unified interfaces for different trading platforms and data sources
"""

__version__ = "1.0.0"
__author__ = "Seraphina"

# Import all providers for easy access
from .kraken_provider import KrakenDataProvider, get_kraken_provider
# Temporarily disable IBKR import to avoid uvloop conflicts during Django startup
# from .ibkr_socket_provider import IBKRSocketProvider, get_ibkr_socket_provider

__all__ = [
    'KrakenDataProvider', 
    'get_kraken_provider',
    # Temporarily disabled - IBKR providers commented out
    # 'IBKRSocketProvider',
    # 'get_ibkr_socket_provider'
]
