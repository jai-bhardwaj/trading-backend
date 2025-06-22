"""
Angel One Instrument Manager
Fetches all available instruments (equities, futures, options, commodities) 
from Angel One's instrument master API based on base symbols from CSV
"""

import asyncio
import logging
import csv
import os
import json
import aiohttp
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class Instrument:
    """Represents a tradeable instrument from Angel One"""
    token: str
    symbol: str
    name: str
    expiry: Optional[str]
    strike: Optional[float]
    lotsize: int
    instrumenttype: str
    exch_seg: str
    tick_size: float
    
    # Derived fields
    base_symbol: str = ""
    option_type: Optional[str] = None
    priority: int = 3
    auto_subscribe: bool = False
    include_derivatives: bool = False

class AngelOneInstrumentManager:
    """Manages instruments from Angel One's master API"""
    
    def __init__(self):
        self.base_symbols: Dict[str, dict] = {}  # From CSV
        self.all_instruments: Dict[str, Instrument] = {}  # All fetched instruments
        self.auto_subscribe_instruments: List[str] = []
        self.instrument_master_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        self.last_fetch_time = None
        self.fetch_interval = timedelta(hours=6)  # Refresh every 6 hours
        
    async def initialize(self):
        """Initialize the instrument manager"""
        logger.info("🚀 Initializing Angel One Instrument Manager...")
        
        # Load base symbols from CSV
        self._load_base_symbols_from_csv()
        
        # Fetch instrument master from Angel One
        await self._fetch_instrument_master()
        
        # Filter and organize instruments
        self._organize_instruments()
        
        logger.info("✅ Angel One Instrument Manager initialized successfully")
        return True
    
    def _load_base_symbols_from_csv(self):
        """Load base symbols from simplified CSV"""
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'subscribed_symbols.csv')
        
        try:
            if os.path.exists(csv_path):
                with open(csv_path, 'r', newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        # Skip comment lines
                        if row['symbol'].startswith('#'):
                            continue
                            
                        symbol = row['symbol'].strip()
                        self.base_symbols[symbol] = {
                            'priority': int(row.get('priority', 3)),
                            'auto_subscribe': row.get('auto_subscribe', 'false').lower() == 'true',
                            'include_derivatives': row.get('include_derivatives', 'false').lower() == 'true'
                        }
                
                logger.info(f"📊 Loaded {len(self.base_symbols)} base symbols from CSV")
            else:
                logger.warning(f"⚠️ CSV file not found at {csv_path}, using fallback symbols")
                self._load_fallback_base_symbols()
                
        except Exception as e:
            logger.error(f"❌ Error loading base symbols from CSV: {e}")
            self._load_fallback_base_symbols()
    
    def _load_fallback_base_symbols(self):
        """Fallback base symbols if CSV loading fails"""
        fallback_symbols = {
            "RELIANCE": {"priority": 1, "auto_subscribe": True, "include_derivatives": True},
            "TCS": {"priority": 1, "auto_subscribe": True, "include_derivatives": True},
            "INFY": {"priority": 1, "auto_subscribe": True, "include_derivatives": True},
            "HDFCBANK": {"priority": 1, "auto_subscribe": True, "include_derivatives": True},
            "NIFTY": {"priority": 1, "auto_subscribe": True, "include_derivatives": True},
            "BANKNIFTY": {"priority": 1, "auto_subscribe": True, "include_derivatives": True},
            "GOLD": {"priority": 1, "auto_subscribe": True, "include_derivatives": True},
            "USDINR": {"priority": 1, "auto_subscribe": True, "include_derivatives": True}
        }
        
        self.base_symbols = fallback_symbols
        logger.info(f"📊 Loaded {len(fallback_symbols)} fallback base symbols")
    
    async def _fetch_instrument_master(self):
        """Fetch instrument master from Angel One API"""
        try:
            logger.info("📡 Fetching instrument master from Angel One API...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.instrument_master_url, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Fetched {len(data)} instruments from Angel One API")
                        self.raw_instruments = data
                        self.last_fetch_time = datetime.now()
                        return True
                    else:
                        logger.error(f"❌ Failed to fetch instrument master: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Error fetching instrument master: {e}")
            # Use demo mode if API fails
            self._create_demo_instruments()
            return False
    
    def _create_demo_instruments(self):
        """Create demo instruments for testing when API is unavailable"""
        logger.info("📊 Creating demo instruments for testing...")
        
        demo_instruments = []
        
        for base_symbol, config in self.base_symbols.items():
            # Create equity instrument
            demo_instruments.append({
                "token": str(hash(f"{base_symbol}_EQ") % 100000),
                "symbol": base_symbol,
                "name": base_symbol,
                "expiry": "",
                "strike": "-1",
                "lotsize": "1",
                "instrumenttype": "EQ",
                "exch_seg": "NSE",
                "tick_size": "0.05"
            })
            
            # Create derivatives if enabled
            if config.get('include_derivatives', False):
                # Future
                demo_instruments.append({
                    "token": str(hash(f"{base_symbol}_FUT") % 100000),
                    "symbol": f"{base_symbol}25JAN",
                    "name": f"{base_symbol} JAN FUT",
                    "expiry": "30JAN2025",
                    "strike": "-1",
                    "lotsize": "50" if base_symbol in ["NIFTY", "BANKNIFTY"] else "1",
                    "instrumenttype": "FUTIDX" if base_symbol in ["NIFTY", "BANKNIFTY"] else "FUTSTK",
                    "exch_seg": "NFO",
                    "tick_size": "0.05"
                })
                
                # Options (ATM strikes)
                if base_symbol == "NIFTY":
                    strikes = [23900, 24000, 24100]
                elif base_symbol == "BANKNIFTY":
                    strikes = [51900, 52000, 52100]
                else:
                    strikes = [100, 200, 300]  # Demo strikes
                
                for strike in strikes:
                    for option_type in ["CE", "PE"]:
                        demo_instruments.append({
                            "token": str(hash(f"{base_symbol}_{strike}_{option_type}") % 100000),
                            "symbol": f"{base_symbol}25JAN{strike}{option_type}",
                            "name": f"{base_symbol} JAN {strike} {option_type}",
                            "expiry": "30JAN2025",
                            "strike": str(strike),
                            "lotsize": "50" if base_symbol in ["NIFTY", "BANKNIFTY"] else "1",
                            "instrumenttype": "OPTIDX" if base_symbol in ["NIFTY", "BANKNIFTY"] else "OPTSTK",
                            "exch_seg": "NFO",
                            "tick_size": "0.05"
                        })
        
        self.raw_instruments = demo_instruments
        logger.info(f"📊 Created {len(demo_instruments)} demo instruments")
    
    def _organize_instruments(self):
        """Organize and filter instruments based on base symbols"""
        logger.info("🔄 Organizing instruments based on base symbols...")
        
        relevant_instruments = []
        base_symbol_set = set(self.base_symbols.keys())
        
        for raw_instrument in self.raw_instruments:
            try:
                # Extract base symbol from instrument
                symbol = raw_instrument.get('symbol', '')
                name = raw_instrument.get('name', '')
                instrument_type = raw_instrument.get('instrumenttype', '')
                
                # Determine base symbol
                base_symbol = self._extract_base_symbol(symbol, name, instrument_type)
                
                # Only include if base symbol is in our list
                if base_symbol in base_symbol_set:
                    config = self.base_symbols[base_symbol]
                    
                    # Check if we should include derivatives
                    if instrument_type in ['EQ']:
                        # Always include equity
                        should_include = True
                    elif instrument_type in ['FUTIDX', 'FUTSTK', 'FUTCOM', 'FUTCUR']:
                        # Include futures if derivatives enabled
                        should_include = config.get('include_derivatives', False)
                    elif instrument_type in ['OPTIDX', 'OPTSTK', 'OPTCOM', 'OPTCUR']:
                        # Include options if derivatives enabled
                        should_include = config.get('include_derivatives', False)
                    else:
                        should_include = True  # Include other types
                    
                    if should_include:
                        instrument = self._create_instrument(raw_instrument, base_symbol, config)
                        relevant_instruments.append(instrument)
                        
                        # Add to auto-subscribe if enabled
                        if config.get('auto_subscribe', False):
                            self.auto_subscribe_instruments.append(instrument.token)
            
            except Exception as e:
                logger.debug(f"Error processing instrument {raw_instrument}: {e}")
                continue
        
        # Store organized instruments
        self.all_instruments = {inst.token: inst for inst in relevant_instruments}
        
        # Count by type
        equity_count = sum(1 for inst in relevant_instruments if inst.instrumenttype == 'EQ')
        futures_count = sum(1 for inst in relevant_instruments if 'FUT' in inst.instrumenttype)
        options_count = sum(1 for inst in relevant_instruments if 'OPT' in inst.instrumenttype)
        
        logger.info(f"📊 Organized {len(relevant_instruments)} relevant instruments:")
        logger.info(f"   • {equity_count} Equities")
        logger.info(f"   • {futures_count} Futures")
        logger.info(f"   • {options_count} Options")
        logger.info(f"   • {len(self.auto_subscribe_instruments)} auto-subscribe")
    
    def _extract_base_symbol(self, symbol: str, name: str, instrument_type: str) -> str:
        """Extract base symbol from instrument symbol"""
        # Remove common suffixes and prefixes
        base = symbol.upper()
        
        # For derivatives, remove expiry and strike info
        if instrument_type in ['FUTIDX', 'FUTSTK', 'OPTIDX', 'OPTSTK']:
            # Remove date patterns like 25JAN, 30JAN2025
            import re
            base = re.sub(r'\d{1,2}[A-Z]{3}\d{0,4}', '', base)
            # Remove strike and option type
            base = re.sub(r'\d+[CP]E$', '', base)
        
        # For commodities, handle MCX naming
        if instrument_type in ['FUTCOM', 'OPTCOM']:
            # MCX symbols often have month codes
            base = re.sub(r'\d{1,2}[A-Z]{3}\d{0,4}', '', base)
        
        # Clean up
        base = base.strip('-_')
        
        return base
    
    def _create_instrument(self, raw_instrument: dict, base_symbol: str, config: dict) -> Instrument:
        """Create Instrument object from raw data"""
        # Parse option type from symbol
        option_type = None
        if raw_instrument.get('instrumenttype', '').startswith('OPT'):
            if raw_instrument.get('symbol', '').endswith('CE'):
                option_type = 'CE'
            elif raw_instrument.get('symbol', '').endswith('PE'):
                option_type = 'PE'
        
        return Instrument(
            token=raw_instrument.get('token', ''),
            symbol=raw_instrument.get('symbol', ''),
            name=raw_instrument.get('name', ''),
            expiry=raw_instrument.get('expiry', ''),
            strike=float(raw_instrument.get('strike', -1)) if raw_instrument.get('strike', '-1') != '-1' else None,
            lotsize=int(raw_instrument.get('lotsize', 1)),
            instrumenttype=raw_instrument.get('instrumenttype', ''),
            exch_seg=raw_instrument.get('exch_seg', ''),
            tick_size=float(raw_instrument.get('tick_size', 0.05)),
            base_symbol=base_symbol,
            option_type=option_type,
            priority=config.get('priority', 3),
            auto_subscribe=config.get('auto_subscribe', False),
            include_derivatives=config.get('include_derivatives', False)
        )
    
    def get_all_instruments(self) -> List[Instrument]:
        """Get all instruments"""
        return list(self.all_instruments.values())
    
    def get_auto_subscribe_instruments(self) -> List[Instrument]:
        """Get instruments that should be auto-subscribed"""
        return [self.all_instruments[token] for token in self.auto_subscribe_instruments if token in self.all_instruments]
    
    def search_instruments(self, query: str, limit: int = 50) -> List[Instrument]:
        """Search instruments by symbol or name"""
        if not query:
            return list(self.all_instruments.values())[:limit]
        
        query = query.upper()
        matches = []
        
        for instrument in self.all_instruments.values():
            if (query in instrument.symbol.upper() or 
                query in instrument.name.upper() or 
                query in instrument.base_symbol.upper()):
                matches.append(instrument)
                if len(matches) >= limit:
                    break
        
        return matches
    
    def get_instruments_by_base_symbol(self, base_symbol: str) -> List[Instrument]:
        """Get all instruments for a base symbol"""
        return [inst for inst in self.all_instruments.values() if inst.base_symbol == base_symbol]
    
    def get_stats(self) -> dict:
        """Get statistics about loaded instruments"""
        instruments = list(self.all_instruments.values())
        
        # Count by type
        type_counts = {}
        exchange_counts = {}
        
        for inst in instruments:
            type_counts[inst.instrumenttype] = type_counts.get(inst.instrumenttype, 0) + 1
            exchange_counts[inst.exch_seg] = exchange_counts.get(inst.exch_seg, 0) + 1
        
        return {
            "total_base_symbols": len(self.base_symbols),
            "total_instruments": len(instruments),
            "auto_subscribe_instruments": len(self.auto_subscribe_instruments),
            "last_fetch_time": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            "instrument_types": type_counts,
            "exchanges": exchange_counts,
            "data_source": "angel_one_instrument_api"
        }

# Global instance
_instrument_manager = None

async def get_instrument_manager() -> AngelOneInstrumentManager:
    """Get the global instrument manager instance"""
    global _instrument_manager
    if _instrument_manager is None:
        _instrument_manager = AngelOneInstrumentManager()
        await _instrument_manager.initialize()
    return _instrument_manager 