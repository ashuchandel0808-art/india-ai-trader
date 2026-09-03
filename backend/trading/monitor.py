"""
INDIA AI TRADER V15.6-F
PAPER POSITION MONITOR

Purpose
-------
Continuously monitor open SQLite paper trades.

For every open trade:

    LIVE PRICE
        ↓
    STOP LOSS CHECK
        ↓
    TARGET CHECK
        ↓
    AUTO EXIT
        ↓
    SQLITE UPDATE
        ↓
    REALIZED P&L

IMPORTANT
---------
This module ONLY manages PAPER trades.

REAL MONEY EXECUTION IS NEVER PERFORMED.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional


# ============================================================
# HELPERS
# ============================================================

def now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        if value is None:
            return default

        return float(value)

    except (
        TypeError,
        ValueError,
    ):

        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:

        return int(value)

    except (
        TypeError,
        ValueError,
    ):

        return default


# ============================================================
# PRICE TRIGGER LOGIC
# ============================================================

def check_exit_trigger(
    trade: Dict[str, Any],
    current_price: float,
) -> Optional[str]:
    """
    Determine whether an open trade should close.

    BUY:
        price <= stop_loss  -> STOP_LOSS
        price >= target     -> TARGET_1

    SELL:
        price >= stop_loss  -> STOP_LOSS
        price <= target     -> TARGET_1
    """

    side = str(
        trade.get(
            "side",
            "",
        )
    ).upper()

    stop_loss = safe_float(
        trade.get(
            "stop_loss"
        )
    )

    target_price = safe_float(
        trade.get(
            "target_price"
        )
    )

    if current_price <= 0:
        return None

    if side == "BUY":

        if (
            stop_loss > 0
            and current_price <= stop_loss
        ):

            return "STOP_LOSS"

        if (
            target_price > 0
            and current_price >= target_price
        ):

            return "TARGET_1"

    elif side == "SELL":

        if (
            stop_loss > 0
            and current_price >= stop_loss
        ):

            return "STOP_LOSS"

        if (
            target_price > 0
            and current_price <= target_price
        ):

            return "TARGET_1"

    return None


# ============================================================
# P&L CALCULATION
# ============================================================

def calculate_pnl(
    side: str,
    entry_price: float,
    exit_price: float,
    quantity: int,
) -> float:

    side = (
        side
        or "BUY"
    ).upper()

    if side == "BUY":

        return (
            exit_price -
            entry_price
        ) * quantity

    return (
        entry_price -
        exit_price
    ) * quantity


# ============================================================
# MONITOR ENGINE
# ============================================================

class PaperPositionMonitor:

    def __init__(
        self,
        get_open_trades: Callable,
        get_price: Callable,
        close_trade: Callable,
    ):

        self.get_open_trades = (
            get_open_trades
        )

        self.get_price = (
            get_price
        )

        self.close_trade = (
            close_trade
        )

        self.last_scan_at: Optional[
            str
        ] = None

        self.last_result: Dict[
            str,
            Any
        ] = {
            "scanned":
                0,
            "triggered":
                0,
            "closed":
                0,
            "errors":
                0,
        }

    # ========================================================
    # SINGLE TRADE
    # ========================================================

    def monitor_trade(
        self,
        trade: Dict[str, Any],
    ) -> Dict[str, Any]:

        trade_id = safe_int(
            trade.get(
                "id"
            )
        )

        symbol = str(
            trade.get(
                "symbol",
                "",
            )
        ).upper()

        try:

            current_price = safe_float(
                self.get_price(
                    symbol
                )
            )

        except Exception as exc:

            return {
                "trade_id":
                    trade_id,
                "symbol":
                    symbol,
                "status":
                    "ERROR",
                "error":
                    str(exc),
            }

        trigger = check_exit_trigger(
            trade,
            current_price,
        )

        entry_price = safe_float(
            trade.get(
                "entry_price"
            )
        )

        quantity = safe_int(
            trade.get(
                "quantity"
            )
        )

        side = str(
            trade.get(
                "side",
                "BUY",
            )
        ).upper()

        unrealized_pnl = calculate_pnl(
            side,
            entry_price,
            current_price,
            quantity,
        )

        # ----------------------------------------------------
        # NO TRIGGER
        # ----------------------------------------------------

        if trigger is None:

            return {
                "trade_id":
                    trade_id,
                "symbol":
                    symbol,
                "status":
                    "MONITORED",
                "side":
                    side,
                "entry_price":
                    entry_price,
                "current_price":
                    current_price,
                "quantity":
                    quantity,
                "unrealized_pnl":
                    round(
                        unrealized_pnl,
                        2,
                    ),
                "stop_loss":
                    trade.get(
                        "stop_loss"
                    ),
                "target_price":
                    trade.get(
                        "target_price"
                    ),
                "exit_trigger":
                    None,
            }

        # ----------------------------------------------------
        # TRIGGERED
        # ----------------------------------------------------

        try:

            result = self.close_trade(
                trade_id,
                current_price,
                trigger,
            )

            return {
                "trade_id":
                    trade_id,
                "symbol":
                    symbol,
                "status":
                    "AUTO_CLOSED",
                "side":
                    side,
                "entry_price":
                    entry_price,
                "exit_price":
                    current_price,
                "quantity":
                    quantity,
                "exit_trigger":
                    trigger,
                "realized_pnl":
                    result.get(
                        "realized_pnl"
                    ),
                "execution":
                    result,
            }

        except Exception as exc:

            return {
                "trade_id":
                    trade_id,
                "symbol":
                    symbol,
                "status":
                    "CLOSE_ERROR",
                "exit_trigger":
                    trigger,
                "error":
                    str(exc),
            }

    # ========================================================
    # FULL SCAN
    # ========================================================

    def scan(self) -> Dict[str, Any]:

        scan_time = now_iso()

        self.last_scan_at = scan_time

        scanned = 0
        triggered = 0
        closed = 0
        errors = 0

        results = []

        try:

            trades = (
                self.get_open_trades()
            )

        except Exception as exc:

            self.last_result = {
                "scanned":
                    0,
                "triggered":
                    0,
                "closed":
                    0,
                "errors":
                    1,
                "error":
                    str(exc),
            }

            return self.last_result

        for trade in trades:

            scanned += 1

            result = self.monitor_trade(
                trade
            )

            status = result.get(
                "status"
            )

            if status == "AUTO_CLOSED":

                triggered += 1
                closed += 1

            elif status in {
                "ERROR",
                "CLOSE_ERROR",
            }:

                errors += 1

            elif result.get(
                "exit_trigger"
            ):

                triggered += 1

            results.append(
                result
            )

        self.last_result = {
            "status":
                "success",
            "timestamp":
                scan_time,
            "scanned":
                scanned,
            "triggered":
                triggered,
            "closed":
                closed,
            "errors":
                errors,
            "results":
                results,
        }

        return self.last_result


# ============================================================
# FACTORY
# ============================================================

def create_monitor(
    get_open_trades: Callable,
    get_price: Callable,
    close_trade: Callable,
) -> PaperPositionMonitor:

    return PaperPositionMonitor(
        get_open_trades=
            get_open_trades,
        get_price=
            get_price,
        close_trade=
            close_trade,
    )