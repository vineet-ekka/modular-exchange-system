"""
dYdX v4 Exchange Module
======================
Handles data fetching and normalization for dYdX v4 exchange.
Supports perpetual contracts with funding rate data.
"""

import pandas as pd
import time
from datetime import datetime, timezone
from .base_exchange import BaseExchange
import logging

class DydxExchange(BaseExchange):
    """
    dYdX v4 Exchange data fetcher.
    Uses the dYdX v4 Indexer API to fetch perpetual market data.
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize dYdX v4 exchange.
        
        Args:
            enabled: Whether this exchange is enabled
        """
        super().__init__("dYdX", enabled)
        self.base_url = "https://indexer.dydx.trade"
        self.logger = logging.getLogger(__name__)
        
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch perpetual market data from dYdX v4.
        
        Returns:
            DataFrame with raw dYdX data
        """
        try:
            # Fetch all perpetual markets
            markets_data = self._fetch_perpetual_markets()
            if not markets_data:
                self.logger.warning("No perpetual markets data received from dYdX")
                return pd.DataFrame()
            
            # Convert to DataFrame
            markets_list = []
            for ticker, market_data in markets_data.items():
                if market_data.get('status') == 'ACTIVE':
                    # Extract base and quote assets from ticker (e.g., "BTC-USD" -> "BTC", "USD")
                    ticker_parts = ticker.split('-')
                    base_part = ticker_parts[0] if len(ticker_parts) > 0 else ''

                    # For Solana/DEX tokens with format "TOKEN,DEX,MINT_ADDRESS", extract just TOKEN
                    # Example: "FARTCOIN,RAYDIUM,9BB6..." -> "FARTCOIN"
                    if ',' in base_part:
                        base_asset = base_part.split(',')[0]
                    else:
                        base_asset = base_part

                    quote_asset = ticker_parts[1] if len(ticker_parts) > 1 else ''
                    
                    markets_list.append({
                        'ticker': ticker,
                        'base_asset': base_asset,
                        'quote_asset': quote_asset,
                        'next_funding_rate': market_data.get('nextFundingRate', '0'),
                        'oracle_price': market_data.get('oraclePrice', '0'),
                        'open_interest': market_data.get('openInterest', '0'),
                        'status': market_data.get('status', ''),
                        'market_type': market_data.get('marketType', 'CROSS'),
                        'initial_margin_fraction': market_data.get('initialMarginFraction', '0'),
                        'maintenance_margin_fraction': market_data.get('maintenanceMarginFraction', '0')
                    })
            
            if not markets_list:
                self.logger.warning("No active perpetual markets found on dYdX")
                return pd.DataFrame()
            
            df = pd.DataFrame(markets_list)
            self.logger.info(f"Found {len(df)} active perpetual markets on dYdX")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching dYdX data: {e}")
            return pd.DataFrame()
    
    def _fetch_perpetual_markets(self) -> dict:
        """
        Fetch all perpetual markets from dYdX v4 API.
        
        Returns:
            Dictionary of market data
        """
        url = f"{self.base_url}/v4/perpetualMarkets"
        
        try:
            response = self.safe_request(url)
            if response and isinstance(response, dict) and 'markets' in response:
                return response['markets']
            else:
                self.logger.warning("Invalid response format from dYdX perpetual markets API")
                return {}
        except Exception as e:
            self.logger.error(f"Error fetching perpetual markets from dYdX: {e}")
            return {}
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform dYdX data to unified format.
        
        Args:
            df: Raw dYdX data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        try:
            # Create normalized DataFrame with same index as input
            normalized_df = pd.DataFrame(index=df.index)
            
            # Basic fields
            normalized_df['exchange'] = self.name
            normalized_df['symbol'] = df['ticker']
            normalized_df['base_asset'] = df['base_asset']
            normalized_df['quote_asset'] = df['quote_asset']
            
            # Convert funding rate to decimal
            normalized_df['funding_rate'] = pd.to_numeric(df['next_funding_rate'], errors='coerce').fillna(0)
            
            # dYdX uses 8-hour funding intervals (standard for perpetuals)
            normalized_df['funding_interval_hours'] = 8
            
            # Calculate APR: funding_rate * (365 * 24 / 8) * 100
            # 8-hour intervals = 3 times per day = 1095 times per year
            periods_per_year = (365 * 24) / 8
            normalized_df['apr'] = (normalized_df['funding_rate'] * periods_per_year * 100).round(4)
            
            # Price data
            normalized_df['index_price'] = pd.to_numeric(df['oracle_price'], errors='coerce').fillna(0)
            normalized_df['mark_price'] = normalized_df['index_price']  # dYdX uses oracle price as mark price
            
            # Open interest
            normalized_df['open_interest'] = pd.to_numeric(df['open_interest'], errors='coerce').fillna(0)
            
            # Contract type and market type
            normalized_df['contract_type'] = 'PERPETUAL'
            normalized_df['market_type'] = df['market_type']
            
            # Filter out contracts with zero open interest or invalid data
            valid_mask = (
                (normalized_df['open_interest'] > 0) &
                (normalized_df['index_price'] > 0) &
                (normalized_df['symbol'].notna())
            )
            
            filtered_df = normalized_df[valid_mask].copy()
            
            if len(filtered_df) < len(normalized_df):
                self.logger.info(f"Filtered out {len(normalized_df) - len(filtered_df)} contracts with zero open interest or invalid data")
            
            return filtered_df
            
        except Exception as e:
            self.logger.error(f"Error normalizing dYdX data: {e}")
            return pd.DataFrame(columns=self.get_unified_columns())
