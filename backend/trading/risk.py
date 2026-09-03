"""
INDIA AI TRADER V15.6-D
RISK ENGINE

Purpose
-------
Convert an approved trading decision into a safe
position-sizing and risk decision.

The engine NEVER changes the ML prediction.

It only answers:

    How much can we risk?
    How many shares can we trade?
    Is the trade allowed?

Decisions
---------
APPROVE
REDUCE
REJECT

Default philosophy
------------------
Conservative first.

Default risk per trade:
1% of account equity

The engine applies the strictest limit from:
- risk budget
- available cash
- maximum position value
- portfolio exposure
- maximum open positions
- daily loss limit
- minimum risk/reward
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ============================================================
# DEFAULT RISK CONFIGURATION
# ============================================================

DEFAULT_RISK_PERCENT = 1.0

MAX_RISK_PERCENT = 2.0

MAX_POSITION_VALUE_PERCENT = 20.0

MAX_PORTFOLIO_EXPOSURE_PERCENT = 60.0

MAX_OPEN_POSITIONS = 5

MAX_DAILY_LOSS_PERCENT = 3.0

MIN_RISK_REWARD = 1.5

MIN_TRADE_VALUE = 500.0


# ============================================================
# HELPERS
# ============================================================

def _float(
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


def _int(
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


def _positive(
    value: Any,
) -> float:

    number = _float(
        value
    )

    return max(
        number,
        0.0,
    )


# ============================================================
# RISK CONFIG
# ============================================================

@dataclass
class RiskConfig:

    risk_percent: float = (
        DEFAULT_RISK_PERCENT
    )

    max_risk_percent: float = (
        MAX_RISK_PERCENT
    )

    max_position_value_percent: float = (
        MAX_POSITION_VALUE_PERCENT
    )

    max_portfolio_exposure_percent: float = (
        MAX_PORTFOLIO_EXPOSURE_PERCENT
    )

    max_open_positions: int = (
        MAX_OPEN_POSITIONS
    )

    max_daily_loss_percent: float = (
        MAX_DAILY_LOSS_PERCENT
    )

    min_risk_reward: float = (
        MIN_RISK_REWARD
    )

    min_trade_value: float = (
        MIN_TRADE_VALUE
    )


# ============================================================
# PORTFOLIO METRICS
# ============================================================

def calculate_portfolio_metrics(
    portfolio: Optional[Dict[str, Any]],
) -> Dict[str, float]:

    if not portfolio:

        return {
            "starting_capital": 0.0,
            "cash": 0.0,
            "market_value": 0.0,
            "equity": 0.0,
            "exposure": 0.0,
            "exposure_percent": 0.0,
            "open_positions": 0.0,
        }

    starting_capital = _positive(
        portfolio.get(
            "starting_capital"
        )
    )

    cash = _positive(
        portfolio.get(
            "cash"
        )
    )

    market_value = 0.0

    positions = (
        portfolio.get(
            "positions"
        )
        or []
    )

    for position in positions:

        quantity = _int(
            position.get(
                "quantity"
            )
        )

        average_price = _positive(
            position.get(
                "average_price"
            )
        )

        market_value += (
            quantity *
            average_price
        )

    equity = (
        cash +
        market_value
    )

    exposure_percent = (
        market_value /
        equity *
        100
        if equity > 0
        else 0.0
    )

    return {
        "starting_capital":
            starting_capital,

        "cash":
            cash,

        "market_value":
            market_value,

        "equity":
            equity,

        "exposure":
            market_value,

        "exposure_percent":
            exposure_percent,

        "open_positions":
            float(
                len(positions)
            ),
    }


# ============================================================
# DAILY P&L
# ============================================================

def calculate_daily_realized_pnl(
    paper_trades: Optional[List[Dict[str, Any]]],
    date_prefix: Optional[str] = None,
) -> float:

    if not paper_trades:
        return 0.0

    if date_prefix is None:

        from datetime import datetime, timezone

        date_prefix = (
            datetime.now(
                timezone.utc
            ).date().isoformat()
        )

    total = 0.0

    for trade in paper_trades:

        if trade.get(
            "status"
        ) != "CLOSED":

            continue

        closed_at = str(
            trade.get(
                "closed_at",
                "",
            )
        )

        if not closed_at.startswith(
            date_prefix
        ):

            continue

        total += _float(
            trade.get(
                "realized_pnl"
            )
        )

    return total


# ============================================================
# DAILY LOSS CHECK
# ============================================================

def daily_loss_check(
    equity: float,
    daily_realized_pnl: float,
    config: RiskConfig,
):

    if equity <= 0:

        return {
            "allowed":
                False,
            "reason":
                "Invalid account equity.",
            "daily_loss_percent":
                0.0,
        }

    daily_loss_percent = (
        abs(
            min(
                daily_realized_pnl,
                0.0,
            )
        )
        /
        equity
        *
        100
    )

    if (
        daily_loss_percent
        >=
        config.max_daily_loss_percent
    ):

        return {
            "allowed":
                False,
            "reason":
                (
                    f"Daily loss limit reached: "
                    f"{daily_loss_percent:.2f}% "
                    f">= "
                    f"{config.max_daily_loss_percent:.2f}%"
                ),
            "daily_loss_percent":
                daily_loss_percent,
        }

    return {
        "allowed":
            True,
        "reason":
            None,
        "daily_loss_percent":
            daily_loss_percent,
    }


# ============================================================
# CORE RISK CALCULATION
# ============================================================

def calculate_risk(
    *,
    symbol: str,
    side: str,
    entry: float,
    stop_loss: Optional[float],
    target_1: Optional[float],
    target_2: Optional[float],
    risk_reward: Optional[float],
    portfolio: Optional[Dict[str, Any]],
    paper_trades: Optional[List[Dict[str, Any]]] = None,
    config: Optional[RiskConfig] = None,
) -> Dict[str, Any]:

    if config is None:

        config = RiskConfig()

    # --------------------------------------------------------
    # Normalize inputs
    # --------------------------------------------------------

    symbol = (
        symbol
        or "UNKNOWN"
    ).upper()

    side = (
        side
        or "BUY"
    ).upper()

    entry = _positive(
        entry
    )

    stop = _positive(
        stop_loss
    )

    target1 = _positive(
        target_1
    )

    target2 = _positive(
        target_2
    )

    rr = _positive(
        risk_reward
    )

    # --------------------------------------------------------
    # Portfolio
    # --------------------------------------------------------

    portfolio_metrics = (
        calculate_portfolio_metrics(
            portfolio
        )
    )

    equity = portfolio_metrics[
        "equity"
    ]

    cash = portfolio_metrics[
        "cash"
    ]

    current_exposure = (
        portfolio_metrics[
            "exposure"
        ]
    )

    current_exposure_percent = (
        portfolio_metrics[
            "exposure_percent"
        ]
    )

    open_positions = _int(
        portfolio_metrics[
            "open_positions"
        ]
    )

    # --------------------------------------------------------
    # Base result
    # --------------------------------------------------------

    reasons: List[str] = []

    blockers: List[str] = []

    warnings: List[str] = []

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if side not in {
        "BUY",
        "SELL",
    }:

        blockers.append(
            "Invalid side. Use BUY or SELL."
        )

    if entry <= 0:

        blockers.append(
            "Entry price must be positive."
        )

    if stop <= 0:

        blockers.append(
            "Stop-loss is required."
        )

    if equity <= 0:

        blockers.append(
            "Portfolio equity must be positive."
        )

    # --------------------------------------------------------
    # Stop direction validation
    # --------------------------------------------------------

    if (
        entry > 0
        and stop > 0
    ):

        if side == "BUY":

            if stop >= entry:

                blockers.append(
                    "BUY stop-loss must be below entry."
                )

        else:

            if stop <= entry:

                blockers.append(
                    "SELL stop-loss must be above entry."
                )

    # --------------------------------------------------------
    # Risk per share
    # --------------------------------------------------------

    risk_per_share = abs(
        entry -
        stop
    )

    if (
        risk_per_share <= 0
    ):

        blockers.append(
            "Stop-loss distance is zero."
        )

    # --------------------------------------------------------
    # Risk budget
    # --------------------------------------------------------

    risk_percent = min(
        max(
            config.risk_percent,
            0.1,
        ),
        config.max_risk_percent,
    )

    max_risk_amount = (
        equity *
        risk_percent /
        100
    )

    # --------------------------------------------------------
    # Risk-based quantity
    # --------------------------------------------------------

    if risk_per_share > 0:

        quantity_by_risk = int(
            max_risk_amount /
            risk_per_share
        )

    else:

        quantity_by_risk = 0

    # --------------------------------------------------------
    # Position value limit
    # --------------------------------------------------------

    maximum_position_value = (
        equity *
        config.max_position_value_percent
        /
        100
    )

    quantity_by_position_value = (
        int(
            maximum_position_value /
            entry
        )
        if entry > 0
        else 0
    )

    # --------------------------------------------------------
    # Available cash limit
    # --------------------------------------------------------

    quantity_by_cash = (
        int(
            cash /
            entry
        )
        if entry > 0
        else 0
    )

    # --------------------------------------------------------
    # Portfolio exposure limit
    # --------------------------------------------------------

    maximum_portfolio_exposure = (
        equity *
        config.max_portfolio_exposure_percent
        /
        100
    )

    remaining_exposure_capacity = max(
        maximum_portfolio_exposure -
        current_exposure,
        0.0,
    )

    quantity_by_portfolio = (
        int(
            remaining_exposure_capacity /
            entry
        )
        if entry > 0
        else 0
    )

    # --------------------------------------------------------
    # Open-position limit
    # --------------------------------------------------------

    position_limit_allowed = (
        open_positions
        <
        config.max_open_positions
    )

    # --------------------------------------------------------
    # Determine final quantity
    # --------------------------------------------------------

    quantity_candidates = [
        quantity_by_risk,
        quantity_by_position_value,
        quantity_by_cash,
        quantity_by_portfolio,
    ]

    quantity_candidates = [
        value
        for value in quantity_candidates
        if value >= 0
    ]

    quantity = min(
        quantity_candidates
    ) if quantity_candidates else 0

    # --------------------------------------------------------
    # Special handling for SELL
    #
    # Paper trading supports a development
    # short model, so cash isn't used as the
    # sole short-side constraint.
    # --------------------------------------------------------

    if side == "SELL":

        quantity = min(
            quantity_by_risk,
            quantity_by_position_value,
            quantity_by_portfolio,
        )

    # --------------------------------------------------------
    # Trade value
    # --------------------------------------------------------

    trade_value = (
        quantity *
        entry
    )

    # --------------------------------------------------------
    # Actual maximum loss
    # --------------------------------------------------------

    maximum_loss = (
        quantity *
        risk_per_share
    )

    actual_risk_percent = (
        maximum_loss /
        equity *
        100
        if equity > 0
        else 0
    )

    # --------------------------------------------------------
    # Risk/reward validation
    # --------------------------------------------------------

    if rr > 0:

        if (
            rr <
            config.min_risk_reward
        ):

            warnings.append(
                (
                    f"Risk/reward {rr:.2f} "
                    f"is below preferred "
                    f"{config.min_risk_reward:.2f}."
                )
            )

    elif (
        target1 > 0
        and risk_per_share > 0
    ):

        reward = abs(
            target1 -
            entry
        )

        calculated_rr = (
            reward /
            risk_per_share
        )

        rr = calculated_rr

        if (
            rr <
            config.min_risk_reward
        ):

            warnings.append(
                (
                    f"Calculated risk/reward "
                    f"{rr:.2f} is below "
                    f"preferred "
                    f"{config.min_risk_reward:.2f}."
                )
            )

    # --------------------------------------------------------
    # Portfolio constraints
    # --------------------------------------------------------

    if (
        open_positions >=
        config.max_open_positions
    ):

        blockers.append(
            (
                f"Maximum open position "
                f"limit reached: "
                f"{open_positions}/"
                f"{config.max_open_positions}"
            )
        )

    # --------------------------------------------------------
    # Daily loss
    # --------------------------------------------------------

    daily_pnl = (
        calculate_daily_realized_pnl(
            paper_trades
        )
    )

    daily_check = (
        daily_loss_check(
            equity,
            daily_pnl,
            config,
        )
    )

    if not daily_check[
        "allowed"
    ]:

        blockers.append(
            daily_check[
                "reason"
            ]
        )

    # --------------------------------------------------------
    # Quantity checks
    # --------------------------------------------------------

    if quantity <= 0:

        blockers.append(
            "Calculated position size is zero."
        )

    if (
        trade_value <
        config.min_trade_value
        and
        quantity > 0
    ):

        warnings.append(
            (
                f"Trade value ₹{trade_value:,.2f} "
                f"is below recommended "
                f"minimum ₹{config.min_trade_value:,.2f}."
            )
        )

    # --------------------------------------------------------
    # Add useful reasons
    # --------------------------------------------------------

    if (
        quantity ==
        quantity_by_risk
    ):

        reasons.append(
            "Position size is limited by risk budget."
        )

    if (
        quantity ==
        quantity_by_position_value
    ):

        reasons.append(
            "Position size is limited by maximum position value."
        )

    if (
        side == "BUY"
        and
        quantity ==
        quantity_by_cash
    ):

        reasons.append(
            "Position size is limited by available cash."
        )

    if (
        quantity ==
        quantity_by_portfolio
    ):

        reasons.append(
            "Position size is limited by portfolio exposure."
        )

    if daily_check[
        "allowed"
    ]:

        reasons.append(
            "Daily loss limit is currently available."
        )

    # --------------------------------------------------------
    # Final risk decision
    # --------------------------------------------------------

    if blockers:

        risk_decision = "REJECT"

    elif quantity <= 0:

        risk_decision = "REJECT"

    elif (
        actual_risk_percent <
        risk_percent * 0.999
    ):

        risk_decision = "REDUCE"

    else:

        risk_decision = "APPROVE"

    # --------------------------------------------------------
    # Risk score
    # --------------------------------------------------------

    risk_score = 100

    risk_score -= (
        len(blockers) *
        30
    )

    risk_score -= (
        len(warnings) *
        5
    )

    if (
        current_exposure_percent >
        config.max_portfolio_exposure_percent
        * 0.75
    ):

        risk_score -= 10

    if (
        daily_check[
            "daily_loss_percent"
        ]
        >
        config.max_daily_loss_percent
        * 0.5
    ):

        risk_score -= 10

    risk_score = max(
        0,
        min(
            100,
            risk_score,
        ),
    )

    return {
        "risk_decision":
            risk_decision,

        "risk_score":
            risk_score,

        "symbol":
            symbol,

        "side":
            side,

        "entry":
            entry,

        "stop_loss":
            stop if stop > 0 else None,

        "target_1":
            target1 if target1 > 0 else None,

        "target_2":
            target2 if target2 > 0 else None,

        "risk_reward":
            round(
                rr,
                4,
            ),

        "risk_percent":
            risk_percent,

        "maximum_risk_amount":
            round(
                max_risk_amount,
                2,
            ),

        "risk_per_share":
            round(
                risk_per_share,
                4,
            ),

        "quantity":
            quantity,

        "maximum_loss":
            round(
                maximum_loss,
                2,
            ),

        "actual_risk_percent":
            round(
                actual_risk_percent,
                4,
            ),

        "trade_value":
            round(
                trade_value,
                2,
            ),

        "available_cash":
            round(
                cash,
                2,
            ),

        "current_portfolio_exposure":
            round(
                current_exposure,
                2,
            ),

        "current_portfolio_exposure_percent":
            round(
                current_exposure_percent,
                2,
            ),

        "remaining_portfolio_capacity":
            round(
                remaining_exposure_capacity,
                2,
            ),

        "open_positions":
            open_positions,

        "max_open_positions":
            config.max_open_positions,

        "daily_realized_pnl":
            round(
                daily_pnl,
                2,
            ),

        "daily_loss_percent":
            round(
                daily_check[
                    "daily_loss_percent"
                ],
                4,
            ),

        "reasons":
            reasons,

        "warnings":
            warnings,

        "blockers":
            blockers,

        "limits":
            {
                "risk_percent":
                    risk_percent,
                "max_position_value_percent":
                    config.max_position_value_percent,
                "max_portfolio_exposure_percent":
                    config.max_portfolio_exposure_percent,
                "max_daily_loss_percent":
                    config.max_daily_loss_percent,
                "min_risk_reward":
                    config.min_risk_reward,
            },
    }