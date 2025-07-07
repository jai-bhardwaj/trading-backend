# Instrument Fetcher

This module handles fetching trading instruments from Angel One API and filtering them based on the symbols configuration.

## Features

- **Daily Morning Fetch**: Automatically fetches instruments every morning (6 AM - 10 AM IST)
- **Symbol Filtering**: Filters instruments based on `data/symbols_to_trade.csv`
- **Multiple Instrument Types**: Supports Futures, Options, and Equity instruments
- **Automatic Scheduling**: Uses cron jobs for daily execution

## Files

- `fetcher.py`: Main instrument fetching script
- `data/symbols_to_trade.csv`: Configuration file for symbols to trade
- `data/instruments_*.json`: Fetched instrument data files

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   ```bash
   cp env.template .env
   # Edit .env with your Angel One API credentials
   ```

3. **Setup Cron Job**:
   ```bash
   python scripts/schedule_instrument_fetch.py install
   ```

## Symbols CSV Format

The `data/symbols_to_trade.csv` file should contain:

| Column | Type | Description |
|--------|------|-------------|
| symbol_name | string | NSE symbol name (e.g., RELIANCE, TCS) |
| futures | boolean | Enable futures trading for this symbol |
| options | boolean | Enable options trading for this symbol |
| equity | boolean | Enable equity trading for this symbol |
| enabled | boolean | Overall enable/disable for this symbol |

## Usage

### Manual Run
```bash
python instruments/fetcher.py
```

### Schedule Management
```bash
# Install cron job (runs daily at 6:30 AM IST)
python scripts/schedule_instrument_fetch.py install

# Remove cron job
python scripts/schedule_instrument_fetch.py remove

# List current cron jobs
python scripts/schedule_instrument_fetch.py list
```

## Output Files

- `data/instruments_YYYYMMDD_HHMMSS.json`: Timestamped instrument data
- `data/instruments_latest.json`: Latest instrument data (always updated)

## Timezone

The system uses IST (Indian Standard Time, UTC+5:30) for all scheduling and timestamps. 