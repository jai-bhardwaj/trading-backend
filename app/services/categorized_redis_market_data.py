"""
Categorized Redis Market Data Service - Clean Implementation

Organizes AngelOne instruments into clean categories:
- EQUITY: Cash equity stocks
- OPTIONS: All option contracts (OPTSTK, OPTIDX, OPTCUR, OPTFUT, etc.)
- FUTURES: All future contracts (FUTSTK, FUTIDX, FUTCOM, FUTCUR, etc.)
- COMMODITY: Commodity instruments (COMDTY)
- CURRENCY: Currency instruments (UNDCUR, UNDIRC, UNDIRD, UNDIRT)
- INDEX: Index instruments (INDEX, AMXIDX)
"""

import asyncio
import logging
import json
import websockets
import pandas as pd
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from datetime import datetime, timedelta
import time as time_module
import redis.asyncio as aioredis
import aiohttp
import schedule
import threading
import pyotp
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

class CategorizedMarketDataService:
    """Clean categorized market data service for AngelOne instruments"""
    
    # Clean instrument category mapping
    CATEGORIES = {
        'EQUITY': ['EQUITY'],
        'OPTIONS': ['OPTSTK', 'OPTIDX', 'OPTCUR', 'OPTFUT', 'OPTBLN', 'OPTIRC'],
        'FUTURES': ['FUTSTK', 'FUTIDX', 'FUTCOM', 'FUTCUR', 'FUTENR', 'FUTBAS', 'FUTBLN', 'FUTIRC', 'FUTIRT'],
        'COMMODITY': ['COMDTY'],
        'CURRENCY': ['UNDCUR', 'UNDIRC', 'UNDIRD', 'UNDIRT'],
        'INDEX': ['INDEX', 'AMXIDX']
    }
    
    def __init__(self, broker_config: Dict[str, Any], redis_url: str = "redis://localhost:6379"):
        self.broker_config = broker_config
        self.redis_url = redis_url
        self.redis_client = None
        self.is_running = False
        
        # Service metrics
        self.metrics = {
            'total_instruments': 0,
            'categories_count': 0,
            'last_update': None,
            'download_status': 'pending',
            'errors': 0
        }

    async def initialize(self) -> bool:
        """Initialize the service"""
        try:
            # Connect to Redis
            self.redis_client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            
            # Ensure data directories exist
            self.ensure_data_directories()
            
            # Load or refresh instruments
            await self.load_instruments()
            
            # Start daily scheduler
            self.start_daily_scheduler()
            
            logger.info("✅ Categorized market data service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {e}")
            return False

    def ensure_data_directories(self):
        """Ensure data directories exist"""
        data_dir = Path("data")
        instruments_dir = data_dir / "instruments"
        market_data_dir = data_dir / "market_data"
        
        # Create directories if they don't exist
        instruments_dir.mkdir(parents=True, exist_ok=True)
        market_data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("📁 Data directories ensured")

    async def load_instruments(self):
        """Load categorized instruments from cache or download fresh"""
        try:
            # Check if we have recent data
            last_update = await self.redis_client.get("instruments:last_update")
            
            if last_update:
                update_time = datetime.fromisoformat(last_update)
                if datetime.now() - update_time < timedelta(hours=12):
                    await self.load_from_cache()
                    return
            
            # Download fresh data
            logger.info("📡 Downloading fresh instrument data...")
            await self.download_and_categorize()
            
        except Exception as e:
            logger.error(f"❌ Failed to load instruments: {e}")
            await self.create_sample_data()

    async def download_and_categorize(self):
        """Download instruments from AngelOne and categorize them"""
        try:
            # Get access token
            access_token = await self.get_access_token()
            if not access_token:
                raise Exception("Failed to authenticate with AngelOne")
            
            # Download instruments
            instruments_data = await self.download_instruments(access_token)
            if not instruments_data:
                raise Exception("No instrument data received")
            
            logger.info(f"📊 Downloaded {len(instruments_data):,} instruments")
            
            # Save raw instruments to file
            await self.save_instruments_to_file(instruments_data)
            
            # Categorize instruments
            categorized = self.categorize_instruments(instruments_data)
            
            # Store in Redis
            await self.store_categorized_data(categorized, instruments_data)
            
            # Update metrics
            self.metrics['total_instruments'] = len(instruments_data)
            self.metrics['categories_count'] = len([cat for cat in categorized.values() if cat])
            self.metrics['last_update'] = datetime.now().isoformat()
            self.metrics['download_status'] = 'success'
            
            logger.info("✅ Instruments downloaded and categorized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to download and categorize: {e}")
            self.metrics['download_status'] = 'failed'
            self.metrics['errors'] += 1

    async def save_instruments_to_file(self, instruments_data: Dict[str, Any]):
        """Save raw instruments data to file for backup/archival"""
        try:
            # Create filename with current date
            today = datetime.now().strftime("%Y%m%d")
            filename = f"instruments_{today}.json"
            file_path = Path("data/instruments") / filename
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(instruments_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Saved {len(instruments_data):,} instruments to {file_path}")
            
            # Clean up old files (keep only last 7 days)
            await self.cleanup_old_instrument_files()
            
        except Exception as e:
            logger.error(f"❌ Failed to save instruments to file: {e}")

    async def cleanup_old_instrument_files(self):
        """Clean up old instrument files, keeping only the last 7 days"""
        try:
            instruments_dir = Path("data/instruments")
            if not instruments_dir.exists():
                return
            
            # Get current date
            current_date = datetime.now()
            cutoff_date = current_date - timedelta(days=7)
            
            # Find and remove old files
            removed_count = 0
            for file_path in instruments_dir.glob("instruments_*.json"):
                try:
                    # Extract date from filename
                    date_str = file_path.stem.replace("instruments_", "")
                    file_date = datetime.strptime(date_str, "%Y%m%d")
                    
                    # Remove if older than cutoff
                    if file_date < cutoff_date:
                        file_path.unlink()
                        removed_count += 1
                        logger.info(f"🗑️  Removed old instrument file: {file_path.name}")
                        
                except (ValueError, OSError) as e:
                    logger.warning(f"⚠️  Could not process file {file_path.name}: {e}")
            
            if removed_count > 0:
                logger.info(f"🧹 Cleaned up {removed_count} old instrument files")
                
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old instrument files: {e}")

    def categorize_instruments(self, instruments_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Categorize instruments by type"""
        categories = {cat: {} for cat in self.CATEGORIES.keys()}
        type_counts = defaultdict(int)
        
        for token, instrument in instruments_data.items():
            inst_type = instrument.get('instrument_type', '').strip() or 'EQUITY'
            symbol = instrument.get('symbol', '').strip()
            exchange = instrument.get('exchange', '').strip() 
            name = instrument.get('name', symbol).strip()
            
            # Count types for analysis
            type_counts[inst_type] += 1
            
            # Find target category
            target_category = None
            for category, types in self.CATEGORIES.items():
                if inst_type in types:
                    target_category = category
                    break
            
            # Skip unknown types
            if not target_category:
                continue
            
            # Create clean instrument entry
            symbol_key = f"{symbol}:{exchange}" if exchange else symbol
            categories[target_category][symbol_key] = {
                'token': token,
                'symbol': symbol,
                'name': name,
                'exchange': exchange,
                'instrument_type': inst_type,
                'lot_size': instrument.get('lot_size', 1),
                'tick_size': instrument.get('tick_size', 0.05)
            }
        
        # Log categorization results
        logger.info("📂 Categorization results:")
        for category, instruments in categories.items():
            if instruments:
                logger.info(f"  {category}: {len(instruments):,} instruments")
        
        return categories

    async def store_categorized_data(self, categorized: Dict[str, Dict[str, Any]], raw_data: Dict[str, Any]):
        """Store categorized data in Redis"""
        pipeline = self.redis_client.pipeline()
        
        # Store each category
        for category, instruments in categorized.items():
            if instruments:
                key = f"instruments:category:{category.lower()}"
                pipeline.set(key, json.dumps(instruments))
        
        # Store raw data for backup
        pipeline.set("instruments:raw", json.dumps(raw_data))
        
        # Create summary
        summary = {}
        for category, instruments in categorized.items():
            if instruments:
                exchanges = set(inst['exchange'] for inst in instruments.values() if inst['exchange'])
                summary[category] = {
                    'count': len(instruments),
                    'exchanges': sorted(list(exchanges)),
                    'sample_symbols': list(instruments.keys())[:5]
                }
        
        pipeline.set("instruments:summary", json.dumps(summary))
        pipeline.set("instruments:last_update", datetime.now().isoformat())
        
        await pipeline.execute()

    async def load_from_cache(self):
        """Load instruments from Redis cache"""
        try:
            summary_data = await self.redis_client.get("instruments:summary")
            if summary_data:
                summary = json.loads(summary_data)
                total = sum(cat['count'] for cat in summary.values())
                
                logger.info("📋 Loaded from cache:")
                for category, info in summary.items():
                    exchanges = ', '.join(info['exchanges'][:3])
                    logger.info(f"  📂 {category}: {info['count']:,} instruments ({exchanges})")
                
                self.metrics['total_instruments'] = total
                self.metrics['categories_count'] = len(summary)
                
        except Exception as e:
            logger.error(f"❌ Failed to load from cache: {e}")

    async def get_category_instruments(self, category: str) -> Dict[str, Any]:
        """Get all instruments from a specific category"""
        try:
            key = f"instruments:category:{category.lower()}"
            data = await self.redis_client.get(key)
            return json.loads(data) if data else {}
        except Exception as e:
            logger.error(f"❌ Failed to get {category} instruments: {e}")
            return {}

    async def search_instruments(self, 
                               query: str, 
                               category: str = None, 
                               exchange: str = None, 
                               limit: int = 50) -> List[Dict[str, Any]]:
        """Search instruments with filters"""
        results = []
        query_upper = query.upper()
        
        try:
            # Determine categories to search
            categories_to_search = [category.upper()] if category else list(self.CATEGORIES.keys())
            
            for cat in categories_to_search:
                instruments = await self.get_category_instruments(cat)
                
                for symbol_key, instrument in instruments.items():
                    # Check if query matches symbol or name
                    if (query_upper in instrument['symbol'].upper() or 
                        query_upper in instrument['name'].upper()):
                        
                        # Apply exchange filter
                        if exchange and instrument['exchange'] != exchange:
                            continue
                        
                        results.append({
                            'category': cat,
                            'symbol': instrument['symbol'],
                            'name': instrument['name'],
                            'exchange': instrument['exchange'],
                            'token': instrument['token'],
                            'instrument_type': instrument['instrument_type'],
                            'symbol_key': symbol_key
                        })
                        
                        if len(results) >= limit:
                            return results
        
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
        
        return results

    async def get_category_summary(self) -> Dict[str, Any]:
        """Get summary of all categories"""
        try:
            summary_data = await self.redis_client.get("instruments:summary")
            return json.loads(summary_data) if summary_data else {}
        except Exception as e:
            logger.error(f"❌ Failed to get category summary: {e}")
            return {}

    async def get_access_token(self) -> Optional[str]:
        """Get AngelOne access token"""
        try:
            totp = pyotp.TOTP(self.broker_config['totp_token'])
            totp_code = totp.now()
            
            url = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"
            payload = {
                "clientcode": self.broker_config['client_id'],
                "password": self.broker_config['password'],
                "totp": totp_code
            }
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "192.168.1.1",
                "X-ClientPublicIP": "106.193.147.98",
                "X-MACAddress": "00:00:00:00:00:00",
                "X-PrivateKey": self.broker_config['api_key']
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('status') and result.get('data'):
                            return result['data']['jwtToken']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return None

    async def download_instruments(self, access_token: str) -> Dict[str, Any]:
        """Download instruments from AngelOne API"""
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        instruments_list = await response.json()
                        
                        # Convert to token-keyed dictionary
                        instruments_dict = {}
                        for instrument in instruments_list:
                            token = instrument.get('token')
                            if token:
                                instruments_dict[token] = instrument
                        
                        return instruments_dict
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            return {}

    async def create_sample_data(self):
        """Create sample data for testing"""
        sample_data = {
            'EQUITY': {
                'INFY:NSE': {'token': '1594', 'symbol': 'INFY', 'name': 'Infosys Ltd', 'exchange': 'NSE', 'instrument_type': 'EQUITY', 'lot_size': 1, 'tick_size': 0.05},
                'TCS:NSE': {'token': '11536', 'symbol': 'TCS', 'name': 'Tata Consultancy Services', 'exchange': 'NSE', 'instrument_type': 'EQUITY', 'lot_size': 1, 'tick_size': 0.05},
                'RELIANCE:NSE': {'token': '2885', 'symbol': 'RELIANCE', 'name': 'Reliance Industries', 'exchange': 'NSE', 'instrument_type': 'EQUITY', 'lot_size': 1, 'tick_size': 0.05}
            },
            'INDEX' : {
                'Nifty 200:NSE': {'token': '99926033', 'symbol': 'Nifty 200', 'name': 'NIFTY 200', 'exchange': 'NSE', 'instrument_type': 'AMXIDX', 'lot_size': 1, 'tick_size': 0.0},
                'Nifty Div Opps 50:NSE': {'token': '99926034', 'symbol': 'Nifty Div Opps 50', 'name': 'NIFTY DIV OPPS 50', 'exchange': 'NSE', 'instrument_type': 'AMXIDX', 'lot_size': 1, 'tick_size': 0.0}
            }
        }
        
        pipeline = self.redis_client.pipeline()
        
        for category, instruments in sample_data.items():
            key = f"instruments:category:{category.lower()}"
            pipeline.set(key, json.dumps(instruments))
        
        summary = {
            category: {
                'count': len(instruments),
                'exchanges': ['NSE'],
                'sample_symbols': list(instruments.keys())
            } for category, instruments in sample_data.items()
        }
        
        pipeline.set("instruments:summary", json.dumps(summary))
        pipeline.set("instruments:last_update", datetime.now().isoformat())
        
        await pipeline.execute()
        
        total = sum(len(instruments) for instruments in sample_data.values())
        self.metrics['total_instruments'] = total
        self.metrics['categories_count'] = len(sample_data)
        
        logger.info(f"✅ Created sample data with {total} instruments")

    def start_daily_scheduler(self):
        """Start daily 9:00 AM scheduler"""
        def run_scheduler():
            schedule.every().day.at("09:00").do(
                lambda: asyncio.create_task(self.download_and_categorize())
            )
            
            while self.is_running:
                schedule.run_pending()
                time_module.sleep(60)
        
        self.is_running = True
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("⏰ Daily 9:00 AM scheduler started")

    async def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        return self.metrics.copy()

    async def cleanup(self):
        """Cleanup resources"""
        self.is_running = False
        if self.redis_client:
            await self.redis_client.close()
        logger.info("🧹 Service cleaned up")

# Factory function
async def create_categorized_service(broker_config: Dict[str, Any]) -> CategorizedMarketDataService:
    """Create and initialize the categorized service"""
    service = CategorizedMarketDataService(broker_config)
    await service.initialize()
    return service 