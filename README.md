# Optimus TrustLayer

**The Knowledge Operating System for Revenue Teams.**

Optimus TrustLayer is an entity-centric, trust-aware knowledge layer that connects to your existing tools (Gmail, HubSpot, Google Drive, Sheets, and more), resolves entities across sources, and provides governed, cited answers — never hallucinated, always traceable.

Built for RevOps and CS leaders who need to trust the data behind every decision.

---

## Architecture

```
                         +------------------+
                         |   React Frontend |
                         |   (Vite + TS)    |
                         +--------+---------+
                                  |
                         +--------+---------+
                         |   FastAPI Backend |
                         |   (Python 3.11+) |
                         +--------+---------+
                                  |
          +----------+----+-------+-------+----------+
          |          |         |          |           |
     +----+---+ +---+----+ +-+------+ +-+-------+ +-+--------+
     | Nango  | |HubSpot | |OpenAI  | |Splink+  | | LlamaCloud|
     | (OAuth)| |(Direct)| |(LLM)   | |RapidFuzz| | (Parsing) |
     +--------+ +--------+ +--------+ |(ER)     | +-----------+
                                       +--------+
```

### Two-Plane Architecture

- **Plane A (Async)**: Batch ingestion, entity resolution, reconciliation
- **Plane B (Sync)**: Live reads, belief computation, answer assembly

### Core Engines

| Engine | Purpose |
|--------|---------|
| **Belief Engine** | Recomputes beliefs per viewer from visible evidence. Never stores beliefs as durable truths. |
| **Entity Resolution** | Splink + RapidFuzz (MIT). Probabilistic record linkage with tuned precision (>=0.98). |
| **Reconciliation** | Three-way merge for new source structures. Non-blocking. |
| **Policy Engine** | Classifies data by volatility and cost-of-staleness. |
| **Canon Service** | Governed company knowledge: assertions, proposals, approval queue, SoR declarations. |

### Two Layers of Knowledge

- **Personal Layer**: Your connected data, your view, your permissions
- **Company Layer (Canon)**: Governed, versioned, approved facts. Every assertion has an author, citation, and approval.

---

## Surfaces

| Surface | Description |
|---------|-------------|
| **Ask** | AI assistant grounded in your connected data. Cited answers, conflict surfacing, file/image support. |
| **Browse** | Entity graph explorer. Search, filter, drill into any entity across all sources. |
| **Decisions** | Entity resolution review queue. Approve/reject potential duplicates with full evidence breakdown. |
| **Canon** | Company knowledge management. Approval queue for proposed facts, Systems of Record declarations. |
| **Sources** | Connection management. OAuth (Gmail, Drive, Sheets) + direct API (HubSpot). |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, Lucide Icons |
| Backend | FastAPI, Pydantic, Python 3.11+ |
| LLM | OpenAI GPT-4o (via Portkey gateway) |
| Entity Resolution | Splink + RapidFuzz (MIT, zero cost) |
| OAuth / Connectors | Nango Cloud (per-user OAuth, token lifecycle) |
| CRM | HubSpot (Private App, direct API) |
| Document Parsing | LlamaCloud (LlamaParse) |
| Database | Neon Postgres (async) |
| Vector DB | Qdrant Cloud |
| Event Bus | Redpanda Cloud (Kafka protocol) |
| Workflows | Temporal Cloud |
| Observability | OpenTelemetry, Grafana Cloud |
| CI/CD | GitHub Actions |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### 1. Clone and setup

```bash
git clone https://github.com/asapabhii/OPTIMUS.git
cd OPTIMUS
```

### 2. Environment variables

```bash
cp .env.example .env
# Fill in your API keys (see .env.example for all required keys)
```

### 3. Backend

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

### 4. Frontend

```bash
cd services/web
npm install
cd ../..
```

### 5. Run

**Backend** (from project root):
```bash
PYTHONPATH=. uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend** (from `services/web`):
```bash
cd services/web
npm run dev
```

---

## Environment Variables

All configuration is environment-driven. Copy `.env.example` to `.env` and fill in values.

| Variable | Required | Service |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | LLM answers |
| `NANGO_SECRET_KEY` | Yes | OAuth connectors (Gmail, Drive, Sheets) |
| `HUBSPOT_ACCESS_TOKEN` | Optional | HubSpot CRM (create at Legacy Apps > Private App) |
| `DATABASE_URL` | Yes | Neon Postgres |
| `LLAMA_CLOUD_API_KEY` | Optional | Document parsing |
| `QDRANT_URL` / `QDRANT_API_KEY` | Optional | Vector search |
| `GRAFANA_OTLP_ENDPOINT` / `GRAFANA_OTLP_TOKEN` | Optional | Observability |
| `PORTKEY_API_KEY` | Optional | LLM gateway routing |
| `AIRBYTE_API_KEY` | Optional | Batch ingestion |
| `REDPANDA_BROKERS` | Optional | Event bus |
| `TEMPORAL_API_KEY` | Optional | Workflow orchestration |

---

