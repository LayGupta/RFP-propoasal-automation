<p align="center">
  <h1 align="center">⚡ FMCG — RFP Bid Intelligence Platform</h1>
  <p align="center">
    <strong>Autonomous multi-agent RFP processing pipeline with human-in-the-loop review, RAG chatbot, proactive tender scouting, and executive analytics.</strong>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/LangGraph-8_Node_Pipeline-blue?style=flat-square" />
    <img src="https://img.shields.io/badge/LLM-Llama_3.3_70B-green?style=flat-square" />
    <img src="https://img.shields.io/badge/Frontend-React_+_Vite-61DAFB?style=flat-square" />
    <img src="https://img.shields.io/badge/Database-Supabase_+_PostgreSQL-3ECF8E?style=flat-square" />
    <img src="https://img.shields.io/badge/Auth-Custom_JWT-orange?style=flat-square" />
  </p>
</p>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [API Reference](#api-reference)
- [Frontend Components](#frontend-components)
- [LangGraph Workflow Nodes](#langgraph-workflow-nodes)
- [RAG Chatbot](#rag-chatbot)
- [Auto-Scout Tender System](#auto-scout-tender-system)
- [Email Outreach](#email-outreach)
- [Analytics Dashboard](#analytics-dashboard)
- [Screenshots](#screenshots)
- [Deployment](#deployment)
- [License](#license)

---

## Overview

FMCG RFP Bid Intelligence Platform is an enterprise-grade B2B application that automates the entire Request for Proposal (RFP) lifecycle for an industrial cable manufacturing company. Users upload RFP documents (PDF, DOCX, TXT), and the system autonomously:

1. **Extracts** structured requirements from the document
2. **Matches** each line item against a 45-product cable catalog in Supabase
3. **Routes** items through compliance checks — standard items go direct, custom items trigger MTO (Make-to-Order) blueprint generation
4. **Pauses** for human review when custom manufacturing is needed
5. **Prices** everything with commodity volatility multipliers
6. **Generates** a formatted markdown proposal
7. **Drafts** a professional outreach email for client submission
8. **Saves** the proposal to history for future reference

Beyond proposal generation, the platform includes an AI chatbot for querying document content and product catalogs, a proactive tender scouting system that scans government portals daily, and an executive analytics dashboard.

---

## Key Features

### 🏭 Core RFP Processing
- **PDF/DOCX/TXT ingestion** with server-side text extraction (pdfplumber + python-docx)
- **8-node LangGraph workflow** with persistent PostgreSQL checkpointing
- **Human-in-the-loop review** — workflow pauses at MTO items for manager approval
- **Commodity volatility pricing** — adjustable 0.5x–2.5x multiplier with real-time slider
- **Formatted proposal output** with download as `.txt` file

### 🤖 RAG Chatbot
- **FAISS vector store** auto-built from uploaded RFPs + product catalog
- **Gemini embeddings** (`gemini-embedding-001`) for semantic search
- **ChatGroq (Llama 3.3 70B)** for answer generation
- **Guardrails** — keyword + LLM dual-layer filtering blocks off-topic questions
- **Source citations** — shows retrieved chunks used for each answer

### 🔍 Auto-Scout Tender System
- **Inventory-wide scanning** — queries all product categories (insulation, voltage, material combinations)
- **Tavily deep web search** — crawls tender portals (tendersontime.com, GeM, govt sites)
- **LLM structuring** — Llama 3.3 extracts title, authority, summary, URL from raw results
- **Deduplication** — same tender found via multiple queries appears once
- **Email alerts** — tabulated HTML email via Resend API
- **Cron schedule** — daily at 6:00 AM IST via APScheduler
- **Collapsible UI** — minimize/expand toggle in sidebar

### 📊 Executive Analytics Dashboard
- **KPI cards** — Total proposals, products, scout runs, inventory items
- **Proposals timeline** — 30-day bar chart (Recharts)
- **Scout history** — results count over time
- **Product distribution** — breakdown by category

### 📧 Email Outreach
- **AI-drafted email** — auto-generated from proposal content
- **Fully editable** — textarea for body, editable subject + recipient
- **Manual send** — "Send to Client" button (never auto-sends)
- **Reset to original** — restore AI draft after edits
- **Resend API** integration

### 🔐 Authentication
- **Custom JWT auth** — replaces Supabase Auth
- **bcrypt password hashing** (cost factor 12)
- **72-hour token expiry** with HS256 signing
- **Register + Login** pages with validation
- **localStorage persistence** — auto-login on refresh

### 🎨 Premium Dark UI
- **Glassmorphism** — `backdrop-filter: blur()` on sidebar, header, cards
- **Ambient glow** — radial blue/emerald gradients in background
- **Micro-interactions** — hover lift, active scale, slide transitions
- **Floating icon animation** — dropzone icon gently bobs
- **Premium buttons** — gradient fills with glow on hover

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │
│  │LoginPage │ │BidManager│ │MtoModal  │ │ProposalViewer      │ │
│  │          │ │(Dropzone)│ │(Review)  │ │(Output + Download) │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │
│  │ChatPanel │ │Analytics │ │ScoutSet. │ │OutreachEmailViewer │ │
│  │(RAG Bot) │ │Dashboard │ │(Tenders) │ │(Editable Draft)    │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (Vite Proxy → :8000)
┌───────────────────────────▼─────────────────────────────────────┐
│                     BACKEND (FastAPI + Uvicorn)                  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              api/index.py — API Gateway                    │  │
│  │  /api/process-rfp/start   /api/process-rfp/resume         │  │
│  │  /api/chat                /api/chat/init                   │  │
│  │  /api/history             /api/analytics                   │  │
│  │  /api/scout-trigger       /api/scout-tenders               │  │
│  │  /api/scout-logs          /api/send-outreach               │  │
│  │  /api/auth/register       /api/auth/login                  │  │
│  │  /api/health                                               │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │         api/graph/workflow.py — LangGraph Pipeline    │       │
│  │                                                       │       │
│  │  sales_discovery → technical_matching → compliance    │       │
│  │       → mto_blueprint_gen → human_review (INTERRUPT)  │       │
│  │       → pricing_engine → output_compiler              │       │
│  │       → email_draft → END                             │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐     │
│  │ api/auth.py  │  │ api/rag/     │  │ api/scheduler.py  │     │
│  │ JWT + bcrypt │  │ FAISS+Gemini │  │ APScheduler cron  │     │
│  └──────────────┘  └──────────────┘  └───────────────────┘     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
   ┌──────────┐     ┌──────────┐     ┌──────────────┐
   │ Supabase │     │PostgreSQL│     │  External     │
   │  Tables  │     │Checkpoint│     │  APIs         │
   │ users    │     │(LangGraph│     │ • Groq Cloud  │
   │ products │     │  state)  │     │ • Gemini      │
   │ proposals│     │          │     │ • Tavily      │
   │scout_logs│     │          │     │ • Resend      │
   └──────────┘     └──────────┘     └──────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + Vite | SPA with HMR |
| **Styling** | Vanilla CSS (Custom Properties) | Glassmorphic dark theme design system |
| **Charts** | Recharts | Analytics dashboard visualizations |
| **Backend** | FastAPI + Uvicorn | Async API gateway |
| **Orchestration** | LangGraph | 8-node stateful workflow with interrupts |
| **LLM** | ChatGroq (Llama 3.3 70B Versatile) | All reasoning + generation nodes |
| **Embeddings** | Google Gemini (`gemini-embedding-001`) | Document + catalog vectorization |
| **Vector Store** | FAISS (CPU) | In-memory semantic search for RAG |
| **Database** | Supabase (PostgreSQL) | Tables: users, products, proposals, scout_logs |
| **Checkpointer** | LangGraph PostgresSaver | Persistent workflow state across restarts |
| **Auth** | Custom JWT (PyJWT + bcrypt) | HS256 token signing, 72h expiry |
| **Search** | Tavily API | Deep web search for tender scouting |
| **Email** | Resend API | Transactional emails (outreach + alerts) |
| **Scheduler** | APScheduler | Daily cron job for tender scouting |
| **PDF Parsing** | pdfplumber | Server-side PDF text extraction |
| **DOCX Parsing** | python-docx | Server-side DOCX text extraction |
| **Package Manager** | uv (Python), npm (JS) | Fast dependency resolution |

---

## Project Structure

```
FMCG/
├── .env                          # Environment variables (API keys, DB URLs)
├── .gitignore
├── vercel.json                   # Vercel deployment config
├── README.md                     # This file
│
├── backend/
│   ├── pyproject.toml            # Python dependencies (uv/pip)
│   ├── uv.lock                   # Locked dependency versions
│   ├── test_rfp_sample.txt       # Sample RFP for testing
│   │
│   └── api/
│       ├── __init__.py
│       ├── index.py              # FastAPI app — all 13 API endpoints
│       ├── auth.py               # JWT auth: register, login, verify
│       ├── scheduler.py          # APScheduler cron + inventory-wide scout
│       │
│       ├── database/
│       │   ├── __init__.py
│       │   └── client.py         # Supabase client + PostgreSQL pool singletons
│       │
│       ├── graph/
│       │   ├── __init__.py
│       │   ├── state.py          # TypedDict state schema (RFPState)
│       │   └── workflow.py       # 8-node LangGraph workflow definition
│       │
│       └── rag/
│           ├── __init__.py
│           ├── engine.py         # FAISS index builder + RAG ask()
│           └── guardrails.py     # System prompt + keyword guardrails
│
└── frontend/
    ├── package.json
    ├── vite.config.js            # Vite config with API proxy to :8000
    ├── index.html
    │
    └── src/
        ├── App.jsx               # Root layout: auth gate, sidebar, tabs
        ├── index.css             # Complete design system (1700+ lines)
        ├── main.jsx              # React entry point
        │
        └── components/
            ├── LoginPage.jsx         # Register/Login form with JWT
            ├── BidManager.jsx        # File dropzone + processing overlay
            ├── MtoModal.jsx          # Human-in-the-loop MTO review panel
            ├── VolatilitySlider.jsx   # Commodity multiplier slider (0.5x–2.5x)
            ├── ProposalViewer.jsx     # Markdown renderer + Download .TXT + Copy
            ├── OutreachEmailViewer.jsx# Editable email draft + Send button
            ├── HistorySidebar.jsx     # Proposal history list with select
            ├── ChatPanel.jsx          # RAG chatbot slide-out drawer
            ├── AnalyticsDashboard.jsx # KPI cards + Recharts charts
            └── ScoutSettings.jsx      # Collapsible tender scout panel
```

---

## Local Development

### Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **uv** (Python package manager) — `pip install uv`
- **Supabase** account with a project
- API keys: Groq, Gemini, Tavily, Resend

### 1. Clone the Repository

```bash
git clone https://github.com/LayGupta/RFP-propoasal-automation.git
cd RFP-propoasal-automation

### 2. Setup Environment Variables

```bash
cp .env.example .env
# Fill in all required API keys (see Environment Variables section)
```

### 3. Backend Setup

```bash
cd backend

# Install Python dependencies with uv
uv sync

# Run database migrations (create tables in Supabase)
uv run python -c "from api.database.client import supabase_client; print('DB connected!')"

# Start the backend server
uv run uvicorn api.index:app --host 0.0.0.0 --port 8000
```

### 4. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start the development server
npm run dev
```

### 5. Open the Application

Navigate to **http://localhost:5173** in your browser. Register a new account and start processing RFPs.

---

## Environment Variables

Create a `.env` file in the project root with the following variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq Cloud API key for Llama 3.3 70B | ✅ |
| `GEMINI_API_KEY` | Google Gemini API key for embeddings | ✅ |
| `SUPABASE_URL` | Supabase project REST API URL | ✅ |
| `SUPABASE_SERVICE_KEY` | Supabase service_role secret key | ✅ |
| `DATABASE_URL` | Direct PostgreSQL connection string | ✅ |
| `TAVILY_API_KEY` | Tavily API key for web search | ✅ |
| `JWT_SECRET` | Secret key for signing JWT tokens | ✅ |
| `RESEND_API_KEY` | Resend API key for transactional emails | ✅ |
| `ALERT_EMAIL` | Email address for scout alert notifications | ✅ |
| `SCOUT_QUERY` | Default scout search query (overridden by inventory scan) | ❌ |
| `ENV` | Environment mode (`development` / `production`) | ❌ |
| `PORT` | Backend server port (default: 8000) | ❌ |

---

## Database Setup

Run these SQL migrations in the **Supabase SQL Editor** (Dashboard → SQL Editor → New Query):

### Users Table

```sql
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Products Table (Inventory Catalog)

```sql
CREATE TABLE IF NOT EXISTS products (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sku_id TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    conductor_material TEXT NOT NULL,        -- 'copper' or 'aluminium'
    insulation_type TEXT NOT NULL,           -- 'XLPE', 'PVC', 'EPR'
    voltage_rating INTEGER NOT NULL,         -- e.g., 450, 600, 1100
    core_count INTEGER NOT NULL,             -- e.g., 1, 2, 3, 4
    cross_section_mm2 NUMERIC NOT NULL,      -- e.g., 1.5, 4.0, 25.0
    armor_type TEXT DEFAULT 'unarmoured',
    base_price_per_meter NUMERIC NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    lead_time_days INTEGER DEFAULT 7,
    brand TEXT DEFAULT 'FMCG',
    category TEXT DEFAULT 'power_cable',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Proposals Table

```sql
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
```

### Scout Logs Table

```sql
CREATE TABLE IF NOT EXISTS scout_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    query TEXT NOT NULL,
    results_count INTEGER DEFAULT 0,
    alert_sent BOOLEAN DEFAULT false,
    results_json TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

> **Note:** The `products` table should be populated with your cable product catalog. The system includes 45 real products across Polycab, Havells, and KEI brands with copper/aluminium conductors, XLPE/PVC insulation, and voltage ratings from 450V to 1100V.

---

## API Reference

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register` | — | Register a new user account |
| `POST` | `/api/auth/login` | — | Login and receive JWT token |

### RFP Processing

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/process-rfp/start` | Optional | Upload RFP document, start workflow |
| `POST` | `/api/process-rfp/resume` | — | Resume paused workflow with human review |

### Chatbot

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/chat` | — | Ask a question (RAG retrieval + LLM) |
| `POST` | `/api/chat/init` | — | Manually index a document for RAG |

### History & Analytics

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/history` | Required | Fetch user's saved proposals |
| `GET` | `/api/analytics` | Required | Get dashboard KPIs and charts |

### Tender Scouting

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/scout-trigger` | — | Manually trigger inventory-wide scout |
| `POST` | `/api/scout-tenders` | — | Search for tenders with custom query |
| `GET` | `/api/scout-logs` | — | Fetch scout run history |

### Email & Health

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/send-outreach` | — | Send edited outreach email via Resend |
| `GET` | `/api/health` | — | Health check endpoint |

---

## Frontend Components

| Component | File | Purpose |
|-----------|------|---------|
| **LoginPage** | `LoginPage.jsx` | Register/Login form with JWT auth flow |
| **BidManager** | `BidManager.jsx` | Drag-and-drop file upload + processing overlay |
| **MtoModal** | `MtoModal.jsx` | Human-in-the-loop MTO blueprint review panel |
| **VolatilitySlider** | `VolatilitySlider.jsx` | Commodity multiplier slider with glowing pill badge |
| **ProposalViewer** | `ProposalViewer.jsx` | Markdown renderer with Download .TXT and Copy buttons |
| **OutreachEmailViewer** | `OutreachEmailViewer.jsx` | Editable email draft with manual Send to Client |
| **HistorySidebar** | `HistorySidebar.jsx` | Proposal history list with emerald dot indicators |
| **ChatPanel** | `ChatPanel.jsx` | Slide-out RAG chatbot with source citations |
| **AnalyticsDashboard** | `AnalyticsDashboard.jsx` | KPI cards + Recharts bar/line charts |
| **ScoutSettings** | `ScoutSettings.jsx` | Collapsible tender scout panel with tabulated results |

---

## LangGraph Workflow Nodes

The 8-node pipeline is defined in `backend/api/graph/workflow.py`:

```
START → sales_discovery → technical_matching → compliance_router
  │
  ├─ (all standard) → pricing_engine → output_compiler → email_draft → END
  │
  └─ (has MTO items) → mto_blueprint_gen → human_review (INTERRUPT)
                         ↓ (user resumes)
                    pricing_engine → output_compiler → email_draft → END
```

| # | Node | LLM | Description |
|---|------|-----|-------------|
| 1 | **sales_discovery** | Llama 3.3 70B | Extracts structured requirements from raw RFP text |
| 2 | **technical_matching** | Llama 3.3 70B | Matches each requirement against Supabase product catalog |
| 3 | **compliance_router** | Rule-based | Routes items: standard → pricing, custom → MTO blueprint |
| 4 | **mto_blueprint_gen** | Llama 3.3 70B | Generates engineering blueprints for custom cable items |
| 5 | **human_review** | — | `interrupt()` — pauses workflow for manager approval |
| 6 | **pricing_engine** | Rule-based | Calculates prices with commodity volatility multiplier |
| 7 | **output_compiler** | — | Assembles final markdown proposal with tables |
| 8 | **email_draft** | Llama 3.3 70B | Drafts professional outreach email from proposal |

### State Schema

```python
class RFPState(TypedDict):
    raw_rfp_content: str
    metadata: dict
    extracted_requirements: list[RFPRequirement]
    matched_skus: list[SKURecommendation]
    mto_blueprints: list[str]
    pricing_breakdown: list[dict]
    commodity_volatility_multiplier: float
    human_override_notes: Optional[str]
    final_proposal_markdown: str
    approved_by: Optional[str]
    user_id: Optional[str]
    outreach_email_draft: Optional[str]
```

---

## RAG Chatbot

The chatbot uses Retrieval-Augmented Generation to answer questions about uploaded RFP documents and the product catalog.

### How It Works

1. **Auto-indexing** — When a PDF is uploaded via `/api/process-rfp/start`, the extracted text is automatically indexed into a FAISS vector store using Gemini embeddings (`gemini-embedding-001`)
2. **Product catalog merge** — Product data from the `products` table is concatenated with the document text before indexing
3. **Semantic search** — User questions are embedded and the top-4 most similar chunks are retrieved
4. **LLM answer** — ChatGroq (Llama 3.3 70B) generates an answer grounded in the retrieved context
5. **Guardrails** — Dual-layer filtering: keyword pre-filter + LLM system prompt ensure on-topic responses

### Supported Questions
- "What is the client name in the RFP?"
- "List all cable requirements"
- "What voltage ratings are available?"
- "Show me copper XLPE products in inventory"
- "What is the price for SKU PLB-CU-XLPE-3C-25?"

---

## Auto-Scout Tender System

The scout system proactively discovers government and corporate tenders matching your inventory.

### How It Works

1. **Inventory scan** — Queries the `products` table and groups by distinct `(insulation_type, voltage_rating, conductor_material)` combinations
2. **Targeted queries** — Builds search queries like `"1100V XLPE copper cable tender RFP India 2025"` for each category (max 5)
3. **Tavily deep search** — Advanced-depth web search across tender portals
4. **LLM structuring** — Llama 3.3 extracts structured JSON: title, summary, authority, URL
5. **Deduplication** — Same tender from multiple searches appears only once
6. **Email alert** — Sends a tabulated HTML email to `ALERT_EMAIL` via Resend
7. **Database logging** — Saves results to `scout_logs` table

### Schedule
- **Automatic**: Daily at 6:00 AM IST (00:30 UTC) via APScheduler cron
- **Manual**: Click "🌐 Scout Now (All Categories)" in the sidebar

---

## Email Outreach

The system auto-generates a professional bid submission email after proposal completion.

### Features
- **AI-drafted** by Llama 3.3 based on the final proposal content
- **Fully editable** — body, subject, and recipient are all editable
- **Manual send only** — email is NEVER sent automatically; user must review, edit, and click "Send to Client"
- **Reset to original** — one-click restore of the AI draft
- **Resend API** — transactional email delivery with tracking

---

## Analytics Dashboard

The executive dashboard (accessible via the "📊 Analytics" tab) provides:

| Metric | Source |
|--------|--------|
| Total Proposals Generated | `proposals` table count |
| Product Catalog Size | `products` table count |
| Scout Runs | `scout_logs` table count |
| Proposals Timeline (30 days) | `proposals.created_at` grouped by day |
| Scout Results History | `scout_logs.results_count` over time |

Built with **Recharts** for responsive bar and line charts.

---

## Deployment

### Vercel (Serverless)

The project includes a `vercel.json` for deploying the backend as a Vercel Python serverless function:

```json
{
  "version": 2,
  "builds": [{ "src": "backend/api/index.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/api/(.*)", "dest": "backend/api/index.py" }]
}
```

### Local Development

```bash
# Terminal 1: Backend
cd backend
uv run uvicorn api.index:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

The Vite dev server proxies `/api/*` requests to the backend at `http://localhost:8000`.

---

## License

This project is proprietary software developed for FMCG Industrial Solutions.

---

<p align="center">
  Built with ⚡ LangGraph, 🦙 Llama 3.3, and ☕ late nights.
</p>
