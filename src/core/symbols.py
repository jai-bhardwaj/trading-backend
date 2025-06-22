"""
Enterprise Symbol Management System
Handles CSV-based symbol configuration with Angel One instrument master API
Supports all instrument types: Cash, Derivatives, Commodities, Currency
"""

import asyncio
import logging
import pandas as pd
import aiohttp
import json
import os
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)

class InstrumentType(Enum):
    EQUITY = "EQ"
    FUTURES = "FUT"
    OPTIONS = "OPT"
    COMMODITY = "COM"
    CURRENCY = "CUR"
    BONDS = "BONDS"

@dataclass
class SymbolInfo:
    """Complete symbol information from Angel One"""
    symbol: str
    token: str
    instrument_type: InstrumentType
    exchange: str
    lot_size: int
    tick_size: float
    expiry: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None  # CE/PE for options

class EnterpriseSymbolManager:
    """
    Enterprise-grade symbol management for 500+ users
    Memory efficient, fast lookups, auto-refresh
    """
    
    def __init__(self, csv_path: str = "config/trading_symbols.csv"):
        self.csv_path = csv_path
        self.symbols: Dict[str, SymbolInfo] = {}
        self.symbol_by_token: Dict[str, SymbolInfo] = {}
        self.exchanges = ["NSE", "BSE", "NFO", "MCX", "CDS"]
        
        # Caching and performance
        self.last_refresh = None
        self.refresh_interval = timedelta(hours=6)  # Refresh every 6 hours
        self.session = None
        
        # Angel One instrument master URLs
        self.instrument_urls = {
            "NSE": "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",
            "BSE": "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",
            "NFO": "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",
            "MCX": "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        }
        
        # Statistics
        self.total_symbols_loaded = 0
        self.load_errors = 0
    
    async def initialize(self):
        """Initialize symbol manager with CSV and instrument data"""
        logger.info("🔍 Initializing Enterprise Symbol Manager...")
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            connector=aiohttp.TCPConnector(limit=20)
        )
        
        # Step 1: Load symbols from CSV
        await self._load_symbols_from_csv()
        
        # Step 2: Enrich with Angel One instrument data
        await self._refresh_instrument_data()
        
        logger.info(f"✅ Symbol Manager initialized: {len(self.symbols)} symbols loaded")
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        logger.info("🔍 Symbol Manager shutdown complete")
    
    async def _load_symbols_from_csv(self):
        """Load customizable symbols from CSV"""
        try:
            if not os.path.exists(self.csv_path):
                # Create default CSV if doesn't exist
                await self._create_default_csv()
            
            df = pd.read_csv(self.csv_path)
            logger.info(f"📊 Loaded {len(df)} symbols from CSV: {self.csv_path}")
            
            # Validate CSV format
            required_columns = ['symbol', 'exchange', 'instrument_type', 'enabled']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"CSV must contain columns: {required_columns}")
            
            # Filter enabled symbols
            enabled_symbols = df[df['enabled'] == True]
            self.csv_symbols = enabled_symbols.to_dict('records')
            
            logger.info(f"✅ {len(self.csv_symbols)} enabled symbols loaded from CSV")
            
        except Exception as e:
            logger.error(f"❌ Error loading CSV symbols: {e}")
            self.load_errors += 1
            # Fallback to default symbols
            await self._create_default_csv()
    
    async def _create_default_csv(self):
        """Create default trading symbols CSV"""
        default_symbols = [
            # Major Stocks
            {"symbol": "RELIANCE", "exchange": "NSE", "instrument_type": "EQ", "enabled": True, "category": "large_cap"},
            {"symbol": "TCS", "exchange": "NSE", "instrument_type": "EQ", "enabled": True, "category": "large_cap"},
            {"symbol": "INFY", "exchange": "NSE", "instrument_type": "EQ", "enabled": True, "category": "large_cap"},
            {"symbol": "HDFC", "exchange": "NSE", "instrument_type": "EQ", "enabled": True, "category": "large_cap"},
            {"symbol": "ICICIBANK", "exchange": "NSE", "instrument_type": "EQ", "enabled": True, "category": "large_cap"},
            {"symbol": "HDFCBANK", "exchange": "NSE", "instrument_type": "EQ", "enabled": True, "category": "large_cap"},
            {"symbol": "WIPRO", "exchange": "NSE", "instrument_type": "EQ", "enabled": True, "category": "large_cap"},
            {"symbol": "BHARTIARTL", "exchange": "NSE", "instrument_type": "EQ", "enabled": True, "category": "large_cap"},
            {"symbol": "ITC", "exchange": "NSE", "instrument_type": "EQ", "enabled": True, "category": "large_cap"},
            {"symbol": "SBIN", "exchange": "NSE", "instrument_type": "EQ", "enabled": True, "category": "large_cap"},
            
            # Index Futures
            {"symbol": "NIFTY", "exchange": "NFO", "instrument_type": "FUT", "enabled": True, "category": "index_futures"},
            {"symbol": "BANKNIFTY", "exchange": "NFO", "instrument_type": "FUT", "enabled": True, "category": "index_futures"},
            
            # Popular Options (weekly/monthly)
            {"symbol": "NIFTY", "exchange": "NFO", "instrument_type": "OPT", "enabled": True, "category": "index_options"},
            {"symbol": "BANKNIFTY", "exchange": "NFO", "instrument_type": "OPT", "enabled": True, "category": "index_options"},
            
            # Commodities
            {"symbol": "GOLD", "exchange": "MCX", "instrument_type": "FUT", "enabled": False, "category": "commodities"},
            {"symbol": "SILVER", "exchange": "MCX", "instrument_type": "FUT", "enabled": False, "category": "commodities"},
            {"symbol": "CRUDE", "exchange": "MCX", "instrument_type": "FUT", "enabled": False, "category": "commodities"},
        ]
        
        df = pd.DataFrame(default_symbols)
        
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        
        df.to_csv(self.csv_path, index=False)
        logger.info(f"📝 Created default symbols CSV: {self.csv_path}")
        
        self.csv_symbols = [s for s in default_symbols if s['enabled']]
    
    async def _refresh_instrument_data(self):
        """Refresh instrument data from Angel One API"""
        try:
            logger.info("🔄 Refreshing instrument data from Angel One...")
            
            # Download Angel One instrument master
            instrument_data = await self._download_instrument_master()
            
            if not instrument_data:
                logger.error("❌ Failed to download instrument data")
                return
            
            # Process each CSV symbol
            for csv_symbol in self.csv_symbols:
                symbol_info = await self._find_symbol_in_instruments(
                    csv_symbol, instrument_data
                )
                
                if symbol_info:
                    self.symbols[symbol_info.symbol] = symbol_info
                    self.symbol_by_token[symbol_info.token] = symbol_info
                    self.total_symbols_loaded += 1
                else:
                    logger.warning(f"⚠️ Symbol not found in instruments: {csv_symbol['symbol']}")
                    self.load_errors += 1
            
            self.last_refresh = datetime.now()
            logger.info(f"✅ Instrument refresh complete: {self.total_symbols_loaded} symbols")
            
        except Exception as e:
            logger.error(f"❌ Error refreshing instruments: {e}")
            self.load_errors += 1
    
    async def _download_instrument_master(self) -> Optional[List[Dict]]:
        """Download Angel One instrument master file"""
        try:
            # Use the main URL for all instruments
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"📥 Downloaded {len(data)} instruments from Angel One")
                    return data
                else:
                    logger.error(f"❌ Failed to download instruments: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error downloading instrument master: {e}")
            return None
    
    async def _find_symbol_in_instruments(self, csv_symbol: Dict, instruments: List[Dict]) -> Optional[SymbolInfo]:
        """Find symbol in Angel One instrument data"""
        try:
            symbol = csv_symbol['symbol']
            exchange = csv_symbol['exchange']
            instrument_type = csv_symbol['instrument_type']
            
            # Search for matching instrument
            for instrument in instruments:
                if (instrument.get('name') == symbol and 
                    instrument.get('exch_seg') == exchange and
                    instrument.get('instrumenttype') == instrument_type):
                    
                    return SymbolInfo(
                        symbol=symbol,
                        token=str(instrument.get('token', '')),
                        instrument_type=InstrumentType(instrument_type),
                        exchange=exchange,
                        lot_size=int(instrument.get('lotsize', 1)),
                        tick_size=float(instrument.get('tick_size', 0.05)),
                        expiry=instrument.get('expiry'),
                        strike=float(instrument.get('strike', 0)) if instrument.get('strike') else None,
                        option_type=instrument.get('option_type')
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding symbol {csv_symbol}: {e}")
            return None
    
    async def get_symbol_token(self, symbol: str, exchange: str = "NSE") -> Optional[str]:
        """Get token for symbol with auto-refresh"""
        # Check if refresh needed
        if (self.last_refresh is None or 
            datetime.now() - self.last_refresh > self.refresh_interval):
            await self._refresh_instrument_data()
        
        # Try exact match first
        symbol_key = f"{symbol}_{exchange}"
        if symbol in self.symbols:
            return self.symbols[symbol].token
        
        # Try case-insensitive search
        for sym_info in self.symbols.values():
            if (sym_info.symbol.upper() == symbol.upper() and 
                sym_info.exchange == exchange):
                return sym_info.token
        
        logger.warning(f"⚠️ Token not found for symbol: {symbol} on {exchange}")
        return None
    
    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Get complete symbol information"""
        return self.symbols.get(symbol)
    
    def get_all_symbols(self, exchange: Optional[str] = None, 
                       instrument_type: Optional[InstrumentType] = None) -> List[SymbolInfo]:
        """Get all symbols with optional filters"""
        symbols = list(self.symbols.values())
        
        if exchange:
            symbols = [s for s in symbols if s.exchange == exchange]
        
        if instrument_type:
            symbols = [s for s in symbols if s.instrument_type == instrument_type]
        
        return symbols
    
    async def add_symbol(self, symbol: str, exchange: str, instrument_type: str) -> bool:
        """Dynamically add symbol to tracking"""
        try:
            # Add to CSV (append mode)
            new_row = {
                'symbol': symbol,
                'exchange': exchange, 
                'instrument_type': instrument_type,
                'enabled': True,
                'category': 'dynamic'
            }
            
            df = pd.read_csv(self.csv_path)
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(self.csv_path, index=False)
            
            # Refresh instruments to pick up new symbol
            await self._refresh_instrument_data()
            
            logger.info(f"✅ Added symbol: {symbol} on {exchange}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding symbol {symbol}: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get symbol manager statistics"""
        exchange_count = {}
        type_count = {}
        
        for symbol_info in self.symbols.values():
            exchange_count[symbol_info.exchange] = exchange_count.get(symbol_info.exchange, 0) + 1
            type_count[symbol_info.instrument_type.value] = type_count.get(symbol_info.instrument_type.value, 0) + 1
        
        return {
            'total_symbols': len(self.symbols),
            'total_loaded': self.total_symbols_loaded,
            'load_errors': self.load_errors,
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'exchanges': exchange_count,
            'instrument_types': type_count,
            'csv_path': self.csv_path
        }

# Global symbol manager instance
_symbol_manager = None

async def get_symbol_manager() -> EnterpriseSymbolManager:
    """Get global symbol manager instance"""
    global _symbol_manager
    if _symbol_manager is None:
        _symbol_manager = EnterpriseSymbolManager()
        await _symbol_manager.initialize()
    return _symbol_manager 