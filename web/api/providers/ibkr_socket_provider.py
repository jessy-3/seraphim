"""
IBKR Socket Provider for Seraphim Trading System
Uses ib_insync to connect to IB Gateway via TCP Socket
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import threading
import time

# ib_insync imports
from ib_insync import IB, Stock, Contract, MarketOrder, LimitOrder, Order
from ib_insync import util

logger = logging.getLogger(__name__)

class IBKRSocketProvider:
    """Interactive Brokers Socket API provider using ib_insync"""
    
    def __init__(self, host: str = "ib-gateway", port: int = 4004, client_id: int = 1):
        self.name = "IBKR Socket API"
        self.host = host  # Docker service name
        self.port = port  # 4004 for paper trading
        self.client_id = client_id
        
        self.ib = None  # Delay IB creation to avoid uvloop conflicts
        self.connected = False
        self.accounts = []
        self.positions = {}
        self.orders = {}
        
        # Skip startLoop() in Django environment to avoid uvloop conflicts
        # util.startLoop()  # Commented out for Django compatibility
        
    def connect(self, timeout: int = 10) -> bool:
        """Connect to IB Gateway"""
        try:
            logger.info(f"Connecting to IB Gateway at {self.host}:{self.port}")
            
            # Use synchronous connection with event loop handling
            try:
                # Create IB instance only when connecting to avoid startup conflicts
                if self.ib is None:
                    self.ib = IB()
                    
                self.ib.connect(
                    host=self.host,
                    port=self.port,
                    clientId=self.client_id,
                    timeout=timeout
                )
                self.connected = True
                logger.info("✅ Successfully connected to IBKR")
                
                # Get accounts
                self.accounts = self.ib.managedAccounts()
                logger.info(f"📋 Found accounts: {self.accounts}")
                
                return True
                
            except RuntimeError as e:
                if "Can't patch loop" in str(e):
                    logger.warning(f"Event loop conflict detected, using alternative connection method: {e}")
                    # For Django/uvloop environment, we need to handle this differently
                    # For now, we'll return False and let the view handle gracefully
                    self.connected = False
                    return False
                else:
                    raise e
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to IBKR: {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from IB Gateway"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("🔌 Disconnected from IBKR")
    
    def is_connected(self) -> bool:
        """Check if connected to IB Gateway"""
        return self.connected and self.ib.isConnected()
    
    def get_accounts(self) -> List[str]:
        """Get list of account IDs"""
        if not self.is_connected():
            logger.warning("Not connected to IBKR")
            return []
        
        return self.accounts
    
    def get_account_summary(self, account: str = None) -> Dict:
        """Get account summary information"""
        if not self.is_connected():
            return {"error": "Not connected"}
            
        try:
            if account is None:
                account = self.accounts[0] if self.accounts else ""
            
            # Get account values
            account_values = self.ib.accountSummary(account)
            
            summary = {}
            for av in account_values:
                summary[av.tag] = {
                    'value': av.value,
                    'currency': av.currency,
                    'account': av.account
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get account summary: {str(e)}")
            return {"error": str(e)}
    
    def get_positions(self, account: str = None) -> List[Dict]:
        """Get current positions"""
        if not self.is_connected():
            return []
            
        try:
            if account is None:
                account = self.accounts[0] if self.accounts else ""
            
            positions = self.ib.positions(account)
            
            result = []
            for pos in positions:
                result.append({
                    'symbol': pos.contract.symbol,
                    'secType': pos.contract.secType,
                    'exchange': pos.contract.exchange,
                    'currency': pos.contract.currency,
                    'position': pos.position,
                    'avgCost': pos.avgCost,
                    'marketPrice': 0,  # Will be filled by market data
                    'marketValue': 0,  # Will be calculated
                    'unrealizedPNL': 0,
                    'realizedPNL': 0
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            return []
    
    def get_market_data(self, symbols: List[str], sec_type: str = "STK", 
                       exchange: str = "SMART", currency: str = "USD") -> Dict[str, Dict]:
        """Get market data for symbols"""
        if not self.is_connected():
            return {}
            
        try:
            contracts = []
            for symbol in symbols:
                contract = Stock(symbol, exchange, currency)
                contracts.append(contract)
            
            # Request market data
            results = {}
            for contract in contracts:
                try:
                    # Qualify the contract first
                    qualified = self.ib.qualifyContracts(contract)
                    if qualified:
                        contract = qualified[0]
                        
                        # Request market data
                        ticker = self.ib.reqMktData(contract, '', False, False)
                        
                        # Wait a bit for data
                        self.ib.sleep(1)
                        
                        results[contract.symbol] = {
                            'symbol': contract.symbol,
                            'bid': ticker.bid if ticker.bid else 0,
                            'ask': ticker.ask if ticker.ask else 0,
                            'last': ticker.last if ticker.last else 0,
                            'close': ticker.close if ticker.close else 0,
                            'volume': ticker.volume if ticker.volume else 0,
                            'timestamp': datetime.now().isoformat(),
                            'source': 'IBKR Socket'
                        }
                        
                        # Cancel market data to avoid hitting limits
                        self.ib.cancelMktData(contract)
                        
                except Exception as e:
                    logger.warning(f"Failed to get data for {contract.symbol}: {str(e)}")
                    results[contract.symbol] = {'error': str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get market data: {str(e)}")
            return {}
    
    def place_order(self, symbol: str, action: str, quantity: int, 
                   order_type: str = "MKT", price: float = None,
                   sec_type: str = "STK", exchange: str = "SMART", 
                   currency: str = "USD") -> Dict:
        """Place an order"""
        if not self.is_connected():
            return {"error": "Not connected"}
            
        try:
            # Create contract
            contract = Stock(symbol, exchange, currency)
            qualified = self.ib.qualifyContracts(contract)
            if not qualified:
                return {"error": f"Could not qualify contract for {symbol}"}
            
            contract = qualified[0]
            
            # Create order
            if order_type.upper() == "MKT":
                order = MarketOrder(action, quantity)
            elif order_type.upper() == "LMT":
                if price is None:
                    return {"error": "Price required for limit order"}
                order = LimitOrder(action, quantity, price)
            else:
                return {"error": f"Unsupported order type: {order_type}"}
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            return {
                'orderId': trade.order.orderId,
                'symbol': contract.symbol,
                'action': action,
                'quantity': quantity,
                'orderType': order_type,
                'price': price,
                'status': trade.orderStatus.status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            return {"error": str(e)}
    
    def get_orders(self, account: str = None) -> List[Dict]:
        """Get open orders"""
        if not self.is_connected():
            return []
            
        try:
            orders = self.ib.openOrders()
            
            result = []
            for trade in orders:
                result.append({
                    'orderId': trade.order.orderId,
                    'symbol': trade.contract.symbol,
                    'action': trade.order.action,
                    'totalQuantity': trade.order.totalQuantity,
                    'orderType': trade.order.orderType,
                    'lmtPrice': trade.order.lmtPrice,
                    'status': trade.orderStatus.status,
                    'filled': trade.orderStatus.filled,
                    'remaining': trade.orderStatus.remaining,
                    'avgFillPrice': trade.orderStatus.avgFillPrice,
                    'lastFillTime': trade.log[-1].time.isoformat() if trade.log else None
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get orders: {str(e)}")
            return []
    
    def cancel_order(self, order_id: int) -> Dict:
        """Cancel an order"""
        if not self.is_connected():
            return {"error": "Not connected"}
            
        try:
            orders = self.ib.openOrders()
            order_to_cancel = None
            
            for trade in orders:
                if trade.order.orderId == order_id:
                    order_to_cancel = trade
                    break
            
            if order_to_cancel is None:
                return {"error": f"Order {order_id} not found"}
            
            self.ib.cancelOrder(order_to_cancel.order)
            
            return {
                'orderId': order_id,
                'status': 'Cancelled',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {str(e)}")
            return {"error": str(e)}
    
    def health_check(self) -> Dict[str, Union[bool, str]]:
        """Check connection health"""
        try:
            is_connected = self.is_connected()
            
            return {
                'status': is_connected,
                'message': 'IBKR Socket API is connected' if is_connected else 'IBKR Socket API is disconnected',
                'host': self.host,
                'port': self.port,
                'accounts': len(self.accounts),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': False,
                'message': f'IBKR Socket API health check failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }


def get_ibkr_socket_provider(host: str = "ib-gateway", port: int = 4004, client_id: int = 1) -> IBKRSocketProvider:
    """
    Get IBKR Socket provider instance
    Args:
        host: IB Gateway host (default: ib-gateway for Docker)
        port: IB Gateway port (4002 for paper, 4001 for live)
        client_id: Unique client ID
    """
    return IBKRSocketProvider(host=host, port=port, client_id=client_id)


# Usage example
if __name__ == "__main__":
    provider = get_ibkr_socket_provider()
    
    # Health check
    health = provider.health_check()
    print(f"Health: {health}")
    
    # Try to connect
    if provider.connect():
        print("✅ Connected!")
        
        # Get accounts
        accounts = provider.get_accounts()
        print(f"Accounts: {accounts}")
        
        # Get account summary
        if accounts:
            summary = provider.get_account_summary(accounts[0])
            print(f"Account Summary: {summary}")
        
        # Get market data
        market_data = provider.get_market_data(['AAPL', 'MSFT'])
        print(f"Market Data: {market_data}")
        
        provider.disconnect()
    else:
        print("❌ Failed to connect")
