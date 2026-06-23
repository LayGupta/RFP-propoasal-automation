"""
main.py — FastAPI Application Factory

Creates and configures the FastAPI app instance with:
  - CORS middleware
  - All routers
  - Lifespan events (scheduler start/stop)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.scheduler import start_scheduler, stop_scheduler
from app.routers import auth, rfp, history, scout, chat, email
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


TAGS_METADATA = [
    {
        "name": "auth",
        "description": "Authentication endpoints. Register, login, and JWT validation.",
    },
    {
        "name": "rfp",
        "description": "Core LangGraph RFP processing. Start new analyses and resume human-in-the-loop workflows.",
    },
    {
        "name": "history",
        "description": "Fetch user proposal history and analytics dashboard metrics.",
    },
    {
        "name": "scout",
        "description": "Tender scouting and discovery tools for government/public sector RFPs.",
    },
    {
        "name": "chat",
        "description": "Conversational RAG interface for querying past proposals and engineering context.",
    },
    {
        "name": "email",
        "description": "Automated outreach and proposal sharing via SMTP dispatch.",
    },
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="FMCG RFP Processing API",
        description=(
            "Enterprise-grade Multi-agent LangGraph workflow for RFP analysis, "
            "SKU matching, and automated proposal generation.\n\n"
            "**Core Features:**\n"
            "* **Stateful Agent Workflows:** Postgres-backed checkpointing for Human-in-the-loop.\n"
            "* **Intelligent Parsing:** PDF & Docx extraction and RAG chunking.\n"
            "* **Proposal Export:** Markdown and text-file proposal output with email dispatch.\n"
            "* **Outreach & Scouting:** Automated tender discovery and email alerts."
        ),
        version="3.0.0",
        openapi_tags=TAGS_METADATA,
        contact={
            "name": "FMCG Industrial Solutions Integration Team",
            "email": "laygupta142@gmail.com",
        },
        license_info={
            "name": "Proprietary / Confidential",
        },
        lifespan=lifespan,
    )

    s = get_settings()

    # Split-stack CORS strategy
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ]
    if getattr(s, "FRONTEND_URL", None):
        # Allow the production frontend domain
        origins.append(s.FRONTEND_URL.rstrip("/"))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(rfp.router)
    app.include_router(history.router)
    app.include_router(scout.router)
    app.include_router(chat.router)
    app.include_router(email.router)


    @app.get("/api/health", tags=["system"])
    def health_check() -> dict[str, str]:
        """Deep health check endpoint for container orchestrators."""
        return {"status": "healthy", "service": "fmcg-rfp-api", "version": "3.0.0"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
