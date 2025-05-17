# tests/test_strategies.py
import pandas as pd
import pytest

from app.strategies.base import Strategy
from app.strategies.strategies import MovingAverageCrossoverAngelOne


def test_strategy_creation():
    """Test that a Strategy object can be created."""
    strategy = Strategy(name="Test Strategy", description="A test strategy.")
    assert strategy.name == "Test Strategy"
    assert strategy.description == "A test strategy."
    assert strategy.parameters == {}

    strategy_with_params = Strategy(
        name="Test Strategy with Params",
        description="A test strategy with parameters.",
        parameters={"param1": 1, "param2": "abc"},
    )
    assert strategy_with_params.parameters == {"param1": 1, "param2": "abc"}


def test_moving_average_crossover_creation():
    """Test that a MovingAverageCrossoverAngelOne object can be created."""
    ma_strategy = MovingAverageCrossoverAngelOne(
        short_period=10, long_period=20, lot_size=100
    )
    assert ma_strategy.name == "Moving Average Crossover (Angel One)"
    assert "Buy/sell based on MA crossover" in ma_strategy.description
    assert ma_strategy.short_period == 10
    assert ma_strategy.long_period == 20
    assert ma_strategy.parameters == {"short_period": 10, "long_period": 20}
    assert ma_strategy.lot_size == 100


def test_moving_average_crossover_signals():
    """Test the generate_signals method of MovingAverageCrossoverAngelOne."""
    # Create sample data
    data = pd.DataFrame({"Close": [10, 11, 12, 13, 14, 15, 14, 13, 12, 11]})
    # must have a date time index
    data.index = pd.to_datetime(
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
    )

    ma_strategy = MovingAverageCrossoverAngelOne(short_period=3, long_period=5)
    signals = ma_strategy.generate_signals(data)
    print("Actual signals:")
    print(signals["signal"].tolist())
    # Expected signals (manually calculated)
    expected_signals = pd.DataFrame(
        {"signal": [0, 0, 0, 1, 0, 0, 0, 0, -1, 0]}, index=data.index
    )

    pd.testing.assert_frame_equal(signals, expected_signals)


def test_moving_average_crossover_signals_error():
    """Test that the generate_signals method raises an error if 'Close' column is missing."""
    data = pd.DataFrame({"Open": [10, 11, 12, 13, 14, 15, 14, 13, 12, 11]})
    data.index = pd.to_datetime(
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
    )
    ma_strategy = MovingAverageCrossoverAngelOne(short_period=3, long_period=5)
    with pytest.raises(
        ValueError, match="Input DataFrame must contain a 'Close' column."
    ):
        ma_strategy.generate_signals(data)


# Add your strategy tests here
def test_strategy_initialization():
    # Test strategy initialization
    pass
