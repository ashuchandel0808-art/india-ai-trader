"""
INDIA AI TRADER V15
XGBOOST TRAINING ENGINE

Trains a packaged V15 model using the same 26-feature pipeline as ml.py.
Uses chronological splits and walk-forward validation.
No real orders are placed by this file.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from urllib.parse import quote

import joblib
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from ml import FEATURES, calculate_features

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
load_dotenv(override=True)

TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
if not TOKEN:
    raise RuntimeError("UPSTOX_ACCESS_TOKEN is not configured")

UPSTOX_V3 = "https://api.upstox.com/v3"
MODEL_PATH = os.path.join(BASE_DIR, "ml_model.joblib")
METADATA_PATH = os.path.join(BASE_DIR, "ml_metadata.json")

VERSION = "V15"
INTERVAL_MINUTES = 5
HORIZON = 6
LOOKBACK_DAYS = 30
MIN_ROWS = 300
MIN_TARGET_PCT = 0.30
ATR_MULTIPLIER = 0.80

STOCKS = {
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "INFY": "NSE_EQ|INE009A01021",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "SBIN": "NSE_EQ|INE062A01020",
}

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {TOKEN}",
}


def fetch_candles(instrument_key: str) -> pd.DataFrame:
    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=LOOKBACK_DAYS)
    encoded = quote(instrument_key, safe="")

    url = (
        f"{UPSTOX_V3}/historical-candle/"
        f"{encoded}/minutes/{INTERVAL_MINUTES}/"
        f"{to_date}/{from_date}"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Upstox {response.status_code}: {response.text}"
        )

    payload = response.json()
    raw = payload.get("data", {}).get("candles", [])

    rows = []
    for candle in raw:
        if len(candle) < 6:
            continue

        rows.append({
            "timestamp": candle[0],
            "open": float(candle[1]),
            "high": float(candle[2]),
            "low": float(candle[3]),
            "close": float(candle[4]),
            "volume": float(candle[5]),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(f"No candles returned for {instrument_key}")

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df = (
        df.dropna(subset=["timestamp"])
        .drop_duplicates("timestamp")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    return df


def create_target(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    close = result["close"]
    previous_close = close.shift(1)

    tr = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - previous_close).abs(),
            (result["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(
        alpha=1 / 14,
        adjust=False,
    ).mean()

    atr_pct = atr / close * 100.0

    threshold_pct = np.maximum(
        MIN_TARGET_PCT,
        ATR_MULTIPLIER * atr_pct,
    )

    future_return_pct = (
        close.shift(-HORIZON) / close - 1
    ) * 100.0

    result["future_return_pct"] = future_return_pct
    result["threshold_pct"] = threshold_pct

    result["target"] = np.where(
        future_return_pct > threshold_pct,
        2,
        np.where(
            future_return_pct < -threshold_pct,
            0,
            1,
        ),
    )

    return result


def make_dataset() -> pd.DataFrame:
    pieces: List[pd.DataFrame] = []

    print("=" * 70)
    print("INDIA AI TRADER V15 TRAINING")
    print("=" * 70)

    for symbol, instrument in STOCKS.items():
        print(f"\nDownloading: {symbol} {instrument}")

        candles = fetch_candles(instrument)
        print(f"{symbol} candles: {len(candles)}")

        if len(candles) < MIN_ROWS:
            print(f"Skipping {symbol}: insufficient candles")
            continue

        features = calculate_features(candles)
        labeled = create_target(features)

        labeled["symbol"] = symbol

        labeled = labeled.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        labeled = labeled.dropna(
            subset=FEATURES + ["target"]
        )

        # Drop final HORIZON rows because future outcome doesn't exist.
        if len(labeled) > HORIZON:
            labeled = labeled.iloc[:-HORIZON]

        print(
            f"{symbol} usable rows: {len(labeled)}"
        )

        if len(labeled) >= MIN_ROWS:
            pieces.append(labeled)

    if not pieces:
        raise RuntimeError("No usable training data")

    combined = pd.concat(
        pieces,
        ignore_index=True,
    )

    # Keep chronological ordering across all instruments.
    if "timestamp" in combined.columns:
        combined = combined.sort_values(
            ["timestamp", "symbol"]
        )

    return combined.reset_index(drop=True)


def create_model() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.035,
        min_child_weight=5,
        subsample=0.85,
        colsample_bytree=0.85,
        gamma=0.10,
        reg_alpha=0.05,
        reg_lambda=1.2,
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )


def evaluate_model(model, data: pd.DataFrame) -> Dict:
    X = data[FEATURES]
    y = data["target"].astype(int)

    predictions = model.predict(X)
    probabilities = model.predict_proba(X)

    accuracy = accuracy_score(y, predictions)
    balanced = balanced_accuracy_score(y, predictions)

    metrics = {
        "rows": int(len(data)),
        "accuracy": float(accuracy),
        "balanced_accuracy": float(balanced),
        "classification_report": classification_report(
            y,
            predictions,
            target_names=["SELL", "WAIT", "BUY"],
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(
            y,
            predictions,
        ).tolist(),
    }

    # Probability diagnostics.
    directional = np.maximum(
        probabilities[:, 0],
        probabilities[:, 2],
    )

    metrics["directional_probability_mean"] = float(
        directional.mean()
    )

    return metrics


def walk_forward(data: pd.DataFrame, folds: int = 4) -> List[Dict]:
    results = []
    n = len(data)

    if n < 500:
        return results

    fold_size = n // (folds + 1)

    for fold in range(1, folds + 1):
        train_end = fold_size * fold
        test_end = min(train_end + fold_size, n)

        if train_end < 300 or test_end <= train_end:
            continue

        train = data.iloc[:train_end]
        test = data.iloc[train_end:test_end]

        model = create_model()
        weights = compute_sample_weight(
            class_weight="balanced",
            y=train["target"].astype(int),
        )

        model.fit(
            train[FEATURES],
            train["target"].astype(int),
            sample_weight=weights,
            verbose=False,
        )

        metrics = evaluate_model(model, test)
        metrics["fold"] = fold
        results.append(metrics)

        print(
            f"Fold {fold}: "
            f"accuracy={metrics['accuracy']:.4f} "
            f"balanced={metrics['balanced_accuracy']:.4f}"
        )

    return results


def main():
    data = make_dataset()

    print("\nTOTAL TRAINING ROWS:", len(data))
    print("\nTARGET DISTRIBUTION:")
    print(
        data["target"]
        .value_counts(normalize=True)
        .sort_index()
    )

    # Chronological split.
    split = int(len(data) * 0.80)

    train = data.iloc[:split].copy()
    test = data.iloc[split:].copy()

    model = create_model()

    sample_weights = compute_sample_weight(
        class_weight="balanced",
        y=train["target"].astype(int),
    )

    print("\nTRAINING XGBOOST...")

    model.fit(
        train[FEATURES],
        train["target"].astype(int),
        sample_weight=sample_weights,
        verbose=False,
    )

    test_metrics = evaluate_model(
        model,
        test,
    )

    print("\nTEST RESULTS")
    print(
        json.dumps(
            {
                "accuracy": test_metrics["accuracy"],
                "balanced_accuracy": test_metrics["balanced_accuracy"],
                "confusion_matrix": test_metrics["confusion_matrix"],
            },
            indent=2,
        )
    )

    print("\nCLASSIFICATION REPORT")
    print(
        classification_report(
            test["target"],
            model.predict(test[FEATURES]),
            target_names=["SELL", "WAIT", "BUY"],
            zero_division=0,
        )
    )

    wf = walk_forward(data)

    feature_importance = {
        feature: float(value)
        for feature, value in zip(
            FEATURES,
            model.feature_importances_,
        )
    }

    feature_importance = dict(
        sorted(
            feature_importance.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    )

    metadata = {
        "features": FEATURES,
        "version": VERSION,
        "classes": {
            0: "SELL",
            1: "WAIT",
            2: "BUY",
        },
        "interval_minutes": INTERVAL_MINUTES,
        "horizon_candles": HORIZON,
        "buy_threshold_pct": MIN_TARGET_PCT / 100.0,
        "sell_threshold_pct": -MIN_TARGET_PCT / 100.0,
        "interval": f"{INTERVAL_MINUTES}minute",
        "lookback_days": LOOKBACK_DAYS,
        "target_method": "volatility_aware_forward_return",
        "target_threshold": "max(0.30%, 0.80 * ATR%)",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "test_metrics": test_metrics,
        "walk_forward": wf,
        "feature_importance": feature_importance,
        "stocks": STOCKS,
    }

    bundle = {
        "model": model,
        "features": FEATURES,
        "classes": {
            0: "SELL",
            1: "WAIT",
            2: "BUY",
        },
        "version": VERSION,
        "interval_minutes": INTERVAL_MINUTES,
        "horizon_candles": HORIZON,
        "buy_threshold_pct": MIN_TARGET_PCT / 100.0,
        "sell_threshold_pct": -MIN_TARGET_PCT / 100.0,
        "stocks": STOCKS,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "final_test_metrics": test_metrics,
        "walk_forward_metrics": wf,
        "metadata": metadata,
    }

    joblib.dump(
        bundle,
        MODEL_PATH,
    )

    with open(METADATA_PATH, "w", encoding="utf-8") as handle:
        json.dump(
            metadata,
            handle,
            indent=2,
            default=str,
        )

    print("\n" + "=" * 70)
    print("V15 MODEL SAVED")
    print(MODEL_PATH)
    print(METADATA_PATH)
    print("=" * 70)


if __name__ == "__main__":
    main()
