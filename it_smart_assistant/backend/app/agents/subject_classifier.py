"""Subject classifier using Gemini for accurate academic subject detection.

Phân loại môn học dựa trên nội dung câu hỏi sử dụng Gemini 1.5 Flash.
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.knowledge.bai_giang_schema import SubjectType, parse_subject

logger = logging.getLogger(__name__)

# Danh sách môn học có thể phân loại
SubjectName = Literal[
    "toan", "vat_ly", "hoa_hoc", "lap_trinh", "csdl", 
    "mang", "ai", "web", "khac"
]

# Mô tả chi tiết từng môn cho Gemini
SUBJECT_DESCRIPTIONS = {
    "toan": "Toán học: đại số, giải tích, hình học, ma trận, xác suất, thống kê, đạo hàm, tích phân",
    "vat_ly": "Vật lý: cơ học, nhiệt học, điện từ, quang học, sóng, vật lý lượng tử",
    "hoa_hoc": "Hóa học: vô cơ, hữu cơ, este, ankan, anken, phản ứng hóa học, mol",
    "lap_trinh": "Lập trình: thuật toán, cấu trúc dữ liệu, Python, Java, C++, code",
    "csdl": "Cơ sở dữ liệu: SQL, query, database, bảng, khóa chính, quan hệ, MySQL, PostgreSQL",
    "mang": "Mạng máy tính: TCP/IP, HTTP, routing, switch, firewall, giao thức mạng",
    "ai": "Trí tuệ nhân tạo: machine learning, deep learning, neural network, học máy",
    "web": "Phát triển Web: HTML, CSS, JavaScript, frontend, backend, API, React",
    "khac": "Khác: không thuộc các môn trên"
}

# Cache cho kết quả phân loại
_classification_cache: dict[str, SubjectType] = {}


async def classify_subject(user_question: str, conversation_history: list[dict] | None = None) -> SubjectType:
    """Phân loại môn học từ câu hỏi của người dùng.
    
    Args:
        user_question: Câu hỏi của sinh viên
        conversation_history: Lịch sử trò chuyện (nếu có) để lấy context
        
    Returns:
        SubjectType: Môn học được phân loại
    """
    # Check cache
    cache_key = user_question.lower().strip()
    if cache_key in _classification_cache:
        logger.debug(f"Subject cache hit for: {cache_key[:50]}...")
        return _classification_cache[cache_key]
    
    # Build prompt
    subject_list = "\n".join([f"- {k}: {v}" for k, v in SUBJECT_DESCRIPTIONS.items()])
    
    # Lấy context từ lịch sử nếu có
    context = ""
    if conversation_history and len(conversation_history) > 0:
        # Lấy 2 tin nhắn gần nhất
        recent = conversation_history[-2:]
        context = "\n".join([f"- {msg.get('content', '')[:100]}" for msg in recent])
        context = f"\nContext từ cuộc trò chuyện trước:\n{context}\n"
    
    prompt = f"""Bạn là một hệ thống phân loại môn học thông minh cho sinh viên đại học.

Nhiệm vụ: Xác định môn học liên quan đến câu hỏi sau.

Câu hỏi: "{user_question}"{context}

Các môn học có thể:
{subject_list}

Yêu cầu:
1. Phân tích nội dung câu hỏi và context (nếu có)
2. Xác định môn học chính xác nhất
3. Nếu câu hỏi có thể thuộc nhiều môn, chọn môn chính (ví dụ: "tính đạo hàm trong Python" → lap_trinh)
4. Trả về JSON với format: {{"subject": "ten_mon", "confidence": 0.95, "reason": "giải thích ngắn"}}

Chỉ trả về JSON, không giải thích gì thêm."""

    try:
        # Initialize Gemini
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,
            max_output_tokens=200,
        )
        
        # Get response
        response = await llm.ainvoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parse JSON
        # Clean response text
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        subject_key = result.get("subject", "khac")
        confidence = result.get("confidence", 0.5)
        reason = result.get("reason", "")
        
        # Convert to SubjectType
        subject = parse_subject(subject_key)
        
        # Cache result
        _classification_cache[cache_key] = subject
        
        logger.info(f"Subject classified: {subject.value} (confidence: {confidence:.2f}) - {reason}")
        
        return subject
        
    except Exception as e:
        logger.error(f"Failed to classify subject with Gemini: {e}")
        # Fallback: try keyword matching
        return _fallback_classify(user_question)


def _fallback_classify(user_question: str) -> SubjectType:
    """Fallback classification using keyword matching."""
    text = user_question.lower()
    
    keyword_mapping = {
        SubjectType.TOAN: ["đạo hàm", "tích phân", "ma trận", "phương trình", "giới hạn", "hàm số", "đồ thị", "số phức"],
        SubjectType.VAT_LY: ["cơ học", "điện trường", "mạch điện", "quang học", "nhiệt động", "sóng", "lực", "vận tốc"],
        SubjectType.HOA_HOC: ["phản ứng", "mol", "este", "anken", "ankhan", "điện phân", "acid", "base"],
        SubjectType.LAP_TRINH: ["python", "java", "c++", "code", "lập trình", "thuật toán", "hàm", "biến", "class"],
        SubjectType.CSDL: ["sql", "query", "database", "bảng", "khóa chính", "select", "insert", "update"],
        SubjectType.MANG: ["tcp/ip", "http", "routing", "switch", "firewall", "giao thức", "mạng"],
        SubjectType.AI: ["machine learning", "deep learning", "neural", "học máy", "mô hình", "training"],
        SubjectType.WEB: ["html", "css", "javascript", "frontend", "backend", "react", "api", "web"],
    }
    
    scores = {subject: 0 for subject in SubjectType}
    
    for subject, keywords in keyword_mapping.items():
        for keyword in keywords:
            if keyword in text:
                scores[subject] += 1
    
    # Find best match
    best_subject = max(scores, key=scores.get)
    
    if scores[best_subject] > 0:
        logger.info(f"Fallback classification: {best_subject.value}")
        return best_subject
    
    return SubjectType.KHAC


async def batch_classify(questions: list[str]) -> list[SubjectType]:
    """Phân loại nhiều câu hỏi cùng lúc."""
    results = []
    for q in questions:
        result = await classify_subject(q)
        results.append(result)
    return results
