from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SignalRecord:
    symbol: str
    timestamp: str
    model_version: str
    signal: str
    buy_probability: float
    sell_probability: float
    wait_probability: float
    market_regime: Optional[str]
    entry: Optional[float]
    stop_loss: Optional[float]
    target_1: Optional[float]
    target_2: Optional[float]
    risk_reward: Optional[float]
    decision: Optional[str]
    decision_reason: Optional[str]


@dataclass
class OrderRecord:
    symbol: str
    side: str
    quantity: int
    requested_price: Optional[float]
    filled_price: Optional[float]
    order_type: str
    status: str


@dataclass
class PositionRecord:
    symbol: str
    side: str
    quantity: int
    average_price: float
    stop_loss: Optional[float]
    target_price: Optional[float]
    status: str


@dataclass
class TradeRecord:
    symbol: str
    side: str
    quantity: int
    entry_price: float
    exit_price: Optional[float]
    stop_loss: Optional[float]
    target_price: Optional[float]
    pnl: Optional[float]
    exit_reason: Optional[str]
    status: str