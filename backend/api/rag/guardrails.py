"""
guardrails.py — System prompt and guardrail logic for the RAG chatbot.

Constrains the LLM to only answer questions about:
  - Cable products and specifications
  - RFP document content (client names, project details, requirements, etc.)
  - Pricing, compliance, and inventory
  - General cable engineering context

Rejects off-topic questions with a polite redirect.
"""

SYSTEM_PROMPT = """You are an expert AI assistant for an industrial cable manufacturing company called FMCG Industrial Solutions.

Your role is to answer questions about:
- Cable products, specifications, and inventory from our product catalog
- RFP (Request for Proposal) documents uploaded by the user — including client names, project details, scope of work, delivery schedules, and any content in the document
- Pricing, compliance standards (IEC 60502, IS 7098, IS 694), and technical specifications
- Cable engineering: conductor materials (copper, aluminium), insulation types (XLPE, PVC, EPR), voltage ratings, core counts, cross-sections
- Bid proposals and procurement processes

STRICT RULES:
1. ONLY answer questions related to the topics above. If a question is clearly off-topic (weather, sports, entertainment, coding, recipes, etc.), politely say: "I'm specialized in cable products and RFP analysis. I can help with questions about our product catalog, specifications, pricing, or any uploaded RFP documents. Could you rephrase your question in that context?"
2. If a question asks about something from the uploaded document (like client name, project name, scope, address, contact, dates, quantities, etc.), ALWAYS try to answer it from the context — these are valid RFP questions.
3. ALWAYS ground your answers in the provided context. If the context doesn't contain enough information, say "The uploaded document/catalog does not contain this information."
4. NEVER fabricate product data, SKU IDs, prices, or specifications. Only cite what's in the retrieved context.
5. When referencing products, include the SKU ID, product name, and key specs.
6. Be concise but thorough. Use bullet points for lists of products or specifications.
7. If asked about pricing, mention that prices are base rates per meter and subject to commodity volatility adjustments.

Answer the user's question based on the following context:

{context}
"""

GUARDRAIL_KEYWORDS = [
    # Cable/wire domain
    "cable", "wire", "conductor", "insulation", "xlpe", "pvc", "voltage",
    "core", "copper", "aluminium", "aluminum", "armour", "armor", "swa",
    "cross section", "mm2", "sq.mm", "rating", "ampere",
    # RFP/bid domain
    "rfp", "tender", "bid", "proposal", "procurement", "specification",
    "requirement", "scope", "schedule", "delivery", "quantity",
    # Pricing/inventory
    "price", "pricing", "cost", "quote", "sku", "product", "catalog",
    "inventory", "stock", "lead time", "supply",
    # Standards
    "compliance", "iec", "is 7098", "is 694",
    # Brands
    "polycab", "havells", "kei", "fmcg",
    # Manufacturing
    "mto", "make to order", "custom", "manufacturing",
    # Document content — valid questions about the uploaded RFP
    "client", "company", "project", "document", "uploaded", "pdf",
    "name", "address", "contact", "detail", "summary", "scope",
    "what does", "what is", "who is", "tell me about", "extract",
    "list", "show", "find", "how many", "how much",
]


def is_on_topic(question: str) -> bool:
    """Quick keyword-based pre-filter to catch obviously off-topic questions.
    
    Returns True if the question likely relates to cables/RFPs/products/documents.
    The LLM system prompt provides the final guardrail layer.
    
    This is intentionally permissive — it's better to let a borderline question
    through to the LLM (which can make a nuanced decision) than to block a valid
    question about the uploaded document.
    """
    q_lower = question.lower()
    return any(keyword in q_lower for keyword in GUARDRAIL_KEYWORDS)
