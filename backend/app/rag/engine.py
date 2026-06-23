"""
engine.py — RAG Engine for Document QA Chatbot

Google Gemini embeddings, FAISS vector store, ChatGroq for answer generation.
"""

from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.database import supabase_client
from app.rag.guardrails import SYSTEM_PROMPT, is_on_topic

_embeddings = None
_llm = None
_text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
_index_cache: dict[str, FAISS] = {}
_catalog_index: FAISS | None = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
    return _embeddings


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
    return _llm


def _get_catalog_index() -> FAISS:
    global _catalog_index
    if _catalog_index is not None:
        return _catalog_index

    embeddings = _get_embeddings()
    result = supabase_client.table("products").select("*").execute()
    products = result.data or []

    if not products:
        doc = Document(page_content="No products in catalog.", metadata={"source": "catalog"})
        _catalog_index = FAISS.from_documents([doc], embeddings)
        return _catalog_index

    docs = []
    for p in products:
        text = (
            f"SKU: {p['sku_id']} | Product: {p['product_name']} | "
            f"Material: {p['conductor_material']} | Insulation: {p['insulation_type']} | "
            f"Voltage: {p['voltage_rating']}V | Cores: {p['core_count']} | "
            f"Cross-section: {p['cross_section_mm2']}mm2 | Armour: {p['armour_type']} | "
            f"Standard: {p['standard']} | Price: INR {p['base_price_per_meter']}/m | "
            f"Stock: {p['stock_quantity']} units | Lead time: {p['lead_time_days']} days | "
            f"Category: {p['category']}"
        )
        docs.append(Document(page_content=text, metadata={"source": "catalog", "sku": p["sku_id"]}))

    _catalog_index = FAISS.from_documents(docs, embeddings)
    return _catalog_index


def build_index_from_text(thread_id: str, text: str) -> None:
    embeddings = _get_embeddings()
    chunks = _text_splitter.split_text(text)
    docs = [Document(page_content=c, metadata={"source": "rfp", "thread_id": thread_id}) for c in chunks]

    if docs:
        rfp_index = FAISS.from_documents(docs, embeddings)
        catalog_index = _get_catalog_index()
        rfp_index.merge_from(catalog_index)
        _index_cache[thread_id] = rfp_index
    else:
        _index_cache[thread_id] = _get_catalog_index()


def ask(question: str, thread_id: str | None = None) -> dict:
    on_topic = is_on_topic(question)

    if thread_id and thread_id in _index_cache:
        index = _index_cache[thread_id]
    else:
        index = _get_catalog_index()

    retriever = index.as_retriever(search_kwargs={"k": 5})
    retrieved_docs = retriever.invoke(question)
    context_str = "\n\n---\n\n".join(doc.page_content for doc in retrieved_docs)
    full_prompt = SYSTEM_PROMPT.format(context=context_str) + f"\n\nQuestion: {question}"

    llm = _get_llm()
    response = llm.invoke(full_prompt)
    answer = response.content.strip()

    sources = [{"content": doc.page_content[:200], "source": doc.metadata.get("source", "unknown")} for doc in retrieved_docs]
    return {"answer": answer, "sources": sources, "on_topic": on_topic}


def clear_index(thread_id: str) -> None:
    _index_cache.pop(thread_id, None)
