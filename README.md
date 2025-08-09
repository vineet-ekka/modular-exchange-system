# Binance Funding Rate Dashboard

A professional cryptocurrency funding rate tracking system focused exclusively on Binance perpetual futures, with real-time dashboard and historical data capabilities.

## 🚀 One-Command Quick Start

```bash
# Simplest method - starts everything automatically
python start.py

# Or on Windows, just double-click:
start.bat
```

This automatically:
1. Checks prerequisites (Python, Node, Docker)
2. Starts PostgreSQL database
3. Installs npm dependencies (if needed)
4. Starts API server
5. Starts React dashboard  
6. Starts data collector with 30-second updates
7. Opens browser automatically

## 🎯 System Overview

### What It Does
- **Real-time Collection**: Fetches Binance funding rates every 30 seconds
- **Asset-Based View**: Shows ~200 unique assets (BTC, ETH, SOL, etc.)
- **Historical Data**: Optional 30-day historical funding rate tracking
- **Professional Dashboard**: Clean grid interface inspired by CoinGlass
- **APR Calculations**: Automatic annualized percentage rate calculations

### Architecture
- **Data Source**: Binance USD-M and COIN-M perpetual futures
- **Database**: PostgreSQL via Docker
- **Backend**: FastAPI with optimized endpoints
- **Frontend**: React with TypeScript and Tailwind CSS
- **Update Cycle**: 30-second real-time refresh

## 📊 Binance Coverage

| Market Type | Contracts | Funding Interval | Features |
|------------|-----------|------------------|----------|
| USD-M | ~300+ | 8 hours | USDT-margined perpetuals |
| COIN-M | ~50+ | 8 hours | Coin-margined perpetuals |

**Total**: ~350+ perpetual contracts across ~200 unique assets

## 🛠 Installation & Setup

### Prerequisites
- **Python 3.8+** - [Download](https://python.org)
- **Node.js 16+** - [Download](https://nodejs.org)  
- **Docker Desktop** - [Download](https://docker.com)

### Manual Setup (if not using start.py)

#### 1. Clone Repository
```bash
git clone https://github.com/yourusername/modular-exchange-system.git
cd modular-exchange-system
```

#### 2. Install Dependencies
```bash
# Python dependencies
pip install -r requirements.txt

# Dashboard dependencies
cd dashboard && npm install && cd ..
```

#### 3. Start PostgreSQL with Docker
```bash
docker-compose up -d

# Verify it's running
docker ps  # Should show exchange_postgres
```

#### 4. Configure Environment
Create `.env` file:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
```

#### 5. Start Services
```bash
# API Server (Terminal 1)
python api.py

# Dashboard (Terminal 2)
cd dashboard && npm start

# Data Collector (Terminal 3)
python main.py --loop --interval 30 --quiet
```

## 📈 Dashboard Features

### Asset Grid View
- **Single Row Per Asset**: All funding info at a glance
- **Color Coding**: Green (positive), Red (negative)
- **Sorting**: Click any column header
- **Search**: Filter assets by name
- **Real-time Updates**: Auto-refresh every 30 seconds

### Historical View (Click any asset)
- **Time Range Selection**: 1D, 7D, 30D views
- **Interactive Charts**: Funding rate trends over time
- **Data Export**: CSV download capability
- **Statistics**: Average, min, max rates

## 🔧 Configuration

### Binance-Only Settings (`config/settings.py`)
```python
EXCHANGES = {
    "binance": True,      # Only Binance enabled
    "backpack": False,
    "kucoin": False,
    "deribit": False,
    "kraken": False
}
```

## 📊 Historical Data (Optional)

### Initial 30-Day Backfill
```bash
python scripts/binance_historical_backfill.py
```

### Continuous Updates
```bash
python scripts/historical_updater.py
```

## 🌐 Access Points

- **Dashboard**: http://localhost:3000
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

## 🗃 Database Management

### Check Database Status
```bash
python check_database.py
```

### Clear All Data
```bash
python clear_database.py --quick
```

## 🐛 Troubleshooting

### No Data Showing
1. Ensure PostgreSQL is running: `docker ps`
2. Check data collection: `python main.py`
3. Verify API: http://localhost:8000/api/funding-rates-grid

### Port Already in Use
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (Windows)
taskkill /PID <process_id> /F
```

### Docker Not Running
Start Docker Desktop first, then run `docker-compose up -d`

## 📁 Project Structure

```
modular-exchange-system/
├── main.py                    # Data collector
├── api.py                     # FastAPI backend
├── start.py                   # One-command launcher
├── config/
│   └── settings.py           # Configuration
├── exchanges/
│   └── binance_exchange.py   # Binance integration
├── dashboard/                 # React frontend
│   └── src/
│       └── components/
│           └── Grid/         # Asset grid components
├── database/
│   └── postgres_manager.py   # Database operations
├── docker-compose.yml         # PostgreSQL setup
└── scripts/
    ├── binance_historical_backfill.py  # Historical data
    └── historical_updater.py           # Continuous updates
```

## 🚦 System Status Indicators

- **Data Collection**: Look for "OK" messages in collector terminal
- **API Health**: Check http://localhost:8000/api/health
- **Database**: Green "Connected" in dashboard header
- **Update Time**: Shows last refresh in dashboard

## 📈 Data Schema

```python
{
    'exchange': 'Binance',
    'symbol': 'BTCUSDT',
    'base_asset': 'BTC',
    'funding_rate': 0.0001,    # Current rate
    'apr': 10.95,              # Annualized rate
    'mark_price': 45000.00,
    'funding_interval_hours': 8
}
```

## ⚡ Performance

- **Data Points**: ~350 Binance contracts
- **Refresh Rate**: Every 30 seconds
- **API Response**: <100ms typical
- **Database Write**: <2 seconds for full update
- **Dashboard Load**: ~2 seconds initial

## 🔒 Security Notes

- Default passwords are for development only
- Never commit `.env` file to version control
- Use environment variables for production

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Support

For issues or questions:
- Check the [docs/archive](docs/archive) folder for detailed documentation
- Review [dashboard-plan.md](docs/archive/dashboard-plan.md) for implementation details
- See [handoff-summary.md](docs/archive/handoff-summary.md) for development history

---

**Quick Commands Reference**
```bash
# Start everything
python start.py

# Data collection only
python main.py --loop --interval 30 --quiet

# Check database
python check_database.py

# Clear database
python clear_database.py --quick

# Historical backfill
python scripts/binance_historical_backfill.py
```