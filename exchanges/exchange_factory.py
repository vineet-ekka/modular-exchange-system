"""
Exchange Factory
===============
Manages all exchange instances and provides easy access to them.
"""

from typing import Dict, List
import pandas as pd
from .base_exchange import BaseExchange
from .backpack_exchange import BackpackExchange
from .binance_exchange import BinanceExchange
from .kucoin_exchange import KuCoinExchange
from .deribit_exchange import DeribitExchange
from .kraken_exchange import KrakenExchange


class ExchangeFactory:
    """
    Factory class for managing all exchange instances.
    Makes it easy to add new exchanges and manage their settings.
    """
    
    def __init__(self, exchange_settings: Dict[str, bool]):
        """
        Initialize the exchange factory.
        
        Args:
            exchange_settings: Dictionary mapping exchange names to enabled status
        """
        self.exchanges: Dict[str, BaseExchange] = {}
        self._create_exchanges(exchange_settings)
    
    def _create_exchanges(self, settings: Dict[str, bool]):
        """
        Create exchange instances based on settings.
        
        Args:
            settings: Dictionary of exchange settings
        """
        # Map exchange names to their classes
        exchange_classes = {
            'backpack': BackpackExchange,
            'binance': BinanceExchange,
            'kucoin': KuCoinExchange,
            'deribit': DeribitExchange,
            'kraken': KrakenExchange,
            # Add new exchanges here as they become available
            # 'new_exchange': NewExchangeClass,
        }
        
        # Create exchange instances
        for exchange_name, enabled in settings.items():
            if exchange_name in exchange_classes:
                exchange_class = exchange_classes[exchange_name]
                self.exchanges[exchange_name] = exchange_class(enabled=enabled)
            else:
                print(f"! Unknown exchange: {exchange_name}")
    
    def get_exchange(self, name: str) -> BaseExchange:
        """
        Get a specific exchange instance.
        
        Args:
            name: Name of the exchange
            
        Returns:
            Exchange instance or None if not found
        """
        return self.exchanges.get(name)
    
    def get_all_exchanges(self) -> List[BaseExchange]:
        """
        Get all exchange instances.
        
        Returns:
            List of all exchange instances
        """
        return list(self.exchanges.values())
    
    def get_enabled_exchanges(self) -> List[BaseExchange]:
        """
        Get only enabled exchange instances.
        
        Returns:
            List of enabled exchange instances
        """
        return [ex for ex in self.exchanges.values() if ex.enabled]
    
    def process_all_exchanges(self) -> pd.DataFrame:
        """
        Process data from all enabled exchanges.
        
        Returns:
            Combined DataFrame from all exchanges
        """
        all_data = []
        
        for exchange in self.get_enabled_exchanges():
            try:
                data = exchange.process_data()
                if not data.empty:
                    all_data.append(data)
            except Exception as e:
                print(f"X Error processing {exchange.name}: {str(e)}")
        
        # Combine all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values(['exchange', 'symbol'])
            combined_df = combined_df.reset_index(drop=True)
            return combined_df
        else:
            # Return empty DataFrame with unified columns (without instantiating abstract BaseExchange)
            unified_columns = [
                'exchange', 'symbol', 'base_asset', 'quote_asset', 
                'funding_rate', 'funding_interval_hours', 'apr', 'index_price', 
                'mark_price', 'open_interest', 
                'contract_type', 'market_type'
            ]
            return pd.DataFrame(columns=unified_columns)
    
    def get_exchange_status(self) -> Dict[str, bool]:
        """
        Get the status of all exchanges.
        
        Returns:
            Dictionary mapping exchange names to enabled status
        """
        return {name: exchange.enabled for name, exchange in self.exchanges.items()}
    
    def add_exchange(self, name: str, exchange_class: type, enabled: bool = True):
        """
        Add a new exchange to the factory.
        
        Args:
            name: Name of the exchange
            exchange_class: Exchange class (must inherit from BaseExchange)
            enabled: Whether the exchange is enabled
        """
        if not issubclass(exchange_class, BaseExchange):
            raise ValueError(f"Exchange class must inherit from BaseExchange")
        
        self.exchanges[name] = exchange_class(enabled=enabled)
        print(f"OK Added exchange: {name} (enabled: {enabled})") 