# 📊 Instrument Manager Configuration Guide

The Angel One instrument manager now supports **fully configurable** instrument loading with smart sorting and filtering. You can load anywhere from 10 instruments to all 120,000+ instruments based on your needs.

## 🎛️ Configuration Options

Add these environment variables to your `.env` file to configure instrument loading:

### Basic Configuration
```bash
# Maximum number of equity instruments to load (default: 1000)
MAX_EQUITY_INSTRUMENTS=1000

# Maximum number of derivatives instruments to load (default: 500) 
MAX_DERIVATIVES_INSTRUMENTS=500

# Maximum total instruments when using LOAD_ALL_INSTRUMENTS=true (default: 2000)
MAX_TOTAL_INSTRUMENTS=2000

# Load all instruments instead of separating by asset class (default: false)
LOAD_ALL_INSTRUMENTS=false
```

## 📈 Usage Examples

### 1. Conservative Setup (Good for Testing)
```bash
MAX_EQUITY_INSTRUMENTS=50
MAX_DERIVATIVES_INSTRUMENTS=20
LOAD_ALL_INSTRUMENTS=false
```
**Result**: 70 total instruments (50 equity + 20 derivatives)

### 2. Balanced Setup (Recommended for Production)
```bash
MAX_EQUITY_INSTRUMENTS=1000
MAX_DERIVATIVES_INSTRUMENTS=500
LOAD_ALL_INSTRUMENTS=false
```
**Result**: 1,500 total instruments (1,000 equity + 500 derivatives)

### 3. Comprehensive Setup (For Advanced Strategies)
```bash
MAX_EQUITY_INSTRUMENTS=5000
MAX_DERIVATIVES_INSTRUMENTS=2000
LOAD_ALL_INSTRUMENTS=false
```
**Result**: 7,000 total instruments (5,000 equity + 2,000 derivatives)

### 4. Load Everything Setup (Maximum Coverage)
```bash
LOAD_ALL_INSTRUMENTS=true
MAX_TOTAL_INSTRUMENTS=10000
```
**Result**: Up to 10,000 instruments of all types mixed together

### 5. Load Absolutely Everything (All Angel One Data)
```bash
LOAD_ALL_INSTRUMENTS=true
MAX_TOTAL_INSTRUMENTS=150000
```
**Result**: All ~120,000+ instruments from Angel One

## 🎯 Smart Sorting & Prioritization

The system automatically sorts instruments by quality:

### Equity Instruments Priority:
1. **Major Nifty 50 stocks** (RELIANCE, TCS, INFY, etc.) - sorted by market importance
2. **All other stocks** - sorted alphabetically

### Derivatives Instruments Priority:
1. **Index Futures** (NIFTY, BANKNIFTY) - highest priority
2. **Stock Futures** - medium priority  
3. **Options** - lower priority

## ⚡ Performance Considerations

| Configuration | Instruments | Memory Usage | Load Time | Recommended For |
|---------------|-------------|--------------|-----------|-----------------|
| Conservative | 50-100 | Low | <1s | Testing, Demo |
| Balanced | 1,000-2,000 | Medium | 2-3s | Production |
| Comprehensive | 5,000-10,000 | High | 5-10s | Advanced Trading |
| Everything | 100,000+ | Very High | 30-60s | Research, Backtesting |

## 🔧 Dynamic Configuration

You can change these settings **without code changes**:

### Method 1: Environment Variables
```bash
export MAX_EQUITY_INSTRUMENTS=200
export MAX_DERIVATIVES_INSTRUMENTS=100
python main.py
```

### Method 2: Runtime Override
```bash
MAX_EQUITY_INSTRUMENTS=200 MAX_DERIVATIVES_INSTRUMENTS=100 python main.py
```

### Method 3: Update .env File
```bash
# Edit .env file
MAX_EQUITY_INSTRUMENTS=200
MAX_DERIVATIVES_INSTRUMENTS=100

# Restart application
python main.py
```

## 📊 Real-World Examples

### Day Trading Setup
```bash
# Focus on most liquid instruments
MAX_EQUITY_INSTRUMENTS=100
MAX_DERIVATIVES_INSTRUMENTS=50
```

### Swing Trading Setup  
```bash
# Broader coverage for opportunities
MAX_EQUITY_INSTRUMENTS=1000
MAX_DERIVATIVES_INSTRUMENTS=300
```

### Arbitrage Strategy
```bash
# Need comprehensive coverage
LOAD_ALL_INSTRUMENTS=true
MAX_TOTAL_INSTRUMENTS=20000
```

### Research & Backtesting
```bash
# Load everything for complete analysis
LOAD_ALL_INSTRUMENTS=true
MAX_TOTAL_INSTRUMENTS=150000
```

## 🚀 Benefits of New System

✅ **Fully Configurable** - No more hard-coded limits  
✅ **Smart Sorting** - Priority-based instrument selection  
✅ **Performance Optimized** - Choose your performance vs coverage trade-off  
✅ **Runtime Configurable** - Change settings without code changes  
✅ **Scales from 10 to 120,000+ instruments** - Works for any use case  
✅ **Real Angel One Data** - Always uses live instrument data from Angel One API  

## 🎯 Quick Start

1. **Copy the configuration you want** from the examples above
2. **Add to your .env file** or set as environment variables
3. **Restart the trading engine** to apply new settings
4. **Monitor logs** to see instrument loading progress

The system will automatically fetch, sort, and limit instruments according to your configuration! 🎉 