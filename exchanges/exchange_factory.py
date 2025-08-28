"""
Exchange Factory
===============
Manages all exchange instances and provides easy access to them.
"""

from typing import Dict, List
import pandas as pd
import time
import threading
from datetime import datetime, timezone
from .base_exchange import BaseExchange
from .backpack_exchange import BackpackExchange
from .binance_exchange import BinanceExchange
from .kucoin_exchange import KuCoinExchange
from .deribit_exchange import DeribitExchange
from .kraken_exchange import KrakenExchange
from .hyperliquid_exchange import HyperliquidExchange


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
        
        # Import settings for sequential collection
        try:
            from config.settings import ENABLE_SEQUENTIAL_COLLECTION, EXCHANGE_COLLECTION_DELAY
            self.sequential_mode = ENABLE_SEQUENTIAL_COLLECTION
            self.exchange_delay = EXCHANGE_COLLECTION_DELAY
        except ImportError:
            self.sequential_mode = False
            self.exchange_delay = 30
        
        # Import sequential configuration if available
        try:
            from config.sequential_config import get_exchange_schedule, get_exchange_delay
            self.get_exchange_schedule = get_exchange_schedule
            self.get_exchange_delay = get_exchange_delay
        except ImportError:
            self.get_exchange_schedule = None
            self.get_exchange_delay = None
        
        # Store for sequential collection data
        self.sequential_data: Dict[str, pd.DataFrame] = {}
        self.collection_threads: List[threading.Thread] = []
    
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
            'hyperliquid': HyperliquidExchange,
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
        Uses sequential mode if enabled to stagger API calls.
        
        Returns:
            Combined DataFrame from all exchanges
        """
        if self.sequential_mode:
            return self._process_exchanges_sequential()
        else:
            return self._process_exchanges_parallel()
    
    def _process_exchanges_parallel(self) -> pd.DataFrame:
        """
        Process all exchanges in parallel (original behavior).
        
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
            return self._get_empty_dataframe()
    
    def _process_exchanges_sequential(self) -> pd.DataFrame:
        """
        Process exchanges sequentially with delays to reduce API load.
        Uses configured schedule if available, otherwise uses default delays.
        
        Returns:
            Combined DataFrame from all exchanges
        """
        # Clear previous data
        self.sequential_data.clear()
        self.collection_threads.clear()
        
        enabled_exchanges = self.get_enabled_exchanges()
        
        # Use configured schedule if available
        if self.get_exchange_delay:
            print(f"\n[Sequential Mode] Using configured schedule")
            exchange_delays = {}
            for exchange in enabled_exchanges:
                delay = self.get_exchange_delay(exchange.name)
                if delay is not None:
                    exchange_delays[exchange.name] = delay
                else:
                    # Fallback: use index-based delay for unconfigured exchanges
                    idx = len(exchange_delays)
                    exchange_delays[exchange.name] = idx * self.exchange_delay
        else:
            print(f"\n[Sequential Mode] Processing exchanges with {self.exchange_delay}s delay between each")
            exchange_delays = {
                exchange.name: idx * self.exchange_delay 
                for idx, exchange in enumerate(enabled_exchanges)
            }
        
        # Start collection threads with delays
        for exchange in enabled_exchanges:
            delay = exchange_delays[exchange.name]
            thread = threading.Thread(
                target=self._collect_exchange_data_delayed,
                args=(exchange, delay),
                name=f"Collector-{exchange.name}"
            )
            thread.start()
            self.collection_threads.append(thread)
            
            if delay > 0:
                print(f"  • {exchange.name}: scheduled for {delay}s from now")
            else:
                print(f"  • {exchange.name}: starting immediately")
        
        # Wait for all threads to complete
        for thread in self.collection_threads:
            thread.join()
        
        # Combine all collected data
        all_data = []
        for exchange_name, data in self.sequential_data.items():
            if not data.empty:
                all_data.append(data)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values(['exchange', 'symbol'])
            combined_df = combined_df.reset_index(drop=True)
            
            print(f"\n[Sequential Mode] Collection complete: {len(combined_df)} total contracts")
            return combined_df
        else:
            return self._get_empty_dataframe()
    
    def _collect_exchange_data_delayed(self, exchange: BaseExchange, delay: float):
        """
        Collect data from an exchange after a specified delay.
        
        Args:
            exchange: Exchange instance to collect from
            delay: Seconds to wait before collection
        """
        if delay > 0:
            time.sleep(delay)
        
        timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S')
        print(f"  [{timestamp}] Starting {exchange.name} collection...")
        
        try:
            data = exchange.process_data()
            if not data.empty:
                self.sequential_data[exchange.name] = data
                print(f"  [{timestamp}] {exchange.name}: collected {len(data)} contracts")
            else:
                print(f"  [{timestamp}] {exchange.name}: no data retrieved")
        except Exception as e:
            print(f"  [{timestamp}] {exchange.name}: ERROR - {str(e)}")
            self.sequential_data[exchange.name] = pd.DataFrame()
    
    def _get_empty_dataframe(self) -> pd.DataFrame:
        """
        Get an empty DataFrame with unified columns.
        
        Returns:
            Empty DataFrame with standard columns
        """
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