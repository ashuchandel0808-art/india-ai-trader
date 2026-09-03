# 🇮🇳 India AI Trader

### AI-Powered Indian Stock Market Intelligence & Trading Platform

India AI Trader is an AI-driven trading intelligence platform designed to help Indian retail investors analyze market conditions, understand market trends, and make more informed **BUY / SELL / WAIT** decisions.

The platform combines **real-time market data, technical indicators, machine learning, market-regime detection, signal generation, and risk-management metrics** into a unified dashboard.

> **Turning complex market data into simple, actionable trading intelligence.**

---

## 🚀 Product Overview

Retail investors often need to use multiple tools to monitor prices, analyze technical indicators, understand volatility, and make trading decisions.

**India AI Trader** aims to bring these capabilities together into one intelligent platform.

### Core Product Flow

```text
Live Market Data
       ↓
Market Data Processing
       ↓
Technical Indicators
       ↓
Market Regime Detection
       ↓
Machine Learning
       ↓
Multi-Factor Signal Engine
       ↓
Risk Management
       ↓
BUY / SELL / WAIT
```

---

## ✨ Key Features

### 📊 Real-Time Market Intelligence

* Live Indian market data using the Upstox API
* NIFTY 50 monitoring
* BANK NIFTY monitoring
* India VIX tracking
* Intraday market data
* Historical market data

### 🤖 Machine Learning

The platform includes an XGBoost-based machine learning pipeline for financial market prediction.

Key components include:

* Feature engineering
* Historical market-data processing
* ML model training
* Model inference
* Prediction pipeline
* Integration with the trading intelligence engine

### 📈 Technical Analysis

The system analyzes multiple technical indicators including:

* RSI
* MACD
* EMA 9 / 20 / 50 / 200
* VWAP
* ATR
* Bollinger Bands
* Volume analysis
* Momentum
* Rate of Change
* Trend analysis

Instead of depending on a single indicator, multiple factors are combined to generate a more robust market signal.

### 🧠 Market Regime Detection

The platform evaluates broader market conditions and classifies the market into different regimes:

* Strong Bullish
* Bullish
* Mildly Bullish
* Sideways
* Mildly Bearish
* Bearish
* Strong Bearish
* High Volatility
* Extreme Volatility

This allows the signal engine to adapt its interpretation according to the current market environment.

### 🎯 Trading Signals

The decision engine generates:

```text
BUY
SELL
WAIT
```

Signals are supported by information such as:

* Signal strength
* Confidence score
* Market regime
* Momentum
* Trend conditions
* Volume conditions
* Volatility
* Risk metrics

### 🛡️ Risk Management

The system incorporates risk-management concepts including:

* ATR-based risk calculations
* Volatility awareness
* Market-regime filtering
* Signal confidence
* Risk/reward analysis

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │     Upstox API      │
                    │   Market Data       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Backend   │
                    │ Data Processing      │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        ┌────────────┐ ┌────────────┐ ┌────────────┐
        │ Technical  │ │    ML      │ │  Market    │
        │ Indicators │ │  Pipeline  │ │  Regime    │
        └──────┬─────┘ └──────┬─────┘ └──────┬─────┘
               │              │              │
               └──────────────┼──────────────┘
                              ▼
                    ┌─────────────────────┐
                    │  Signal Engine      │
                    │ BUY / SELL / WAIT   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Next.js Dashboard │
                    │ Market Intelligence │
                    └─────────────────────┘
```

---

## 🛠️ Technology Stack

### Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS

### Backend

* Python
* FastAPI
* Uvicorn

### Machine Learning

* XGBoost
* Pandas
* NumPy
* Scikit-learn
* Joblib

### Market Data

* Upstox API

### Database

* SQLite

### Development

* Git
* GitHub
* VS Code

---

## 📁 Project Structure

```text
india-ai-trader/
│
├── backend/
│   ├── ai/
│   ├── trading/
│   ├── upstox/
│   ├── main.py
│   ├── ml.py
│   ├── ml_train.py
│   └── requirements.txt
│
├── database/
│   ├── db.py
│   └── models.py
│
├── frontend-new/
│   ├── app/
│   ├── components/
│   ├── public/
│   └── package.json
│
├── .gitignore
└── README.md
```

---

## ⚙️ Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/ashuchandel0808-art/india-ai-trader.git
cd india-ai-trader
```

### 2. Backend Setup

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project directory:

```env
UPSTOX_ACCESS_TOKEN=your_upstox_access_token
```

> ⚠️ Never commit API keys, access tokens, passwords, or other secrets to GitHub.

### 4. Start the Backend

```bash
cd backend
python3 -m uvicorn main:app --reload
```

The backend will run locally at:

```text
http://127.0.0.1:8000
```

### 5. Start the Frontend

Open another terminal:

```bash
cd frontend-new
npm install
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:3000
```

---

## 🔐 Security

Sensitive credentials and locally generated files are excluded from version control.

The repository ignores:

```text
.env
.env.local
.venv/
node_modules/
.next/
*.joblib
database/*.db
database/*.db-shm
database/*.db-wal
```

API credentials should always be stored using environment variables.

---

## 📊 Current Capabilities

* [x] Live market data integration
* [x] NIFTY 50 monitoring
* [x] BANK NIFTY monitoring
* [x] India VIX monitoring
* [x] Technical indicator engine
* [x] Market regime detection
* [x] Multi-factor signal engine
* [x] Risk-management framework
* [x] FastAPI backend
* [x] Next.js dashboard
* [x] XGBoost ML pipeline
* [x] GitHub repository

---

## 🚧 Roadmap

### Phase 1 — Intelligence

* [x] Real-time market monitoring
* [x] Technical analysis
* [x] Market regime detection
* [x] Signal generation
* [x] ML pipeline

### Phase 2 — Advanced AI

* [ ] Improve prediction accuracy
* [ ] Advanced feature engineering
* [ ] Model evaluation and continuous retraining
* [ ] News and sentiment analysis
* [ ] Portfolio-aware predictions

### Phase 3 — Trading Platform

* [ ] Backtesting engine
* [ ] Paper trading
* [ ] Strategy performance analytics
* [ ] Personalized trading recommendations
* [ ] Portfolio monitoring
* [ ] Broker order execution

### Phase 4 — Production

* [ ] Production deployment
* [ ] Multi-user architecture
* [ ] Authentication and authorization
* [ ] Cloud database
* [ ] Monitoring and logging
* [ ] Scalable infrastructure

---

## 💡 Product Thinking

India AI Trader is designed around a simple user problem:

> **"What is happening in the market, and what should I consider doing next?"**

The platform focuses on converting:

```text
Raw Data
   ↓
Information
   ↓
Market Intelligence
   ↓
Decision Support
```

Instead of requiring users to independently interpret dozens of indicators, the platform combines multiple signals into a simplified decision-support layer.

This approach focuses on reducing information overload and making complex financial data easier to interpret.

---

## 🎯 Product Management Perspective

The project was developed with a product-first approach:

### Problem

Retail investors often face fragmented information, multiple analytical tools, and difficulty interpreting market signals.

### Solution

Build a unified market-intelligence platform that converts real-time data and multiple analytical factors into understandable trading signals.

### Key Product Principles

* User-centric decision support
* Data-driven recommendations
* Real-time information
* Explainable signals
* Risk-aware decision making
* Continuous iteration

---

## 📈 Future Vision

The long-term vision is to evolve India AI Trader from a market-analysis dashboard into a comprehensive **AI-powered personal trading intelligence platform**.

Potential capabilities include:

```text
Market Data
     +
Technical Analysis
     +
Machine Learning
     +
News & Sentiment
     +
Portfolio Context
     +
Risk Management
     ↓
Personalized Trading Intelligence
```

---

## ⚠️ Disclaimer

India AI Trader is an educational and experimental technology project.

The signals generated by this platform are **not financial advice** and should not be treated as guaranteed predictions or recommendations to buy or sell securities.

Financial markets involve substantial risk. Users should conduct their own research and make independent financial decisions.

---

## 👨‍💻 Developer

### Ayush Chandel

Mechanical Engineering Student
India

**Project:** India AI Trader

Built as an independent AI/FinTech engineering project exploring:

* Artificial Intelligence
* Machine Learning
* Financial Technology
* Product Development
* Real-Time Data Systems
* Algorithmic Trading

---

## ⭐ Project

If you find the project interesting, feel free to explore the repository and follow its development.

**India AI Trader — Turning Market Data Into Trading Intelligence.**
