<p align="center">
  <h1 align="center">⚡ FMCG — RFP Bid Intelligence Platform</h1>
  <p align="center">
    <strong>Drop in an RFP. Get a polished proposal out the other side — with a human still in the loop when it matters.</strong>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/LangGraph-8_Node_Pipeline-blue?style=flat-square" />
    <img src="https://img.shields.io/badge/LLM-Llama_3.3_70B-green?style=flat-square" />
    <img src="https://img.shields.io/badge/Frontend-React_+_Vite-61DAFB?style=flat-square" />
    <img src="https://img.shields.io/badge/Database-Supabase_+_PostgreSQL-3ECF8E?style=flat-square" />
  </p>
</p>

---

## What is this?

FMCG is a bid intelligence platform built for an industrial cable manufacturer. Upload an RFP (PDF, DOCX, or TXT), and the system takes it from raw document to a ready-to-send proposal — autonomously, but with a human review step baked in for anything custom.

Here's what happens under the hood:

1. Requirements are extracted from the document
2. Each line item is matched against a 45-product cable catalog
3. Standard items go straight to pricing; custom items get an MTO blueprint generated
4. If MTO items exist, the workflow **pauses** and waits for a manager to review
5. Pricing is applied with a commodity volatility multiplier you can tune
6. A formatted markdown proposal is compiled
7. An outreach email draft is auto-generated — you review and send manually

Beyond the core pipeline, there's also a RAG chatbot for querying your documents and product catalog, a tender scouting system that crawls government portals daily, and an analytics dashboard for executives.

---

## LangGraph Workflow

The 8-node pipeline is the heart of this system. Every RFP runs through the same graph, with one key branch: if custom manufacturing is needed, the workflow pauses and waits for human approval before continuing.

```
START
  └─► sales_discovery
        └─► technical_matching
              └─► compliance_router
                    ├─► (all standard) ──────────────────────────────────────┐
                    │                                                         │
                    └─► (has MTO items) ──► mto_blueprint_gen                │
                                                └─► human_review ⏸️          │
                                                      └─► (approved)          │
                                                            └────────────────►┤
                                                                              │
                                                                    pricing_engine
                                                                         └─► output_compiler
                                                                               └─► email_draft
                                                                                     └─► END
```

| Node | What it does |
|------|-------------|
| `sales_discovery` | Reads the raw RFP and extracts structured requirements |
| `technical_matching` | Matches each requirement against the Supabase product catalog |
| `compliance_router` | Rule-based router — standard items skip ahead, custom items go to MTO |
| `mto_blueprint_gen` | Generates an engineering blueprint for custom cable orders |
| `human_review` | Pauses via `interrupt()` — a manager reviews and approves before the workflow continues |
| `pricing_engine` | Calculates final prices with the commodity volatility multiplier |
| `output_compiler` | Assembles the markdown proposal with tables and formatting |
| `email_draft` | Drafts a professional outreach email from the completed proposal |

Workflow state is persisted to PostgreSQL via LangGraph's `PostgresSaver`, so a paused workflow survives server restarts.

---

## Features

**RFP Processing** — upload a PDF, DOCX, or TXT and the pipeline handles the rest. Adjust the commodity volatility multiplier (0.5x–2.5x) with a real-time slider before finalising. Download the output as a `.txt` file.

**RAG Chatbot** — ask questions about the uploaded RFP or the product catalog. Built on FAISS + Gemini embeddings (`gemini-embedding-001`) with Llama 3.3 70B answering. Dual-layer guardrails (keyword filter + LLM prompt) keep it on topic, and every answer cites the source chunks it used.

**Tender Scout** — daily at 6:00 AM IST, the system scans tender portals (GeM, tendersontime.com, government sites) for opportunities matching your inventory. Results are deduplicated, structured by Llama 3.3, and emailed as an HTML table. You can also trigger a scan manually.

**Email Outreach** — the AI-drafted email is fully editable before you send. Subject, recipient, and body are all yours to change. The system never sends automatically.

**Analytics Dashboard** — KPI cards for proposals, products, scout runs, and inventory. 30-day proposal timeline and scout history charts via Recharts.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite |
| Styling | Vanilla CSS with custom properties (glassmorphic dark theme) |
| Charts | Recharts |
| Backend | FastAPI + Uvicorn |
| Orchestration | LangGraph (8-node workflow with PostgresSaver checkpointing) |
| LLM | ChatGroq — Llama 3.3 70B Versatile |
| Embeddings | Google Gemini `gemini-embedding-001` |
| Vector Store | FAISS (in-memory, CPU) |
| Database | Supabase (PostgreSQL) |
| Auth | Custom JWT — PyJWT + bcrypt, 72h HS256 tokens |
| Tender Search | Tavily API |
| Email | Resend API |
| Scheduler | APScheduler (cron) |
| PDF/DOCX Parsing | pdfplumber + python-docx |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- `uv` — `pip install uv`
- A Supabase project
- API keys for: Groq, Gemini, Tavily, Resend

### 1. Clone

```bash
git clone https://github.com/LayGupta/RFP-propoasal-automation.git
cd RFP-propoasal-automation
```

### 2. Environment Variables

```bash
cp .env.example .env
# Fill in your keys (see the table below)
```

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq Cloud key for Llama 3.3 70B | ✅ |
| `GEMINI_API_KEY` | Google Gemini key for embeddings | ✅ |
| `SUPABASE_URL` | Supabase project REST URL | ✅ |
| `SUPABASE_SERVICE_KEY` | Supabase `service_role` secret | ✅ |
| `DATABASE_URL` | Direct PostgreSQL connection string | ✅ |
| `TAVILY_API_KEY` | Tavily key for web search | ✅ |
| `JWT_SECRET` | Secret for signing JWT tokens | ✅ |
| `RESEND_API_KEY` | Resend key for transactional email | ✅ |
| `ALERT_EMAIL` | Where scout alerts are sent | ✅ |
| `ENV` | `development` or `production` | ❌ |
| `PORT` | Backend port (default: 8000) | ❌ |

### 3. Database Setup

Run these in the Supabase SQL Editor:

```sql
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sku_id TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    conductor_material TEXT NOT NULL,
    insulation_type TEXT NOT NULL,
    voltage_rating INTEGER NOT NULL,
    core_count INTEGER NOT NULL,
    cross_section_mm2 NUMERIC NOT NULL,
    armor_type TEXT DEFAULT 'unarmoured',
    base_price_per_meter NUMERIC NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    lead_time_days INTEGER DEFAULT 7,
    brand TEXT DEFAULT 'FMCG',
    category TEXT DEFAULT 'power_cable',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS proposals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    thread_id TEXT NOT NULL,
    project_name TEXT NOT NULL DEFAULT 'Untitled Project',
    final_markdown TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_proposals_user_id ON proposals(user_id);
CREATE INDEX IF NOT EXISTS idx_proposals_created_at ON proposals(created_at DESC);

CREATE TABLE IF NOT EXISTS scout_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    query TEXT NOT NULL,
    results_count INTEGER DEFAULT 0,
    alert_sent BOOLEAN DEFAULT false,
    results_json TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

> The `products` table should be seeded with your cable catalog. The system ships with 45 products across Polycab, Havells, and KEI — copper and aluminium conductors, XLPE/PVC insulation, 450V–1100V.

### 4. Run It

```bash
# Terminal 1 — backend
cd backend
uv sync
uv run uvicorn api.index:app --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**, register an account, and start uploading RFPs.

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register` | — | Register a new user |
| `POST` | `/api/auth/login` | — | Login, get JWT token |
| `POST` | `/api/process-rfp/start` | Optional | Upload RFP and start the workflow |
| `POST` | `/api/process-rfp/resume` | — | Resume a paused workflow after human review |
| `POST` | `/api/chat` | — | Ask the RAG chatbot a question |
| `POST` | `/api/chat/init` | — | Manually index a document |
| `GET` | `/api/history` | Required | Fetch saved proposals |
| `GET` | `/api/analytics` | Required | Dashboard KPIs and chart data |
| `POST` | `/api/scout-trigger` | — | Manually trigger a full inventory scout |
| `GET` | `/api/scout-logs` | — | Scout run history |
| `POST` | `/api/send-outreach` | — | Send the outreach email via Resend |
| `GET` | `/api/health` | — | Health check |

---

## Deployment

The project includes a `vercel.json` for deploying the backend as a serverless Python function on Vercel:

```json
{
  "version": 2,
  "builds": [{ "src": "backend/api/index.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/api/(.*)", "dest": "backend/api/index.py" }]
}
```

---

## License

Proprietary software developed for FMCG Industrial Solutions.

---

<p align="center">Built with ⚡ LangGraph, 🦙 Llama 3.3, and ☕ late nights.</p>
