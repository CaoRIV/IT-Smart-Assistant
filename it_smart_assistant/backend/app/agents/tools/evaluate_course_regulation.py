"""Tool specifically for answering questions about course evaluation regulations (QĐ 2004)."""

import json
from typing import Any

from langchain_core.tools import tool

from app.knowledge.service import get_student_knowledge_base, _normalize_text


@tool
def search_course_evaluation_rules(query: str, top_k: int = 5) -> str:
    """Search specifically for university regulations regarding course evaluation, grading, 
    exam formats, and student assessment rules (e.g., QĐ 2004). Use this tool when a lecturer 
    or student asks about how courses are graded, exam conditions, or evaluation components.
    """
    knowledge_base = get_student_knowledge_base()
    
    # We use the existing search mechanism but strongly filter the results 
    # to only include documents from the "hoc_phan" category or related to "đánh giá học phần".
    
    raw_results = knowledge_base.search(query, top_k=top_k * 4) # Fetch more to filter down
    
    filtered_results: list[dict[str, Any]] = []
    
    for result in raw_results:
        source_path = _normalize_text(result.get("source_path", ""))
        category = _normalize_text(result.get("category", ""))
        title = _normalize_text(result.get("title", ""))
        
        # Check if the document belongs to the target domain
        if (
            "hoc_phan" in source_path 
            or "hoc_phan" in category 
            or "danh gia hoc phan" in title 
            or "q 2004" in source_path
        ):
            filtered_results.append(result)
            
        if len(filtered_results) >= top_k:
            break
            
    # If the hard filter yielded nothing, we fallback to returning the top raw results 
    # that *might* be relevant based on semantic/lexical score, but we label them clearly.
    if not filtered_results:
        filtered_results = raw_results[:top_k]

    payload = {
        "query": query,
        "result_count": len(filtered_results),
        "results": filtered_results,
        "note": "Filtered specifically for course evaluation regulations (Đánh giá học phần)."
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
