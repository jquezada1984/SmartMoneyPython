"""
Connectors package for broker connections.

This package contains modules for connecting to different brokers
like MT5, Binance, and other trading platforms.
"""

from .mt5_connector import MT5Connector

__all__ = ['MT5Connector']
