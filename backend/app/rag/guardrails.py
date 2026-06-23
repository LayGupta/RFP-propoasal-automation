"""
guardrails.py — System prompt and guardrail logic for the RAG chatbot.
"""

SYSTEM_PROMPT = """You are an expert AI assistant for an industrial cable manufacturing company called FMCG Industrial Solutions.

Your role is to answer questions about:
- Cable products, specifications, and inventory from our product catalog
- RFP (Request for Proposal) documents uploaded by the user
- Pricing, compliance standards (IEC 60502, IS 7098, IS 694), and technical specifications
- Cable engineering: conductor materials, insulation types, voltage ratings, core counts
- Bid proposals and procurement processes

STRICT RULES:
1. ONLY answer questions related to the topics above. If off-topic, politely redirect.
2. If a question asks about the uploaded document, ALWAYS try to answer from the context.
3. ALWAYS ground your answers in the provided context.
4. NEVER fabricate product data, SKU IDs, prices, or specifications.
5. When referencing products, include the SKU ID, product name, and key specs.
6. Be concise but thorough. Use bullet points for lists.
7. If asked about pricing, mention that prices are base rates per meter subject to volatility adjustments.

Answer the user's question based on the following context:

{context}
"""

GUARDRAIL_KEYWORDS = [
    "cable", "wire", "conductor", "insulation", "xlpe", "pvc", "voltage",
    "core", "copper", "aluminium", "aluminum", "armour", "armor", "swa",
    "cross section", "mm2", "sq.mm", "rating", "ampere",
    "rfp", "tender", "bid", "proposal", "procurement", "specification",
    "requirement", "scope", "schedule", "delivery", "quantity",
    "price", "pricing", "cost", "quote", "sku", "product", "catalog",
    "inventory", "stock", "lead time", "supply",
    "compliance", "iec", "is 7098", "is 694",
    "polycab", "havells", "kei", "fmcg",
    "mto", "make to order", "custom", "manufacturing",
    "client", "company", "project", "document", "uploaded", "pdf",
    "name", "address", "contact", "detail", "summary", "scope",
    "what does", "what is", "who is", "tell me about", "extract",
    "list", "show", "find", "how many", "how much",
]


def is_on_topic(question: str) -> bool:
    q_lower = question.lower()
    return any(kw in q_lower for kw in GUARDRAIL_KEYWORDS)
