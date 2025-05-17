import numpy as np
import pandas as pd

from .base import Strategy


class MovingAverageCrossoverAngelOne(Strategy):
    """
    Moving average crossover strategy, adapted for Angel One.
    """

    def __init__(
        self, short_period: int = 20, long_period: int = 50, lot_size: int = 1
    ):
        super().__init__(
            name="Moving Average Crossover (Angel One)",
            description="Buy/sell based on MA crossover, using Angel One for data and orders.",
            parameters={"short_period": short_period, "long_period": long_period},
        )
        self.short_period = short_period
        self.long_period = long_period
        # self.angel = angel_api  #  Placeholder:  Instance of your AngelOne API wrapper.
        self.lot_size = lot_size  # added lot size

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on moving average crossover.

        Args:
            data: DataFrame with market data.

        Returns:
            A pandas DataFrame with a 'signal' column:
            -1: Sell, 0: Hold, 1: Buy.
        """
        if "Close" not in data.columns:
            raise ValueError("Input DataFrame must contain a 'Close' column.")

        # Calculate moving averages
        short_ma = data["Close"].rolling(window=self.short_period, min_periods=1).mean()
        long_ma = data["Close"].rolling(window=self.long_period, min_periods=1).mean()

        # Initialize signals DataFrame
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0

        # Buy signal: short_ma crosses above long_ma
        buy = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))
        signals.loc[buy, "signal"] = 1

        # Sell signal: short_ma crosses below long_ma
        sell = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))
        signals.loc[sell, "signal"] = -1

        return signals

    def execute_trade(self, signal: int, symbol: str, quantity: int):
        """
        Execute a trade using the Angel One API.

        Args:
            signal: 1 (Buy), -1 (Sell), 0 (Hold - No action).
            symbol: The trading symbol (e.g., "RELIANCE").
            quantity: The quantity to trade.
        """
        if signal == 1:
            order_type = "BUY"
            if hasattr(self, "angel"):
                self.angel.place_order(
                    symbol=symbol, quantity=quantity, order_type=order_type
                )
            print(f"Angel One: Buying {quantity} shares of {symbol}")
        elif signal == -1:
            order_type = "SELL"
            if hasattr(self, "angel"):
                self.angel.place_order(
                    symbol=symbol, quantity=quantity, order_type=order_type
                )
            print(f"Angel One: Selling {quantity} shares of {symbol}")
        else:
            print(f"Angel One: Holding {symbol}")

    def run(self, data: pd.DataFrame, symbol: str):
        """
        Run the strategy on the given data and execute trades.

        Args:
            data: DataFrame with market data.
            symbol: The trading symbol.
        """
        signals_df = self.generate_signals(data)

        for index, row in signals_df.iterrows():
            signal = row["signal"]
            self.execute_trade(signal, symbol, self.lot_size)


# Example Usage
if __name__ == "__main__":
    # 1.  Initialize Angel One API (Placeholder - Replace with your actual initialization)
    # angel_one = AngelOne(client_id="your_client_id", access_token="your_access_token")
    # 2.  Fetch historical data using Angel One API  (Placeholder -  Replace with your data fetching)
    # data = angel_one.get_historical_data(symbol="RELIANCE", from_date="2024-01-01", to_date="2024-01-10")
    data = {
        "Date": pd.to_datetime(
            [
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-01-05",
                "2024-01-06",
                "2024-01-07",
                "2024-01-08",
                "2024-01-09",
                "2024-01-10",
            ]
        ),
        "Open": [2400, 2410, 2420, 2415, 2430, 2440, 2450, 2445, 2460, 2470],
        "High": [2420, 2430, 2440, 2425, 2450, 2460, 2470, 2455, 2480, 2490],
        "Low": [2390, 2400, 2410, 2405, 2420, 2430, 2440, 2435, 2450, 2460],
        "Close": [2405, 2415, 2425, 2410, 2435, 2445, 2455, 2440, 2465, 2475],
        "Volume": [
            100000,
            120000,
            130000,
            110000,
            140000,
            150000,
            145000,
            135000,
            160000,
            170000,
        ],
    }
    df = pd.DataFrame(data)
    df = df.set_index("Date")

    # 3.  Initialize and run the strategy
    ma_crossover_angel = MovingAverageCrossoverAngelOne(
        short_period=3, long_period=5, lot_size=100
    )  # Example lot size of 100
    print(ma_crossover_angel)
    ma_crossover_angel.run(
        df, symbol="RELIANCE"
    )  #  Replace "RELIANCE" with the actual symbol.
