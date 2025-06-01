#!/usr/bin/env python3
"""
Instrument Manager
Fetches and manages trading instruments from AngelOne API
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
import aiohttp
import os
from dotenv import load_dotenv
import pyotp
import base64
from collections import defaultdict

from app.database import DatabaseManager
from app.models.base import AssetClass, Strategy, StrategyStatus
from sqlalchemy import select, text

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class Instrument:
    """Trading instrument data"""
    symbol: str
    token: str
    name: str
    exchange: str
    asset_class: AssetClass
    lot_size: int = 1
    tick_size: float = 0.05
    instrument_type: str = "EQ"
    expiry: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None

class InstrumentManager:
    """
    Instrument Manager
    
    Responsibilities:
    1. Fetch instruments from AngelOne API
    2. Filter and categorize by asset class
    3. Update strategy symbol lists dynamically
    4. Cache instruments for performance
    5. Handle instrument updates
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.instruments: Dict[AssetClass, List[Instrument]] = {}
        self.last_updated: Optional[datetime] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
        # AngelOne API configuration
        self.api_key = os.getenv("ANGELONE_API_KEY_INSTRUMENTS", "your_api_key")
        self.client_id = os.getenv("ANGELONE_CLIENT_ID_INSTRUMENTS", "your_client_id") 
        self.password = os.getenv("ANGELONE_PASSWORD_INSTRUMENTS", "your_password")
        self.totp_secret = os.getenv("ANGELONE_TOTP_SECRET_INSTRUMENTS", "your_totp_secret")
        
        # API endpoints
        self.base_url = "https://apiconnect.angelone.in"
        self.auth_token: Optional[str] = None
        
        # Filtering configuration
        self.equity_filters = {
            'exchanges': ['NSE', 'BSE'],
            'instrument_types': ['EQ'],
            'min_market_cap': 1000,  # Crores
            'exclude_patterns': ['BE', 'BZ', 'IL', 'BL']  # Exclude illiquid segments
        }
        
        self.derivatives_filters = {
            'exchanges': ['NFO'],
            'instrument_types': ['FUTSTK', 'OPTIDX', 'OPTSTK'],
            'min_oi': 100  # Minimum open interest
        }
    
    async def initialize(self):
        """Initialize instrument manager"""
        logger.info("📊 Initializing Instrument Manager")
        
        try:
            self.session = aiohttp.ClientSession()
            
            # Try to authenticate with AngelOne
            await self.authenticate()
            
            # Fetch instruments
            await self.fetch_instruments()
            
            logger.info("✅ Instrument Manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Instrument Manager: {e}")
            # Fallback to demo instruments
            await self.load_demo_instruments()
    
    async def stop(self):
        """Stop instrument manager"""
        if self.session:
            await self.session.close()
        logger.info("🏁 Instrument Manager stopped")
    
    async def authenticate(self):
        """Authenticate with AngelOne API"""
        try:
            # Generate TOTP if secret is provided
            totp_value = None
            if self.totp_secret and self.totp_secret != "your_totp_secret":
                try:
                    # Validate and prepare TOTP secret
                    totp_secret = self._prepare_totp_secret(self.totp_secret)
                    if totp_secret:
                        totp = pyotp.TOTP(totp_secret)
                        totp_value = totp.now()
                    else:
                        logger.warning("⚠️ Invalid TOTP secret format, proceeding without TOTP")
                except Exception as e:
                    logger.warning(f"⚠️ TOTP generation failed: {e}, proceeding without TOTP")
            
            login_data = {
                "clientcode": self.client_id,
                "password": self.password,
                "totp": totp_value
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "aa:bb:cc:dd:ee:ff",
                "X-PrivateKey": self.api_key
            }
            
            async with self.session.post(
                f"{self.base_url}/rest/auth/angelbroking/user/v1/loginByPassword",
                json=login_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status"):
                        self.auth_token = data["data"]["jwtToken"]
                        logger.info("✅ AngelOne authentication successful")
                        return True
                    else:
                        logger.error(f"❌ AngelOne auth failed: {data.get('message')}")
                else:
                    logger.error(f"❌ AngelOne auth HTTP error: {response.status}")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ AngelOne authentication error: {e}")
            return False
    
    def _prepare_totp_secret(self, secret: str) -> Optional[str]:
        """Prepare TOTP secret for pyotp, handling various formats"""
        try:
            # If it's already a valid Base32 string, use it directly
            try:
                base64.b32decode(secret.upper())
                return secret.upper()
            except Exception:
                pass
            
            # For test environments, generate a valid Base32 secret
            if secret.lower() in ['test_secret', 'test', 'demo']:
                # Generate a valid Base32 test secret
                return base64.b32encode(f"TEST{secret.upper()}".ljust(16, '0')[:16].encode()).decode()
            
            # Try to encode as Base32 if it's a regular string
            if len(secret) >= 10:
                padded_secret = secret.ljust(16, '0')[:16]
                return base64.b32encode(padded_secret.encode()).decode()
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to prepare TOTP secret: {e}")
            return None
    
    async def fetch_instruments(self):
        """Fetch instruments from AngelOne API"""
        try:
            if not self.auth_token:
                logger.warning("⚠️ No auth token, using demo instruments")
                await self.load_demo_instruments()
                return
            
            # Fetch instrument master
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB"
            }
            
            # Download instrument file
            async with self.session.get(
                f"{self.base_url}/rest/secure/angelbroking/order/v1/getInstrumentMaster",
                headers=headers
            ) as response:
                if response.status == 200:
                    instruments_data = await response.text()
                    if not instruments_data or len(instruments_data) < 100:
                        logger.warning("⚠️ Empty/invalid response from AngelOne API, using demo instruments")
                        await self.load_demo_instruments()
                    else:
                        await self.parse_instruments(instruments_data)
                        logger.info("✅ Instruments fetched from AngelOne")
                else:
                    logger.error(f"❌ Failed to fetch instruments: {response.status}")
                    await self.load_demo_instruments()
        
        except Exception as e:
            logger.error(f"❌ Error fetching instruments: {e}")
            await self.load_demo_instruments()
    
    async def parse_instruments(self, instruments_data: str):
        """Parse instruments data from AngelOne"""
        try:
            lines = instruments_data.strip().split('\n')
            if not lines or len(lines) <= 1:
                logger.warning("⚠️ Empty or invalid instruments data from API, falling back to demo")
                await self.load_demo_instruments()
                return
            
            # Parse header
            header = lines[0].split(',')
            
            equity_instruments = []
            derivatives_instruments = []
            
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                fields = line.split(',')
                if len(fields) < len(header):
                    continue
                
                try:
                    # Map fields (adjust based on AngelOne format)
                    instrument_data = dict(zip(header, fields))
                    
                    symbol = instrument_data.get('symbol', '').strip()
                    exchange = instrument_data.get('exchange', '').strip()
                    instrument_type = instrument_data.get('instrumenttype', '').strip()
                    
                    if not symbol or not exchange:
                        continue
                    
                    # Filter equity instruments
                    if self._is_valid_equity(instrument_data):
                        instrument = Instrument(
                            symbol=symbol,
                            token=instrument_data.get('token', ''),
                            name=instrument_data.get('name', symbol),
                            exchange=exchange,
                            asset_class=AssetClass.EQUITY,
                            lot_size=int(instrument_data.get('lotsize', 1)),
                            tick_size=float(instrument_data.get('tick_size', 0.05)),
                            instrument_type=instrument_type
                        )
                        equity_instruments.append(instrument)
                    
                    # Filter derivatives instruments
                    elif self._is_valid_derivative(instrument_data):
                        instrument = Instrument(
                            symbol=symbol,
                            token=instrument_data.get('token', ''),
                            name=instrument_data.get('name', symbol),
                            exchange=exchange,
                            asset_class=AssetClass.DERIVATIVES,
                            lot_size=int(instrument_data.get('lotsize', 1)),
                            tick_size=float(instrument_data.get('tick_size', 0.05)),
                            instrument_type=instrument_type,
                            expiry=instrument_data.get('expiry'),
                            strike=float(instrument_data.get('strike', 0)) if instrument_data.get('strike') else None,
                            option_type=instrument_data.get('optiontype')
                        )
                        derivatives_instruments.append(instrument)
                
                except Exception as e:
                    logger.debug(f"Error parsing instrument line: {e}")
                    continue
            
            # Check if we got any instruments
            total_instruments = len(equity_instruments) + len(derivatives_instruments)
            if total_instruments == 0:
                logger.warning("⚠️ No valid instruments parsed from API, falling back to demo")
                await self.load_demo_instruments()
                return
            
            # Store instruments
            self.instruments[AssetClass.EQUITY] = equity_instruments[:500]  # Limit for performance
            self.instruments[AssetClass.DERIVATIVES] = derivatives_instruments[:200]
            
            self.last_updated = datetime.now(timezone.utc)
            
            logger.info(f"📊 Parsed instruments: "
                       f"Equity: {len(self.instruments[AssetClass.EQUITY])}, "
                       f"Derivatives: {len(self.instruments[AssetClass.DERIVATIVES])}")
        
        except Exception as e:
            logger.error(f"❌ Error parsing instruments: {e}")
            await self.load_demo_instruments()
    
    def _is_valid_equity(self, instrument_data: dict) -> bool:
        """Check if instrument is valid equity"""
        try:
            exchange = instrument_data.get('exchange', '').strip()
            instrument_type = instrument_data.get('instrumenttype', '').strip()
            symbol = instrument_data.get('symbol', '').strip()
            
            # Basic filters
            if exchange not in self.equity_filters['exchanges']:
                return False
            
            if instrument_type not in self.equity_filters['instrument_types']:
                return False
            
            # Exclude patterns
            for pattern in self.equity_filters['exclude_patterns']:
                if pattern in symbol:
                    return False
            
            return True
        
        except Exception:
            return False
    
    def _is_valid_derivative(self, instrument_data: dict) -> bool:
        """Check if instrument is valid derivative"""
        try:
            exchange = instrument_data.get('exchange', '').strip()
            instrument_type = instrument_data.get('instrumenttype', '').strip()
            
            if exchange not in self.derivatives_filters['exchanges']:
                return False
            
            if instrument_type not in self.derivatives_filters['instrument_types']:
                return False
            
            return True
        
        except Exception:
            return False
    
    async def load_demo_instruments(self):
        """Load demo instruments for testing"""
        logger.info("📊 Loading demo instruments")
        
        # Demo equity instruments (top NSE stocks)
        equity_symbols = [
            "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "KOTAKBANK",
            "HINDUNILVR", "LT", "SBIN", "BHARTIARTL", "ASIANPAINT", "MARUTI",
            "BAJFINANCE", "HCLTECH", "WIPRO", "ULTRACEMCO", "NESTLEIND",
            "TATAMOTORS", "TITAN", "POWERGRID", "NTPC", "COALINDIA",
            "TECHM", "DRREDDY", "SUNPHARMA", "INDUSINDBK", "BAJAJFINSV",
            "GRASIM", "CIPLA", "TATASTEEL", "JSWSTEEL", "HINDALCO",
            "ADANIPORTS", "ONGC", "IOC", "BPCL", "DIVISLAB", "BRITANNIA"
        ]
        
        equity_instruments = []
        for symbol in equity_symbols:
            instrument = Instrument(
                symbol=symbol,
                token=f"demo_{symbol}",
                name=symbol,
                exchange="NSE",
                asset_class=AssetClass.EQUITY,
                lot_size=1,
                tick_size=0.05,
                instrument_type="EQ"
            )
            equity_instruments.append(instrument)
        
        # Demo derivatives instruments
        derivatives_symbols = [
            "NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "INFY", "HDFCBANK",
            "ICICIBANK", "KOTAKBANK", "SBIN", "BAJFINANCE"
        ]
        
        derivatives_instruments = []
        for symbol in derivatives_symbols:
            # Add futures
            instrument = Instrument(
                symbol=f"{symbol}FUT",
                token=f"demo_{symbol}_FUT",
                name=f"{symbol} Future",
                exchange="NFO",
                asset_class=AssetClass.DERIVATIVES,
                lot_size=50 if symbol in ["NIFTY", "BANKNIFTY"] else 1,
                tick_size=0.05,
                instrument_type="FUTSTK",
                expiry="2025-01-30"
            )
            derivatives_instruments.append(instrument)
        
        self.instruments[AssetClass.EQUITY] = equity_instruments
        self.instruments[AssetClass.DERIVATIVES] = derivatives_instruments
        self.last_updated = datetime.now(timezone.utc)
        
        logger.info(f"✅ Demo instruments loaded: "
                   f"Equity: {len(equity_instruments)}, "
                   f"Derivatives: {len(derivatives_instruments)}")
    
    async def update_strategy_symbols(self):
        """Update strategy symbol lists based on their asset class"""
        try:
            async with self.db_manager.get_session() as db:
                # Get all active strategies
                result = await db.execute(
                    select(Strategy).where(Strategy.status == StrategyStatus.ACTIVE)
                )
                strategies = result.scalars().all()
                
                for strategy in strategies:
                    asset_class = strategy.asset_class
                    
                    if asset_class in self.instruments:
                        # Get instruments for this asset class
                        instruments = self.instruments[asset_class]
                        
                        # Select top instruments (you can customize selection logic)
                        selected_symbols = self._select_symbols_for_strategy(
                            strategy, instruments
                        )
                        
                        # Update strategy symbols
                        strategy.symbols = selected_symbols
                        
                        logger.info(f"📈 Updated {strategy.name} with {len(selected_symbols)} {asset_class.value} symbols")
                
                await db.commit()
                logger.info("✅ Strategy symbols updated")
        
        except Exception as e:
            logger.error(f"❌ Error updating strategy symbols: {e}")
    
    def _select_symbols_for_strategy(self, strategy: Strategy, instruments: List[Instrument]) -> List[str]:
        """Select appropriate symbols for a strategy"""
        try:
            # Strategy-specific symbol selection logic
            if strategy.asset_class == AssetClass.EQUITY:
                # For equity strategies, select top liquid stocks
                selected = instruments[:20]  # Top 20 for now
                return [inst.symbol for inst in selected]
            
            elif strategy.asset_class == AssetClass.DERIVATIVES:
                # For derivatives, select index futures and top stock futures
                futures = [inst for inst in instruments if inst.instrument_type == "FUTSTK"]
                selected = futures[:10]  # Top 10 futures
                return [inst.symbol for inst in selected]
            
            else:
                # Default fallback
                return [inst.symbol for inst in instruments[:10]]
        
        except Exception as e:
            logger.error(f"Error selecting symbols for strategy {strategy.name}: {e}")
            return ["RELIANCE", "TCS", "INFY"]  # Fallback
    
    def get_instruments_by_asset_class(self, asset_class: AssetClass) -> List[Instrument]:
        """Get instruments by asset class"""
        return self.instruments.get(asset_class, [])
    
    def get_all_symbols(self, asset_class: Optional[AssetClass] = None) -> List[str]:
        """Get all available symbols"""
        if asset_class:
            instruments = self.instruments.get(asset_class, [])
            return [inst.symbol for inst in instruments]
        else:
            all_symbols = []
            for instruments in self.instruments.values():
                all_symbols.extend([inst.symbol for inst in instruments])
            return all_symbols
    
    async def refresh_instruments(self):
        """Refresh instruments from API"""
        logger.info("🔄 Refreshing instruments...")
        await self.fetch_instruments()
        await self.update_strategy_symbols()
        logger.info("✅ Instruments refreshed")
    
    def get_instrument_info(self, symbol: str) -> Optional[Instrument]:
        """Get detailed instrument information"""
        for instruments in self.instruments.values():
            for instrument in instruments:
                if instrument.symbol == symbol:
                    return instrument
        return None
    
    def get_status(self) -> Dict:
        """Get instrument manager status"""
        return {
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'equity_count': len(self.instruments.get(AssetClass.EQUITY, [])),
            'derivatives_count': len(self.instruments.get(AssetClass.DERIVATIVES, [])),
            'total_instruments': sum(len(instruments) for instruments in self.instruments.values()),
            'auth_status': 'authenticated' if self.auth_token else 'demo_mode'
        }

# Global instrument manager instance
instrument_manager: Optional[InstrumentManager] = None

async def get_instrument_manager(db_manager: DatabaseManager) -> InstrumentManager:
    """Get or create instrument manager instance"""
    global instrument_manager
    if instrument_manager is None:
        instrument_manager = InstrumentManager(db_manager)
        await instrument_manager.initialize()
    return instrument_manager 