"""Tools dành riêng cho Management Insight Agent."""

import json
from typing import Any
from langchain_core.tools import tool
from app.db.session import get_db_context
from app.repositories import feedback as feedback_repo
from app.knowledge.service import get_student_knowledge_base

@tool
def summarize_meeting_minutes(query: str, time_range: str = "gần đây", top_k: int = 5) -> str:
    """
    Sử dụng công cụ này để tổng hợp dữ liệu phi cấu trúc từ các biên bản họp, 
    báo cáo giao ban, hoặc email nội bộ ban lãnh đạo.
    Input: query (chủ đề cần tìm, vd: "định hướng phát triển AI", "nghiên cứu khoa học").
    """
    # Tái sử dụng base search, nhưng lọc theo category 'bien_ban_hop'
    kb = get_student_knowledge_base() 
    raw_results = kb.search(query, top_k=top_k * 3)
    
    filtered_results = [
        res for res in raw_results 
        if "bien_ban_hop" in res.get("category", "").lower() or "báo cáo" in res.get("category", "").lower()
    ]
    
    payload = {
        "query": query,
        "time_context": time_range,
        "findings": filtered_results[:top_k],
        "note": "Dựa trên các biên bản họp và báo cáo nội bộ của Khoa/Trường."
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

@tool
def compare_legal_regulations(topic: str) -> str:
    """
    Sử dụng công cụ này để tra cứu, so sánh các quy định pháp luật, 
    thông tư của Bộ GD&ĐT hoặc quy chế nội bộ của Trường.
    Input: topic (chủ đề cần tra cứu, vd: "quy chế đào tạo tín chỉ", "đánh giá học phần").
    """
    kb = get_student_knowledge_base() 
    raw_results = kb.search(topic, top_k=6)
    
    # Lọc các văn bản thuộc danh mục pháp quy, quy chế
    filtered_results = [
        res for res in raw_results 
        if "phap_quy" in res.get("category", "").lower() or "quy_che" in res.get("category", "").lower()
    ]
    
    if not filtered_results:
        # Fallback nếu không có category rõ ràng
        filtered_results = raw_results[:3]

    payload = {
        "topic": topic,
        "regulations": filtered_results,
        "instruction": "Hãy phân tích và so sánh các điểm giống/khác nhau dựa trên dữ liệu này."
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

@tool
async def get_student_and_lecturer_insights(limit: int = 5) -> str:
    """
    Sử dụng công cụ này khi Lãnh đạo muốn biết Tình hình sinh viên/giảng viên hiện tại.
    Công cụ này lấy dữ liệu thống kê THỰC TẾ từ database: các câu hỏi sinh viên hay hỏi nhất, 
    những thủ tục hành chính nào đang bị tắc nghẽn (phản hồi xấu).
    """
    async with get_db_context() as db:
        top_questions = await feedback_repo.get_top_questions(db, limit=limit)
        weak_intents = await feedback_repo.get_intent_feedback_quality(db, limit=limit)
        
    payload = {
        "top_frequent_questions": [{"question": q, "count": c} for q, c in top_questions],
        "pain_points_and_weak_intents": [
            {
                "intent": i[0], 
                "total_queries": i[1], 
                "negative_feedback": i[3],
                "satisfaction_rate": f"{i[4]}%"
            } for i in weak_intents
        ],
        "insight": "Đây là dữ liệu realtime từ hệ thống chatbot của sinh viên và giảng viên."
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)