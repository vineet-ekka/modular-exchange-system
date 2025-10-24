"""
Comprehensive test suite for the Arbitrage Filter functionality.
Tests API endpoints, filter logic, and integration with the arbitrage scanner.
"""

import requests
import json
import time
import unittest
from typing import Dict, List, Any, Optional
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

class ArbitrageFilterTestSuite(unittest.TestCase):
    """Test suite for arbitrage filter functionality"""

    @classmethod
    def setUpClass(cls):
        """Check if API server is running before tests"""
        try:
            response = requests.get(f"{API_BASE_URL}/api/health/performance")
            if response.status_code != 200:
                raise Exception("API server not responding correctly")
        except Exception as e:
            raise Exception(f"API server must be running for tests: {e}")

    def test_asset_search_basic(self):
        """Test basic asset search functionality"""
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/assets/search",
            params={"q": "BTC", "limit": 10}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify response structure
        self.assertIn("results", data)
        self.assertIn("query", data)
        self.assertIn("count", data)
        self.assertIn("timestamp", data)

        # Verify search results
        self.assertEqual(data["query"], "BTC")
        self.assertIsInstance(data["results"], list)

        # Check first result structure if available
        if data["results"]:
            asset = data["results"][0]
            self.assertIn("symbol", asset)
            self.assertIn("exchanges", asset)
            self.assertIn("avg_spread_pct", asset)
            self.assertIn("total_opportunities", asset)

    def test_asset_search_partial_match(self):
        """Test partial matching in asset search"""
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/assets/search",
            params={"q": "ET", "limit": 5}
        )
        data = response.json()

        # Should find ETH, ETC, ETHFI etc.
        self.assertTrue(len(data["results"]) > 0)

        # Verify partial matches
        for asset in data["results"]:
            self.assertTrue(
                "ET" in asset["symbol"].upper(),
                f"Asset {asset['symbol']} should contain 'ET'"
            )

    def test_asset_search_empty_query(self):
        """Test asset search with empty query"""
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/assets/search",
            params={"q": "", "limit": 5}
        )
        # API should reject empty queries
        self.assertNotEqual(response.status_code, 200)

    def test_opportunities_with_asset_filter(self):
        """Test opportunities endpoint with asset filter"""
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.00001,
                "page": 1,
                "page_size": 10,
                "assets": ["BTC", "ETH"]
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify filter is applied in parameters
        self.assertIn("parameters", data)
        self.assertEqual(data["parameters"]["assets"], ["BTC", "ETH"])

        # Check opportunities only contain specified assets
        for opp in data["opportunities"]:
            self.assertIn(opp["asset"], ["BTC", "ETH"])

    def test_opportunities_with_exchange_filter(self):
        """Test opportunities endpoint with exchange filter"""
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.00001,
                "page": 1,
                "page_size": 10,
                "exchanges": ["Binance", "KuCoin"]
            }
        )
        data = response.json()

        # Verify exchanges filter
        self.assertEqual(data["parameters"]["exchanges"], ["Binance", "KuCoin"])

        # Check opportunities contain specified exchanges
        for opp in data["opportunities"]:
            exchanges = [opp["long_exchange"], opp["short_exchange"]]
            self.assertTrue(
                any(ex in ["Binance", "KuCoin"] for ex in exchanges),
                f"Opportunity should involve Binance or KuCoin: {exchanges}"
            )

    def test_opportunities_with_interval_filter(self):
        """Test opportunities endpoint with funding interval filter"""
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.00001,
                "page": 1,
                "page_size": 10,
                "intervals": [8]  # 8-hour funding
            }
        )
        data = response.json()

        # Verify interval filter
        self.assertEqual(data["parameters"]["intervals"], [8])

        # Check opportunities contain specified intervals
        for opp in data["opportunities"]:
            intervals = [opp["long_interval_hours"], opp["short_interval_hours"]]
            self.assertTrue(
                8 in intervals,
                f"Opportunity should involve 8-hour funding: {intervals}"
            )

    def test_opportunities_with_apr_range_filter(self):
        """Test opportunities endpoint with APR range filter"""
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.00001,
                "page": 1,
                "page_size": 10,
                "min_apr": 10,
                "max_apr": 100
            }
        )
        data = response.json()

        # Verify APR filters
        self.assertEqual(data["parameters"]["min_apr"], 10.0)
        self.assertEqual(data["parameters"]["max_apr"], 100.0)

        # Check opportunities are within APR range
        for opp in data["opportunities"]:
            if opp["apr_spread"] is not None:
                self.assertTrue(
                    10 <= opp["apr_spread"] <= 100,
                    f"APR spread {opp['apr_spread']} should be between 10 and 100"
                )

    def test_opportunities_with_liquidity_filter(self):
        """Test opportunities endpoint with liquidity/OI filter"""
        min_oi = 100000  # $100k minimum

        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.00001,
                "page": 1,
                "page_size": 10,
                "min_oi_either": min_oi
            }
        )
        data = response.json()

        # Verify OI filter
        self.assertEqual(data["parameters"]["min_oi_either"], min_oi)

        # Check opportunities meet OI requirement
        for opp in data["opportunities"]:
            oi_values = [opp["long_open_interest"], opp["short_open_interest"]]
            # At least one side should meet minimum
            valid_oi = [oi for oi in oi_values if oi is not None and oi >= min_oi]
            self.assertTrue(
                len(valid_oi) > 0,
                f"At least one OI should be >= {min_oi}: {oi_values}"
            )

    def test_opportunities_with_combined_filters(self):
        """Test opportunities endpoint with multiple filters combined"""
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.0001,
                "page": 1,
                "page_size": 5,
                "assets": ["DOGS", "MTL"],
                "exchanges": ["Binance"],
                "intervals": [8],
                "min_apr": 50
            }
        )
        data = response.json()

        # Verify all filters are present
        params = data["parameters"]
        self.assertEqual(params["assets"], ["DOGS", "MTL"])
        self.assertEqual(params["exchanges"], ["Binance"])
        self.assertEqual(params["intervals"], [8])
        self.assertEqual(params["min_apr"], 50.0)

        # Results should match all filter criteria
        for opp in data["opportunities"]:
            self.assertIn(opp["asset"], ["DOGS", "MTL"])
            exchanges = [opp["long_exchange"], opp["short_exchange"]]
            self.assertIn("Binance", exchanges)

    def test_pagination_with_filters(self):
        """Test pagination works correctly with active filters"""
        # Get first page
        response1 = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.00001,
                "page": 1,
                "page_size": 5,
                "intervals": [4, 8]
            }
        )
        data1 = response1.json()

        # Get second page
        response2 = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.00001,
                "page": 2,
                "page_size": 5,
                "intervals": [4, 8]
            }
        )
        data2 = response2.json()

        # Verify pagination metadata
        self.assertEqual(data1["pagination"]["page"], 1)
        self.assertEqual(data2["pagination"]["page"], 2)
        self.assertEqual(data1["pagination"]["page_size"], 5)

        # Ensure different results on different pages
        if data1["opportunities"] and data2["opportunities"]:
            first_page_ids = [
                f"{o['long_contract']}-{o['short_contract']}"
                for o in data1["opportunities"]
            ]
            second_page_ids = [
                f"{o['long_contract']}-{o['short_contract']}"
                for o in data2["opportunities"]
            ]
            # Pages should not have duplicate entries
            self.assertEqual(
                len(set(first_page_ids) & set(second_page_ids)), 0,
                "Pages should not contain duplicate opportunities"
            )

    def test_filter_validation(self):
        """Test filter parameter validation"""
        # Test invalid APR range (min > max)
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.001,
                "min_apr": 100,
                "max_apr": 10  # Invalid: max < min
            }
        )
        # Should handle gracefully
        self.assertIn(response.status_code, [200, 400])

        # Test invalid page number
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.001,
                "page": -1  # Invalid page
            }
        )
        self.assertEqual(response.status_code, 422)  # Validation error

        # Test excessive page size
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.001,
                "page_size": 1000  # Too large
            }
        )
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_empty_filter_results(self):
        """Test behavior when filters return no results"""
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 10.0,  # Impossibly high spread
                "page": 1,
                "page_size": 10
            }
        )
        data = response.json()

        # Should return empty results gracefully
        self.assertEqual(len(data["opportunities"]), 0)
        self.assertEqual(data["pagination"]["total"], 0)
        self.assertEqual(data["statistics"]["total_opportunities"], 0)

    def test_case_insensitive_search(self):
        """Test asset search is case-insensitive"""
        # Test lowercase
        response_lower = requests.get(
            f"{API_BASE_URL}/api/arbitrage/assets/search",
            params={"q": "btc", "limit": 5}
        )

        # Test uppercase
        response_upper = requests.get(
            f"{API_BASE_URL}/api/arbitrage/assets/search",
            params={"q": "BTC", "limit": 5}
        )

        data_lower = response_lower.json()
        data_upper = response_upper.json()

        # Should return same results
        self.assertEqual(
            len(data_lower["results"]),
            len(data_upper["results"]),
            "Case should not affect search results"
        )

    def test_filter_performance(self):
        """Test filter performance with multiple parameters"""
        start_time = time.time()

        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.0001,
                "page": 1,
                "page_size": 20,
                "assets": ["BTC", "ETH", "SOL", "DOGE"],
                "exchanges": ["Binance", "KuCoin", "ByBit"],
                "intervals": [4, 8],
                "min_apr": 5,
                "max_apr": 200,
                "min_oi_either": 50000
            }
        )

        elapsed_time = time.time() - start_time

        # Should respond within reasonable time even with complex filters
        self.assertLess(
            elapsed_time, 2.0,
            f"Complex filter query took {elapsed_time:.2f}s, should be < 2s"
        )
        self.assertEqual(response.status_code, 200)


class FilterIntegrationTests(unittest.TestCase):
    """Integration tests for filter functionality"""

    def test_filter_cache_behavior(self):
        """Test that filtered results are cached appropriately"""
        params = {
            "min_spread": 0.0001,
            "page": 1,
            "page_size": 10,
            "assets": ["DOGS"]
        }

        # First request (cache miss)
        response1 = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params=params
        )

        # Second request (should be cached)
        response2 = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params=params
        )

        # Results should be identical
        self.assertEqual(response1.json(), response2.json())

    def test_filter_statistics_accuracy(self):
        """Test that statistics are correctly calculated for filtered results"""
        response = requests.get(
            f"{API_BASE_URL}/api/arbitrage/opportunities-v2",
            params={
                "min_spread": 0.0001,
                "page": 1,
                "page_size": 50,
                "intervals": [8]
            }
        )
        data = response.json()

        if data["opportunities"]:
            # Calculate statistics manually
            spreads = [o["rate_spread_pct"] for o in data["opportunities"]]
            apr_spreads = [o["apr_spread"] for o in data["opportunities"]
                          if o["apr_spread"] is not None]

            if spreads:
                manual_avg_spread = sum(spreads) / len(spreads)
                manual_max_spread = max(spreads)

                # Compare with returned statistics (allow small float differences)
                self.assertAlmostEqual(
                    data["statistics"]["average_spread"],
                    manual_avg_spread,
                    places=4,
                    msg="Average spread calculation mismatch"
                )
                self.assertAlmostEqual(
                    data["statistics"]["max_spread"],
                    manual_max_spread,
                    places=4,
                    msg="Max spread calculation mismatch"
                )


def run_tests():
    """Run all test suites and generate report"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(ArbitrageFilterTestSuite))
    suite.addTests(loader.loadTestsFromTestCase(FilterIntegrationTests))

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    # Report failures if any
    if result.failures:
        print("\nFAILED TESTS:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\nERROR TESTS:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)