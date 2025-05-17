# tests/test_markets.py
import pytest

from app.markets.markets import BSE_AngelOne, Market, NSE_AngelOne


def test_market_creation():
    """Test that a Market object can be created correctly."""
    market = Market(
        name="Test Market",
        exchange="TM",
        country="Testland",
        currency="TST",
        trading_hours="09:00 - 17:00",
        instruments=["EQ", "FUT"],
        api_endpoint="https://test.com/api",
    )
    assert market.name == "Test Market"
    assert market.exchange == "TM"
    assert market.country == "Testland"
    assert market.currency == "TST"
    assert market.trading_hours == "09:00 - 17:00"
    assert market.instruments == ["EQ", "FUT"]
    assert market.api_endpoint == "https://test.com/api"


def test_predefined_markets():
    """Test that the predefined NSE_AngelOne and BSE_AngelOne markets are set up correctly."""
    assert NSE_AngelOne.name == "National Stock Exchange (via Angel One)"
    assert NSE_AngelOne.exchange == "NSE"
    assert NSE_AngelOne.country == "India"
    assert NSE_AngelOne.currency == "INR"
    assert NSE_AngelOne.trading_hours == "09:15 - 15:30 IST"
    assert NSE_AngelOne.instruments == ["EQ", "FUT", "OPT", "ETF"]
    assert NSE_AngelOne.api_endpoint == "https://api.angelbroking.com/rest/secure/v3/"
    assert BSE_AngelOne.name == "Bombay Stock Exchange (via Angel One)"
    assert BSE_AngelOne.exchange == "BSE"
    assert BSE_AngelOne.country == "India"
    assert BSE_AngelOne.currency == "INR"
    assert BSE_AngelOne.trading_hours == "09:15 - 15:30 IST"
    assert BSE_AngelOne.instruments == ["EQ", "FUT", "OPT", "ETF"]
    assert BSE_AngelOne.api_endpoint == "https://api.angelbroking.com/rest/secure/v3/"


def test_market_string_representation():
    """Test the __str__ method of the Market class."""
    market = NSE_AngelOne
    expected_string = "National Stock Exchange (via Angel One) (NSE, India) - Trading Hours: 09:15 - 15:30 IST (via Angel One)"
    assert str(market) == expected_string


# You can add more test functions to cover other aspects of the markets module


# Add your market tests here
def test_market_initialization():
    # Test market initialization
    pass
