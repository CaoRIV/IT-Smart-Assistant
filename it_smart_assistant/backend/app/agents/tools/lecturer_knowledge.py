"""General knowledge retrieval tool for the lecturer assistant."""

import json

from langchain_core.tools import tool

from app.knowledge import get_lecturer_knowledge_base


@tool
def search_lecturer_knowledge_base(query: str, top_k: int = 5) -> str:
    """Search the lecturer-specific knowledge base for information on university policies,
    departmental guidelines, and other administrative or academic topics. This tool is
    the primary resource for answering lecturer questions.
    """
    knowledge_base = get_lecturer_knowledge_base()
    results = knowledge_base.search(query, top_k=top_k)
    payload = {
        "query": query,
        "result_count": len(results),
        "results": results,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
