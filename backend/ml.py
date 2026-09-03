"""
INDIA AI TRADER V15
LIVE XGBOOST INFERENCE ENGINE

The live feature calculations in this file MUST stay aligned with
ml_train.py. The model supports both the current packaged dictionary
format and a raw XGBClassifier for backward compatibility.
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ml_model.joblib")

MODEL_VERSION = "V15"
INTERVAL_MINUTES = 5
HORIZON_CANDLES = 6

FEATURES = [
    "return_1", "return_3", "return_5", "return_10", "return_20",
    "price_ema9", "price_ema20", "price_ema50", "price_ema200",
    "ema9_20", "ema20_50", "ema50_200",
    "rsi", "macd", "macd_signal", "macd_hist",
    "atr_percent", "volatility", "price_vwap", "volume_ratio",
    "range_percent", "body_percent", "close_location",
    "momentum_5", "momentum_10", "bb_position",
]

CLASS_NAMES = {
    0: "SELL",
    1: "WAIT",
    2: "BUY",
}

MODEL = None
MODEL_META: Dict[str, Any] = {}
MODEL_ERROR: Optional[str] = None


def _load():
    global MODEL, MODEL_META, MODEL_ERROR

    if MODEL is not None:
        return MODEL

    if not os.path.exists(MODEL_PATH):
        MODEL_ERROR = f"Model not found: {MODEL_PATH}"
        return None

    try:
        bundle = joblib.load(MODEL_PATH)

        if isinstance(bundle, dict):
            MODEL = bundle.get("model")
            MODEL_META = bundle
            if MODEL is None:
                raise ValueError("Model bundle does not contain 'model'.")
        else:
            MODEL = bundle
            MODEL_META = {}

        return MODEL
    except Exception as exc:
        MODEL_ERROR = str(exc)
        MODEL = None
        return None


def model_status() -> Dict[str, Any]:
    model = _load()
    metadata = MODEL_META.get("metadata", MODEL_META) if isinstance(MODEL_META, dict) else {}

    return {
        "status": "success" if model is not None else "error",
        "model_loaded": model is not None,
        "model_exists": os.path.exists(MODEL_PATH),
        "model_path": MODEL_PATH,
        "model_type": type(model).__name__ if model is not None else None,
        "feature_count": len(FEATURES),
        "features": FEATURES,
        "version": MODEL_META.get("version", metadata.get("version", MODEL_VERSION)),
        "classes": MODEL_META.get("classes", {"0": "SELL", "1": "WAIT", "2": "BUY"}),
        "interval_minutes": MODEL_META.get("interval_minutes", INTERVAL_MINUTES),
        "horizon_candles": MODEL_META.get("horizon_candles", HORIZON_CANDLES),
        "metadata": metadata if metadata else {},
        "error": MODEL_ERROR,
    }


def _safe_numeric(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in result.columns:
            raise ValueError(f"Missing candle column: {col}")
        result[col] = pd.to_numeric(result[col], errors="coerce")
    result["volume"] = result["volume"].fillna(0)
    result = result.dropna(subset=["open", "high", "low", "close"])
    return result.reset_index(drop=True)


def calculate_features(candles) -> pd.DataFrame:
    """Generate the exact V15 26-feature schema using percentage units."""
    df = candles.copy() if isinstance(candles, pd.DataFrame) else pd.DataFrame(candles)
    df = _safe_numeric(df)
    if df.empty:
        return df

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # Returns as percentage, matching the historical V15 feature convention.
    df["return_1"] = close.pct_change(1) * 100
    df["return_3"] = close.pct_change(3) * 100
    df["return_5"] = close.pct_change(5) * 100
    df["return_10"] = close.pct_change(10) * 100
    df["return_20"] = close.pct_change(20) * 100

    # EMAs
    df["ema9"] = close.ewm(span=9, adjust=False).mean()
    df["ema20"] = close.ewm(span=20, adjust=False).mean()
    df["ema50"] = close.ewm(span=50, adjust=False).mean()
    df["ema200"] = close.ewm(span=200, adjust=False).mean()

    # Price vs EMA as percentage deviation.
    df["price_ema9"] = (close - df["ema9"]) / df["ema9"].replace(0, np.nan) * 100
    df["price_ema20"] = (close - df["ema20"]) / df["ema20"].replace(0, np.nan) * 100
    df["price_ema50"] = (close - df["ema50"]) / df["ema50"].replace(0, np.nan) * 100
    df["price_ema200"] = (close - df["ema200"]) / df["ema200"].replace(0, np.nan) * 100

    # EMA spreads as percentages.
    df["ema9_20"] = (df["ema9"] - df["ema20"]) / df["ema20"].replace(0, np.nan) * 100
    df["ema20_50"] = (df["ema20"] - df["ema50"]) / df["ema50"].replace(0, np.nan) * 100
    df["ema50_200"] = (df["ema50"] - df["ema200"]) / df["ema200"].replace(0, np.nan) * 100

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = (100 - (100 / (1 + rs))).fillna(50)

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # ATR / volatility as percentage.
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    df["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    df["atr_percent"] = df["atr"] / close.replace(0, np.nan) * 100
    df["volatility"] = close.pct_change().rolling(20).std() * 100

    # VWAP from available candle history.
    typical = (high + low + close) / 3
    cumulative_volume = volume.cumsum()
    cumulative_pv = (typical * volume).cumsum()
    df["vwap"] = (cumulative_pv / cumulative_volume.replace(0, np.nan)).fillna(close)
    df["price_vwap"] = (close - df["vwap"]) / df["vwap"].replace(0, np.nan) * 100

    # Volume ratio.
    volume_ma20 = volume.rolling(20).mean()
    df["volume_ratio"] = (
        volume / volume_ma20.replace(0, np.nan)
    )

    # Candle structure.
    candle_range = high - low
    df["range_percent"] = candle_range / close.replace(0, np.nan) * 100
    df["body_percent"] = (close - df["open"]).abs() / close.replace(0, np.nan) * 100
    df["close_location"] = (
        (close - low) / candle_range.replace(0, np.nan)
    )

    # Momentum as percentage.
    df["momentum_5"] = close.pct_change(5) * 100
    df["momentum_10"] = close.pct_change(10) * 100

    # Bollinger position.
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    df["bb_position"] = (
        (close - bb_lower) /
        (bb_upper - bb_lower).replace(0, np.nan)
    )

    df = df.replace([np.inf, -np.inf], np.nan)
    df[FEATURES] = df[FEATURES].ffill().bfill().fillna(0)

    return df


def _regime(df: pd.DataFrame) -> str:
    row = df.iloc[-1]
    price = float(row["close"])
    ema20 = float(row["ema20"])
    ema50 = float(row["ema50"])
    ema200 = float(row["ema200"])
    rsi = float(row["rsi"])

    if price > ema20 > ema50 > ema200 and rsi >= 60:
        return "STRONG BULLISH"
    if price > ema20 > ema50:
        return "BULLISH"
    if price < ema20 < ema50 < ema200 and rsi <= 40:
        return "STRONG BEARISH"
    if price < ema20 < ema50:
        return "BEARISH"
    return "SIDEWAYS"


def _trade_setup(signal: str, row: pd.Series) -> Dict[str, Optional[float]]:
    entry = float(row["close"])
    atr = float(row["atr"])

    if not math.isfinite(atr) or atr <= 0 or signal not in {"BUY", "SELL"}:
        return {
            "entry": round(entry, 2),
            "stop_loss": None,
            "target_1": None,
            "target_2": None,
            "risk_reward": None,
        }

    risk = 1.25 * atr

    if signal == "BUY":
        sl = entry - risk
        t1 = entry + 1.5 * risk
        t2 = entry + 2.5 * risk
    else:
        sl = entry + risk
        t1 = entry - 1.5 * risk
        t2 = entry - 2.5 * risk

    return {
        "entry": round(entry, 2),
        "stop_loss": round(sl, 2),
        "target_1": round(t1, 2),
        "target_2": round(t2, 2),
        "risk_reward": 1.5,
    }


def predict(candles) -> Dict[str, Any]:
    model = _load()

    if model is None:
        return {
            "signal": "WAIT",
            "raw_model_signal": "WAIT",
            "confidence": 0,
            "score": 0,
            "reason": f"ML model unavailable: {MODEL_ERROR or 'unknown error'}",
            "engine": "XGBOOST_ML",
            "model_loaded": False,
        }

    df = calculate_features(candles)

    if len(df) < 220:
        return {
            "signal": "WAIT",
            "raw_model_signal": "WAIT",
            "confidence": 0,
            "score": 0,
            "reason": f"Only {len(df)} usable candles; V15 needs at least 220.",
            "engine": "XGBOOST_ML",
            "model_loaded": True,
            "model_version": MODEL_META.get("version", MODEL_VERSION),
        }

    latest = df.iloc[-1]
    X = pd.DataFrame([latest[FEATURES].values], columns=FEATURES)

    try:
        probabilities = model.predict_proba(X)[0]
        prediction = int(model.predict(X)[0])
    except Exception as exc:
        return {
            "signal": "WAIT",
            "raw_model_signal": "WAIT",
            "confidence": 0,
            "score": 0,
            "reason": f"XGBoost inference failed: {exc}",
            "engine": "XGBOOST_ML",
            "model_loaded": True,
            "model_version": MODEL_META.get("version", MODEL_VERSION),
        }

    probability_map = {}
    for class_id, p in zip(getattr(model, "classes_", range(len(probabilities))), probabilities):
        probability_map[CLASS_NAMES.get(int(class_id), str(class_id))] = round(float(p) * 100, 2)

    for name in ("SELL", "WAIT", "BUY"):
        probability_map.setdefault(name, 0.0)

    raw_signal = CLASS_NAMES.get(prediction, "WAIT")
    regime = _regime(df)

    buy = probability_map["BUY"]
    sell = probability_map["SELL"]
    wait = probability_map["WAIT"]

    signal = raw_signal
    filter_reasons = []

    # Conservative directional threshold.
    if signal == "BUY":
        if buy < 45 or buy <= sell + 10:
            signal = "WAIT"
            filter_reasons.append("BUY probability/edge insufficient")
        elif regime in {"BEARISH", "STRONG BEARISH"}:
            signal = "WAIT"
            filter_reasons.append("bullish signal conflicts with bearish regime")
        elif float(latest["rsi"]) >= 78:
            signal = "WAIT"
            filter_reasons.append("BUY signal is extremely extended")

    elif signal == "SELL":
        if sell < 45 or sell <= buy + 10:
            signal = "WAIT"
            filter_reasons.append("SELL probability/edge insufficient")
        elif regime in {"BULLISH", "STRONG BULLISH"}:
            signal = "WAIT"
            filter_reasons.append("bearish signal conflicts with bullish regime")
        elif float(latest["rsi"]) <= 22:
            signal = "WAIT"
            filter_reasons.append("SELL signal is extremely extended")

    directional = max(buy, sell)
    score = round(buy - sell, 2)
    confidence = round(directional if signal != "WAIT" else max(wait, 100 - directional), 2)

    setup = _trade_setup(signal, latest)

    return {
        "signal": signal,
        "raw_model_signal": raw_signal,
        "confidence": confidence,
        "score": score,
        "reason": (
            f"V15 XGBoost prediction. "
            f"BUY={buy:.2f}%, WAIT={wait:.2f}%, SELL={sell:.2f}%. "
            f"Regime={regime}. "
            + ("Filter: " + "; ".join(filter_reasons) if filter_reasons else "")
        ),
        "engine": "V15_XGBOOST_ML",
        "model_loaded": True,
        "model_version": MODEL_META.get("version", MODEL_VERSION),
        "probabilities": {
            "BUY": buy,
            "WAIT": wait,
            "SELL": sell,
        },
        "class_probabilities": {
            "BUY": buy,
            "WAIT": wait,
            "SELL": sell,
        },
        "market_regime": regime,
        **setup,
        "model_metadata": {
            "version": MODEL_META.get("version", MODEL_VERSION),
            "interval_minutes": MODEL_META.get("interval_minutes", INTERVAL_MINUTES),
            "horizon_candles": MODEL_META.get("horizon_candles", HORIZON_CANDLES),
            "feature_count": len(FEATURES),
        },
        "indicators": {
            "rsi": round(float(latest["rsi"]), 2),
            "macd": round(float(latest["macd"]), 4),
            "macd_signal": round(float(latest["macd_signal"]), 4),
            "macd_hist": round(float(latest["macd_hist"]), 4),
            "ema9": round(float(latest["ema9"]), 2),
            "ema20": round(float(latest["ema20"]), 2),
            "ema50": round(float(latest["ema50"]), 2),
            "ema200": round(float(latest["ema200"]), 2),
            "vwap": round(float(latest["vwap"]), 2),
            "atr": round(float(latest["atr"]), 2),
            "atr_percent": round(float(latest["atr_percent"]), 4),
            "volume_ratio": round(float(latest["volume_ratio"]), 2),
            "volatility": round(float(latest["volatility"]), 4),
            "momentum_5": round(float(latest["momentum_5"]), 3),
            "momentum_10": round(float(latest["momentum_10"]), 3),
            "bb_position": round(float(latest["bb_position"]), 4),
        },
        "latest_close": round(float(latest["close"]), 2),
        "features": {
            name: round(float(latest[name]), 8)
            for name in FEATURES
        },
    }
