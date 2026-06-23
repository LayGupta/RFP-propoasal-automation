# Codebase Cleanup, Deployment Optimization & New README

Clean up the codebase, remove Docker artifacts, optimize for Render + Vercel deployment, remove broken PDF generation (keep text file export), keep email working, and write a comprehensive README.

## User Review Required

> [!IMPORTANT]
> **PDF Generation Removal:** Per your instruction, the WeasyPrint PDF generator is broken and will be removed. The email share feature currently generates a PDF and attaches it. I will **change it to attach the proposal as a `.txt` file instead**, since that's what works. This means the `weasyprint` and `jinja2` dependencies will be removed.

> [!IMPORTANT]
> **Render Deployment:** The backend will be configured for [Render](https://render.com) with a `render.yaml` blueprint file and a `start.sh` script. Render natively supports Python and will run the FastAPI app with `uvicorn`. No Docker needed.

> [!IMPORTANT]
> **Files to Delete — Please confirm:**
> - `docker-compose.yml` (root) — Docker orchestration
> - `backend/Dockerfile` — Docker build
> - `frontend/Dockerfile` — Docker build  
> - `frontend/nginx.conf` — nginx config (only used by Docker)
> - `vercel.json` (root) — stale/incorrect root-level Vercel config (the correct one is in `frontend/`)
> - `implementation_plan.md` (root) — old plan, not part of the app
> - `README (1).md` — duplicate README
> - `RFP_Proposal_0fcc8d47.txt` — leftover generated file
> - `backend/test_rfp_mto_trigger.txt` — test data file
> - `backend/app/templates/proposal.html` — unused (was for Jinja2 PDF rendering)
> - `backend/app/services/pdf_service.py` — the broken WeasyPrint PDF service
> - `backend/app/routers/pdf.py` — PDF download endpoints (broken)
> - `backend/tests/test_pdf.py` — tests for removed PDF service
> - `backend/app/api/` directory — empty `__init__.py` only, unused

## Proposed Changes

### 1. Delete Unnecessary Files

| File | Reason |
|------|--------|
| `docker-compose.yml` | Docker removed per request |
| `backend/Dockerfile` | Docker removed |
| `frontend/Dockerfile` | Docker removed |
| `frontend/nginx.conf` | Only used by Docker |
| `vercel.json` (root) | Stale; correct config in `frontend/vercel.json` |
| `implementation_plan.md` (root) | Old dev artifact |
| `README (1).md` | Duplicate README |
| `RFP_Proposal_0fcc8d47.txt` | Generated test output |
| `backend/test_rfp_mto_trigger.txt` | Test fixture (keep `test_rfp_sample.txt` in gitignore) |
| `backend/app/templates/proposal.html` | Unused template |
| `backend/app/services/pdf_service.py` | Broken PDF gen |
| `backend/app/routers/pdf.py` | Broken PDF endpoints |
| `backend/tests/test_pdf.py` | Tests for removed code |
| `backend/app/api/__init__.py` | Empty unused package |

---

### 2. Backend Changes

#### [MODIFY] [pyproject.toml](file:///d:/FMCG/backend/pyproject.toml)
- Remove `weasyprint` and `jinja2` dependencies

#### [MODIFY] [main.py](file:///d:/FMCG/backend/app/main.py)
- Remove PDF router import and registration
- Remove PDF tag from OpenAPI metadata
- Update description text to not mention WeasyPrint/PDF

#### [MODIFY] [email.py](file:///d:/FMCG/backend/app/routers/email.py)
- Remove PDF import and generation
- Change `/api/proposals/{id}/share` to attach the proposal as a `.txt` file instead of PDF
- Keep `/api/send-outreach` unchanged (it already works)

#### [MODIFY] [email_service.py](file:///d:/FMCG/backend/app/services/email_service.py)
- Rename `send_proposal_email` → generalize to support any attachment type (change `pdf_bytes` → `attachment_bytes`, `pdf_part` MIME type dynamic)

#### [MODIFY] [config.py](file:///d:/FMCG/backend/app/core/config.py)
- Add `FRONTEND_URL` documentation for Render/Vercel setup (already exists, good)

#### [NEW] [start.sh](file:///d:/FMCG/backend/start.sh)
- Render start script: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

#### [NEW] [render.yaml](file:///d:/FMCG/render.yaml)
- Render Blueprint IaC file defining the backend web service

---

### 3. Frontend Changes

#### [MODIFY] [ProposalViewer.tsx](file:///d:/FMCG/frontend/src/components/ProposalViewer.tsx)
- Remove the "Download PDF" button entirely
- Remove the `downloadProposalPdf` import and all PDF-related logic
- Update the email modal's info text to say "attached as a text file" instead of "PDF"

#### [MODIFY] [api.ts](file:///d:/FMCG/frontend/src/lib/api.ts)
- Remove the `downloadProposalPdf` function

#### [MODIFY] [rfp.ts](file:///d:/FMCG/frontend/src/types/rfp.ts)
- No changes needed (types don't reference PDF directly)

---

### 4. CI Cleanup

#### [MODIFY] [ci.yml](file:///d:/FMCG/.github/workflows/ci.yml)
- Remove WeasyPrint system dependency installation (libcairo, libpango, etc.)

---

### 5. Gitignore & Environment

#### [MODIFY] [.gitignore](file:///d:/FMCG/.gitignore)
- Add `backend/test_rfp_mto_trigger.txt`
- Add `*.txt` proposals at root level pattern

#### [MODIFY] [.env.example](file:///d:/FMCG/.env.example)
- Add `FRONTEND_URL` with documentation
- Remove leftover `NEXT_PUBLIC_*` vars (these are not used by the Vite frontend)
- Clean up comments

---

### 6. New README

#### [MODIFY] [README.md](file:///d:/FMCG/README.md)
Complete rewrite with:
- Project overview & architecture diagram (Mermaid)
- Tech stack table
- LangGraph workflow explanation
- Supabase schema
- Local development setup (step-by-step)
- Deployment guides for Render (backend) and Vercel (frontend)
- Environment variables reference
- API endpoint documentation
- Project structure tree

---

## Verification Plan

### Manual Verification
- Ensure no import errors by checking all cross-references after deletion
- Verify `pyproject.toml` installs cleanly without WeasyPrint
- Confirm the email share endpoint logic sends `.txt` attachment correctly
- Verify frontend builds without errors (`npm run build`)
