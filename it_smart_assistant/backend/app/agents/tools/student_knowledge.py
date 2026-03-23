"""Student knowledge retrieval tools."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from app.knowledge import get_student_knowledge_base


@tool
def search_student_knowledge(query: str, top_k: int = 3) -> str:
    """Search the internal student advisory knowledge base.

    Use this tool for questions about academic policy, procedures, student services,
    tuition, scholarships, internship paperwork, or administrative requests.
    """
    knowledge_base = get_student_knowledge_base()
    results = knowledge_base.search(query, top_k=max(1, min(top_k, 5)))

    payload = {
        "query": query,
        "result_count": len(results),
        "results": results,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
