# Symbol Configuration with Auto-Derivatives Fetching

## Overview

The trading engine now uses a **simplified CSV approach** where you only specify **base symbols**, and the system automatically fetches **all available derivatives** (futures, options, commodities, currencies) from Angel One's instrument master API. This provides:

- **Zero maintenance** of derivative details (expiry, strikes, etc.)
- **Automatic discovery** of all available instruments
- **Real-time updates** from Angel One's comprehensive instrument database
- **Perfect separation of concerns** - configuration vs. data fetching

## Configuration File

**File:** `config/subscribed_symbols.csv`

### Simplified CSV Format

```csv
symbol,priority,auto_subscribe,include_derivatives
# EQUITY SYMBOLS - System auto-fetches all derivatives
RELIANCE,1,true,true
TCS,1,true,true
NIFTY,1,true,true
BANKNIFTY,1,true,true

# COMMODITY SYMBOLS - System auto-fetches all derivatives  
GOLD,1,true,true
SILVER,1,true,true
USDINR,1,true,true
```

### Column Descriptions

- **symbol**: Base symbol (e.g., RELIANCE, NIFTY, GOLD, USDINR)
- **priority**: Priority level (1=High, 2=Medium, 3=Low)
- **auto_subscribe**: Whether to automatically subscribe for real-time data (true/false)
- **include_derivatives**: Whether to fetch and include all derivatives for this symbol (true/false)

## How It Works

### 1. Base Symbol Input
You specify only the base symbols you're interested in (e.g., `RELIANCE`, `NIFTY`, `GOLD`)

### 2. Automatic Instrument Discovery
The system connects to Angel One's instrument master API and automatically discovers:
- **Equity Cash**: RELIANCE (NSE)
- **Stock Futures**: RELIANCE25JAN, RELIANCE25FEB, etc.
- **Stock Options**: RELIANCE25JAN2450CE, RELIANCE25JAN2450PE, etc.
- **Index Futures**: NIFTY25JAN, BANKNIFTY25JAN, etc.
- **Index Options**: NIFTY25JAN24000CE, NIFTY25JAN24000PE, etc.
- **Commodity Futures**: GOLD25FEB, SILVER25MAR, etc.
- **Commodity Options**: GOLD25JAN77000CE, GOLD25JAN77000PE, etc.
- **Currency Futures**: USDINR25JAN, EURINR25JAN, etc.
- **Currency Options**: USDINR25JAN85.00CE, USDINR25JAN85.00PE, etc.

### 3. Intelligent Filtering
- If `include_derivatives=true`: Fetches ALL available instruments for that base symbol
- If `include_derivatives=false`: Fetches only the base equity/commodity/currency
- Automatically handles expiry dates, strike prices, and option types

### 4. Real-time Data
- Auto-subscribes to instruments based on `auto_subscribe` setting
- Provides real-time tick data for all discovered instruments
- Handles different pricing formats (equity, futures, options, currencies)

## Supported Asset Classes

The system automatically discovers instruments across:

### Equities (NSE)
- **Cash Market**: Direct equity trading
- **Futures**: Stock futures with various expiries
- **Options**: Call and Put options with multiple strikes

### Indices (NFO)
- **Index Futures**: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY, etc.
- **Index Options**: Comprehensive strike coverage for all major indices

### Commodities (MCX)
- **Precious Metals**: GOLD, SILVER with futures and options
- **Energy**: CRUDEOIL, NATURALGAS with derivatives
- **Base Metals**: COPPER, ZINC, ALUMINIUM, NICKEL, LEAD

### Currencies (CDS)
- **Major Pairs**: USDINR, EURINR, GBPINR, JPYINR
- **Futures and Options**: Available for all major currency pairs

### Agricultural (NCDEX)
- **Commodities**: WHEAT, RICE, SUGAR, COTTON, SOYBEAN
- **Spices**: TURMERIC, CARDAMOM, PEPPER

## API Endpoints

### View All Discovered Instruments

```bash
GET /admin/market-data/csv-config
```

Returns all base symbols and their discovered instruments with full metadata.

### Search Instruments

```bash
GET /admin/market-data/search-symbols?query=RELIANCE&limit=50
```

Search across all discovered instruments by symbol, name, or base symbol.

### View Auto-Subscribe Instruments

```bash
GET /admin/market-data/auto-subscribe-symbols
```

Returns instruments that are auto-subscribed with current market data.

### Real-time Status

```bash
GET /admin/market-data/realtime-status
```

Shows comprehensive statistics including instrument counts by type and exchange.

## Configuration Examples

### High-Priority Stocks with Full Derivatives
```csv
RELIANCE,1,true,true
TCS,1,true,true
HDFCBANK,1,true,true
```
*Result*: Equity + All futures + All options for these stocks

### Index Trading Focus
```csv
NIFTY,1,true,true
BANKNIFTY,1,true,true
FINNIFTY,2,true,true
```
*Result*: Index futures + Comprehensive options chain

### Commodity Trading
```csv
GOLD,1,true,true
SILVER,1,true,true
CRUDEOIL,2,true,true
```
*Result*: Commodity futures + Options (where available)

### Equity Only (No Derivatives)
```csv
COALINDIA,3,true,false
DRREDDY,3,true,false
```
*Result*: Only equity cash instruments

## Benefits

### 1. **Zero Maintenance**
- No need to manually track expiry dates
- No need to specify strike prices
- No need to update derivative symbols

### 2. **Comprehensive Coverage**
- Automatically discovers ALL available instruments
- Includes new derivatives as they become available
- Covers all exchanges (NSE, NFO, MCX, CDS, BFO, NCDEX)

### 3. **Intelligent Organization**
- Groups instruments by base symbol
- Maintains metadata for each instrument type
- Provides proper categorization and filtering

### 4. **Real-time Updates**
- Fetches latest instrument master from Angel One
- Refreshes instrument list periodically
- Handles new listings automatically

### 5. **Perfect Separation of Concerns**
- **Configuration**: Simple base symbols in CSV
- **Data Fetching**: Automated via Angel One API
- **Real-time Data**: Handled by market data manager

## Current Configuration

- **Total Base Symbols**: 60+ across all asset classes
- **Auto-Discovered Instruments**: 500+ instruments automatically fetched
- **Exchanges Covered**: NSE, NFO, MCX, CDS, BFO, NCDEX
- **Asset Classes**: Equities, Index Derivatives, Commodities, Currencies, Agricultural
- **Auto-Subscribe**: Configurable per base symbol
- **Update Frequency**: Real-time via Angel One instrument master API

## Monitoring

The system provides comprehensive monitoring:
- **Instrument Discovery**: Track how many instruments are discovered per base symbol
- **API Health**: Monitor Angel One instrument master API connectivity
- **Real-time Data**: Track tick data flow across all instrument types
- **Performance**: Monitor system performance with large instrument sets 