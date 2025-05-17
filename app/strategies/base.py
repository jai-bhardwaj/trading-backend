# strategies.py
from typing import Dict, List

import pandas as pd

# from angel_api import AngelOne  #  Placeholder:  Create a wrapper for the Angel One API.  You might need to install their SDK.


class Strategy:
    """
    Base class for all trading strategies.
    """

    def __init__(self, name: str, description: str, parameters: Dict = None):
        self.name = name
        self.description = description
        self.parameters = parameters or {}

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("Subclasses must implement generate_signals")

    def __str__(self):
        return f"{self.name} Strategy: {self.description}"
