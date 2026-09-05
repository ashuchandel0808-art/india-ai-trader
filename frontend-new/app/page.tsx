"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type ProbabilitySet = {
  BUY: number;
  WAIT: number;
  SELL: number;
};

type Indicators = {
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_hist?: number;
  ema9?: number;
  ema20?: number;
  ema50?: number;
  ema200?: number;
  vwap?: number;
  atr?: number;
  atr_percent?: number;
  volume_ratio?: number;
  volatility?: number;
  momentum_5?: number;
  momentum_10?: number;
  bb_position?: number;
};

type Decision = {
  decision?: string;
  quality_score?: number;
  model_signal?: string;
  final_signal?: string;
  directional_probability?: number;
  directional_edge?: number;
  reasons?: string[];
  blockers?: string[];
  risk_reward?: number;
};

type Risk = {
  risk_decision?: string;
  risk_score?: number;
  quantity?: number;
  maximum_loss?: number;
  available_cash?: number;
  trade_value?: number;
  risk_per_share?: number;
  blockers?: string[];
  warnings?: string[];
};

type InstrumentSignal = {
  signal?: string;
  raw_model_signal?: string;
  confidence?: number;
  score?: number;
  reason?: string;
  model_loaded?: boolean;
  model_version?: string;
  probabilities?: ProbabilitySet;
  market_regime?: string;
  entry?: number;
  stop_loss?: number;
  target_1?: number;
  target_2?: number;
  risk_reward?: number;
  indicators?: Indicators;
  latest_close?: number;
  calibrated_probabilities?: ProbabilitySet;
  v16_signal?: string;
  candle_timestamp?: string;
  candle_age_seconds?: number;
  candle_age_minutes?: number;
  candle_complete?: boolean;
  candle_is_stale?: boolean;
  candle_data_quality?: string;
  symbol?: string;
  decision?: Decision;
  risk?: Risk;
};

type VixData = {
  symbol?: string;
  last_price?: number;
  previous_close?: number;
  change?: number;
  change_percent?: number;
  volume?: number;
  timestamp?: string;
};

type PersistenceItem = {
  saved?: boolean;
  duplicate?: boolean;
  blocked?: boolean;
  reason?: string;
  candle_timestamp?: string;
  candle_age_minutes?: number;
};

type AiSignalResponse = {
  status?: string;
  version?: string;
  ai_signal?: string;
  confidence?: number;
  score?: number;
  market_regime?: string;
  engine?: string;
  production_model?: {
    model?: string;
    version?: string;
  };
  model_loaded?: boolean;
  decision_engine_loaded?: boolean;
  risk_engine_loaded?: boolean;
  paper_engine_loaded?: boolean;
  monitor_engine_loaded?: boolean;
  analytics_engine_loaded?: boolean;
  outcome_engine_loaded?: boolean;
  calibration_engine_loaded?: boolean;
  outcome_resolver_loaded?: boolean;
  prediction_gate_loaded?: boolean;
  v16_engine_loaded?: boolean;
  combined_probabilities?: ProbabilitySet;
  nifty_signal?: InstrumentSignal;
  banknifty_signal?: InstrumentSignal;
  market_decision?: Decision;
  vix?: VixData;
  persistence?: {
    nifty?: PersistenceItem;
    banknifty?: PersistenceItem;
  };
  paper_trading?: {
    enabled?: boolean;
    real_orders?: boolean;
    status?: string;
  };
  outcomes?: {
    nifty?: unknown;
    banknifty?: unknown;
  };
  timestamp?: string;
};

type HealthResponse = {
  status?: string;
  application?: string;
  version?: string;
  upstox_configured?: boolean;
  ml_engine_loaded?: boolean;
  decision_engine_loaded?: boolean;
  risk_engine_loaded?: boolean;
  paper_engine_loaded?: boolean;
  monitor_engine_loaded?: boolean;
  analytics_engine_loaded?: boolean;
  outcome_engine_loaded?: boolean;
  calibration_engine_loaded?: boolean;
  model_registry_loaded?: boolean;
  v16_engine_loaded?: boolean;
  outcome_resolver_loaded?: boolean;
  prediction_gate_loaded?: boolean;
  database_loaded?: boolean;
  feature_count?: number;
  production_model?: {
    model?: string;
    version?: string;
  };
  paper_trading?: boolean;
  real_money?: boolean;
  timestamp?: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const REFRESH_INTERVAL = 5000;

function formatNumber(value?: number, digits = 2) {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "--";
  }

  return value.toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatPercent(value?: number) {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "--";
  }

  return `${value.toFixed(2)}%`;
}

function signalClass(signal?: string) {
  const value = signal?.toUpperCase();

  if (value === "BUY") return "buy";
  if (value === "SELL") return "sell";
  return "wait";
}

function statusClass(status?: string) {
  const value = status?.toUpperCase();

  if (
    value === "LIVE" ||
    value === "SUCCESS" ||
    value === "CONNECTED" ||
    value === "LOADED" ||
    value === "ENABLED" ||
    value === "HEALTHY"
  ) {
    return "good";
  }

  if (
    value === "STALE" ||
    value === "REJECT" ||
    value === "NO_TRADE" ||
    value === "BLOCKED"
  ) {
    return "warning";
  }

  return "neutral";
}

function probabilityBar(value: number | undefined, type: "buy" | "wait" | "sell") {
  const safeValue = Math.max(0, Math.min(100, value ?? 0));

  return (
    <div className="probability-row">
      <div className={`probability-label ${type}`}>
        {type.toUpperCase()}
      </div>

      <div className="probability-track">
        <div
          className={`probability-fill ${type}`}
          style={{ width: `${safeValue}%` }}
        />
      </div>

      <div className="probability-value">
        {safeValue.toFixed(2)}%
      </div>
    </div>
  );
}

function EngineItem({
  label,
  enabled,
}: {
  label: string;
  enabled?: boolean;
}) {
  return (
    <div className="engine-item">
      <span className={`engine-dot ${enabled ? "active" : "inactive"}`} />
      <span>{label}</span>
      <span className={`engine-state ${enabled ? "active" : "inactive"}`}>
        {enabled ? "LOADED" : "OFF"}
      </span>
    </div>
  );
}

function InstrumentCard({
  title,
  data,
}: {
  title: string;
  data?: InstrumentSignal;
}) {
  if (!data) {
    return (
      <div className="card">
        <div className="card-title">{title}</div>
        <div className="empty-state">No signal data available</div>
      </div>
    );
  }

  const signal = data.signal || "WAIT";
  const indicators = data.indicators;
  const decision = data.decision;
  const risk = data.risk;

  return (
    <div className="card instrument-card">
      <div className="instrument-header">
        <div>
          <div className="card-title">{title}</div>

          <div className="small-muted">
            Model {data.model_version || "V15"} • 5 minute horizon
          </div>
        </div>

        <div className={`large-signal ${signalClass(signal)}`}>
          {signal}
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-box">
          <span>Confidence</span>
          <strong>{formatPercent(data.confidence)}</strong>
        </div>

        <div className="metric-box">
          <span>Score</span>
          <strong>{formatNumber(data.score)}</strong>
        </div>

        <div className="metric-box">
          <span>Regime</span>
          <strong className="small-value">
            {data.market_regime || "--"}
          </strong>
        </div>

        <div className="metric-box">
          <span>Last Price</span>
          <strong>{formatNumber(data.latest_close)}</strong>
        </div>
      </div>

      <div className="section-block">
        <div className="section-heading">Model Probabilities</div>

        {probabilityBar(data.probabilities?.BUY, "buy")}
        {probabilityBar(data.probabilities?.WAIT, "wait")}
        {probabilityBar(data.probabilities?.SELL, "sell")}
      </div>

      <div className="section-block">
        <div className="section-heading">Technical Indicators</div>

        <div className="indicator-grid">
          <div>
            <span>RSI</span>
            <strong>{formatNumber(indicators?.rsi)}</strong>
          </div>

          <div>
            <span>MACD</span>
            <strong>{formatNumber(indicators?.macd)}</strong>
          </div>

          <div>
            <span>MACD Hist</span>
            <strong>{formatNumber(indicators?.macd_hist)}</strong>
          </div>

          <div>
            <span>EMA 9</span>
            <strong>{formatNumber(indicators?.ema9)}</strong>
          </div>

          <div>
            <span>EMA 20</span>
            <strong>{formatNumber(indicators?.ema20)}</strong>
          </div>

          <div>
            <span>EMA 50</span>
            <strong>{formatNumber(indicators?.ema50)}</strong>
          </div>

          <div>
            <span>EMA 200</span>
            <strong>{formatNumber(indicators?.ema200)}</strong>
          </div>

          <div>
            <span>ATR</span>
            <strong>{formatNumber(indicators?.atr)}</strong>
          </div>

          <div>
            <span>Momentum 5</span>
            <strong>{formatNumber(indicators?.momentum_5)}</strong>
          </div>

          <div>
            <span>Momentum 10</span>
            <strong>{formatNumber(indicators?.momentum_10)}</strong>
          </div>

          <div>
            <span>BB Position</span>
            <strong>{formatNumber(indicators?.bb_position)}</strong>
          </div>

          <div>
            <span>Volatility</span>
            <strong>{formatNumber(indicators?.volatility)}</strong>
          </div>
        </div>
      </div>

      <div className="trade-levels">
        <div>
          <span>Entry</span>
          <strong>{formatNumber(data.entry)}</strong>
        </div>

        <div>
          <span>Stop Loss</span>
          <strong>{formatNumber(data.stop_loss)}</strong>
        </div>

        <div>
          <span>Target 1</span>
          <strong>{formatNumber(data.target_1)}</strong>
        </div>

        <div>
          <span>Target 2</span>
          <strong>{formatNumber(data.target_2)}</strong>
        </div>
      </div>

      <div className="decision-section">
        <div className="decision-row">
          <span>Decision Engine</span>
          <strong className={statusClass(decision?.decision)}>
            {decision?.decision || "--"}
          </strong>
        </div>

        <div className="decision-row">
          <span>Quality Score</span>
          <strong>
            {decision?.quality_score !== undefined
              ? decision.quality_score.toFixed(2)
              : "--"}
          </strong>
        </div>

        <div className="decision-row">
          <span>Risk Engine</span>
          <strong className={statusClass(risk?.risk_decision)}>
            {risk?.risk_decision || "--"}
          </strong>
        </div>

        <div className="decision-row">
          <span>Quantity</span>
          <strong>{risk?.quantity ?? 0}</strong>
        </div>
      </div>

      {(data.candle_is_stale || data.candle_data_quality === "STALE") && (
        <div className="stale-warning">
          <strong>STALE MARKET DATA</strong>
          <span>
            Latest candle:{" "}
            {data.candle_timestamp
              ? new Date(data.candle_timestamp).toLocaleString("en-IN")
              : "--"}
          </span>
          <span>
            Age:{" "}
            {data.candle_age_minutes !== undefined
              ? `${data.candle_age_minutes.toFixed(2)} minutes`
              : "--"}
          </span>
        </div>
      )}

      {decision?.blockers && decision.blockers.length > 0 && (
        <div className="blocker-box">
          <div className="section-heading">Trade Blockers</div>
          {decision.blockers.map((blocker, index) => (
            <div key={index}>• {blocker}</div>
          ))}
        </div>
      )}

      {data.reason && (
        <div className="reason-box">
          <div className="section-heading">AI Reason</div>
          <p>{data.reason}</p>
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [signalData, setSignalData] = useState<AiSignalResponse | null>(null);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);

  const [loadingSignal, setLoadingSignal] = useState(true);
  const [loadingHealth, setLoadingHealth] = useState(true);

  const [signalError, setSignalError] = useState("");
  const [healthError, setHealthError] = useState("");

  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/health`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`Health request failed: ${response.status}`);
      }

      const data: HealthResponse = await response.json();

      setHealthData(data);
      setHealthError("");
    } catch (error) {
      console.error("Health error:", error);

      setHealthError(
        error instanceof Error ? error.message : "Unable to connect to backend"
      );
    } finally {
      setLoadingHealth(false);
    }
  }, []);

  const fetchSignal = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/ai/signal`, {
        cache: "no-store",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail?.message ||
            data?.detail ||
            `Signal request failed: ${response.status}`
        );
      }

      setSignalData(data);
      setSignalError("");
      setLastUpdated(new Date());
    } catch (error) {
      console.error("Signal error:", error);

      setSignalError(
        error instanceof Error
          ? error.message
          : "Unable to fetch AI signal"
      );
    } finally {
      setLoadingSignal(false);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([fetchHealth(), fetchSignal()]);
  }, [fetchHealth, fetchSignal]);

  useEffect(() => {
    refreshAll();

    const interval = setInterval(() => {
      refreshAll();
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [refreshAll]);

  const overallSignal = signalData?.ai_signal || "WAIT";

  const systemHealthy =
    healthData?.status?.toLowerCase() === "healthy" &&
    healthData?.upstox_configured === true &&
    healthData?.ml_engine_loaded === true &&
    healthData?.database_loaded === true;

  const marketDataStatus = useMemo(() => {
    if (!signalData?.nifty_signal) return "WAITING";

    if (
      signalData.nifty_signal.candle_is_stale ||
      signalData.nifty_signal.candle_data_quality === "STALE"
    ) {
      return "STALE";
    }

    return "LIVE";
  }, [signalData]);

  return (
    <main className="page">
      <div className="container">
        <header className="topbar">
          <div>
            <div className="eyebrow">AI TRADING INTELLIGENCE PLATFORM</div>
            <h1>India AI Trader</h1>
            <p className="subtitle">
              V16 Integrated Intelligence • V15 Production Model • Paper Trading
            </p>
          </div>

          <div className="top-actions">
            <button
              className="refresh-button"
              onClick={refreshAll}
              disabled={loadingSignal || loadingHealth}
            >
              {loadingSignal || loadingHealth ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </header>

        <section className="hero-grid">
          <div className="hero-card">
            <div className="hero-label">CURRENT AI SIGNAL</div>

            <div className={`hero-signal ${signalClass(overallSignal)}`}>
              {overallSignal}
            </div>

            <div className="hero-meta">
              <div>
                <span>Confidence</span>
                <strong>{formatPercent(signalData?.confidence)}</strong>
              </div>

              <div>
                <span>Score</span>
                <strong>{formatNumber(signalData?.score)}</strong>
              </div>

              <div>
                <span>Market Regime</span>
                <strong>{signalData?.market_regime || "--"}</strong>
              </div>
            </div>
          </div>

          <div className="status-card">
            <div className="status-header">
              <span>System Status</span>

              <span className={`status-pill ${systemHealthy ? "good" : "warning"}`}>
                {systemHealthy ? "HEALTHY" : "CHECK"}
              </span>
            </div>

            <div className="status-list">
              <div>
                <span>Backend</span>
                <strong>
                  {healthData?.application || "India AI Trader"}
                </strong>
              </div>

              <div>
                <span>API</span>
                <strong>{API_BASE}</strong>
              </div>

              <div>
                <span>Upstox</span>
                <strong>
                  {healthData?.upstox_configured
                    ? "CONNECTED"
                    : "NOT CONFIGURED"}
                </strong>
              </div>

              <div>
                <span>Market Data</span>
                <strong
                  className={
                    marketDataStatus === "LIVE"
                      ? "good-text"
                      : "warning-text"
                  }
                >
                  {marketDataStatus}
                </strong>
              </div>

              <div>
                <span>Production Model</span>
                <strong>
                  {healthData?.production_model?.model || "V15"}
                </strong>
              </div>

              <div>
                <span>Features</span>
                <strong>{healthData?.feature_count ?? 26}</strong>
              </div>
            </div>
          </div>
        </section>

        {signalError && (
          <div className="error-banner">
            <strong>AI signal error:</strong> {signalError}
          </div>
        )}

        {healthError && (
          <div className="error-banner">
            <strong>Backend health error:</strong> {healthError}
          </div>
        )}

        <section className="card">
          <div className="section-top">
            <div>
              <div className="card-title">Combined Model Probabilities</div>
              <div className="small-muted">
                V16 integrated probability view
              </div>
            </div>

            <div className="engine-badge">
              {signalData?.engine || "V16_INTEGRATED_INTELLIGENCE"}
            </div>
          </div>

          <div className="probability-large-grid">
            <div className="probability-large buy">
              <span>BUY</span>
              <strong>
                {formatPercent(signalData?.combined_probabilities?.BUY)}
              </strong>
            </div>

            <div className="probability-large wait">
              <span>WAIT</span>
              <strong>
                {formatPercent(signalData?.combined_probabilities?.WAIT)}
              </strong>
            </div>

            <div className="probability-large sell">
              <span>SELL</span>
              <strong>
                {formatPercent(signalData?.combined_probabilities?.SELL)}
              </strong>
            </div>
          </div>
        </section>

        <section className="two-column">
          <InstrumentCard
            title="NIFTY 50"
            data={signalData?.nifty_signal}
          />

          <InstrumentCard
            title="BANK NIFTY"
            data={signalData?.banknifty_signal}
          />
        </section>

        <section className="two-column">
          <div className="card">
            <div className="section-top">
              <div>
                <div className="card-title">India VIX</div>
                <div className="small-muted">
                  Volatility reference
                </div>
              </div>

              <div className="vix-value">
                {formatNumber(signalData?.vix?.last_price)}
              </div>
            </div>

            <div className="metric-grid">
              <div className="metric-box">
                <span>Previous Close</span>
                <strong>
                  {formatNumber(signalData?.vix?.previous_close)}
                </strong>
              </div>

              <div className="metric-box">
                <span>Change</span>
                <strong>
                  {formatNumber(signalData?.vix?.change)}
                </strong>
              </div>

              <div className="metric-box">
                <span>Change %</span>
                <strong>
                  {formatPercent(signalData?.vix?.change_percent)}
                </strong>
              </div>

              <div className="metric-box">
                <span>Status</span>
                <strong className="good-text">CONNECTED</strong>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Trading Safety</div>

            <div className="safety-panel">
              <div className="safety-row">
                <span>Paper Trading</span>
                <strong className="good-text">
                  {signalData?.paper_trading?.enabled ? "ENABLED" : "OFF"}
                </strong>
              </div>

              <div className="safety-row">
                <span>Real Money</span>
                <strong className="warning-text">
                  {signalData?.paper_trading?.real_orders
                    ? "ENABLED"
                    : "DISABLED"}
                </strong>
              </div>

              <div className="safety-row">
                <span>Execution Mode</span>
                <strong>
                  {signalData?.paper_trading?.status || "PAPER_ONLY"}
                </strong>
              </div>

              <div className="safety-row">
                <span>Prediction Gate</span>
                <strong
                  className={
                    signalData?.prediction_gate_loaded
                      ? "good-text"
                      : "warning-text"
                  }
                >
                  {signalData?.prediction_gate_loaded ? "ACTIVE" : "OFF"}
                </strong>
              </div>

              <div className="safety-note">
                Real-money order execution remains disabled.
              </div>
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card-title">V16 Engine Status</div>

          <div className="engine-grid">
            <EngineItem
              label="ML Engine"
              enabled={healthData?.ml_engine_loaded}
            />

            <EngineItem
              label="Decision Engine"
              enabled={healthData?.decision_engine_loaded}
            />

            <EngineItem
              label="Risk Engine"
              enabled={healthData?.risk_engine_loaded}
            />

            <EngineItem
              label="Paper Engine"
              enabled={healthData?.paper_engine_loaded}
            />

            <EngineItem
              label="Monitor Engine"
              enabled={healthData?.monitor_engine_loaded}
            />

            <EngineItem
              label="Analytics Engine"
              enabled={healthData?.analytics_engine_loaded}
            />

            <EngineItem
              label="Outcome Engine"
              enabled={healthData?.outcome_engine_loaded}
            />

            <EngineItem
              label="Calibration"
              enabled={healthData?.calibration_engine_loaded}
            />

            <EngineItem
              label="Model Registry"
              enabled={healthData?.model_registry_loaded}
            />

            <EngineItem
              label="V16 Engine"
              enabled={healthData?.v16_engine_loaded}
            />

            <EngineItem
              label="Outcome Resolver"
              enabled={healthData?.outcome_resolver_loaded}
            />

            <EngineItem
              label="Prediction Gate"
              enabled={healthData?.prediction_gate_loaded}
            />

            <EngineItem
              label="Database"
              enabled={healthData?.database_loaded}
            />
          </div>
        </section>

        {signalData?.persistence && (
          <section className="card">
            <div className="card-title">Prediction Persistence</div>

            <div className="persistence-grid">
              <div className="persistence-box">
                <div className="persistence-title">NIFTY 50</div>

                <div className="decision-row">
                  <span>Saved</span>
                  <strong>
                    {signalData.persistence.nifty?.saved ? "YES" : "NO"}
                  </strong>
                </div>

                <div className="decision-row">
                  <span>Duplicate</span>
                  <strong>
                    {signalData.persistence.nifty?.duplicate ? "YES" : "NO"}
                  </strong>
                </div>

                <div className="decision-row">
                  <span>Blocked</span>
                  <strong>
                    {signalData.persistence.nifty?.blocked ? "YES" : "NO"}
                  </strong>
                </div>

                <div className="decision-row">
                  <span>Reason</span>
                  <strong>
                    {signalData.persistence.nifty?.reason || "--"}
                  </strong>
                </div>
              </div>

              <div className="persistence-box">
                <div className="persistence-title">BANK NIFTY</div>

                <div className="decision-row">
                  <span>Saved</span>
                  <strong>
                    {signalData.persistence.banknifty?.saved ? "YES" : "NO"}
                  </strong>
                </div>

                <div className="decision-row">
                  <span>Duplicate</span>
                  <strong>
                    {signalData.persistence.banknifty?.duplicate ? "YES" : "NO"}
                  </strong>
                </div>

                <div className="decision-row">
                  <span>Blocked</span>
                  <strong>
                    {signalData.persistence.banknifty?.blocked ? "YES" : "NO"}
                  </strong>
                </div>

                <div className="decision-row">
                  <span>Reason</span>
                  <strong>
                    {signalData.persistence.banknifty?.reason || "--"}
                  </strong>
                </div>
              </div>
            </div>
          </section>
        )}

        <footer className="footer">
          <div>
            India AI Trader V16 • Research / Paper Trading Platform
          </div>

          <div>
            Last update:{" "}
            {lastUpdated
              ? lastUpdated.toLocaleString("en-IN")
              : "Waiting..."}
          </div>
        </footer>
      </div>

      <style jsx global>{`
        * {
          box-sizing: border-box;
        }

        html,
        body {
          margin: 0;
          padding: 0;
          min-height: 100%;
          background: #080b12;
          color: #f3f5f7;
          font-family:
            Inter,
            ui-sans-serif,
            system-ui,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
        }

        body {
          overflow-x: hidden;
        }

        button,
        input,
        textarea,
        select {
          font: inherit;
        }

        .page {
          min-height: 100vh;
          padding: 32px 18px 50px;
          background:
            radial-gradient(circle at top left, #141b2e 0%, transparent 32%),
            radial-gradient(circle at top right, #101826 0%, transparent 28%),
            #080b12;
        }

        .container {
          width: min(1450px, 100%);
          margin: 0 auto;
        }

        .topbar {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 20px;
          margin-bottom: 28px;
        }

        .eyebrow {
          font-size: 11px;
          letter-spacing: 0.18em;
          color: #7f8da6;
          font-weight: 700;
          margin-bottom: 9px;
        }

        h1 {
          margin: 0;
          font-size: clamp(32px, 4vw, 54px);
          line-height: 1;
          letter-spacing: -0.04em;
        }

        .subtitle {
          margin: 12px 0 0;
          color: #8e99ad;
          font-size: 14px;
        }

        .refresh-button {
          border: 1px solid #293247;
          background: #111724;
          color: #f3f5f7;
          padding: 11px 17px;
          border-radius: 10px;
          cursor: pointer;
          transition: 0.2s ease;
        }

        .refresh-button:hover:not(:disabled) {
          background: #172033;
          border-color: #43516d;
        }

        .refresh-button:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .hero-grid {
          display: grid;
          grid-template-columns: 1.35fr 1fr;
          gap: 18px;
          margin-bottom: 18px;
        }

        .hero-card,
        .status-card,
        .card {
          border: 1px solid #20283a;
          background: rgba(14, 19, 30, 0.92);
          border-radius: 18px;
          box-shadow: 0 16px 50px rgba(0, 0, 0, 0.18);
        }

        .hero-card {
          padding: 28px;
        }

        .status-card {
          padding: 24px;
        }

        .hero-label {
          color: #77839a;
          font-size: 12px;
          font-weight: 800;
          letter-spacing: 0.15em;
        }

        .hero-signal {
          display: inline-flex;
          align-items: center;
          margin: 13px 0 22px;
          font-size: clamp(48px, 7vw, 82px);
          line-height: 1;
          font-weight: 900;
          letter-spacing: -0.06em;
        }

        .buy {
          color: #4ade80;
        }

        .sell {
          color: #fb7185;
        }

        .wait {
          color: #fbbf24;
        }

        .hero-meta {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }

        .hero-meta div {
          padding: 14px;
          border-radius: 12px;
          background: #101725;
          border: 1px solid #1e2839;
        }

        .hero-meta span,
        .metric-box span,
        .trade-levels span,
        .indicator-grid span,
        .safety-row span,
        .decision-row span {
          display: block;
          color: #7f8ca3;
          font-size: 12px;
          margin-bottom: 5px;
        }

        .hero-meta strong {
          font-size: 16px;
        }

        .status-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 17px;
          font-size: 15px;
          font-weight: 750;
        }

        .status-pill {
          border-radius: 999px;
          padding: 6px 10px;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.06em;
        }

        .status-pill.good {
          color: #4ade80;
          background: rgba(74, 222, 128, 0.09);
        }

        .status-pill.warning {
          color: #fbbf24;
          background: rgba(251, 191, 36, 0.09);
        }

        .status-list {
          display: grid;
          gap: 10px;
        }

        .status-list > div,
        .safety-row,
        .decision-row {
          display: flex;
          justify-content: space-between;
          gap: 15px;
          align-items: center;
        }

        .status-list > div {
          border-bottom: 1px solid #1b2332;
          padding-bottom: 10px;
        }

        .status-list strong {
          text-align: right;
          max-width: 65%;
          word-break: break-word;
          font-size: 13px;
        }

        .good-text {
          color: #4ade80 !important;
        }

        .warning-text {
          color: #fbbf24 !important;
        }

        .error-banner {
          margin-bottom: 18px;
          padding: 14px 16px;
          border-radius: 12px;
          border: 1px solid rgba(251, 113, 133, 0.25);
          background: rgba(127, 29, 29, 0.15);
          color: #fecdd3;
          font-size: 13px;
        }

        .card {
          padding: 23px;
          margin-bottom: 18px;
        }

        .section-top {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 18px;
        }

        .card-title {
          font-size: 17px;
          font-weight: 800;
          letter-spacing: -0.01em;
        }

        .small-muted {
          color: #6e7a90;
          font-size: 11px;
          margin-top: 4px;
        }

        .engine-badge {
          border: 1px solid #273148;
          background: #111725;
          color: #9aa8c1;
          border-radius: 999px;
          padding: 6px 10px;
          font-size: 10px;
          letter-spacing: 0.08em;
          white-space: nowrap;
        }

        .probability-large-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }

        .probability-large {
          background: #101725;
          border: 1px solid #1e2839;
          border-radius: 14px;
          padding: 20px;
        }

        .probability-large span {
          display: block;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.12em;
          margin-bottom: 9px;
        }

        .probability-large strong {
          font-size: 30px;
          line-height: 1;
        }

        .probability-large.buy strong,
        .probability-large.buy span {
          color: #4ade80;
        }

        .probability-large.wait strong,
        .probability-large.wait span {
          color: #fbbf24;
        }

        .probability-large.sell strong,
        .probability-large.sell span {
          color: #fb7185;
        }

        .two-column {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 18px;
        }

        .instrument-card {
          min-width: 0;
        }

        .instrument-header {
          display: flex;
          justify-content: space-between;
          gap: 15px;
          align-items: flex-start;
          margin-bottom: 18px;
        }

        .large-signal {
          font-size: 26px;
          font-weight: 900;
          letter-spacing: -0.03em;
        }

        .metric-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 10px;
        }

        .metric-box {
          padding: 12px;
          border-radius: 11px;
          background: #101725;
          border: 1px solid #1e2839;
          min-width: 0;
        }

        .metric-box strong {
          display: block;
          font-size: 14px;
          word-break: break-word;
        }

        .small-value {
          font-size: 11px !important;
          line-height: 1.35;
        }

        .section-block {
          margin-top: 20px;
        }

        .section-heading {
          color: #8390a7;
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0.14em;
          font-weight: 800;
          margin-bottom: 10px;
        }

        .probability-row {
          display: grid;
          grid-template-columns: 54px 1fr 58px;
          gap: 9px;
          align-items: center;
          margin-bottom: 9px;
        }

        .probability-label {
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.06em;
        }

        .probability-label.buy {
          color: #4ade80;
        }

        .probability-label.wait {
          color: #fbbf24;
        }

        .probability-label.sell {
          color: #fb7185;
        }

        .probability-track {
          height: 7px;
          border-radius: 999px;
          background: #1a2231;
          overflow: hidden;
        }

        .probability-fill {
          height: 100%;
          border-radius: inherit;
        }

        .probability-fill.buy {
          background: #4ade80;
        }

        .probability-fill.wait {
          background: #fbbf24;
        }

        .probability-fill.sell {
          background: #fb7185;
        }

        .probability-value {
          text-align: right;
          font-size: 11px;
          color: #c4ccda;
          font-variant-numeric: tabular-nums;
        }

        .indicator-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
        }

        .indicator-grid > div {
          padding: 10px;
          border: 1px solid #1b2535;
          border-radius: 10px;
          background: #0d131e;
        }

        .indicator-grid strong {
          font-size: 12px;
        }

        .trade-levels {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
          margin-top: 18px;
        }

        .trade-levels > div {
          padding: 11px;
          border-radius: 10px;
          background: #101725;
          border: 1px solid #1e2839;
        }

        .trade-levels strong {
          font-size: 12px;
        }

        .decision-section {
          display: grid;
          gap: 10px;
          margin-top: 17px;
        }

        .decision-row {
          padding-bottom: 9px;
          border-bottom: 1px solid #1b2332;
        }

        .decision-row strong {
          font-size: 12px;
          text-align: right;
        }

        .decision-row strong.good {
          color: #4ade80;
        }

        .decision-row strong.warning {
          color: #fbbf24;
        }

        .stale-warning {
          display: grid;
          gap: 3px;
          padding: 13px;
          border-radius: 11px;
          margin-top: 17px;
          border: 1px solid rgba(251, 191, 36, 0.24);
          background: rgba(120, 53, 15, 0.15);
          color: #fcd34d;
          font-size: 11px;
        }

        .blocker-box,
        .reason-box {
          margin-top: 15px;
          padding: 12px;
          border-radius: 11px;
          border: 1px solid #222d40;
          background: #0c121c;
          color: #9aa6ba;
          font-size: 11px;
          line-height: 1.5;
        }

        .reason-box p {
          margin: 0;
        }

        .vix-value {
          font-size: 32px;
          font-weight: 900;
          color: #fbbf24;
        }

        .safety-panel {
          display: grid;
          gap: 11px;
        }

        .safety-row {
          padding-bottom: 10px;
          border-bottom: 1px solid #1b2332;
        }

        .safety-note {
          margin-top: 4px;
          color: #718097;
          font-size: 11px;
        }

        .engine-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-top: 15px;
        }

        .engine-item {
          display: grid;
          grid-template-columns: 9px 1fr auto;
          align-items: center;
          gap: 9px;
          padding: 12px;
          border-radius: 11px;
          background: #101725;
          border: 1px solid #1e2839;
          font-size: 12px;
        }

        .engine-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }

        .engine-dot.active {
          background: #4ade80;
          box-shadow: 0 0 10px rgba(74, 222, 128, 0.35);
        }

        .engine-dot.inactive {
          background: #475569;
        }

        .engine-state {
          font-size: 9px;
          font-weight: 800;
          letter-spacing: 0.06em;
        }

        .engine-state.active {
          color: #4ade80;
        }

        .engine-state.inactive {
          color: #64748b;
        }

        .persistence-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-top: 15px;
        }

        .persistence-box {
          padding: 14px;
          background: #101725;
          border: 1px solid #1e2839;
          border-radius: 12px;
        }

        .persistence-title {
          font-weight: 800;
          font-size: 13px;
          margin-bottom: 13px;
        }

        .footer {
          display: flex;
          justify-content: space-between;
          gap: 14px;
          color: #59657a;
          font-size: 11px;
          padding: 8px 3px;
        }

        .empty-state {
          padding: 35px 5px;
          color: #67758c;
          font-size: 13px;
        }

        @media (max-width: 1100px) {
          .hero-grid,
          .two-column {
            grid-template-columns: 1fr;
          }

          .engine-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }

        @media (max-width: 800px) {
          .page {
            padding: 20px 12px 35px;
          }

          .topbar {
            flex-direction: column;
          }

          .hero-meta,
          .probability-large-grid,
          .metric-grid,
          .trade-levels,
          .indicator-grid,
          .engine-grid,
          .persistence-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .footer {
            flex-direction: column;
          }
        }

        @media (max-width: 520px) {
          .hero-meta,
          .probability-large-grid,
          .metric-grid,
          .trade-levels,
          .indicator-grid,
          .engine-grid,
          .persistence-grid {
            grid-template-columns: 1fr;
          }

          .status-list strong {
            max-width: 55%;
          }

          .hero-card,
          .status-card,
          .card {
            padding: 17px;
          }
        }
      `}</style>
    </main>
  );
}