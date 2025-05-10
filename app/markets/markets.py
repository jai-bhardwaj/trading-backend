# markets.py
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Market:
    name: str
    exchange: str  # Keep this as NSE or BSE
    country: str
    currency: str
    trading_hours: str
    instruments: List[str]
    api_endpoint: str  # Changed to Angel One API
    broker: str = "Angel One" # Add Broker

    def __str__(self):
        return f"{self.name} ({self.exchange}, {self.country}) - Trading Hours: {self.trading_hours} (via {self.broker})"

# Predefined Markets via Angel One
NSE_AngelOne = Market(
    name="National Stock Exchange (via Angel One)",
    exchange="NSE",
    country="India",
    currency="INR",
    trading_hours="09:15 - 15:30 IST",
    instruments=["EQ", "FUT", "OPT", "ETF"],
    api_endpoint="https://api.angelbroking.com/rest/secure/v3/"  #  Angel One API endpoint (Base URL -  check for the most up-to-date version)
)

BSE_AngelOne = Market(
    name="Bombay Stock Exchange (via Angel One)",
    exchange="BSE",
    country="India",
    currency="INR",
    trading_hours="09:15 - 15:30 IST",
    instruments=["EQ", "FUT", "OPT", "ETF"],
    api_endpoint="https://api.angelbroking.com/rest/secure/v3/" # Angel One API endpoint (Base URL - check for the most up-to-date version)
)

# Store markets in a dictionary
available_markets: Dict[str, Market] = {
    "NSE_AngelOne": NSE_AngelOne,
    "BSE_AngelOne": BSE_AngelOne,
}

# Example Usage
if __name__ == "__main__":
    print(NSE_AngelOne)
    print(BSE_AngelOne)
    print(f"Instruments traded on NSE via Angel One: {NSE_AngelOne.instruments}")



    print(f"Available Markets: {available_markets.keys()}")
