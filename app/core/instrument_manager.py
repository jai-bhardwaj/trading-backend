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
from app.utils.timezone_utils import ist_utcnow as datetime_now, IST  # IST replacement

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
        self.api_key = os.getenv("ANGELONE_API_KEY_INSTRUMENTS")
        self.client_id = os.getenv("ANGELONE_CLIENT_ID_INSTRUMENTS")
        self.password = os.getenv("ANGELONE_PASSWORD_INSTRUMENTS")
        self.totp_secret = os.getenv("ANGELONE_TOTP_SECRET_INSTRUMENTS")
        
        # Validate required credentials
        if not self.api_key:
            raise ValueError("ANGELONE_API_KEY_INSTRUMENTS environment variable is required")
        if not self.client_id:
            raise ValueError("ANGELONE_CLIENT_ID_INSTRUMENTS environment variable is required")
        if not self.password:
            raise ValueError("ANGELONE_PASSWORD_INSTRUMENTS environment variable is required")
        
        # API endpoints
        self.base_url = "https://apiconnect.angelone.in"
        self.auth_token: Optional[str] = None
        
        # Configurable instrument limits
        self.max_equity_instruments = int(os.getenv("MAX_EQUITY_INSTRUMENTS", "1000"))
        self.max_derivatives_instruments = int(os.getenv("MAX_DERIVATIVES_INSTRUMENTS", "500"))
        self.max_total_instruments = int(os.getenv("MAX_TOTAL_INSTRUMENTS", "2000"))
        
        # Load all instruments flag
        self.load_all_instruments = os.getenv("LOAD_ALL_INSTRUMENTS", "false").lower() == "true"
        
        # Filtering configuration
        self.equity_filters = {
            'exchanges': ['NSE', 'BSE'],
            'instrument_types': ['EQ', 'EQUITY'],  # Added EQUITY as alternative
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
            
            # Check if AngelOne credentials are properly configured
            if self._are_credentials_configured():
                logger.info("🔑 AngelOne credentials found, attempting authentication...")
                # Try to authenticate with AngelOne
                auth_success = await self.authenticate()
                if auth_success:
                    # Fetch instruments from API
                    await self.fetch_instruments()
                else:
                    logger.warning("⚠️ AngelOne authentication failed, falling back to demo instruments")
                    await self.load_demo_instruments()
            else:
                logger.info("📊 AngelOne credentials not configured, using demo instruments")
                await self.load_demo_instruments()
            
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
                    # Use the same TOTP generation as the broker
                    totp = pyotp.TOTP(self.totp_secret)
                    totp_value = totp.now()
                    logger.info(f"🔐 Generated TOTP for instrument auth: {totp_value}")
                except Exception as e:
                    logger.warning(f"⚠️ TOTP generation failed: {e}, proceeding without TOTP")
            
            # Try authentication with current TOTP first
            auth_success = await self._attempt_authentication(totp_value)
            
            if not auth_success and totp_value:
                logger.warning("🔄 First TOTP attempt failed, trying with previous TOTP...")
                # Try with previous TOTP window (30 seconds earlier)
                totp = pyotp.TOTP(self.totp_secret)
                previous_totp = totp.at(datetime_now().timestamp() - 30)
                auth_success = await self._attempt_authentication(previous_totp)
                
                if not auth_success:
                    logger.warning("🔄 Trying with next TOTP window...")
                    # Try with next TOTP window (30 seconds later)
                    next_totp = totp.at(datetime_now().timestamp() + 30)
                    auth_success = await self._attempt_authentication(next_totp)
            
            return auth_success
            
        except Exception as e:
            logger.error(f"❌ AngelOne authentication error: {e}")
            return False
    
    async def _attempt_authentication(self, totp_value: Optional[str]) -> bool:
        """Attempt authentication with given TOTP"""
        try:
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
            
            # Add small delay to avoid rate limiting
            await asyncio.sleep(1)
            
            async with self.session.post(
                f"{self.base_url}/rest/auth/angelbroking/user/v1/loginByPassword",
                json=login_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status"):
                        self.auth_token = data["data"]["jwtToken"]
                        logger.info("✅ AngelOne authentication successful")
                        return True
                    else:
                        error_msg = data.get('message', 'Unknown error')
                        logger.warning(f"⚠️ AngelOne auth failed: {error_msg}")
                        return False
                else:
                    response_text = await response.text()
                    logger.warning(f"⚠️ AngelOne auth HTTP error: {response.status}, {response_text}")
                    return False
            
        except Exception as e:
            logger.warning(f"⚠️ Authentication attempt failed: {e}")
            return False
    
    async def fetch_instruments(self):
        """Fetch instruments from AngelOne API"""
        try:
            if not self.auth_token:
                logger.warning("⚠️ No auth token, using demo instruments")
                await self.load_demo_instruments()
                return
            
            # Use the correct instrument endpoint that works
            instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB"
            }
            
            # Download instrument file
            async with self.session.get(instrument_url, headers=headers) as response:
                if response.status == 200:
                    instruments_data = await response.json()
                    if not instruments_data or len(instruments_data) < 100:
                        logger.warning("⚠️ Empty/invalid response from AngelOne API, using demo instruments")
                        await self.load_demo_instruments()
                    else:
                        await self.parse_json_instruments(instruments_data)
                        logger.info("✅ Instruments fetched from AngelOne")
                else:
                    logger.error(f"❌ Failed to fetch instruments: {response.status}")
                    await self.load_demo_instruments()
        
        except Exception as e:
            logger.error(f"❌ Error fetching instruments: {e}")
            await self.load_demo_instruments()
    
    async def parse_json_instruments(self, instruments_data: List[dict]):
        """Parse instruments data from AngelOne JSON format"""
        try:
            if not instruments_data:
                logger.warning("⚠️ Empty instruments data from API, falling back to demo")
                await self.load_demo_instruments()
                return
            
            equity_instruments = []
            derivatives_instruments = []
            
            for instrument_data in instruments_data:
                try:
                    symbol = instrument_data.get('symbol', '').strip()
                    exchange = instrument_data.get('exch_seg', '').strip()
                    instrument_type = instrument_data.get('instrumenttype', '').strip()
                    
                    if not symbol or not exchange:
                        continue
                    
                    # Filter equity instruments
                    if self._is_valid_equity_json(instrument_data):
                        instrument = Instrument(
                            symbol=symbol,
                            token=instrument_data.get('token', ''),
                            name=instrument_data.get('name', symbol),
                            exchange=exchange,
                            asset_class=AssetClass.EQUITY,
                            lot_size=int(float(instrument_data.get('lotsize', 1))),
                            tick_size=float(instrument_data.get('tick_size', 0.05)),
                            instrument_type=instrument_type
                        )
                        equity_instruments.append(instrument)
                    
                    # Filter derivatives instruments
                    elif self._is_valid_derivative_json(instrument_data):
                        strike_price = None
                        try:
                            strike_str = instrument_data.get('strike', '0')
                            if strike_str and float(strike_str) > 0:
                                strike_price = float(strike_str)
                        except (ValueError, TypeError):
                            pass
                        
                        instrument = Instrument(
                            symbol=symbol,
                            token=instrument_data.get('token', ''),
                            name=instrument_data.get('name', symbol),
                            exchange=exchange,
                            asset_class=AssetClass.DERIVATIVES,
                            lot_size=int(float(instrument_data.get('lotsize', 1))),
                            tick_size=float(instrument_data.get('tick_size', 0.05)),
                            instrument_type=instrument_type,
                            expiry=instrument_data.get('expiry') if instrument_data.get('expiry') else None,
                            strike=strike_price,
                            option_type=instrument_data.get('optiontype') if instrument_data.get('optiontype') else None
                        )
                        derivatives_instruments.append(instrument)
                
                except Exception as e:
                    logger.debug(f"Error parsing instrument: {e}")
                    continue
            
            # Check if we got any instruments
            total_instruments = len(equity_instruments) + len(derivatives_instruments)
            if total_instruments == 0:
                logger.warning("⚠️ No valid instruments parsed from API, falling back to demo")
                await self.load_demo_instruments()
                return
            
            logger.info(f"📊 Raw instruments parsed: Equity: {len(equity_instruments)}, Derivatives: {len(derivatives_instruments)}")
            
            # Apply configurable limits with sorting
            final_equity = await self._apply_instrument_limits(equity_instruments, AssetClass.EQUITY)
            final_derivatives = await self._apply_instrument_limits(derivatives_instruments, AssetClass.DERIVATIVES)
            
            # Store instruments
            self.instruments[AssetClass.EQUITY] = final_equity
            self.instruments[AssetClass.DERIVATIVES] = final_derivatives
            
            self.last_updated = datetime_now()
            
            logger.info(f"📊 Final instruments: "
                       f"Equity: {len(self.instruments[AssetClass.EQUITY])}, "
                       f"Derivatives: {len(self.instruments[AssetClass.DERIVATIVES])}")
        
        except Exception as e:
            logger.error(f"❌ Error parsing JSON instruments: {e}")
            await self.load_demo_instruments()
    
    def _is_valid_equity_json(self, instrument_data: dict) -> bool:
        """Check if instrument is valid equity (JSON format)"""
        try:
            exchange = instrument_data.get('exch_seg', '').strip()
            instrument_type = instrument_data.get('instrumenttype', '').strip()
            symbol = instrument_data.get('symbol', '').strip()
            
            # Basic filters
            if exchange not in self.equity_filters['exchanges']:
                return False
            
            # Angel One equity instruments have empty instrument_type and symbol ending with '-EQ'
            if not (instrument_type == '' and symbol.endswith('-EQ')):
                return False
            
            # Exclude patterns (check base symbol without -EQ suffix)
            base_symbol = symbol.replace('-EQ', '')
            for pattern in self.equity_filters['exclude_patterns']:
                if pattern in base_symbol:
                    return False
            
            return True
        
        except Exception:
            return False
    
    def _is_valid_derivative_json(self, instrument_data: dict) -> bool:
        """Check if instrument is valid derivative (JSON format)"""
        try:
            exchange = instrument_data.get('exch_seg', '').strip()
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
        self.last_updated = datetime_now()
        
        logger.info(f"✅ Demo instruments loaded: "
                   f"Equity: {len(equity_instruments)}, "
                   f"Derivatives: {len(derivatives_instruments)}")
    
    async def update_strategy_symbols(self):
        """Update strategy symbol lists based on their asset class"""
        try:
            async with self.db_manager.get_async_session() as db:
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

    def _are_credentials_configured(self) -> bool:
        """Check if AngelOne credentials are properly configured"""
        # Check if all required fields are set and not placeholder values
        if not self.api_key or self.api_key.startswith('your_') or len(self.api_key) < 5:
            return False
            
        if not self.client_id or self.client_id.startswith('your_') or len(self.client_id) < 5:
            return False
            
        # Password can be shorter (like numeric PINs)
        if not self.password or self.password.startswith('your_'):
            return False
        
        return True

    async def _apply_instrument_limits(self, instruments: List[Instrument], asset_class: AssetClass) -> List[Instrument]:
        """Apply configurable limits to instruments with smart sorting"""
        try:
            if not instruments:
                return []
            
            # If load_all_instruments is True, return all (up to max_total_instruments)
            if self.load_all_instruments:
                max_limit = self.max_total_instruments
                logger.info(f"📊 Loading ALL {asset_class.value} instruments (limit: {max_limit})")
            else:
                # Use specific limits for each asset class
                if asset_class == AssetClass.EQUITY:
                    max_limit = self.max_equity_instruments
                elif asset_class == AssetClass.DERIVATIVES:
                    max_limit = self.max_derivatives_instruments
                else:
                    max_limit = 1000  # Default fallback
                
                logger.info(f"📊 Applying {asset_class.value} limit: {max_limit}")
            
            # Sort instruments by quality/priority
            sorted_instruments = await self._sort_instruments_by_quality(instruments, asset_class)
            
            # Apply limit
            final_instruments = sorted_instruments[:max_limit]
            
            logger.info(f"📊 {asset_class.value} instruments: {len(instruments)} -> {len(final_instruments)}")
            return final_instruments
            
        except Exception as e:
            logger.error(f"❌ Error applying limits for {asset_class.value}: {e}")
            # Fallback to original logic
            if asset_class == AssetClass.EQUITY:
                return instruments[:self.max_equity_instruments]
            else:
                return instruments[:self.max_derivatives_instruments]
    
    async def _sort_instruments_by_quality(self, instruments: List[Instrument], asset_class: AssetClass) -> List[Instrument]:
        """Sort instruments by quality/liquidity metrics"""
        try:
            if asset_class == AssetClass.EQUITY:
                # Sort equity by symbol alphabetically for now (could add market cap, volume etc.)
                # Prioritize major stocks by putting known major stocks first
                major_stocks = [
                    "RELIANCE-EQ", "TCS-EQ", "INFY-EQ", "HDFCBANK-EQ", "ICICIBANK-EQ", 
                    "HINDUNILVR-EQ", "LT-EQ", "SBIN-EQ", "BHARTIARTL-EQ", "ASIANPAINT-EQ",
                    "MARUTI-EQ", "BAJFINANCE-EQ", "HCLTECH-EQ", "WIPRO-EQ", "ULTRACEMCO-EQ",
                    "NESTLEIND-EQ", "TATAMOTORS-EQ", "TITAN-EQ", "POWERGRID-EQ", "NTPC-EQ",
                    "COALINDIA-EQ", "TECHM-EQ", "DRREDDY-EQ", "SUNPHARMA-EQ", "INDUSINDBK-EQ"
                ]
                
                # Separate major stocks and others
                major_instruments = []
                other_instruments = []
                
                for instrument in instruments:
                    if instrument.symbol in major_stocks:
                        major_instruments.append(instrument)
                    else:
                        other_instruments.append(instrument)
                
                # Sort major stocks by order in major_stocks list
                major_instruments.sort(key=lambda x: major_stocks.index(x.symbol) if x.symbol in major_stocks else 999)
                
                # Sort others alphabetically
                other_instruments.sort(key=lambda x: x.symbol)
                
                # Combine: major stocks first, then others
                return major_instruments + other_instruments
                
            elif asset_class == AssetClass.DERIVATIVES:
                # Sort derivatives by type priority: Index futures > Stock futures > Options
                def derivative_priority(instrument):
                    if "NIFTY" in instrument.symbol and instrument.instrument_type == "FUTIDX":
                        return 0  # Highest priority: Index futures
                    elif instrument.instrument_type == "FUTSTK":
                        return 1  # Stock futures
                    elif instrument.instrument_type in ["OPTIDX", "OPTSTK"]:
                        return 2  # Options
                    else:
                        return 3  # Others
                
                return sorted(instruments, key=derivative_priority)
            
            else:
                # Default: alphabetical sort
                return sorted(instruments, key=lambda x: x.symbol)
                
        except Exception as e:
            logger.error(f"❌ Error sorting instruments: {e}")
            return instruments  # Return unsorted on error

# Global instrument manager instance
instrument_manager: Optional[InstrumentManager] = None

async def get_instrument_manager(db_manager: DatabaseManager) -> InstrumentManager:
    """Get or create instrument manager instance"""
    global instrument_manager
    if instrument_manager is None:
        instrument_manager = InstrumentManager(db_manager)
        await instrument_manager.initialize()
    return instrument_manager 