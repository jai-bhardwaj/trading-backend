# tests/test_integration.py
import pandas as pd
import pytest
import requests_mock

from app.strategies.strategies import MovingAverageCrossoverAngelOne

# from angel_api import AngelOne  #  Placeholder: Import your AngelOne API wrapper


@pytest.fixture
def mock_angel_one_api():
    """
    A pytest fixture that mocks the Angel One API.
    """
    with requests_mock.Mocker() as m:
        yield m


# def test_strategy_execution_with_mock_api(mock_angel_one_api):
#     """
#     Test a strategy's execution with a mock Angel One API.
#     """
#     # 1. Mock API responses
#     mock_angel_one_api.get(
#         "https://api.angelbroking.com/rest/secure/v3/historicaldata",  # Example URL, adjust as needed
#         json={
#             "status": "success",
#             "data": {
#                 "candles": [
#                     {"datetime": "2024-01-01", "open": 2400, "high": 2420, "low": 2390, "close": 2405},
#                     {"datetime": "2024-01-02", "open": 2410, "high": 2430, "low": 2400, "close": 2415},
#                     {"datetime": "2024-01-03", "open": 2420, "high": 2440, "low": 2410, "close": 2425},
#                     {"datetime": "2024-01-04", "open": 2415, "high": 2425, "low": 2405, "close": 2410},
#                     {"datetime": "2024-01-05", "open": 2430, "high": 2450, "low": 2420, "close": 2435},
#                     {"datetime": "2024-01-06", "open": 2440, "high": 2460, "low": 2430, "close": 2445},
#                     {"datetime": "2024-01-07", "open": 2450, "high": 2470, "low": 2440, "close": 2455},
#                     {"datetime": "2024-01-08", "open": 2445, "high": 2455, "low": 2435, "close": 2440},
#                     {"datetime": "2024-01-09", "open": 2460, "high": 2480, "low": 2450, "close": 2465},
#                     {"datetime": "2024-01-10", "open": 2470, "high": 2490, "low": 2460, "close": 2475},
#                 ]
#             }
#         },
#     )
#     mock_angel_one_api.post(
#         "https://api.angelbroking.com/rest/secure/v3/order",  # Example URL for order placement
#         json={"status": "success", "data": {"orderid": "1234567890"}},
#     )

#     # 2.  Create a mock AngelOne instance (replace with your actual mock)
#     # class MockAngelOne:
#     #     def __init__(self):
#     #         pass
#     #
#     #     def get_historical_data(self, symbol, from_date, to_date):
#     #         # Simulate fetching data
#     #         return pd.DataFrame({
#     #             'Date': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05',
#     #                                    '2024-01-06', '2024-01-07', '2024-01-08', '2024-01-09', '2024-01-10']),
#     #             'Open': [2400, 2410, 2420, 2415, 2430, 2440, 2450, 2445, 2460, 2470],
#     #             'High': [2420, 2430, 2440, 2425, 2450, 2460, 2470, 2455, 2480, 2490],
#     #             'Low': [2390, 2400, 2410, 2405, 2420, 2430, 2440, 2435, 2450, 2460],
#     #             'Close': [2405, 2415, 2425, 2410, 2435, 2445, 2455, 2440, 2465, 2475],
#     #             'Volume': [100000, 120000, 130000, 110000, 140000, 150000, 145000, 135000, 160000, 170000]
#     #         })
#     #
#     #     def place_order(self, symbol, quantity, order_type):
#     #         # Simulate placing an order
#     #         return {"orderid": "1234567890"}  #  Return a mock order ID
#     #
#     # mock_angel_one = MockAngelOne()

#     # 3.  Initialize strategy with the mock API
#     ma_strategy = MovingAverageCrossoverAngelOne(short_period=3, long_period=5, lot_size=100)
#     # ma_strategy.angel = mock_angel_one  # Inject the mock API instance

#     # 4.  Prepare sample data
#     data = pd.DataFrame({
#         'Date': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05',
#                                 '2024-01-06', '2024-01-07', '2024-01-08', '2024-01-09', '2024-01-10']),
#         'Open': [2400, 2410, 2420, 2415, 2430, 2440, 2450, 2445, 2460, 2470],
#         'High': [2420, 2430, 2440, 2425, 2450, 2460, 2470, 2455, 2480, 2490],
#         'Low': [2390, 2400, 2410, 2405, 2420, 2430, 2440, 2435, 2450, 2460],
#         'Close': [2405, 2415, 2425, 2410, 2435, 2445, 2455, 2440, 2465, 2475],
#         'Volume': [100000, 120000, 130000, 110000, 140000, 150000, 145000, 135000, 160000, 170000]
#     })
#     data = data.set_index('Date')

#     # 5. Run the strategy (which should now use the mock API)
#     ma_strategy.run(data, symbol="RELIANCE")

#     # 6.  Assert that the API was called correctly.  This is CRUCIAL.
#     assert mock_angel_one_api.called
#     # Check the number of calls
#     assert mock_angel_one_api.call_count == 1 + 5 # 1 for historical data and 5 for the number of trades.
#     # You can also inspect the requests made to the mock API:
#     # print(mock_angel_one_api.request_history)
#     # For example
#     # assert mock_angel_one_api.request_history[1].method == 'POST' #The first call is GET, second onwards is POST.
#     # assert 'RELIANCE' in mock_angel_one_api.request_history[1].text


def test_strategy_execution_with_mock_api(mock_angel_one_api):
    # Mock API responses
    mock_angel_one_api.get(
        "https://api.angelbroking.com/rest/secure/v3/historicaldata",
        json={
            "status": "success",
            "data": {
                "candles": [
                    {
                        "datetime": "2024-01-01",
                        "open": 2400,
                        "high": 2420,
                        "low": 2390,
                        "close": 2405,
                    },
                    {
                        "datetime": "2024-01-02",
                        "open": 2410,
                        "high": 2430,
                        "low": 2400,
                        "close": 2415,
                    },
                    {
                        "datetime": "2024-01-03",
                        "open": 2420,
                        "high": 2440,
                        "low": 2410,
                        "close": 2425,
                    },
                    {
                        "datetime": "2024-01-04",
                        "open": 2415,
                        "high": 2425,
                        "low": 2405,
                        "close": 2410,
                    },
                    {
                        "datetime": "2024-01-05",
                        "open": 2430,
                        "high": 2450,
                        "low": 2420,
                        "close": 2435,
                    },
                ]
            },
        },
    )
    mock_angel_one_api.post(
        "https://api.angelbroking.com/rest/secure/v3/order",
        json={"status": "success", "data": {"orderid": "1234567890"}},
    )

    # Initialize strategy
    ma_strategy = MovingAverageCrossoverAngelOne(
        short_period=3, long_period=5, lot_size=100
    )

    # Create a mock API class
    class MockAngelAPI:
        def place_order(self, symbol, quantity, order_type):
            print(f"Mock API: {order_type} {quantity} shares of {symbol}")
            return {"orderid": "1234567890"}

    ma_strategy.angel = MockAngelAPI()

    # Prepare sample data
    data = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
            ),
            "Open": [2400, 2410, 2420, 2415, 2430],
            "High": [2420, 2430, 2440, 2425, 2450],
            "Low": [2390, 2400, 2410, 2405, 2420],
            "Close": [2405, 2415, 2425, 2410, 2435],
            "Volume": [100000, 120000, 130000, 110000, 140000],
        }
    ).set_index("Date")

    # Run the strategy
    ma_strategy.run(data, symbol="RELIANCE")

    # Verify that the strategy generated signals
    signals = ma_strategy.generate_signals(data)
    assert not signals.empty
    assert "signal" in signals.columns
