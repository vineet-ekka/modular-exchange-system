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
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import uuid
import logging
import json
from pathlib import Path
from .base_exchange import BaseExchange
from utils.redis_cache import RedisCache
from .backpack_exchange import BackpackExchange
from .binance_exchange import BinanceExchange
from .kucoin_exchange import KuCoinExchange
from .hyperliquid_exchange import HyperliquidExchange
from .drift_exchange import DriftExchange
from .aster_exchange import AsterExchange
from .lighter_exchange import LighterExchange
from .bybit_exchange import ByBitExchange
from .pacifica_exchange import PacificaExchange
from .hibachi_exchange import HibachiExchange
from .deribit_exchange import DeribitExchange
from .mexc_exchange import MexcExchange
from .dydx_exchange import DydxExchange
from .edgex_exchange import EdgexExchange
from .apex_exchange import ApexExchange
# from .kraken_exchange import KrakenExchange  # Not implemented yet


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

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Track collection metrics
        self.last_collection_metrics = {}

        # Redis cache for metrics (with filesystem fallback for compatibility)
        self.cache = RedisCache()
        self.metrics_cache_key = 'collection:metrics'
        self.metrics_cache_ttl = 60  # 60 seconds TTL

        # Metrics file path (fallback for legacy compatibility)
        self.metrics_file = Path(__file__).parent.parent / '.collection_metrics.json'
    
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
            'hyperliquid': HyperliquidExchange,
            'drift': DriftExchange,
            'aster': AsterExchange,
            'lighter': LighterExchange,
            'bybit': ByBitExchange,
            'pacifica': PacificaExchange,
            'hibachi': HibachiExchange,
            'deribit': DeribitExchange,
            'mexc': MexcExchange,
            'dydx': DydxExchange,
            'edgex': EdgexExchange,
            'apex': ApexExchange,
            # 'kraken': KrakenExchange,  # Not implemented yet
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
        Process data from all enabled exchanges in parallel.

        Returns:
            Combined DataFrame from all exchanges
        """
        return self._process_exchanges_parallel()
    
    def _process_exchanges_parallel(self) -> pd.DataFrame:
        """
        Process all exchanges in TRUE parallel using ThreadPoolExecutor.

        Returns:
            Combined DataFrame from all exchanges with batch tracking
        """
        # Generate unique batch ID and timestamp for this collection
        batch_id = str(uuid.uuid4())[:8]  # Short ID for readability
        batch_timestamp = datetime.now(timezone.utc)

        print(f"\n[Parallel Collection] Starting batch {batch_id} at {batch_timestamp.strftime('%H:%M:%S.%f')[:-3]} UTC", flush=True)
        print(f"[Parallel Collection] Processing {len(self.get_enabled_exchanges())} exchanges simultaneously...", flush=True)

        # Reset metrics
        self.last_collection_metrics = {
            'batch_id': batch_id,
            'batch_timestamp': batch_timestamp,
            'exchanges': {},
            'total_duration_ms': 0,
            'success_count': 0,
            'failure_count': 0
        }

        collection_start = time.time()
        all_data = []

        # Use ThreadPoolExecutor for TRUE parallel processing
        with ThreadPoolExecutor(max_workers=10, thread_name_prefix="Exchange") as executor:
            # Submit all exchanges for parallel processing
            future_to_exchange = {}
            for exchange in self.get_enabled_exchanges():
                future = executor.submit(self._collect_exchange_data_with_timing,
                                       exchange, batch_id, batch_timestamp)
                future_to_exchange[future] = exchange

            # Collect results as they complete with timeout (increased to 300s for slow exchanges like MEXC)
            try:
                for future in as_completed(future_to_exchange, timeout=300):
                    exchange = future_to_exchange[future]
                    try:
                        data, duration_ms = future.result(timeout=60)

                        # Track metrics
                        self.last_collection_metrics['exchanges'][exchange.name] = {
                            'duration_ms': duration_ms,
                            'record_count': len(data) if not data.empty else 0,
                            'status': 'success'
                        }

                        if not data.empty:
                            # Add batch tracking columns
                            data['batch_id'] = batch_id
                            data['collection_timestamp'] = batch_timestamp
                            all_data.append(data)
                            self.last_collection_metrics['success_count'] += 1
                            print(f"  [OK] {exchange.name}: {len(data)} contracts in {duration_ms:.0f}ms", flush=True)
                        else:
                            print(f"  [!] {exchange.name}: No data retrieved in {duration_ms:.0f}ms", flush=True)

                    except TimeoutError:
                        self.last_collection_metrics['exchanges'][exchange.name] = {
                            'duration_ms': 60000,
                            'record_count': 0,
                            'status': 'timeout'
                        }
                        self.last_collection_metrics['failure_count'] += 1
                        print(f"  [X] {exchange.name}: TIMEOUT after 60s", flush=True)
                        self.logger.error(f"Exchange {exchange.name} timed out after 60 seconds")

                    except Exception as e:
                        self.last_collection_metrics['exchanges'][exchange.name] = {
                            'duration_ms': 0,
                            'record_count': 0,
                            'status': 'error',
                            'error': str(e)
                        }
                        self.last_collection_metrics['failure_count'] += 1
                        print(f"  [X] {exchange.name}: ERROR - {str(e)[:50]}", flush=True)
                        self.logger.error(f"Exchange {exchange.name} failed: {str(e)}")

            except TimeoutError as e:
                # Handle timeout for the entire as_completed loop
                print(f"\n[Parallel Collection] WARNING: Collection timed out after 120 seconds", flush=True)
                self.logger.error(f"Parallel collection timed out: {str(e)}")
                # Continue with whatever data we collected so far

        # Calculate total collection time
        collection_duration = (time.time() - collection_start) * 1000
        self.last_collection_metrics['total_duration_ms'] = collection_duration

        # Save metrics to file for API access
        self._save_metrics_to_file()

        # Combine all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values(['exchange', 'symbol'])
            combined_df = combined_df.reset_index(drop=True)

            print(f"\n[Parallel Collection] Completed in {collection_duration:.0f}ms")
            print(f"  - Total contracts: {len(combined_df)}")
            print(f"  - Successful exchanges: {self.last_collection_metrics['success_count']}")
            print(f"  - Failed exchanges: {self.last_collection_metrics['failure_count']}")
            print(f"  - Batch ID: {batch_id}")

            # Remove batch tracking columns before returning for database compatibility
            # These columns are useful for arbitrage but not stored in database
            if 'batch_id' in combined_df.columns:
                combined_df = combined_df.drop(columns=['batch_id'])
            if 'collection_timestamp' in combined_df.columns:
                combined_df = combined_df.drop(columns=['collection_timestamp'])

            return combined_df
        else:
            print(f"\n[Parallel Collection] WARNING: No data collected from any exchange")
            return self._get_empty_dataframe()

    def _collect_exchange_data_with_timing(self, exchange: BaseExchange, batch_id: str, batch_timestamp: datetime):
        """
        Collect data from an exchange with timing metrics.

        Args:
            exchange: Exchange instance to collect from
            batch_id: Unique identifier for this collection batch
            batch_timestamp: Timestamp when collection started

        Returns:
            Tuple of (DataFrame, duration_ms)
        """
        start_time = time.time()
        try:
            data = exchange.process_data()
            duration_ms = (time.time() - start_time) * 1000
            return data, duration_ms
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Error collecting from {exchange.name}: {e}")
            raise
    
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

    def get_collection_metrics(self) -> Dict:
        """
        Get metrics from the last collection run.

        Returns:
            Dictionary containing collection performance metrics
        """
        return self.last_collection_metrics

    def _save_metrics_to_file(self):
        """
        Save collection metrics to Redis cache (primary) and filesystem (fallback).
        Redis provides fast IPC, filesystem provides backward compatibility.
        """
        try:
            if not self.last_collection_metrics:
                return

            metrics_to_save = self.last_collection_metrics.copy()

            if 'batch_timestamp' in metrics_to_save and isinstance(metrics_to_save['batch_timestamp'], datetime):
                metrics_to_save['batch_timestamp'] = metrics_to_save['batch_timestamp'].isoformat()

            for exchange_name, exchange_metrics in metrics_to_save.get('exchanges', {}).items():
                if 'last_updated' in exchange_metrics and isinstance(exchange_metrics['last_updated'], datetime):
                    exchange_metrics['last_updated'] = exchange_metrics['last_updated'].isoformat()

            redis_success = self.cache.set(
                self.metrics_cache_key,
                metrics_to_save,
                ttl_seconds=self.metrics_cache_ttl
            )

            if not redis_success:
                self.logger.debug("Redis cache unavailable, falling back to filesystem")

            with open(self.metrics_file, 'w') as f:
                json.dump(metrics_to_save, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")

    def print_collection_summary(self):
        """
        Print a formatted summary of the last collection metrics.
        """
        if not self.last_collection_metrics:
            print("No collection metrics available yet.")
            return

        metrics = self.last_collection_metrics
        total_duration = metrics.get('total_duration_ms', 0)
        total_exchanges = len(metrics.get('exchanges', {}))
        success_count = metrics.get('success_count', 0)
        failure_count = metrics.get('failure_count', 0)
        total_contracts = sum(ex.get('record_count', 0) for ex in metrics.get('exchanges', {}).values())

        print("\n" + "="*80)
        print(" DATA COLLECTION TIMING SUMMARY ".center(80, "="))
        print("="*80)

        print(f"\n OVERALL PERFORMANCE:")
        print(f"   Total Duration:    {total_duration:>10.0f} ms  ({total_duration/1000:.2f} seconds)")
        print(f"   Total Contracts:   {total_contracts:>10,} contracts")
        print(f"   Exchange Success:  {success_count:>10} / {total_exchanges} exchanges")
        if failure_count > 0:
            print(f"   Exchange Failures: {failure_count:>10} exchanges")

        print(f"\n BATCH INFO:")
        print(f"   Batch ID:          {metrics.get('batch_id', 'N/A')}")
        timestamp = metrics.get('batch_timestamp', 'N/A')
        if timestamp != 'N/A':
            print(f"   Timestamp:         {timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")

        print(f"\n EXCHANGE BREAKDOWN (sorted by duration):")
        print(f"   {'Exchange':<15} {'Status':<10} {'Duration':<15} {'Contracts':<12} {'Speed':<15}")
        print(f"   {'-'*15} {'-'*10} {'-'*15} {'-'*12} {'-'*15}")

        exchange_list = []
        for exchange_name, exchange_metrics in metrics.get('exchanges', {}).items():
            exchange_list.append((exchange_name, exchange_metrics))

        exchange_list.sort(key=lambda x: x[1].get('duration_ms', 0), reverse=True)

        for exchange_name, exchange_metrics in exchange_list:
            duration_ms = exchange_metrics.get('duration_ms', 0)
            record_count = exchange_metrics.get('record_count', 0)
            status = exchange_metrics.get('status', 'unknown')

            if status == 'success':
                status_display = "[OK]"
                duration_display = f"{duration_ms:.0f} ms"
                if duration_ms >= 5000:
                    duration_display += " [SLOW]"
                contracts_display = f"{record_count:,}"
                if record_count > 0 and duration_ms > 0:
                    speed = (record_count / duration_ms) * 1000
                    speed_display = f"{speed:.1f} c/s"
                else:
                    speed_display = "N/A"
            elif status == 'timeout':
                status_display = "[TIMEOUT]"
                duration_display = f"{duration_ms:.0f} ms"
                contracts_display = "0"
                speed_display = "N/A"
            else:
                status_display = "[ERROR]"
                duration_display = "N/A"
                contracts_display = "0"
                speed_display = "N/A"
                if 'error' in exchange_metrics:
                    error_msg = exchange_metrics['error'][:30]
                    print(f"   {exchange_name:<15} {status_display:<10} Error: {error_msg}")
                    continue

            print(f"   {exchange_name:<15} {status_display:<10} {duration_display:<15} {contracts_display:<12} {speed_display:<15}")

        if total_contracts > 0 and total_duration > 0:
            overall_speed = (total_contracts / total_duration) * 1000
            print(f"\n OVERALL SPEED: {overall_speed:.1f} contracts/second")

        print("="*80 + "\n") 