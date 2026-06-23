"""chat router — /api/chat endpoints"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.schemas.chat import ChatRequest
from app.rag import engine as rag_engine
from app.services.file_parser import extract_text_from_upload

router = APIRouter(tags=["chat"])


@router.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    try:
        result = rag_engine.ask(request.question, request.thread_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/api/chat/init")
async def chat_init(file: UploadFile = File(...), thread_id: str = Form(...)) -> dict:
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")
    try:
        raw_text = extract_text_from_upload(file_bytes, file.filename or "doc.txt")
        rag_engine.build_index_from_text(thread_id, raw_text)
        return {"status": "indexed", "thread_id": thread_id, "chunks": len(raw_text) // 500}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")
