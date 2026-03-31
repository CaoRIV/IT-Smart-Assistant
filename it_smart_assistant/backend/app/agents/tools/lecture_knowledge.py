"""Lecture knowledge retrieval tools."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from app.knowledge import get_student_knowledge_base


@tool
def search_lecture_knowledge(query: str, subject: str | None = None, top_k: int = 4) -> str:
    """Search the internal lecture notes and course materials knowledge base.

    Use this tool for questions about specific course content, exercises, 
    examples from lectures, or when the user asks to solve a problem 
    based on the lecture's style.

    Args:
        query: The search query (e.g., the exercise description or topic).
        subject: Optional name of the subject/course to filter results.
        top_k: Number of relevant results to return.
    """
    knowledge_base = get_student_knowledge_base()
    
    # Enhance query with subject if provided
    search_query = query
    if subject:
        search_query = f"{subject} {query}"
        
    results = knowledge_base.search(search_query, top_k=max(1, min(top_k, 6)))

    payload = {
        "query": query,
        "subject": subject,
        "result_count": len(results),
        "results": results,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
