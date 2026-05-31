# ⚡ FMCG — RFP Bid Intelligence Platform

> **AI-powered multi-agent system for automated Request for Proposal (RFP) analysis, cable product matching, engineering blueprint generation, and commercial bid proposal compilation — purpose-built for electrical cable manufacturing companies.**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19+-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2+-FF6F00?logo=data:image/svg+xml;base64,&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036)](https://groq.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3FCF8E?logo=supabase&logoColor=white)](https://supabase.com)

---

## 📋 Table of Contents

- [What Does This System Do?](#-what-does-this-system-do)
- [System Architecture](#-system-architecture)
- [Multi-Agent Workflow — The 7-Node Pipeline](#-multi-agent-workflow--the-7-node-pipeline)
- [Human-in-the-Loop Review](#-human-in-the-loop-review)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [Frontend Components](#-frontend-components)
- [Deployment](#-deployment)
- [How It Works — End-to-End Flow](#-how-it-works--end-to-end-flow)

---

## 🎯 What Does This System Do?

In the cable manufacturing industry, companies receive **Requests for Proposals (RFPs)** from clients specifying exact cable requirements — core counts, conductor materials, voltage ratings, insulation types, and quantities. Sales engineers must manually:

1. Parse these multi-page documents to extract individual line item specifications
2. Cross-reference each spec against the company's product catalog
3. Identify which items can be fulfilled from standard inventory vs. which require custom **Make-to-Order (MTO)** manufacturing
4. Generate engineering modification blueprints for custom items
5. Calculate pricing with commodity volatility adjustments
6. Compile everything into a formal bid proposal

**This platform automates the entire process using a multi-agent AI pipeline**, reducing what takes days of manual work into minutes of automated analysis with a single human review checkpoint.

### Key Capabilities

| Capability | Description |
|---|---|
| **Document Parsing** | Accepts PDF, DOCX, and TXT uploads; extracts text server-side |
| **AI Requirement Extraction** | LLM-powered structured parsing of natural language into typed specifications |
| **Automated SKU Matching** | Voltage-threshold-based catalog matching with gap analysis |
| **MTO Detection** | Automatic flagging of items exceeding standard catalog parameters (>600V) |
| **Engineering Blueprints** | AI-generated modification profiles for custom manufacturing items |
| **Human Review Gate** | Workflow pauses for manager approval with adjustable pricing controls |
| **Dynamic Pricing** | Commodity volatility multiplier applied to all base prices |
| **Proposal Generation** | Complete markdown bid document with tables, specs, blueprints, and pricing |
| **Persistent State** | PostgreSQL-backed checkpointing survives server restarts and serverless cold starts |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ BidManager   │  │  MtoModal    │  │ Volatility   │  │ Proposal  │  │
│  │ (File Upload)│  │ (HITL Review)│  │ Slider       │  │ Viewer    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘  └───────────┘  │
│         │ FormData         │ JSON                                      │
│         ▼                  ▼                                           │
│    POST /api/start    POST /api/resume                                 │
└─────────┬──────────────────┬───────────────────────────────────────────┘
          │  Vite Proxy      │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + LangGraph)                       │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   FastAPI Gateway (index.py)                    │   │
│  │  • Multipart file upload + server-side PDF/DOCX/TXT parsing    │   │
│  │  • Routes to LangGraph workflow via .stream()                  │   │
│  │  • Catches interrupt events for HITL pause/resume              │   │
│  └────────────────────────────┬────────────────────────────────────┘   │
│                               │                                        │
│  ┌────────────────────────────▼────────────────────────────────────┐   │
│  │              LangGraph StateGraph (workflow.py)                 │   │
│  │                                                                 │   │
│  │  START → [Sales Discovery] → [Technical Matching]               │   │
│  │               │                       │                         │   │
│  │               │              ┌────────▼────────┐                │   │
│  │               │              │ Compliance       │                │   │
│  │               │              │ Router           │                │   │
│  │               │              └──┬───────────┬──┘                │   │
│  │               │          has MTO│           │all standard       │   │
│  │               │                 ▼           │                   │   │
│  │               │    [MTO Blueprint Gen]      │                   │   │
│  │               │           │                 │                   │   │
│  │               │           ▼                 │                   │   │
│  │               │    [Human Review] ◄─ interrupt()                │   │
│  │               │           │                 │                   │   │
│  │               │           ▼                 │                   │   │
│  │               │    [Pricing Engine] ◄───────┘                   │   │
│  │               │           │                                     │   │
│  │               │           ▼                                     │   │
│  │               │    [Output Compiler] → END                      │   │
│  └───────────────┼─────────────────────────────────────────────────┘   │
│                  │                                                      │
│  ┌───────────────▼─────────────────────────────────────────────────┐   │
│  │                    Persistence Layer                            │   │
│  │  ┌─────────────────────┐    ┌──────────────────────────────┐   │   │
│  │  │ Supabase REST Client│    │ PostgresSaver (Checkpointer) │   │   │
│  │  │ (Table queries)     │    │ psycopg ConnectionPool       │   │   │
│  │  └─────────────────────┘    └──────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │    Supabase PostgreSQL DB     │
                    │  • checkpoint tables          │
                    │  • checkpoint_blobs           │
                    │  • checkpoint_writes          │
                    └──────────────────────────────┘
```

---

## 🤖 Multi-Agent Workflow — The 7-Node Pipeline

The core intelligence is a **LangGraph StateGraph** with 7 nodes, a conditional router, and a human interrupt gate. Each node reads from and writes to a shared `RFPState` dictionary that persists across requests via PostgreSQL checkpointing.

### Node Details

| # | Node | Type | LLM? | What It Does |
|---|---|---|---|---|
| 1 | **Sales Discovery** | Processing | ✅ Llama 3.3 70B | Parses raw RFP text into structured `RFPRequirement` objects — extracts line item IDs, core counts, conductor materials, voltage ratings, insulation types |
| 2 | **Technical Matching** | Processing | ❌ Rule-based | Matches each requirement against the product catalog using a >600V threshold. Items ≤600V get 92.5% match (standard). Items >600V get 65% match and are flagged as custom MTO |
| 3 | **Compliance Router** | Decision | ❌ Pure function | Checks if any matched SKU has `is_custom_mto=True`. Routes to MTO blueprint generation or directly to pricing |
| 4 | **MTO Blueprint Generator** | Processing | ✅ Llama 3.3 70B | For each MTO-flagged item, generates a detailed engineering modification blueprint covering insulation changes, extrusion parameters, QA testing requirements, and lead time estimates |
| 5 | **Human Review Gate** | Interrupt | ❌ `interrupt()` | **Pauses the entire workflow** and persists state to PostgreSQL. Returns blueprint data to the frontend for manager review. Resumes only when the API receives a `Command(resume=...)` call |
| 6 | **Pricing Engine** | Processing | ❌ Formulaic | Calculates base prices using core count, voltage tier, and material premiums. Applies the commodity volatility multiplier (potentially adjusted by the human reviewer) |
| 7 | **Output Compiler** | Processing | ❌ Template | Assembles all results into a structured markdown proposal document with requirements matrix, SKU matching table, MTO blueprints, pricing breakdown, and human review notes |

### State Schema

Every node reads/writes to a shared `RFPState` (TypedDict):

```python
class RFPState(TypedDict):
    raw_rfp_content: str                              # Raw document text
    metadata: dict[str, str]                          # Client name, project, date
    extracted_requirements: list[RFPRequirement]       # Parsed line items
    matched_skus: list[SKURecommendation]             # Catalog matches
    mto_blueprints: list[str]                         # Engineering modification docs
    pricing_breakdown: list[dict[str, float]]         # Per-SKU pricing
    commodity_volatility_multiplier: float            # Human-adjustable pricing factor
    human_override_notes: str | None                  # Manager review comments
    final_proposal_markdown: str                      # Compiled output document
```

---

## 👤 Human-in-the-Loop Review

This is the critical differentiator. When the compliance router detects items requiring custom manufacturing, the workflow **does not complete automatically**. Instead:

1. **Workflow pauses** at the Human Review node via LangGraph's `interrupt()` primitive
2. **State is persisted** to PostgreSQL (survives server restarts, Vercel cold starts)
3. **Blueprint payload is returned** to the frontend via the API response
4. **MTO Modal opens** showing a side-by-side comparison of non-compliant specs vs. engineering blueprints
5. **Manager adjusts** the commodity volatility multiplier and adds compliance notes
6. **Frontend calls `/resume`** with the review data, which issues `Command(resume=...)` to wake the exact checkpointed state
7. **Workflow continues** through pricing and output compilation with the adjusted parameters

This pattern ensures **no automated bid goes out without human verification** on custom manufacturing items.

---

## 🛠 Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.12+ | Runtime |
| **FastAPI** | 0.115+ | API framework with async support |
| **LangGraph** | 1.2+ | Multi-agent state graph orchestration |
| **ChatGroq** | — | LLM inference via Groq Cloud (Llama 3.3 70B) |
| **PostgresSaver** | 3.1+ | Persistent state checkpointing |
| **psycopg** | 3.3+ | PostgreSQL adapter with connection pooling |
| **Supabase** | 2.30+ | Database hosting + REST client |
| **pdfplumber** | 0.11+ | PDF text extraction |
| **python-docx** | 1.2+ | DOCX text extraction |
| **uv** | — | Python package manager |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| **React** | 19+ | UI framework |
| **Vite** | 8+ | Build tool + dev server with HMR |
| **Vanilla CSS** | — | Custom design system (zinc/steel industrial palette) |

### Infrastructure
| Technology | Purpose |
|---|---|
| **Supabase** | Managed PostgreSQL database + REST API |
| **Vercel** | Serverless deployment (monorepo config) |
| **Groq Cloud** | Ultra-fast LLM inference (< 1s latency) |

---

## 📁 Project Structure

```
FMCG/
├── .gitignore                          # Protects .env secrets
├── vercel.json                         # Monorepo deployment routing
├── implementation_plan.md              # Architecture design document
│
├── backend/                            # 🐍 Python Multi-Agent Backend
│   ├── pyproject.toml                  # Project config (uv + hatch)
│   ├── requirements.txt                # Vercel dependency list
│   └── api/
│       ├── __init__.py
│       ├── index.py                    # FastAPI gateway — file upload, /start, /resume endpoints
│       ├── database/
│       │   ├── __init__.py
│       │   └── client.py              # Supabase client + PostgreSQL connection pool
│       └── graph/
│           ├── __init__.py
│           ├── state.py               # RFPState, RFPRequirement, SKURecommendation TypedDicts
│           └── workflow.py            # 7-node LangGraph StateGraph + PostgresSaver
│
└── frontend/                           # ⚛️ React Vite Frontend
    ├── index.html                      # HTML base with SEO meta
    ├── package.json                    # Node dependencies
    ├── vite.config.js                  # Dev proxy /api/* → localhost:8000
    └── src/
        ├── main.jsx                    # React root entry
        ├── index.css                   # Complete design system (~570 lines)
        ├── App.jsx                     # Two-column layout + global state manager
        └── components/
            ├── BidManager.jsx          # Drag-and-drop file upload + processing overlay
            ├── MtoModal.jsx            # Human review modal — SKU grid, blueprints, controls
            ├── ProposalViewer.jsx      # Markdown-to-HTML bid document renderer
            └── VolatilitySlider.jsx    # Sidebar commodity pricing control (0.5×–2.5×)
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+** installed
- **Node.js 18+** installed
- **uv** Python package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Supabase account** with a project ([supabase.com](https://supabase.com))
- **Groq API key** ([console.groq.com/keys](https://console.groq.com/keys))

### 1. Clone the Repository

```bash
git clone https://github.com/LayGupta/RFP-propoasal-automation.git
cd RFP-propoasal-automation
```

### 2. Create the Environment File

Create a `.env` file in the project root with the following variables:

```env
# LLM Provider — Groq Cloud (get key from https://console.groq.com/keys)
GROQ_API_KEY=gsk_your_groq_api_key_here

# Supabase — Backend service role (Dashboard → Settings → API)
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=eyJ...your_service_role_key

# PostgreSQL — Direct connection string (Dashboard → Settings → Database → URI)
# IMPORTANT: If your password contains @, encode it as %40
DATABASE_URL=postgresql://postgres:your_password@db.your-ref.supabase.co:5432/postgres

# Optional
GEMINI_API_KEY=your_gemini_key_for_embeddings
TAVILY_API_KEY=your_tavily_key_for_search
ENV=development
PORT=8000
```

### 3. Install Backend Dependencies

```bash
cd backend
uv sync
```

This installs all 90+ packages including FastAPI, LangGraph, psycopg, pdfplumber, etc.

### 4. Install Frontend Dependencies

```bash
cd ../frontend
npm install
```

### 5. Start Both Servers

**Terminal 1 — Backend (FastAPI on port 8000):**
```bash
cd backend
uv run uvicorn api.index:app --reload --port 8000
```

**Terminal 2 — Frontend (Vite on port 5173):**
```bash
cd frontend
npm run dev
```

### 6. Open the Dashboard

Navigate to **http://localhost:5173** in your browser.

The Vite dev server proxies all `/api/*` requests to the FastAPI backend automatically — no CORS issues.

---

## 🔑 Environment Variables

| Variable | Required | Format | Where to Find |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ | `gsk_xxxxxxxxx` | [console.groq.com/keys](https://console.groq.com/keys) |
| `SUPABASE_URL` | ✅ | `https://xxxx.supabase.co` | Supabase Dashboard → Settings → API → Project URL |
| `SUPABASE_SERVICE_KEY` | ✅ | `eyJhbG...` (JWT) | Supabase Dashboard → Settings → API → `service_role` secret |
| `DATABASE_URL` | ✅ | `postgresql://user:pass@host:5432/db` | Supabase Dashboard → Settings → Database → Connection string (URI) |
| `GEMINI_API_KEY` | ❌ | `AIzaSy...` | [Google AI Studio](https://aistudio.google.com) |
| `TAVILY_API_KEY` | ❌ | `tvly-...` | [tavily.com](https://tavily.com) |

> ⚠️ **Security**: The `.env` file is excluded from git via `.gitignore`. Never commit API keys.

---

## 📡 API Reference

### `GET /api/health`
Health check endpoint.

**Response:**
```json
{ "status": "healthy", "service": "fmcg-rfp-api" }
```

---

### `POST /api/process-rfp/start`
Upload an RFP document and start the multi-agent processing workflow.

**Content-Type:** `multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `file` | File | RFP document (PDF, DOCX, or TXT) |
| `thread_id` | String | Unique UUID session identifier |

**Response (when MTO items detected):**
```json
{
  "status": "PAUSED_FOR_HUMAN_REVIEW",
  "thread_id": "uuid-string",
  "blueprint_payload": ["## MTO Blueprint — LI-001 ..."],
  "matched_skus": [
    {
      "sku_id": "SKU-COPPER-XLPE-3C-CUSTOM",
      "product_name": "Custom 3-Core Copper XLPE Cable (1100V)",
      "spec_match_percentage": 65.0,
      "is_custom_mto": true,
      "gap_analysis_notes": "Exceeds 600V threshold..."
    }
  ]
}
```

**Response (all standard items — no interrupt):**
```json
{
  "status": "COMPLETED_NO_MTO",
  "thread_id": "uuid-string",
  "blueprint_payload": [],
  "matched_skus": [...]
}
```

---

### `POST /api/process-rfp/resume`
Resume a paused workflow after human review.

**Content-Type:** `application/json`

```json
{
  "thread_id": "uuid-from-start-response",
  "adjusted_volatility": 1.15,
  "notes": "Approved with 15% commodity surcharge."
}
```

**Response:**
```json
{
  "status": "COMPLETED",
  "thread_id": "uuid-string",
  "final_proposal_markdown": "# RFP Technical Proposal\n\n**Client:** ..."
}
```

---

## 🎨 Frontend Components

### App.jsx — Layout & State Manager
- Two-column grid: sidebar (300px) + main panel (fluid)
- Manages 5 lifecycle states: `IDLE` → `PROCESSING` → `PAUSED_FOR_HUMAN_REVIEW` → `COMPLETED` / `ERROR`
- Header with live status indicator (animated dot: idle/processing/paused/complete)
- Sidebar pipeline visualization showing which nodes have executed

### BidManager.jsx — Document Ingestion Portal
- Drag-and-drop file upload zone with hover animations
- File type validation (PDF, DOCX, TXT only)
- Automatic UUID session ID generation
- Full-screen processing overlay with progressive stage indicators:
  - Uploading document & extracting text...
  - Sales Discovery Agent analyzing requirements...
  - Technical Matching Engine scanning catalog...
  - Compliance Router evaluating MTO thresholds...

### MtoModal.jsx — Human-in-the-Loop Review Panel
- Glassmorphic modal with backdrop blur
- **SKU Matching Analysis** data grid — shows all items with match %, MTO flag, gap analysis
- **Engineering Blueprint Viewer** — tabbed display for multiple MTO blueprint documents
- **Adjustable Volatility Multiplier** — numeric input synced with sidebar slider
- **Compliance Notes** — free-text area for manager comments
- **Submit** button triggers async `/resume` call

### VolatilitySlider.jsx — Commodity Pricing Control
- Range slider: 0.50× to 2.50× with 0.01 step precision
- Large mono-font numeric display
- Dynamic zone indicator badges:
  - 🟢 Below Market (< 0.85×)
  - 🔵 Market Rate (0.85× – 1.15×)
  - 🟡 Elevated (1.15× – 1.75×)
  - 🔴 Critical Surge (> 1.75×)

### ProposalViewer.jsx — Analytical Document Terminal
- Converts markdown to structured HTML (headings, tables, blockquotes, lists)
- Toolbar with "Copy Markdown" clipboard action and "New Analysis" reset
- Thread ID display for traceability

---

## ☁️ Deployment

### Vercel (Serverless)

The project includes a `vercel.json` for monorepo deployment:

```json
{
  "version": 2,
  "builds": [
    { "src": "backend/api/index.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "backend/api/index.py" }
  ]
}
```

**Steps:**
1. Connect your GitHub repo to Vercel
2. Add all environment variables in Vercel Project Settings → Environment Variables
3. Deploy — Vercel auto-detects the Python backend and routes `/api/*` traffic

> **Note:** The frontend can be deployed as a separate Vercel project or added to the builds array as a static site.

---

## 🔄 How It Works — End-to-End Flow

Here's what happens when a user uploads an RFP document:

```
User uploads "Gujarat Power Station RFP.pdf"
         │
         ▼
┌─ STEP 1: File Upload ─────────────────────────────────────────────┐
│  • Frontend generates UUID thread_id: "a1b2c3d4-..."             │
│  • Wraps file + thread_id into FormData                          │
│  • POST /api/process-rfp/start                                   │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ STEP 2: Server-Side Text Extraction ─────────────────────────────┐
│  • FastAPI receives UploadFile                                    │
│  • pdfplumber extracts text from all PDF pages                    │
│  • Raw text injected into initial RFPState                        │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ STEP 3: Sales Discovery Agent (LLM) ────────────────────────────┐
│  • ChatGroq (Llama 3.3 70B) parses natural language               │
│  • Extracts: 3 line items with core count, voltage, material      │
│  • Output: extracted_requirements[] + metadata{}                  │
│  Example:                                                         │
│    LI-001: 3-Core 240mm² Copper XLPE, 1100V                      │
│    LI-002: 4-Core 16mm² Copper PVC, 415V                         │
│    LI-003: 1-Core 95mm² Aluminium XLPE, 650V                     │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ STEP 4: Technical Matching Engine ───────────────────────────────┐
│  • For each requirement, checks voltage against 600V threshold    │
│  • LI-001 (1100V) → 65% match, is_custom_mto=true               │
│  • LI-002 (415V)  → 92.5% match, is_custom_mto=false            │
│  • LI-003 (650V)  → 65% match, is_custom_mto=true               │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ STEP 5: Compliance Router ──────────────────────────────────────┐
│  • Detects 2 MTO items → routes to blueprint generation           │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ STEP 6: MTO Blueprint Generator (LLM) ─────────────────────────┐
│  • ChatGroq generates engineering modification profiles           │
│  • LI-001: Thicken XLPE insulation from 1.0mm to 1.5mm          │
│  • LI-003: Increase extrusion temp from 220°C to 230°C          │
│  • Includes QA testing, lead time, and process changes            │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ STEP 7: Human Review Gate — WORKFLOW PAUSES ────────────────────┐
│  • interrupt() persists full state to PostgreSQL                  │
│  • API returns PAUSED_FOR_HUMAN_REVIEW with blueprint payload     │
│  • Frontend opens MTO Modal for manager review                    │
│                                                                   │
│  ⏸️ Workflow is frozen. State survives server restarts.           │
│                                                                   │
│  Manager reviews blueprints, adjusts volatility to 1.15×,        │
│  adds notes: "Approved with 15% surcharge"                       │
│  Clicks "Submit Approved Proposal Specification"                  │
│                                                                   │
│  • Frontend POST /api/process-rfp/resume                          │
│  • Command(resume={notes, multiplier}) wakes the graph            │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ STEP 8: Pricing Engine ─────────────────────────────────────────┐
│  • Calculates base prices: core_factor + voltage_factor           │
│  • Applies material premium (copper=1.35×)                        │
│  • Applies MTO surcharge (1.25× for custom items)                 │
│  • Applies volatility multiplier (1.15× from human review)        │
│  • LI-001: $156.09 base → $179.50 adjusted                       │
│  • LI-002: $95.51 base → $109.84 adjusted                        │
│  • LI-003: $56.25 base → $64.69 adjusted                         │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ STEP 9: Output Compiler ────────────────────────────────────────┐
│  • Assembles complete markdown proposal document                  │
│  • Sections: Requirements Matrix, SKU Matching, MTO Blueprints,  │
│    Pricing Breakdown, Human Review Notes                          │
│  • Total: $307.85/m base → $354.03/m adjusted                    │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─ STEP 10: Final Proposal Rendered ───────────────────────────────┐
│  • Frontend receives final_proposal_markdown                      │
│  • ProposalViewer renders structured HTML with tables              │
│  • User can copy markdown or start a new analysis                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📄 License

This project is for educational and demonstration purposes.

---

<p align="center">
  Built with ⚡ by <a href="https://github.com/LayGupta">Lay Gupta</a>
</p>
