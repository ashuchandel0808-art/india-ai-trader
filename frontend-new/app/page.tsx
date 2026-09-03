"use client";

import { useCallback, useEffect, useState } from "react";

const API =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

type ScannerRow = {
  symbol: string;
  price?: number;
  change_percent?: number;
  signal?: string;
  confidence?: number;
  buy_probability?: number;
  sell_probability?: number;
  wait_probability?: number;
  market_regime?: string;
  risk_reward?: number;
  scanner_score?: number;
};

type Portfolio = {
  starting_capital?: number;
  cash?: number;
  invested?: number;
  market_value?: number;
  equity?: number;
  unrealized_pnl?: number;
  total_return_percent?: number;
  position_count?: number;
};

type PaperTrade = {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  stop_loss?: number | null;
  target_price?: number | null;
  current_price?: number;
  unrealized_pnl?: number;
  realized_pnl?: number | null;
  status: string;
};

type AIData = {
  ai_signal?: string;
  confidence?: number;
  score?: number;
  market_regime?: string;

  combined_probabilities?: {
    BUY?: number;
    SELL?: number;
    WAIT?: number;
  };

  nifty_signal?: {
    signal?: string;
    probabilities?: {
      BUY?: number;
      SELL?: number;
      WAIT?: number;
    };
  };

  banknifty_signal?: {
    signal?: string;
    probabilities?: {
      BUY?: number;
      SELL?: number;
      WAIT?: number;
    };
  };

  vix?: {
    last_price?: number;
    change_percent?: number;
  };
};

function money(
  value?: number | null
) {
  if (
    value === undefined ||
    value === null ||
    !Number.isFinite(value)
  ) {
    return "--";
  }

  return `₹${value.toLocaleString(
    "en-IN",
    {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }
  )}`;
}

function num(
  value?: number | null
) {
  if (
    value === undefined ||
    value === null ||
    !Number.isFinite(value)
  ) {
    return "--";
  }

  return value.toFixed(2);
}

function signalColor(
  signal?: string
) {
  const value =
    signal?.toUpperCase() ||
    "WAIT";

  if (
    value.includes("BUY")
  ) {
    return "text-emerald-400";
  }

  if (
    value.includes("SELL")
  ) {
    return "text-red-400";
  }

  return "text-amber-400";
}

function ProbabilityBar({
  label,
  value,
  color,
}: {
  label: string;
  value?: number;
  color: string;
}) {
  const safe =
    typeof value === "number"
      ? Math.max(
          0,
          Math.min(
            100,
            value
          )
        )
      : 0;

  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-slate-400">
          {label}
        </span>

        <span
          className={`font-semibold ${color}`}
        >
          {safe.toFixed(1)}%
        </span>
      </div>

      <div className="h-2 rounded-full bg-slate-800">
        <div
          className={`h-2 rounded-full ${color.replace(
            "text-",
            "bg-"
          )}`}
          style={{
            width: `${safe}%`,
          }}
        />
      </div>
    </div>
  );
}

export default function Home() {
  const [
    ai,
    setAI,
  ] =
    useState<AIData | null>(
      null
    );

  const [
    scanner,
    setScanner,
  ] =
    useState<ScannerRow[]>([]);

  const [
    portfolio,
    setPortfolio,
  ] =
    useState<Portfolio | null>(
      null
    );

  const [
    paperTrades,
    setPaperTrades,
  ] =
    useState<PaperTrade[]>([]);

  const [
    symbol,
    setSymbol,
  ] =
    useState("RELIANCE");

  const [
    newCapital,
    setNewCapital,
  ] =
    useState("100000");

  const [
    connection,
    setConnection,
  ] =
    useState("CONNECTING");

  const [
    scannerLoading,
    setScannerLoading,
  ] =
    useState(false);

  const [
    activeTab,
    setActiveTab,
  ] =
    useState("dashboard");

  const loadAI =
    useCallback(
      async () => {
        try {
          const response =
            await fetch(
              `${API}/api/ai/signal`,
              {
                cache:
                  "no-store",
              }
            );

          if (
            !response.ok
          ) {
            throw new Error(
              "AI request failed"
            );
          }

          const data =
            (await response.json()) as AIData;

          setAI(data);
          setConnection(
            "LIVE"
          );
        } catch (
          error
        ) {
          console.error(
            error
          );

          setConnection(
            "ERROR"
          );
        }
      },
      []
    );

  const loadPortfolio =
    useCallback(
      async () => {
        try {
          const response =
            await fetch(
              `${API}/api/portfolio`,
              {
                cache:
                  "no-store",
              }
            );

          if (!response.ok) {
            return;
          }

          const data =
            await response.json();

          setPortfolio(
            data
          );
        } catch (
          error
        ) {
          console.error(
            error
          );
        }
      },
      []
    );

  const loadPaperTrades =
    useCallback(
      async () => {
        try {
          const response =
            await fetch(
              `${API}/api/paper/trades`,
              {
                cache:
                  "no-store",
              }
            );

          if (!response.ok) {
            return;
          }

          const data =
            await response.json();

          setPaperTrades(
            data.trades || []
          );
        } catch (
          error
        ) {
          console.error(
            error
          );
        }
      },
      []
    );

  const loadScanner =
    useCallback(
      async () => {
        setScannerLoading(
          true
        );

        try {
          const response =
            await fetch(
              `${API}/api/scanner?limit=10`,
              {
                cache:
                  "no-store",
              }
            );

          if (!response.ok) {
            throw new Error(
              "Scanner failed"
            );
          }

          const data =
            await response.json();

          setScanner(
            data.results ||
              []
          );
        } catch (
          error
        ) {
          console.error(
            "Scanner:",
            error
          );
        } finally {
          setScannerLoading(
            false
          );
        }
      },
      []
    );

  async function createPaperTrade(
    row: ScannerRow
  ) {
    if (
      row.signal !==
        "BUY" &&
      row.signal !==
        "SELL"
    ) {
      return;
    }

    try {
      const response =
        await fetch(
          `${API}/api/paper/orders`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              symbol:
                row.symbol,
              side:
                row.signal,
              quantity: 1,
              entry_price:
                row.price,
            }),
          }
        );

      if (!response.ok) {
        const text =
          await response.text();

        throw new Error(
          text
        );
      }

      await Promise.all([
        loadPortfolio(),
        loadPaperTrades(),
      ]);
    } catch (
      error
    ) {
      console.error(
        "Paper order:",
        error
      );
    }
  }

  async function closePaperTrade(
    tradeId: string
  ) {
    try {
      const response =
        await fetch(
          `${API}/api/paper/trades/${tradeId}/close`,
          {
            method: "POST",
          }
        );

      if (!response.ok) {
        throw new Error(
          "Close failed"
        );
      }

      await Promise.all([
        loadPortfolio(),
        loadPaperTrades(),
      ]);
    } catch (
      error
    ) {
      console.error(
        error
      );
    }
  }

  async function resetPortfolio() {
    const capital =
      Number(
        newCapital
      );

    if (
      !Number.isFinite(
        capital
      ) ||
      capital <= 0
    ) {
      return;
    }

    try {
      await fetch(
        `${API}/api/portfolio/reset`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            starting_capital:
              capital,
          }),
        }
      );

      await Promise.all([
        loadPortfolio(),
        loadPaperTrades(),
      ]);
    } catch (
      error
    ) {
      console.error(
        error
      );
    }
  }

  useEffect(() => {
    loadAI();
    loadPortfolio();
    loadPaperTrades();

    const timer =
      window.setInterval(
        () => {
          loadAI();
          loadPortfolio();
          loadPaperTrades();
        },
        10000
      );

    return () => {
      window.clearInterval(
        timer
      );
    };
  }, [
    loadAI,
    loadPortfolio,
    loadPaperTrades,
  ]);

  const aiSignal =
    ai?.ai_signal ||
    "WAIT";

  const probabilities =
    ai?.combined_probabilities ||
    {};

  return (
    <main className="min-h-screen bg-[#050910] text-white">
      {/* HEADER */}

      <header className="sticky top-0 z-50 border-b border-slate-800 bg-[#050910]/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between px-5 py-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold">
                🇮🇳 India AI Trader
              </h1>

              <span className="rounded-md bg-blue-500/10 px-2 py-1 text-[10px] font-bold text-blue-400">
                V15
              </span>
            </div>

            <p className="text-xs text-slate-500">
              AI Trading Intelligence Terminal
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="rounded-full bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400">
              ● {connection}
            </span>

            <button
              onClick={() => {
                loadAI();
                loadPortfolio();
                loadPaperTrades();
                loadScanner();
              }}
              className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-xs hover:bg-slate-800"
            >
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* NAV */}

      <nav className="border-b border-slate-800 bg-[#080d16]">
        <div className="mx-auto flex max-w-[1500px] gap-2 overflow-x-auto px-5 py-3">
          {[
            ["dashboard", "Dashboard"],
            ["scanner", "Scanner"],
            ["portfolio", "Portfolio"],
            ["paper", "Paper Trading"],
            ["risk", "Risk Engine"],
          ].map(
            ([id, label]) => (
              <button
                key={id}
                onClick={() =>
                  setActiveTab(
                    id
                  )
                }
                className={`rounded-xl px-4 py-2 text-xs font-medium ${
                  activeTab === id
                    ? "bg-emerald-500 text-black"
                    : "text-slate-400 hover:bg-slate-900"
                }`}
              >
                {label}
              </button>
            )
          )}
        </div>
      </nav>

      <div className="mx-auto max-w-[1500px] space-y-7 px-5 py-7">
        {/* DASHBOARD */}

        {activeTab ===
          "dashboard" && (
          <>
            <section>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                  <p className="text-xs text-slate-500">
                    AI MARKET SIGNAL
                  </p>

                  <p
                    className={`mt-3 text-5xl font-black ${signalColor(
                      aiSignal
                    )}`}
                  >
                    {aiSignal}
                  </p>

                  <p className="mt-3 text-sm text-slate-400">
                    Confidence{" "}
                    <span className="font-semibold text-white">
                      {num(
                        ai?.confidence
                      )}
                      %
                    </span>
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                  <p className="text-xs text-slate-500">
                    MARKET REGIME
                  </p>

                  <p
                    className={`mt-4 text-2xl font-bold ${signalColor(
                      ai?.market_regime
                    )}`}
                  >
                    {ai?.market_regime ??
                      "--"}
                  </p>

                  <p className="mt-3 text-sm text-slate-500">
                    VIX{" "}
                    {num(
                      ai?.vix
                        ?.last_price
                    )}
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                  <p className="text-xs text-slate-500">
                    PAPER EQUITY
                  </p>

                  <p className="mt-3 text-3xl font-bold">
                    {money(
                      portfolio?.equity
                    )}
                  </p>

                  <p
                    className={`mt-3 text-sm ${
                      (
                        portfolio?.unrealized_pnl ??
                        0
                      ) >= 0
                        ? "text-emerald-400"
                        : "text-red-400"
                    }`}
                  >
                    P&L{" "}
                    {money(
                      portfolio?.unrealized_pnl
                    )}
                  </p>
                </div>
              </div>
            </section>

            <section>
              <div className="grid gap-5 lg:grid-cols-2">
                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
                  <p className="text-xs uppercase tracking-[0.18em] text-blue-400">
                    V15 Probability Engine
                  </p>

                  <h2 className="mt-2 text-xl font-bold">
                    Market Decision
                  </h2>

                  <div className="mt-7 space-y-5">
                    <ProbabilityBar
                      label="BUY"
                      value={
                        probabilities.BUY
                      }
                      color="text-emerald-400"
                    />

                    <ProbabilityBar
                      label="WAIT"
                      value={
                        probabilities.WAIT
                      }
                      color="text-amber-400"
                    />

                    <ProbabilityBar
                      label="SELL"
                      value={
                        probabilities.SELL
                      }
                      color="text-red-400"
                    />
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
                  <p className="text-xs uppercase tracking-[0.18em] text-purple-400">
                    Index Confirmation
                  </p>

                  <div className="mt-5 grid gap-4 sm:grid-cols-2">
                    <div className="rounded-xl bg-slate-950 p-5">
                      <p className="text-xs text-slate-500">
                        NIFTY
                      </p>

                      <p
                        className={`mt-2 text-2xl font-bold ${signalColor(
                          ai?.nifty_signal
                            ?.signal
                        )}`}
                      >
                        {ai?.nifty_signal
                          ?.signal ??
                          "--"}
                      </p>
                    </div>

                    <div className="rounded-xl bg-slate-950 p-5">
                      <p className="text-xs text-slate-500">
                        BANK NIFTY
                      </p>

                      <p
                        className={`mt-2 text-2xl font-bold ${signalColor(
                          ai?.banknifty_signal
                            ?.signal
                        )}`}
                      >
                        {ai?.banknifty_signal
                          ?.signal ??
                          "--"}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </>
        )}

        {/* SCANNER */}

        {activeTab ===
          "scanner" && (
          <section>
            <div className="mb-5 flex items-end justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-emerald-400">
                  V15.1 Scanner
                </p>

                <h2 className="mt-1 text-2xl font-bold">
                  Top NSE Opportunities
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  Ranked by AI probability, direction,
                  regime and risk/reward.
                </p>
              </div>

              <button
                onClick={
                  loadScanner
                }
                className="rounded-xl bg-emerald-500 px-4 py-2 text-xs font-semibold text-black"
              >
                {scannerLoading
                  ? "Scanning..."
                  : "Scan Market"}
              </button>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-950 text-xs text-slate-500">
                  <tr>
                    <th className="px-5 py-4">
                      #
                    </th>
                    <th className="px-5 py-4">
                      Stock
                    </th>
                    <th className="px-5 py-4">
                      Price
                    </th>
                    <th className="px-5 py-4">
                      Signal
                    </th>
                    <th className="px-5 py-4">
                      BUY
                    </th>
                    <th className="px-5 py-4">
                      SELL
                    </th>
                    <th className="px-5 py-4">
                      Confidence
                    </th>
                    <th className="px-5 py-4">
                      R:R
                    </th>
                    <th className="px-5 py-4">
                      Action
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {scanner.map(
                    (
                      row,
                      index
                    ) => (
                      <tr
                        key={
                          row.symbol
                        }
                        className="border-t border-slate-800"
                      >
                        <td className="px-5 py-4 text-slate-500">
                          {index +
                            1}
                        </td>

                        <td className="px-5 py-4 font-semibold">
                          {row.symbol}
                        </td>

                        <td className="px-5 py-4">
                          {money(
                            row.price
                          )}
                        </td>

                        <td
                          className={`px-5 py-4 font-bold ${signalColor(
                            row.signal
                          )}`}
                        >
                          {row.signal}
                        </td>

                        <td className="px-5 py-4 text-emerald-400">
                          {num(
                            row.buy_probability
                          )}
                          %
                        </td>

                        <td className="px-5 py-4 text-red-400">
                          {num(
                            row.sell_probability
                          )}
                          %
                        </td>

                        <td className="px-5 py-4">
                          {num(
                            row.confidence
                          )}
                          %
                        </td>

                        <td className="px-5 py-4">
                          {row.risk_reward
                            ? `1:${row.risk_reward}`
                            : "--"}
                        </td>

                        <td className="px-5 py-4">
                          {(row.signal ===
                            "BUY" ||
                            row.signal ===
                              "SELL") && (
                            <button
                              onClick={() =>
                                createPaperTrade(
                                  row
                                )
                              }
                              className="rounded-lg bg-blue-500/10 px-3 py-2 text-xs text-blue-400 hover:bg-blue-500/20"
                            >
                              Paper Trade
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>

              {!scanner.length && (
                <div className="p-10 text-center text-sm text-slate-500">
                  Click "Scan Market" to
                  analyze the configured NSE
                  universe.
                </div>
              )}
            </div>
          </section>
        )}

        {/* PORTFOLIO */}

        {activeTab ===
          "portfolio" && (
          <section>
            <div className="mb-5">
              <p className="text-xs uppercase tracking-[0.18em] text-blue-400">
                Portfolio
              </p>

              <h2 className="mt-1 text-2xl font-bold">
                Paper Account
              </h2>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <p className="text-xs text-slate-500">
                  STARTING CAPITAL
                </p>

                <p className="mt-3 text-2xl font-bold">
                  {money(
                    portfolio?.starting_capital
                  )}
                </p>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <p className="text-xs text-slate-500">
                  CASH
                </p>

                <p className="mt-3 text-2xl font-bold">
                  {money(
                    portfolio?.cash
                  )}
                </p>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <p className="text-xs text-slate-500">
                  EQUITY
                </p>

                <p className="mt-3 text-2xl font-bold">
                  {money(
                    portfolio?.equity
                  )}
                </p>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <p className="text-xs text-slate-500">
                  RETURN
                </p>

                <p
                  className={`mt-3 text-2xl font-bold ${
                    (
                      portfolio?.total_return_percent ??
                      0
                    ) >= 0
                      ? "text-emerald-400"
                      : "text-red-400"
                  }`}
                >
                  {num(
                    portfolio?.total_return_percent
                  )}
                  %
                </p>
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">
              <h3 className="font-semibold">
                Paper Account Controls
              </h3>

              <div className="mt-4 flex flex-wrap gap-3">
                <input
                  value={
                    newCapital
                  }
                  onChange={(event) =>
                    setNewCapital(
                      event.target
                        .value
                    )
                  }
                  className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm"
                  placeholder="100000"
                />

                <button
                  onClick={
                    resetPortfolio
                  }
                  className="rounded-xl bg-red-500/10 px-5 py-3 text-xs font-semibold text-red-400"
                >
                  Reset Paper Account
                </button>
              </div>
            </div>
          </section>
        )}

        {/* PAPER */}

        {activeTab ===
          "paper" && (
          <section>
            <div className="mb-5">
              <p className="text-xs uppercase tracking-[0.18em] text-purple-400">
                V15.5
              </p>

              <h2 className="mt-1 text-2xl font-bold">
                Paper Trading
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Virtual execution only. No real orders are sent.
              </p>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-950 text-xs text-slate-500">
                  <tr>
                    <th className="px-5 py-4">
                      Stock
                    </th>
                    <th className="px-5 py-4">
                      Side
                    </th>
                    <th className="px-5 py-4">
                      Qty
                    </th>
                    <th className="px-5 py-4">
                      Entry
                    </th>
                    <th className="px-5 py-4">
                      Current
                    </th>
                    <th className="px-5 py-4">
                      P&L
                    </th>
                    <th className="px-5 py-4">
                      Status
                    </th>
                    <th className="px-5 py-4">
                      Action
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {paperTrades.map(
                    (
                      trade
                    ) => (
                      <tr
                        key={
                          trade.id
                        }
                        className="border-t border-slate-800"
                      >
                        <td className="px-5 py-4 font-semibold">
                          {trade.symbol}
                        </td>

                        <td
                          className={`px-5 py-4 font-bold ${signalColor(
                            trade.side
                          )}`}
                        >
                          {trade.side}
                        </td>

                        <td className="px-5 py-4">
                          {trade.quantity}
                        </td>

                        <td className="px-5 py-4">
                          {money(
                            trade.entry_price
                          )}
                        </td>

                        <td className="px-5 py-4">
                          {money(
                            trade.current_price
                          )}
                        </td>

                        <td
                          className={`px-5 py-4 ${
                            (
                              trade.unrealized_pnl ??
                              trade.realized_pnl ??
                              0
                            ) >= 0
                              ? "text-emerald-400"
                              : "text-red-400"
                          }`}
                        >
                          {money(
                            trade.unrealized_pnl ??
                              trade.realized_pnl
                          )}
                        </td>

                        <td className="px-5 py-4">
                          {trade.status}
                        </td>

                        <td className="px-5 py-4">
                          {trade.status ===
                            "OPEN" && (
                            <button
                              onClick={() =>
                                closePaperTrade(
                                  trade.id
                                )
                              }
                              className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-400"
                            >
                              Close
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>

              {!paperTrades.length && (
                <div className="p-10 text-center text-sm text-slate-500">
                  No paper trades yet.
                </div>
              )}
            </div>
          </section>
        )}

        {/* RISK */}

        {activeTab ===
          "risk" && (
          <section>
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
              <p className="text-xs uppercase tracking-[0.18em] text-emerald-400">
                Risk Engine
              </p>

              <h2 className="mt-1 text-2xl font-bold">
                Position sizing
              </h2>

              <p className="mt-2 text-sm text-slate-500">
                This layer determines how much capital a paper trade should risk.
              </p>

              <div className="mt-7 grid gap-4 md:grid-cols-3">
                <div>
                  <label className="text-xs text-slate-500">
                    Symbol
                  </label>

                  <input
                    value={symbol}
                    onChange={(event) =>
                      setSymbol(
                        event.target
                          .value
                          .toUpperCase()
                      )
                    }
                    className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-500">
                    Capital
                  </label>

                  <input
                    value={
                      newCapital
                    }
                    onChange={(event) =>
                      setNewCapital(
                        event.target
                          .value
                      )
                    }
                    className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-500">
                    Risk
                  </label>

                  <input
                    defaultValue="1"
                    id="riskPercent"
                    className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm"
                  />
                </div>
              </div>

              <div className="mt-7 rounded-xl border border-slate-800 bg-slate-950 p-5">
                <p className="text-sm text-slate-400">
                  Use the scanner's AI-generated setup and apply the risk engine before opening a paper position.
                </p>
              </div>
            </div>
          </section>
        )}

        {/* FOOTER */}

        <footer className="border-t border-slate-800 py-8 text-center">
          <p className="text-xs text-slate-600">
            India AI Trader V15.1–V15.5 · Upstox · XGBoost · Paper Trading
          </p>
        </footer>
      </div>
    </main>
  );
}