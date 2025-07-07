"""
Instrument Fetcher - Downloads and filters Angel One instruments from CSV
"""
import csv
import json
import logging
import os
import pandas as pd
import requests
from datetime import datetime
from typing import Dict, List, Optional
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InstrumentFetcher:
    def __init__(self):
        self.ist_tz = pytz.timezone('Asia/Kolkata')
        
    def get_instruments(self) -> List[Dict]:
        """Download and parse Angel One instrument JSON file"""
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = requests.get(url)
            response.raise_for_status()
            
            # Save to a local file
            json_path = "data/angel_instruments.json"
            os.makedirs("data", exist_ok=True)
            with open(json_path, "wb") as f:
                f.write(response.content)
            
            # Parse JSON directly
            instruments = response.json()
            logger.info(f"✅ Downloaded and parsed {len(instruments)} instruments from Angel One JSON")
            return instruments
            
        except Exception as e:
            logger.error(f"❌ Error downloading instruments: {str(e)}")
            return []
    
    def load_symbols_to_trade(self) -> pd.DataFrame:
        """Load symbols to trade from CSV"""
        try:
            csv_path = "data/symbols_to_trade.csv"
            if not os.path.exists(csv_path):
                logger.error(f"❌ Symbols CSV file not found: {csv_path}")
                return pd.DataFrame()
            
            df = pd.read_csv(csv_path)
            logger.info(f"✅ Loaded {len(df)} symbols from CSV")
            return df
        except Exception as e:
            logger.error(f"❌ Error loading symbols CSV: {str(e)}")
            return pd.DataFrame()
    
    def filter_instruments(self, instruments: List[Dict], symbols_df: pd.DataFrame) -> List[Dict]:
        """Filter instruments based on symbols CSV, matching the 'name' field (base symbol), and exclude BSE instruments."""
        if symbols_df.empty:
            logger.warning("⚠️ No symbols loaded from CSV, returning all instruments")
            return instruments

        filtered_instruments = []
        symbols_set = set(symbols_df['symbol_name'].str.upper().tolist())
        
        # Debug: Show what symbols we're looking for
        logger.info(f"🔍 Looking for symbols: {list(symbols_set)}")
        
        # Debug: Count instrument types found
        instrument_types_found = {}
        symbols_found = set()

        for instrument in instruments:
            exch_seg = instrument.get("exch_seg", "").upper()
            if "BSE" in exch_seg:
                continue  # Exclude BSE instruments
            base_name = instrument.get("name", "").upper()
            instrument_type = instrument.get("instrumenttype", "").upper()
            
            # Debug: Track what we find
            if base_name in symbols_set:
                symbols_found.add(base_name)
                if instrument_type not in instrument_types_found:
                    instrument_types_found[instrument_type] = 0
                instrument_types_found[instrument_type] += 1
                
                symbol_row = symbols_df[symbols_df['symbol_name'].str.upper() == base_name]
                if not symbol_row.empty:
                    enabled = False
                    if exch_seg == "NSE" and (instrument_type == "" or instrument_type == "EQ") and symbol_row.iloc[0]['equity']:
                        enabled = True
                    elif exch_seg == "NFO" and instrument_type == "FUTSTK" and symbol_row.iloc[0]['futures']:
                        enabled = True
                    elif exch_seg == "NFO" and instrument_type == "OPTSTK" and symbol_row.iloc[0]['options']:
                        enabled = True

                    if enabled and symbol_row.iloc[0]['enabled']:
                        if instrument_type == "":
                            instrument["instrumenttype"] = "EQ"
                        filtered_instruments.append(instrument)
                        logger.debug(f"✅ Added {base_name}-{instrument_type}")
                    else:
                        logger.debug(f"❌ Skipped {base_name}-{instrument_type}")

        # Debug: Show summary
        logger.info(f"🔍 Found symbols: {list(symbols_found)}")
        logger.info(f"🔍 Instrument types found: {instrument_types_found}")
        logger.info(f"✅ Filtered {len(filtered_instruments)} instruments from {len(instruments)} total (excluding BSE, by name)")
        return filtered_instruments
    
    def save_instruments(self, instruments: List[Dict], filename: Optional[str] = None):
        """Save instruments to JSON file"""
        try:
            if filename is None:
                current_time = datetime.now(self.ist_tz).strftime("%Y%m%d_%H%M%S")
                filename = f"data/instruments_{current_time}.json"
            
            os.makedirs("data", exist_ok=True)
            
            with open(filename, 'w') as f:
                json.dump(instruments, f, indent=2)
            
            logger.info(f"✅ Saved {len(instruments)} instruments to {filename}")
            
            # Also save a latest version
            latest_filename = "data/instruments_latest.json"
            with open(latest_filename, 'w') as f:
                json.dump(instruments, f, indent=2)
            
            logger.info(f"✅ Updated latest instruments file: {latest_filename}")
            
        except Exception as e:
            logger.error(f"❌ Error saving instruments: {str(e)}")
    
    def run_daily_fetch(self):
        """Run the complete daily instrument fetch process"""
        logger.info("🔄 Starting daily instrument fetch process...")
        
        # Check if it's morning time (6 AM to 10 AM IST)
        ist_time = datetime.now(self.ist_tz)
        morning_start = ist_time.replace(hour=6, minute=0, second=0, microsecond=0)
        morning_end = ist_time.replace(hour=10, minute=0, second=0, microsecond=0)
        
        # if not (morning_start <= ist_time <= morning_end):
        #     logger.info(f"⏰ Current time {ist_time.strftime('%H:%M:%S')} IST is not in morning window (6 AM - 10 AM)")
        #     return
        
        # Download instruments
        instruments = self.get_instruments()
        if not instruments:
            logger.error("❌ No instruments downloaded, aborting")
            return
        
        # Load symbols to trade
        symbols_df = self.load_symbols_to_trade()
        
        # Filter instruments
        filtered_instruments = self.filter_instruments(instruments, symbols_df)
        
        # Save instruments
        self.save_instruments(filtered_instruments)
        
        logger.info("✅ Daily instrument fetch completed successfully")

def main():
    """Main function to run the instrument fetcher"""
    fetcher = InstrumentFetcher()
    fetcher.run_daily_fetch()

if __name__ == "__main__":
    main() 