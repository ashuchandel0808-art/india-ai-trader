"""
INDIA AI TRADER V15.6-G
PERFORMANCE & OUTCOME ANALYTICS

Source of truth
---------------
SQLite trades + signals.

Purpose
-------
Measure what actually happened after a model decision.

Metrics
-------
- Total trades
- Wins / losses
- Win rate
- Gross profit
- Gross loss
- Profit factor
- Average win
- Average loss
- Expectancy per trade
- Maximum drawdown
- Return
- BUY performance
- SELL performance
- Symbol performance
- Regime performance
- Confidence-band performance

This module does NOT change:
- ML predictions
- Decision Engine
- Risk Engine
- Paper execution
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.db import get_connection


# ============================================================
# HELPERS
# ============================================================

def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        if value is None:
            return default

        number = float(value)

        if not math.isfinite(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def now_iso() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def normalize_probability(
    value: Any,
) -> Optional[float]:

    if value is None:
        return None

    number = safe_float(
        value,
        -1,
    )

    if number < 0:
        return None

    # Support either:
    # 0.72 or 72.0
    if 0 <= number <= 1:
        number *= 100

    return number


# ============================================================
# DATABASE READ
# ============================================================

def _fetch_closed_trades():

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                t.id,
                t.signal_id,
                t.symbol,
                t.side,
                t.quantity,
                t.entry_price,
                t.exit_price,
                t.stop_loss,
                t.target_price,
                t.pnl,
                t.exit_reason,
                t.status,
                t.opened_at,
                t.closed_at
            FROM trades t
            WHERE t.status = 'CLOSED'
            ORDER BY t.closed_at ASC, t.id ASC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def _fetch_signals():

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM signals
            ORDER BY id ASC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


# ============================================================
# SIGNAL LOOKUP
# ============================================================

def _index_signals(
    signals: List[Dict[str, Any]],
):

    result = {}

    for signal in signals:

        signal_id = signal.get(
            "id"
        )

        if signal_id is not None:

            result[
                safe_int(signal_id)
            ] = signal

    return result


# ============================================================
# CONFIDENCE BAND
# ============================================================

def confidence_band(
    probability: Optional[float],
) -> str:

    if probability is None:
        return "UNKNOWN"

    if probability < 50:
        return "<50%"

    if probability < 55:
        return "50-55%"

    if probability < 60:
        return "55-60%"

    if probability < 65:
        return "60-65%"

    if probability < 70:
        return "65-70%"

    if probability < 75:
        return "70-75%"

    return "75%+"


# ============================================================
# BASIC TRADE STATS
# ============================================================

def calculate_trade_stats(
    trades: List[Dict[str, Any]],
) -> Dict[str, Any]:

    pnl_values = [
        safe_float(
            trade.get("pnl")
        )
        for trade in trades
    ]

    wins = [
        pnl
        for pnl in pnl_values
        if pnl > 0
    ]

    losses = [
        pnl
        for pnl in pnl_values
        if pnl < 0
    ]

    gross_profit = sum(wins)

    gross_loss = abs(
        sum(losses)
    )

    total_pnl = sum(
        pnl_values
    )

    trade_count = len(
        pnl_values
    )

    win_count = len(wins)

    loss_count = len(losses)

    breakeven_count = (
        trade_count
        -
        win_count
        -
        loss_count
    )

    win_rate = (
        win_count /
        trade_count *
        100
        if trade_count
        else 0
    )

    average_win = (
        gross_profit /
        win_count
        if win_count
        else 0
    )

    average_loss = (
        gross_loss /
        loss_count
        if loss_count
        else 0
    )

    expectancy = (
        total_pnl /
        trade_count
        if trade_count
        else 0
    )

    profit_factor = (
        gross_profit /
        gross_loss
        if gross_loss > 0
        else (
            math.inf
            if gross_profit > 0
            else 0
        )
    )

    return {
        "trade_count":
            trade_count,
        "win_count":
            win_count,
        "loss_count":
            loss_count,
        "breakeven_count":
            breakeven_count,
        "win_rate":
            round(
                win_rate,
                4,
            ),
        "gross_profit":
            round(
                gross_profit,
                2,
            ),
        "gross_loss":
            round(
                gross_loss,
                2,
            ),
        "net_pnl":
            round(
                total_pnl,
                2,
            ),
        "average_win":
            round(
                average_win,
                2,
            ),
        "average_loss":
            round(
                average_loss,
                2,
            ),
        "expectancy_per_trade":
            round(
                expectancy,
                2,
            ),
        "profit_factor":
            (
                round(
                    profit_factor,
                    4,
                )
                if math.isfinite(
                    profit_factor
                )
                else "inf"
            ),
    }


# ============================================================
# EQUITY CURVE / DRAWDOWN
# ============================================================

def calculate_drawdown(
    trades: List[Dict[str, Any]],
    starting_capital: float,
):

    equity = (
        starting_capital
    )

    peak = equity

    max_drawdown = 0.0

    max_drawdown_percent = 0.0

    curve = []

    for trade in trades:

        pnl = safe_float(
            trade.get("pnl")
        )

        equity += pnl

        peak = max(
            peak,
            equity,
        )

        drawdown = (
            peak -
            equity
        )

        drawdown_percent = (
            drawdown /
            peak *
            100
            if peak > 0
            else 0
        )

        max_drawdown = max(
            max_drawdown,
            drawdown,
        )

        max_drawdown_percent = max(
            max_drawdown_percent,
            drawdown_percent,
        )

        curve.append({
            "trade_id":
                trade.get("id"),
            "closed_at":
                trade.get("closed_at"),
            "equity":
                round(
                    equity,
                    2,
                ),
            "drawdown":
                round(
                    drawdown,
                    2,
                ),
            "drawdown_percent":
                round(
                    drawdown_percent,
                    4,
                ),
        })

    total_return_percent = (
        (
            equity -
            starting_capital
        )
        /
        starting_capital *
        100
        if starting_capital > 0
        else 0
    )

    return {
        "starting_capital":
            round(
                starting_capital,
                2,
            ),
        "ending_equity":
            round(
                equity,
                2,
            ),
        "total_return_percent":
            round(
                total_return_percent,
                4,
            ),
        "max_drawdown":
            round(
                max_drawdown,
                2,
            ),
        "max_drawdown_percent":
            round(
                max_drawdown_percent,
                4,
            ),
        "equity_curve":
            curve,
    }


# ============================================================
# GROUPED PERFORMANCE
# ============================================================

def grouped_performance(
    trades: List[Dict[str, Any]],
    key_function,
):

    groups = defaultdict(list)

    for trade in trades:

        key = key_function(
            trade
        )

        groups[key].append(
            trade
        )

    result = {}

    for key, group in groups.items():

        result[
            str(key)
        ] = calculate_trade_stats(
            group
        )

    return result


# ============================================================
# MODEL-AWARE DATA
# ============================================================

def enrich_trades_with_signals(
    trades: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
):

    signal_map = _index_signals(
        signals
    )

    enriched = []

    for trade in trades:

        item = dict(
            trade
        )

        signal_id = (
            trade.get(
                "signal_id"
            )
        )

        signal = signal_map.get(
            safe_int(signal_id)
        )

        if signal:

            buy_probability = (
                normalize_probability(
                    signal.get(
                        "buy_probability"
                    )
                )
            )

            sell_probability = (
                normalize_probability(
                    signal.get(
                        "sell_probability"
                    )
                )
            )

            wait_probability = (
                normalize_probability(
                    signal.get(
                        "wait_probability"
                    )
                )
            )

            side = str(
                trade.get(
                    "side",
                    "",
                )
            ).upper()

            if side == "BUY":

                model_probability = (
                    buy_probability
                )

            elif side == "SELL":

                model_probability = (
                    sell_probability
                )

            else:

                model_probability = None

            item[
                "model_probability"
            ] = model_probability

            item[
                "confidence_band"
            ] = confidence_band(
                model_probability
            )

            item[
                "market_regime"
            ] = signal.get(
                "market_regime"
            )

            item[
                "model_signal"
            ] = signal.get(
                "signal"
            )

            item[
                "decision"
            ] = signal.get(
                "decision"
            )

        else:

            item[
                "model_probability"
            ] = None

            item[
                "confidence_band"
            ] = "UNKNOWN"

            item[
                "market_regime"
            ] = "UNKNOWN"

            item[
                "model_signal"
            ] = None

            item[
                "decision"
            ] = None

        enriched.append(
            item
        )

    return enriched


# ============================================================
# COMPLETE REPORT
# ============================================================

def generate_performance_report(
    starting_capital: float = 100000.0,
):

    trades = _fetch_closed_trades()

    signals = _fetch_signals()

    enriched = (
        enrich_trades_with_signals(
            trades,
            signals,
        )
    )

    stats = calculate_trade_stats(
        enriched
    )

    drawdown = calculate_drawdown(
        enriched,
        starting_capital,
    )

    by_symbol = grouped_performance(
        enriched,
        lambda trade:
            trade.get(
                "symbol",
                "UNKNOWN",
            ),
    )

    by_side = grouped_performance(
        enriched,
        lambda trade:
            str(
                trade.get(
                    "side",
                    "UNKNOWN",
                )
            ).upper(),
    )

    by_regime = grouped_performance(
        enriched,
        lambda trade:
            trade.get(
                "market_regime",
                "UNKNOWN",
            )
            or
            "UNKNOWN",
    )

    by_confidence = grouped_performance(
        enriched,
        lambda trade:
            trade.get(
                "confidence_band",
                "UNKNOWN",
            ),
    )

    by_exit_reason = grouped_performance(
        enriched,
        lambda trade:
            trade.get(
                "exit_reason",
                "UNKNOWN",
            )
            or
            "UNKNOWN",
    )

    by_model_signal = grouped_performance(
        enriched,
        lambda trade:
            trade.get(
                "model_signal",
                "UNKNOWN",
            )
            or
            "UNKNOWN",
    )

    # --------------------------------------------------------
    # BEST / WORST
    # --------------------------------------------------------

    best_trade = None

    worst_trade = None

    if enriched:

        best_trade = max(
            enriched,
            key=lambda trade:
                safe_float(
                    trade.get("pnl")
                ),
        )

        worst_trade = min(
            enriched,
            key=lambda trade:
                safe_float(
                    trade.get("pnl")
                ),
        )

    # --------------------------------------------------------
    # EXIT ANALYSIS
    # --------------------------------------------------------

    stop_loss_count = len([
        trade
        for trade in enriched
        if str(
            trade.get(
                "exit_reason",
                "",
            )
        ).upper()
        ==
        "STOP_LOSS"
    ])

    target_count = len([
        trade
        for trade in enriched
        if "TARGET"
        in str(
            trade.get(
                "exit_reason",
                "",
            )
        ).upper()
    ])

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {
        "status":
            "success",

        "generated_at":
            now_iso(),

        "summary":
            stats,

        "equity":
            drawdown,

        "execution_behavior":
            {
                "stop_loss_exits":
                    stop_loss_count,
                "target_exits":
                    target_count,
            },

        "by_symbol":
            by_symbol,

        "by_side":
            by_side,

        "by_market_regime":
            by_regime,

        "by_confidence_band":
            by_confidence,

        "by_model_signal":
            by_model_signal,

        "by_exit_reason":
            by_exit_reason,

        "best_trade":
            best_trade,

        "worst_trade":
            worst_trade,

        "closed_trades":
            enriched,
    }


# ============================================================
# SIMPLE SUMMARY
# ============================================================

def generate_summary(
    starting_capital: float = 100000.0,
):

    report = generate_performance_report(
        starting_capital
    )

    return {
        "status":
            "success",
        "generated_at":
            report[
                "generated_at"
            ],
        "summary":
            report[
                "summary"
            ],
        "equity":
            {
                "starting_capital":
                    report[
                        "equity"
                    ][
                        "starting_capital"
                    ],
                "ending_equity":
                    report[
                        "equity"
                    ][
                        "ending_equity"
                    ],
                "total_return_percent":
                    report[
                        "equity"
                    ][
                        "total_return_percent"
                    ],
                "max_drawdown":
                    report[
                        "equity"
                    ][
                        "max_drawdown"
                    ],
                "max_drawdown_percent":
                    report[
                        "equity"
                    ][
                        "max_drawdown_percent"
                    ],
            },
        "execution_behavior":
            report[
                "execution_behavior"
            ],
    }