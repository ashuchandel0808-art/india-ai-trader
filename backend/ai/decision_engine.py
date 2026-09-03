"""
INDIA AI TRADER V15.6-C
DECISION ENGINE

Purpose:
--------
Convert a V15 model prediction into a trading decision.

IMPORTANT:
----------
This is a decision/filtering layer.
It does NOT retrain or modify V15.

Possible decisions:
- TRADE
- WATCH
- NO_TRADE

The engine is intentionally conservative.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ============================================================
# CONFIGURATION
# ============================================================

MIN_DIRECTIONAL_PROBABILITY = 55.0
MIN_DIRECTIONAL_EDGE = 10.0

TRADE_SCORE_THRESHOLD = 70
WATCH_SCORE_THRESHOLD = 50

MIN_RISK_REWARD = 1.50

MAX_PORTFOLIO_RISK_PERCENT = 5.0


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


def _probabilities(
    analysis: Dict[str, Any],
):
    probabilities = (
        analysis.get(
            "probabilities"
        )
        or analysis.get(
            "class_probabilities"
        )
        or {}
    )

    buy = _float(
        probabilities.get(
            "BUY"
        )
    )

    sell = _float(
        probabilities.get(
            "SELL"
        )
    )

    wait = _float(
        probabilities.get(
            "WAIT"
        )
    )

    return buy, sell, wait


# ============================================================
# REGIME SCORE
# ============================================================

def regime_alignment(
    signal: str,
    regime: str,
):
    """
    Returns:
        score: 0-20
        blocker: optional reason
    """

    signal = (
        signal or "WAIT"
    ).upper()

    regime = (
        regime or "SIDEWAYS"
    ).upper()

    if signal == "BUY":

        if regime == "STRONG BULLISH":
            return 20, None

        if regime == "BULLISH":
            return 16, None

        if regime == "SIDEWAYS":
            return 8, None

        if regime == "BEARISH":
            return 3, (
                "Bullish signal conflicts "
                "with bearish market regime"
            )

        if regime == "STRONG BEARISH":
            return 0, (
                "Bullish signal conflicts "
                "with strong bearish regime"
            )

    if signal == "SELL":

        if regime == "STRONG BEARISH":
            return 20, None

        if regime == "BEARISH":
            return 16, None

        if regime == "SIDEWAYS":
            return 8, None

        if regime == "BULLISH":
            return 3, (
                "Bearish signal conflicts "
                "with bullish market regime"
            )

        if regime == "STRONG BULLISH":
            return 0, (
                "Bearish signal conflicts "
                "with strong bullish regime"
            )

    return 0, None


# ============================================================
# TECHNICAL CONFIRMATION
# ============================================================

def technical_confirmation(
    signal: str,
    indicators: Dict[str, Any],
):
    """
    Maximum score: 25
    """

    signal = (
        signal or "WAIT"
    ).upper()

    if signal == "WAIT":
        return 0, []

    score = 0
    reasons: List[str] = []

    rsi = _float(
        indicators.get(
            "rsi"
        ),
        50,
    )

    macd = _float(
        indicators.get(
            "macd"
        )
    )

    macd_signal = _float(
        indicators.get(
            "macd_signal"
        )
    )

    macd_hist = _float(
        indicators.get(
            "macd_hist"
        )
    )

    price = _float(
        indicators.get(
            "price"
        )
    )

    ema20 = _float(
        indicators.get(
            "ema20"
        )
    )

    ema50 = _float(
        indicators.get(
            "ema50"
        )
    )

    ema200 = _float(
        indicators.get(
            "ema200"
        )
    )

    vwap = _float(
        indicators.get(
            "vwap"
        )
    )

    volume_ratio = _float(
        indicators.get(
            "volume_ratio"
        ),
        0,
    )

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if signal == "BUY":

        if rsi >= 50:
            score += 4
            reasons.append(
                "RSI supports bullish momentum"
            )

        if 50 <= rsi <= 75:
            score += 2

        if macd > macd_signal:
            score += 4
            reasons.append(
                "MACD is bullish"
            )

        if macd_hist > 0:
            score += 3
            reasons.append(
                "MACD histogram is positive"
            )

        if (
            ema20 > 0
            and ema50 > 0
            and ema200 > 0
            and ema20 > ema50 > ema200
        ):
            score += 5
            reasons.append(
                "EMA trend structure is bullish"
            )

        if (
            price > 0
            and ema20 > 0
            and price > ema20
        ):
            score += 3

        if (
            price > 0
            and vwap > 0
            and price > vwap
        ):
            score += 2
            reasons.append(
                "Price is above VWAP"
            )

        if volume_ratio >= 1.2:
            score += 2
            reasons.append(
                "Volume confirms the move"
            )

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    elif signal == "SELL":

        if rsi <= 50:
            score += 4
            reasons.append(
                "RSI supports bearish momentum"
            )

        if 25 <= rsi <= 50:
            score += 2

        if macd < macd_signal:
            score += 4
            reasons.append(
                "MACD is bearish"
            )

        if macd_hist < 0:
            score += 3
            reasons.append(
                "MACD histogram is negative"
            )

        if (
            ema20 > 0
            and ema50 > 0
            and ema200 > 0
            and ema20 < ema50 < ema200
        ):
            score += 5
            reasons.append(
                "EMA trend structure is bearish"
            )

        if (
            price > 0
            and ema20 > 0
            and price < ema20
        ):
            score += 3

        if (
            price > 0
            and vwap > 0
            and price < vwap
        ):
            score += 2
            reasons.append(
                "Price is below VWAP"
            )

        if volume_ratio >= 1.2:
            score += 2
            reasons.append(
                "Volume confirms the move"
            )

    return min(
        score,
        25,
    ), reasons


# ============================================================
# RISK/REWARD
# ============================================================

def risk_reward_score(
    analysis: Dict[str, Any],
):
    rr = _float(
        analysis.get(
            "risk_reward"
        )
    )

    if rr <= 0:
        return 0, (
            "No valid risk/reward setup"
        )

    if rr < 1.0:
        return 0, (
            "Risk/reward below 1:1"
        )

    if rr < 1.5:
        return 4, (
            "Risk/reward is below preferred 1:1.5"
        )

    if rr < 2.0:
        return 8, None

    if rr < 3.0:
        return 10, None

    return 10, (
        None
    )


# ============================================================
# PORTFOLIO CHECK
# ============================================================

def portfolio_check(
    symbol: str,
    portfolio: Optional[Dict[str, Any]],
):
    """
    Portfolio-aware filter.

    Current version:
    - prevents duplicate excessive exposure
    - checks available cash
    - checks basic position count

    Returns:
        score: 0-15
        blockers: list
        reasons: list
    """

    if not portfolio:

        return 10, [], [
            "Portfolio context unavailable"
        ]

    score = 15
    blockers: List[str] = []
    reasons: List[str] = []

    cash = _float(
        portfolio.get(
            "cash"
        )
    )

    positions = (
        portfolio.get(
            "positions"
        )
        or []
    )

    current_symbol_positions = 0

    for position in positions:

        if (
            str(
                position.get(
                    "symbol",
                    ""
                )
            ).upper()
            ==
            symbol.upper()
        ):
            current_symbol_positions += 1

    # Duplicate exposure
    if current_symbol_positions >= 2:

        score -= 8

        blockers.append(
            "Multiple existing positions "
            f"in {symbol}"
        )

    elif current_symbol_positions == 1:

        score -= 3

        reasons.append(
            "Existing position in this symbol"
        )

    if cash <= 0:

        blockers.append(
            "No available paper cash"
        )

        score = 0

    if len(positions) >= 10:

        score -= 5

        reasons.append(
            "Portfolio already has many "
            "open positions"
        )

    return max(
        0,
        min(
            score,
            15,
        ),
    ), blockers, reasons


# ============================================================
# MAIN DECISION ENGINE
# ============================================================

def evaluate_trade(
    analysis: Dict[str, Any],
    symbol: Optional[str] = None,
    portfolio: Optional[Dict[str, Any]] = None,
):
    """
    Evaluate one V15 prediction.

    Returns structured decision information.
    """

    symbol = (
        symbol
        or analysis.get(
            "symbol"
        )
        or "UNKNOWN"
    )

    signal = str(
        analysis.get(
            "signal",
            "WAIT",
        )
    ).upper()

    raw_signal = str(
        analysis.get(
            "raw_model_signal",
            signal,
        )
    ).upper()

    regime = str(
        analysis.get(
            "market_regime",
            "SIDEWAYS",
        )
    ).upper()

    buy, sell, wait = (
        _probabilities(
            analysis
        )
    )

    indicators = (
        analysis.get(
            "indicators"
        )
        or {}
    )

    # Some model responses don't include price
    # inside indicators, so copy entry if needed.
    indicators = dict(
        indicators
    )

    indicators.setdefault(
        "price",
        analysis.get(
            "entry"
        )
    )

    # --------------------------------------------------------
    # WAIT MODEL OUTPUT
    # --------------------------------------------------------

    if signal == "WAIT":

        return {
            "decision":
                "NO_TRADE",
            "quality_score":
                0,
            "model_signal":
                raw_signal,
            "final_signal":
                "WAIT",
            "reasons":
                [
                    "V15 model did not produce "
                    "a directional trade signal"
                ],
            "blockers":
                [],
            "score_breakdown":
                {
                    "model":
                        0,
                    "regime":
                        0,
                    "technical":
                        0,
                    "risk_reward":
                        0,
                    "portfolio":
                        0,
                },
        }

    # --------------------------------------------------------
    # MODEL SCORE
    # Maximum: 40
    # --------------------------------------------------------

    directional_probability = (
        buy
        if signal == "BUY"
        else sell
    )

    opposite_probability = (
        sell
        if signal == "BUY"
        else buy
    )

    directional_edge = (
        directional_probability
        -
        opposite_probability
    )

    model_score = 0
    reasons: List[str] = []
    blockers: List[str] = []

    if (
        directional_probability
        >= 75
    ):

        model_score += 40

    elif (
        directional_probability
        >= 70
    ):

        model_score += 36

    elif (
        directional_probability
        >= 65
    ):

        model_score += 31

    elif (
        directional_probability
        >= 60
    ):

        model_score += 25

    elif (
        directional_probability
        >= 55
    ):

        model_score += 18

    else:

        blockers.append(
            (
                f"{signal} probability "
                f"{directional_probability:.2f}% "
                "is below trade threshold"
            )
        )

    if (
        directional_edge
        >= 20
    ):

        reasons.append(
            "Strong model directional edge"
        )

    elif (
        directional_edge
        >= 10
    ):

        reasons.append(
            "Positive model directional edge"
        )

    else:

        blockers.append(
            (
                f"Directional edge "
                f"{directional_edge:.2f}% "
                "is too small"
            )
        )

    # --------------------------------------------------------
    # REGIME
    # Maximum: 20
    # --------------------------------------------------------

    regime_score, regime_blocker = (
        regime_alignment(
            signal,
            regime,
        )
    )

    if regime_blocker:

        blockers.append(
            regime_blocker
        )

    # --------------------------------------------------------
    # TECHNICAL
    # Maximum: 25
    # --------------------------------------------------------

    technical_score, technical_reasons = (
        technical_confirmation(
            signal,
            indicators,
        )
    )

    reasons.extend(
        technical_reasons
    )

    # --------------------------------------------------------
    # RISK/REWARD
    # Maximum: 10
    # --------------------------------------------------------

    rr_score, rr_reason = (
        risk_reward_score(
            analysis
        )
    )

    if rr_reason:

        if rr_score == 0:

            blockers.append(
                rr_reason
            )

        else:

            reasons.append(
                rr_reason
            )

    # --------------------------------------------------------
    # PORTFOLIO
    # Maximum: 15
    # --------------------------------------------------------

    portfolio_score, portfolio_blockers, portfolio_reasons = (
        portfolio_check(
            symbol,
            portfolio,
        )
    )

    blockers.extend(
        portfolio_blockers
    )

    reasons.extend(
        portfolio_reasons
    )

    # --------------------------------------------------------
    # QUALITY SCORE
    #
    # The raw components total 110.
    # Normalize to 100.
    # --------------------------------------------------------

    raw_score = (
        model_score
        +
        regime_score
        +
        technical_score
        +
        rr_score
        +
        portfolio_score
    )

    quality_score = round(
        min(
            100,
            (
                raw_score /
                110 *
                100
            ),
        ),
        2,
    )

    # --------------------------------------------------------
    # FINAL DECISION
    # --------------------------------------------------------

    if blockers:

        decision = (
            "WATCH"
            if quality_score
            >= WATCH_SCORE_THRESHOLD
            else
            "NO_TRADE"
        )

    elif (
        quality_score
        >= TRADE_SCORE_THRESHOLD
        and
        directional_probability
        >= MIN_DIRECTIONAL_PROBABILITY
        and
        directional_edge
        >= MIN_DIRECTIONAL_EDGE
    ):

        rr = _float(
            analysis.get(
                "risk_reward"
            )
        )

        if (
            rr >= MIN_RISK_REWARD
            or rr == 0
        ):

            decision = "TRADE"

        else:

            decision = "WATCH"

            blockers.append(
                (
                    f"R:R {rr:.2f} below "
                    f"minimum {MIN_RISK_REWARD:.2f}"
                )
            )

    elif (
        quality_score
        >= WATCH_SCORE_THRESHOLD
    ):

        decision = "WATCH"

    else:

        decision = "NO_TRADE"

    # --------------------------------------------------------
    # FINAL SAFETY OVERRIDES
    # --------------------------------------------------------

    if regime == "STRONG BEARISH" and signal == "BUY":

        decision = "NO_TRADE"

        blockers.append(
            "Strong bearish regime blocks BUY"
        )

    if regime == "STRONG BULLISH" and signal == "SELL":

        decision = "NO_TRADE"

        blockers.append(
            "Strong bullish regime blocks SELL"
        )

    if directional_probability < 55:

        decision = "NO_TRADE"

    return {
        "decision":
            decision,

        "quality_score":
            quality_score,

        "model_signal":
            raw_signal,

        "final_signal":
            signal,

        "directional_probability":
            round(
                directional_probability,
                2,
            ),

        "directional_edge":
            round(
                directional_edge,
                2,
            ),

        "reasons":
            reasons,

        "blockers":
            blockers,

        "score_breakdown":
            {
                "model":
                    model_score,
                "regime":
                    regime_score,
                "technical":
                    technical_score,
                "risk_reward":
                    rr_score,
                "portfolio":
                    portfolio_score,
            },

        "risk_reward":
            _float(
                analysis.get(
                    "risk_reward"
                )
            ),

        "timestamp":
            __import__(
                "datetime"
            ).datetime.now(
                __import__(
                    "datetime"
                ).timezone.utc
            ).isoformat(),
    }


# ============================================================
# SIMPLE BATCH DECISION
# ============================================================

def evaluate_multiple(
    analyses: List[Dict[str, Any]],
    portfolio: Optional[Dict[str, Any]] = None,
):

    output = []

    for analysis in analyses:

        output.append(
            evaluate_trade(
                analysis,
                symbol=analysis.get(
                    "symbol"
                ),
                portfolio=portfolio,
            )
        )

    output.sort(
        key=lambda item:
            item.get(
                "quality_score",
                0,
            ),
        reverse=True,
    )

    return output