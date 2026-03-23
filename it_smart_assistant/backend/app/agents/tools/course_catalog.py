"""Course catalog retrieval tool for curriculum Excel workbooks."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from langchain_core.tools import tool

from app.knowledge import get_student_knowledge_base

COURSE_CODE_PATTERN = re.compile(r"\b[A-Z]{2,}[A-Z0-9]*\d[\dA-Z.]*\b")


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value.lower()).strip()


def _extract_course_code(query: str) -> str | None:
    match = COURSE_CODE_PATTERN.search(query.upper())
    return match.group(0) if match else None


def _extract_program_track(normalized_query: str) -> str | None:
    if "ky su" in normalized_query:
        return "ky_su"
    if "cu nhan" in normalized_query:
        return "cu_nhan"
    return None


def _extract_semester_number(normalized_query: str) -> int | None:
    match = re.search(r"hoc ky\s*(\d+)", normalized_query)
    return int(match.group(1)) if match else None


def _rerank_course_results(results: list[dict[str, Any]], *, query: str) -> list[dict[str, Any]]:
    normalized_query = _normalize_text(query)
    course_code = _extract_course_code(query)
    program_track = _extract_program_track(normalized_query)
    semester_number = _extract_semester_number(normalized_query)
    asks_for_list = any(
        phrase in normalized_query
        for phrase in ["co nhung mon nao", "gom nhung mon nao", "danh sach mon", "nhung mon hoc"]
    )

    ranked: list[tuple[int, dict[str, Any]]] = []
    for result in results:
        metadata = result.get("entry_metadata") or {}
        score = int(result.get("score") or 0)
        source_kind = result.get("source_kind")
        result_program_track = metadata.get("program_track")
        result_semester_number = metadata.get("semester_number")

        if program_track and result_program_track not in {program_track, None, ""}:
            continue
        if semester_number is not None and result_semester_number not in {semester_number, None}:
            continue

        if source_kind == "course_record":
            score += 25
        elif source_kind == "course_summary":
            score += 18

        if course_code and metadata.get("course_code") == course_code:
            score += 80

        normalized_course_name = metadata.get("normalized_course_name") or ""
        aliases = metadata.get("aliases") or []
        if normalized_course_name and normalized_course_name in normalized_query:
            score += 35
        elif any(alias and alias in normalized_query for alias in aliases):
            score += 25

        if program_track:
            if result_program_track == program_track:
                score += 40

        if semester_number is not None:
            if result_semester_number == semester_number:
                score += 35

        if asks_for_list and source_kind == "course_summary":
            score += 28
        elif asks_for_list and source_kind == "course_record":
            score -= 10

        ranked.append((score, result))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [{**result, "score": score} for score, result in ranked]


def _fallback_scan_loaded_documents(query: str, *, top_k: int) -> list[dict[str, Any]]:
    knowledge_base = get_student_knowledge_base()
    normalized_query = _normalize_text(query)
    course_code = _extract_course_code(query)
    program_track = _extract_program_track(normalized_query)
    semester_number = _extract_semester_number(normalized_query)

    loaded_results: list[dict[str, Any]] = []
    for document in knowledge_base.documents:
        if document.source_kind not in {"course_record", "course_summary"}:
            continue

        metadata = document.entry_metadata or {}
        if program_track and metadata.get("program_track") != program_track:
            continue
        if semester_number is not None and metadata.get("semester_number") != semester_number:
            continue
        if course_code and metadata.get("course_code") != course_code:
            continue

        loaded_results.append(
            {
                "source_id": document.id,
                "source_document_id": document.source_document_id,
                "source_kind": document.source_kind,
                "title": document.title,
                "category": document.category,
                "summary": document.summary,
                "excerpt": document.content.splitlines()[0] if document.content else document.summary,
                "source_url": document.source_url,
                "source_path": document.source_path,
                "section_title": document.section_title,
                "page_from": document.page_from,
                "page_to": document.page_to,
                "keywords": document.keywords,
                "entry_metadata": metadata,
                "score": 0,
            }
        )

    return _rerank_course_results(loaded_results, query=query)[: max(1, min(top_k, 8))]


@tool
def search_course_catalog(query: str, top_k: int = 5) -> str:
    """Search course catalogs and curriculum spreadsheets for subjects, semesters, credits, and prerequisites."""
    knowledge_base = get_student_knowledge_base()
    normalized_query = _normalize_text(query)
    asks_for_list = any(
        phrase in normalized_query
        for phrase in ["co nhung mon nao", "gom nhung mon nao", "danh sach mon", "nhung mon hoc"]
    )
    candidate_limit = max(20, min(top_k * 8, 60)) if asks_for_list else max(10, min(top_k * 4, 20))
    raw_results = knowledge_base.search(query, top_k=candidate_limit)
    course_results = [
        result for result in raw_results if result.get("source_kind") in {"course_record", "course_summary"}
    ]
    reranked = _rerank_course_results(course_results, query=query)[: max(1, min(top_k, 8))]
    if not reranked and (_extract_program_track(normalized_query) or _extract_semester_number(normalized_query) is not None):
        reranked = _fallback_scan_loaded_documents(query, top_k=top_k)

    payload = {
        "query": query,
        "course_code": _extract_course_code(query),
        "program_track": _extract_program_track(normalized_query),
        "semester_number": _extract_semester_number(normalized_query),
        "result_count": len(reranked),
        "results": reranked,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
