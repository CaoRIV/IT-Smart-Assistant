"""Exercise solving tool with lecture style adaptation.

Bước 4: Tool solve_with_style(exercise, lecture_context)
LLM đọc phong cách bài giảng → giải bài theo đúng cách trình bày của thầy/cô.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from app.core.config import settings
from app.knowledge.bai_giang_schema import SubjectType, parse_subject

logger = logging.getLogger(__name__)


# System prompts for different teaching styles
STYLE_PROMPTS = {
    "default": """Bạn là một trợ lý học tập thông minh, giải bài tập theo phong cách bài giảng của giảng viên.
Hãy phân tích bài toán và trình bày lời giải rõ ràng, mạch lạc theo các bước:
1. Phân tích đề bài
2. Xác định phương pháp giải
3. Trình bày lời giải chi tiết
4. Kiểm tra kết quả (nếu cần)
""",
    "định nghĩa": """Trình bày lời giải bắt đầu bằng việc nêu các định nghĩa, định lý liên quan đến bài toán.
Sau đó áp dụng các định nghĩa đã nêu để giải bài một cách chặt chẽ về mặt logic.
""",
    "ví dụ": """Trình bày lời giải theo phong cách "ví dụ mẫu":
- Nêu một ví dụ tương tự đã được giảng dạy (nếu có)
- Áp dụng cách làm tương tự vào bài toán hiện tại
- Giải thích từng bước một cách cụ thể
""",
    "bài tập": """Trình bày lời giải theo phong cách luyện tập:
- Xác định dạng bài tập
- Nêu các bước giải chuẩn cho dạng này
- Thực hiện từng bước với giải thích ngắn gọn
- Kết luận và ghi chú các điểm cần nhớ
""",
    "lý thuyết": """Trình bày lời giải theo phong cách lý thuyết:
- Nêu cơ sở lý thuyết (định lý, công thức)
- Chứng minh hoặc giải thích ngắn gọn
- Áp dụng vào bài toán cụ thể
- Tổng kết kết quả
""",
    "chứng minh": """Trình bày lời giải theo phong cách chứng minh:
- Phát biểu giả thiết và kết luận cần chứng minh
- Trình bày các bước suy luận logic
- Dẫn dắt đến kết luận cuối cùng
- Kiểm tra tính đúng đắn của chứng minh
""",
}


def _build_subject_prompt(subject: SubjectType) -> str:
    """Build subject-specific solving guidance."""
    prompts = {
        SubjectType.TOAN: "Sử dụng ký hiệu toán học chuẩn. Trình bày các bước giải rõ ràng.",
        SubjectType.VAT_LY: "Nêu các định luật vật lý áp dụng. Chú ý đơn vị và chữ số có nghĩa.",
        SubjectType.HOA_HOC: "Viết phương trình hóa học cân bằng. Giải thích cơ chế phản ứng.",
        SubjectType.LAP_TRINH: "Viết code rõ ràng, có comment. Giải thích thuật toán.",
        SubjectType.CSDL: "Sử dụng SQL chuẩn. Giải thích schema và các ràng buộc.",
        SubjectType.MANG: "Nêu các giao thức áp dụng. Giải thích quá trình truyền dữ liệu.",
        SubjectType.AI: "Giải thích thuật toán và công thức toán học. Nêu ưu/nhược điểm.",
        SubjectType.WEB: "Nêu công nghệ và framework phù hợp. Giải thích kiến trúc.",
        SubjectType.KHAC: "Trình bày lời giải rõ ràng, logic.",
    }
    return prompts.get(subject, prompts[SubjectType.KHAC])


def _analyze_style_hint(style_hint: str) -> str:
    """Analyze style hint and return appropriate prompt addition."""
    style_lower = style_hint.lower()

    if "định nghĩa" in style_lower or "dinh nghia" in style_lower:
        return STYLE_PROMPTS["định nghĩa"]
    elif "ví dụ" in style_lower or "vi du" in style_lower:
        return STYLE_PROMPTS["ví dụ"]
    elif "bài tập" in style_lower or "bai tap" in style_lower:
        return STYLE_PROMPTS["bài tập"]
    elif "chứng minh" in style_lower or "chung minh" in style_lower:
        return STYLE_PROMPTS["chứng minh"]
    elif "lý thuyết" in style_lower or "ly thuyet" in style_lower:
        return STYLE_PROMPTS["lý thuyết"]

    return ""


def _format_lecture_context(lecture_results: list[dict[str, Any]]) -> str:
    """Format lecture context for the prompt."""
    if not lecture_results:
        return ""

    context_parts = []
    has_high_confidence = False
    min_score_threshold = 0.6  # Ngưỡng độ tin cậy tối thiểu
    
    for i, result in enumerate(lecture_results[:3], 1):  # Limit to top 3
        subject = result.get("subject", "")
        chapter = result.get("chapter", "")
        style = result.get("style_hint", "")
        content = result.get("content", "")[:800]  # Truncate for prompt
        score = result.get("score", 0.0)
        
        # Kiểm tra nếu có ít nhất 1 kết quả có độ tin cậy cao
        if score >= min_score_threshold:
            has_high_confidence = True
        
        context_parts.append(
            f"--- Tài liệu tham khảo {i} ---\n"
            f"Môn: {subject}\n"
            f"Chương: {chapter}\n"
            f"Phong cách: {style}\n"
            f"Độ tương đồng: {score:.2f}\n"
            f"Nội dung:\n{content}\n"
        )

    return "\n".join(context_parts), has_high_confidence


def _get_llm_for_solving():
    """Get LLM client for exercise solving."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.AI_MODEL,
            temperature=0.3,  # Lower temperature for consistent solving
            api_key=settings.OPENAI_API_KEY,
        )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.AI_MODEL,
            temperature=0.3,
            google_api_key=settings.GOOGLE_API_KEY,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


async def _solve_with_llm(
    exercise: str,
    subject: SubjectType,
    lecture_context: str,
    style_hint: str,
    use_fallback: bool = False,
) -> dict[str, Any]:
    """Use LLM to solve exercise with lecture context or fallback to general knowledge."""
    try:
        llm = _get_llm_for_solving()

        # Build style-specific prompt
        style_prompt = _analyze_style_hint(style_hint)
        subject_guidance = _build_subject_prompt(subject)

        if use_fallback or not lecture_context:
            # Fallback: Use general knowledge
            system_prompt = f"""Bạn là một trợ lý học tập thông minh, giải bài tập dựa trên kiến thức học thuật chung.

{style_prompt}

Hướng dẫn cho môn {subject.value}:
{subject_guidance}

Lưu ý: Phần kiến thức này không có trong bài giảng hiện tại. Hãy giải bài tập dựa trên kiến thức chung của môn {subject.value}.
"""
            user_prompt = f"""Bài tập cần giải:
{exercise}

Hãy giải bài tập trên theo phong cách giảng dạy chuẩn của môn {subject.value}.
"""
        else:
            # Use lecture context
            system_prompt = f"""{STYLE_PROMPTS["default"]}

{style_prompt}

Hướng dẫn cho môn {subject.value}:
{subject_guidance}
"""
            user_prompt = f"""Bài tập cần giải:
{exercise}

Tài liệu tham khảo từ bài giảng:
{lecture_context}

Hãy giải bài tập trên theo phong cách và phương pháp được trình bày trong tài liệu tham khảo.
"""

        # Call LLM
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await llm.ainvoke(messages)
        solution = response.content if hasattr(response, "content") else str(response)

        return {
            "success": True,
            "solution": solution,
            "subject": subject.value,
            "style_applied": style_hint or "default",
        }

    except Exception as e:
        logger.error(f"LLM solving failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "solution": "Không thể tạo lời giải do lỗi kết nối LLM.",
        }


@tool
def solve_with_style(
    exercise: str,
    lecture_context: str | None = None,
    subject: str | None = None,
    style_hint: str | None = None,
) -> str:
    """Solve an exercise following the style and method from lecture materials.

    This tool uses LLM to analyze the lecture context and solve the exercise
    in the same teaching style demonstrated in the course materials.

    Args:
        exercise: The exercise/problem to solve (can include math formulas, code, etc.)
        lecture_context: Optional JSON string with lecture content (from search_lecture)
        subject: Optional subject name (e.g., "Toán", "Lập trình")
        style_hint: Optional preferred style (e.g., "định nghĩa", "ví dụ", "bài tập")

    Returns:
        JSON string containing the step-by-step solution.
    """
    import asyncio

    # Parse subject
    subject_enum = parse_subject(subject) if subject else SubjectType.KHAC

    # Parse lecture context if provided
    lecture_results = []
    if lecture_context:
        try:
            context_data = json.loads(lecture_context)
            if isinstance(context_data, dict) and "results" in context_data:
                lecture_results = context_data["results"]
        except json.JSONDecodeError:
            logger.warning("Invalid lecture context JSON")

    # Format context for prompt
    formatted_context, has_high_confidence = _format_lecture_context(lecture_results)
    
    # Determine if we should use fallback (general knowledge)
    use_fallback = not has_high_confidence or not formatted_context
    
    # Get style from lecture results if not provided
    if not style_hint and lecture_results:
        styles = [r.get("style_hint", "") for r in lecture_results]
        if styles:
            style_hint = " → ".join(s for s in styles if s)[:100]

    # Run LLM solving
    try:
        result = asyncio.get_event_loop().run_until_complete(
            _solve_with_llm(exercise, subject_enum, formatted_context, style_hint or "", use_fallback)
        )
    except RuntimeError:
        # No running event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _solve_with_llm(exercise, subject_enum, formatted_context, style_hint or "", use_fallback)
        )

    # Build final response
    response_payload = {
        "exercise": exercise[:500],  # Truncate for response
        "subject": subject_enum.value,
        "style_hint": style_hint,
        "solution": result.get("solution", ""),
        "lecture_references": len(lecture_results),
        "has_high_confidence": has_high_confidence,
        "used_fallback": use_fallback,
        "success": result.get("success", False),
    }
    
    # Add warning if using fallback
    if use_fallback:
        response_payload["warning"] = "Phần kiến thức này không có trong bài giảng hiện tại, mình sẽ hỗ trợ bạn dựa trên kiến thức học thuật chung."
    else:
        # Add source citation
        chapters = [r.get("chapter", "") for r in lecture_results[:2] if r.get("chapter")]
        if chapters:
            response_payload["source_citation"] = f"Dựa trên bài giảng: {', '.join(chapters)}"

    return json.dumps(response_payload, ensure_ascii=False, indent=2)


@tool
def solve_exercise_direct(
    exercise: str,
    subject: str,
) -> str:
    """Direct exercise solving without lecture context.

    Use this for simpler exercises where lecture context is not needed,
    or when you want a quick solution.

    Args:
        exercise: The exercise/problem description
        subject: The subject area (e.g., "Toán", "Vật lý", "Lập trình")

    Returns:
        JSON string with the solution.
    """
    return solve_with_style.invoke(
        {
            "exercise": exercise,
            "lecture_context": None,
            "subject": subject,
            "style_hint": None,
        }
    )


@tool
def explain_concept(
    concept: str,
    subject: str,
    level: str = "sinh viên",
) -> str:
    """Explain a concept in the teaching style of the course.

    Args:
        concept: The concept to explain
        subject: The subject area
        level: Target audience level (default: "sinh viên")

    Returns:
        JSON string with the explanation.
    """
    subject_enum = parse_subject(subject)
    subject_guidance = _build_subject_prompt(subject_enum)

    prompt = f"""Giải thích khái niệm "{concept}" trong môn {subject_enum.value}.

Hướng dẫn trình bày:
{subject_guidance}

Đối tượng: {level}

Yêu cầu:
1. Định nghĩa chính xác
2. Giải thích bằng ngôn ngữ dễ hiểu
3. Cho ví dụ minh họa (nếu phù hợp)
4. Nêu ứng dụng thực tế
"""

    try:
        llm = _get_llm_for_solving()
        from langchain_core.messages import HumanMessage

        response = llm.invoke([HumanMessage(content=prompt)])
        explanation = response.content if hasattr(response, "content") else str(response)

        return json.dumps(
            {
                "concept": concept,
                "subject": subject_enum.value,
                "level": level,
                "explanation": explanation,
                "success": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {
                "concept": concept,
                "subject": subject_enum.value,
                "error": str(e),
                "success": False,
            },
            ensure_ascii=False,
        )
