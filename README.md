# Optimus TrustLayer

The Knowledge Operating System for Revenue Teams.

Optimus TrustLayer is an entity-centric, trust-aware knowledge layer that connects to your existing tools — Gmail, HubSpot, Google Drive, Sheets, and more — resolves entities across sources, and provides governed, cited answers. Never hallucinated, always traceable.

Built for RevOps and CS leaders who need to trust the data behind every decision.

---

## Architecture

Optimus follows a two-plane architecture:

- **Plane A (Async)** handles batch ingestion, entity resolution, and reconciliation.
- **Plane B (Sync)** handles live reads, belief computation, and answer assembly.

Knowledge is organized in two layers:

- **Personal Layer** — your connected data, your view, your permissions.
- **Company Layer (Canon)** — governed, versioned, approved facts. Every assertion has an author, citation, and approval trail.

### Core Engines

| Engine | Purpose |
|--------|---------|
| Belief Engine | Recomputes beliefs per viewer from visible evidence. Never stores beliefs as durable truths. |
| Entity Resolution | Splink + RapidFuzz (MIT). Probabilistic record linkage tuned to 0.98+ precision. |
| Reconciliation | Three-way merge for new source structures. Non-blocking. |
| Policy Engine | Classifies data by volatility and cost-of-staleness. |
| Canon Service | Governed company knowledge: assertions, proposals, approval queue, SoR declarations. |

---

## Surfaces

| Surface | Description |
|---------|-------------|
| Ask | AI assistant grounded in connected data. Cited answers, conflict surfacing, file and image support. |
| Browse | Entity graph explorer with search, filtering, and drill-down detail panels. |
| Decisions | Entity resolution review queue with full evidence breakdown. |
| Canon | Company knowledge management with approval workflows and Systems of Record. |
| Sources | Connection management for OAuth and API-key integrations. |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS |
| Backend | FastAPI, Pydantic, Python 3.11+ |
| LLM | OpenAI GPT-4o (via Portkey gateway) |
| Entity Resolution | Splink + RapidFuzz (MIT, zero cost) |
| Connectors | Nango Cloud (per-user OAuth) |
| CRM | HubSpot (Private App, direct API) |
| Document Parsing | LlamaCloud (LlamaParse) |
| Database | Neon Postgres |
| Vector DB | Qdrant Cloud |
| Event Bus | Redpanda Cloud |
| Workflows | Temporal Cloud |
| Observability | OpenTelemetry, Grafana Cloud |
| CI/CD | GitHub Actions, Railway, Vercel |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+

### Setup

```bash
git clone https://github.com/asapabhii/OPTIMUS.git
cd OPTIMUS

cp .env.example .env
# Fill in API keys — see .env.example for all required variables
```

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -e ".[dev]"
```

### Frontend

```bash
cd services/web
npm install
cd ../..
```

### Run

Backend (from project root):

```bash
uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend (from services/web):

```bash
cd services/web
npm run dev
```

Open http://localhost:5173

---

## Environment Variables

Copy `.env.example` to `.env` and fill in values. See the example file for full documentation.

| Variable | Required | Purpose |
|----------|----------|---------|
| OPENAI_API_KEY | Yes | LLM answers |
| NANGO_SECRET_KEY | Yes | OAuth connectors |
| DATABASE_URL | Yes | Neon Postgres |
| HUBSPOT_ACCESS_TOKEN | No | HubSpot CRM |
| LLAMA_CLOUD_API_KEY | No | Document parsing |
| QDRANT_URL, QDRANT_API_KEY | No | Vector search |
| GRAFANA_OTLP_ENDPOINT | No | Observability |
| PORTKEY_API_KEY | No | LLM gateway |

---

## Project Structure

```
OPTIMUS/
  core/                     Domain models, enums, freshness table
  engine/                   Belief, planner, reconciliation, policy, canon
  libs/                     Adapters, config, observability, resilience
  services/
    api/                    FastAPI backend and route handlers
    web/                    React frontend (Vite + TypeScript)
  fixture/                  Test fixtures and labeled ER corpus
  spikes/                   Technical spikes and experiments
  tests/                    Unit, integration, and regression suites
  infra/                    Dockerfiles and infrastructure config
```

---

## Deployment

- **Backend**: Railway (auto-deploys from main branch)
- **Frontend**: Vercel (auto-deploys from main branch)
- **Database**: Neon Postgres (managed)
- **All services**: Cloud-managed (Nango, Qdrant, Redpanda, Temporal)

---

## Testing

```bash
pytest                                          # all tests
pytest tests/suites/er_regression/ -v           # ER precision (Gate-1)
pytest tests/integration/ -v                    # integration tests
```

---

## Security

- JWT authentication on all API endpoints
- Per-viewer row-level security
- No live values stored in the knowledge graph (pointers, not payloads)
- Content-hash extraction cache (viewer-independent)
- All secrets via environment variables, never committed

---

## License

Proprietary. All rights reserved.
