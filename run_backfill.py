#!/usr/bin/env python3
"""
Run Historical Backfill - Wrapper Script
========================================
This script properly sets up the path and runs the backfill.
"""

import sys
from pathlib import Path

# Add parent directory to path (for imports to work)
sys.path.append(str(Path(__file__).parent))

# Now import and run the backfill
from scripts.binance_historical_backfill import main

if __name__ == "__main__":
    sys.exit(main())