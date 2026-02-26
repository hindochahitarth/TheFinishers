# 🌿 GreenPulse AI

> **Research-Grade AI Environmental Intelligence Platform**  
> Real-time monitoring · Predictive analytics · Causal reasoning · Compliance checking

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        GreenPulse AI                            │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │  Next.js     │   │  FastAPI     │   │   AI Agent Layer   │  │
│  │  Frontend    │◄──│  Backend     │◄──│  (LangChain+GPT-4) │  │
│  │  Port 3000   │   │  Port 8000   │   └────────────────────┘  │
│  └──────────────┘   └──────┬───────┘                           │
│                             │                                   │
│              ┌──────────────┼──────────────┐                   │
│              ▼              ▼              ▼                    │
│         ┌─────────┐  ┌──────────┐  ┌──────────────┐           │
│         │  MySQL  │  │  Redis   │  │  ML Models   │           │
│         │  (Data) │  │  (Cache) │  │  XGBoost     │           │
│         └─────────┘  └──────────┘  │  LSTM        │           │
│                                    │  IsolationFst│           │
│                                    └──────────────┘           │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │           Data Pipeline (APScheduler + Async)          │    │
│  │  OpenWeatherMap API  │  OpenAQ API  │  TomTom Traffic  │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.11+
- Node.js 18+
- API Keys (OpenWeatherMap, OpenAQ, TomTom, OpenAI)

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 2. Start with Docker
```bash
docker-compose up --build
```

### 3. Access the Application
| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

---

## Local Development (Without Docker)

### Backend
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m data_pipeline.ingestion.seed_data
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Data Pipeline Scheduler
```bash
cd backend
python -m data_pipeline.ingestion.scheduler
```

---

## Core Capabilities

| Capability | Technology |
|-----------|-----------|
| Real-time AQI monitoring | OpenAQ + OpenWeatherMap APIs |
| 24h AQI Forecasting | XGBoost + LSTM Ensemble |
| Anomaly Detection | Isolation Forest + Z-score |
| Root Cause Analysis | Pearson correlation + LLM reasoning |
| Compliance Checking | WHO/CPCB rule engine |
| Natural Language Interface | LangChain ReAct + GPT-4o |
| Live Updates | WebSocket + Redis Pub/Sub |
| Explainability | SHAP values + Feature importance |

## Environmental Standards Supported
- **WHO** — World Health Organization 2021 guidelines
- **CPCB** — Central Pollution Control Board (India)
- **NAAQS** — National Ambient Air Quality Standards (US)
- **EU AQD** — EU Air Quality Directive

## Project Structure

```
GreenPulse AI/
├── backend/              # FastAPI Python backend
│   ├── app/              # Core application
│   ├── db/               # SQL migrations and init scripts
│   └── tests/            # Pytest test suite
├── frontend/             # Next.js 14 + Tailwind CSS
│   ├── app/              # App Router pages
│   └── components/       # Reusable UI components
├── ai_agents/            # LangChain agent system
├── data_pipeline/        # Ingestion, cleaning, feature engineering
├── ml_models/            # Trained models and training scripts
└── docker-compose.yml
```
