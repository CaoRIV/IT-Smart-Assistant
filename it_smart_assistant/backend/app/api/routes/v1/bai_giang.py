"""API routes for bài giảng (lecture) operations.

Bước 6: Thêm API route mới
- POST /api/v1/bai-giang/solve
- GET /api/v1/bai-giang/subjects (danh sách môn)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.tools.search_lecture_tool import (
    list_available_subjects,
    search_lecture,
)
from app.agents.tools.solve_exercise_tool import solve_with_style
from app.knowledge.bai_giang_schema import get_subject_names, parse_subject

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bai-giang", tags=["bai-giang"])


# ============== Schemas ==============

class SolveExerciseRequest(BaseModel):
    """Request to solve an exercise with lecture style."""

    exercise: str = Field(..., description="Bài tập cần giải", min_length=10)
    subject: str | None = Field(None, description="Môn học (ví dụ: Toán, Lập trình)")
    chapter: str | None = Field(None, description="Tên chương/bài (tùy chọn)")
    use_lecture_context: bool = Field(True, description="Có sử dụng tài liệu bài giảng không")


class SolveExerciseResponse(BaseModel):
    """Response with exercise solution."""

    success: bool
    exercise: str
    subject: str | None
    solution: str
    lecture_references: int
    style_applied: str | None = None
    error: str | None = None


class SubjectInfo(BaseModel):
    """Subject information."""

    name: str
    chunk_count: int


class ListSubjectsResponse(BaseModel):
    """Response with list of available subjects."""

    subjects: list[SubjectInfo]
    total_chunks: int


class SearchLectureRequest(BaseModel):
    """Request to search lecture content."""

    query: str = Field(..., description="Từ khóa tìm kiếm", min_length=3)
    subject: str | None = Field(None, description="Lọc theo môn học")
    chapter: str | None = Field(None, description="Lọc theo chương")
    top_k: int = Field(4, ge=1, le=10, description="Số kết quả tối đa")


class SearchLectureResponse(BaseModel):
    """Response with lecture search results."""

    query: str
    subject: str | None
    chapter: str | None
    result_count: int
    results: list[dict[str, Any]]


# ============== Routes ==============

@router.get(
    "/subjects",
    response_model=ListSubjectsResponse,
    summary="Danh sách môn học có tài liệu",
    description="Lấy danh sách các môn học đã có tài liệu bài giảng được ingest.",
)
async def get_subjects() -> ListSubjectsResponse:
    """Get list of available subjects with lecture materials."""
    try:
        subjects_json = list_available_subjects()
        import json

        data = json.loads(subjects_json)

        subjects = [
            SubjectInfo(name=s["name"], chunk_count=s.get("chunk_count", 0))
            for s in data.get("subjects", [])
        ]

        return ListSubjectsResponse(
            subjects=subjects,
            total_chunks=data.get("total_chunks", 0),
        )
    except Exception as e:
        logger.error(f"Failed to get subjects: {e}")
        # Return default subjects from schema
        return ListSubjectsResponse(
            subjects=[
                SubjectInfo(name=name, chunk_count=0) for name in get_subject_names()
            ],
            total_chunks=0,
        )


@router.post(
    "/search",
    response_model=SearchLectureResponse,
    summary="Tìm kiếm tài liệu bài giảng",
    description="Tìm kiếm nội dung trong tài liệu bài giảng theo từ khóa.",
)
async def search_lecture_content(request: SearchLectureRequest) -> SearchLectureResponse:
    """Search lecture knowledge base."""
    try:
        result = search_lecture.invoke(
            {
                "query": request.query,
                "subject": request.subject,
                "chapter": request.chapter,
                "top_k": request.top_k,
            }
        )

        import json

        data = json.loads(result)

        return SearchLectureResponse(
            query=data.get("query", request.query),
            subject=data.get("subject"),
            chapter=data.get("chapter"),
            result_count=data.get("result_count", 0),
            results=data.get("results", []),
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tìm kiếm thất bại: {str(e)}",
        ) from e


@router.post(
    "/solve",
    response_model=SolveExerciseResponse,
    summary="Giải bài tập theo phong cách bài giảng",
    description="Giải bài tập sử dụng phong cách và phương pháp từ tài liệu bài giảng.",
)
async def solve_exercise(request: SolveExerciseRequest) -> SolveExerciseResponse:
    """Solve an exercise following lecture teaching style."""
    try:
        lecture_context = None

        # First, search for relevant lecture content if enabled
        if request.use_lecture_context:
            logger.info(
                f"Searching lecture context for subject={request.subject}, query={request.exercise[:50]}..."
            )
            search_result = search_lecture.invoke(
                {
                    "query": request.exercise,
                    "subject": request.subject,
                    "chapter": request.chapter,
                    "top_k": 4,
                }
            )
            lecture_context = search_result

        # Then solve with style
        logger.info(f"Solving exercise for subject={request.subject}")
        solve_result = solve_with_style.invoke(
            {
                "exercise": request.exercise,
                "lecture_context": lecture_context,
                "subject": request.subject,
            }
        )

        import json

        data = json.loads(solve_result)

        return SolveExerciseResponse(
            success=data.get("success", False),
            exercise=data.get("exercise", request.exercise)[:500],
            subject=data.get("subject"),
            solution=data.get("solution", ""),
            lecture_references=data.get("lecture_references", 0),
            style_applied=data.get("style_hint"),
            error=data.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to solve exercise: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Giải bài thất bại: {str(e)}",
        ) from e


@router.get(
    "/health",
    summary="Kiểm tra trạng thái bài giảng service",
    description="Kiểm tra xem có tài liệu bài giảng nào được load hay không.",
)
async def health_check() -> dict[str, Any]:
    """Health check for bai giang service."""
    try:
        subjects_json = list_available_subjects()
        import json

        data = json.loads(subjects_json)
        total_chunks = data.get("total_chunks", 0)

        return {
            "status": "healthy" if total_chunks > 0 else "no_data",
            "total_chunks": total_chunks,
            "subjects_available": len(data.get("subjects", [])),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
