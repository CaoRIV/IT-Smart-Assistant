"""Heuristic intent router for the student advisory chatbot."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

from langchain_core.messages import HumanMessage

IntentName = Literal[
    "casual",
    "knowledge_qa",
    "course_catalog",
    "tuition_lookup",
    "procedure_workflow",
    "form_fill",
    "attachment_qa",
]


@dataclass(slots=True)
class IntentRoute:
    """Routing decision for a single user turn."""

    intent: IntentName
    reason: str
    force_tool_calls: list[dict[str, Any]]
    system_hint: str | None = None


GREETING_PHRASES = {
    "hi",
    "hello",
    "hey",
    "chao",
    "xin chao",
    "chao ban",
    "alo",
    "cam on",
    "thanks",
    "thank you",
}

TUITION_KEYWORDS = {
    "hoc phi",
    "muc thu",
    "tin chi",
    "khoi nganh",
    "cao hoc",
    "lien thong",
    "chat luong cao",
    "clc",
    "quy mo nho",
    "thanh toan hoc phi",
}

FORM_KEYWORDS = {
    "bieu mau",
    "mau don",
    "tao don",
    "lam don",
    "dien don",
    "tao bieu mau",
    "mau xac nhan",
    "mau giay",
}

PROCEDURE_KEYWORDS = {
    "thu tuc",
    "quy trinh",
    "ho so",
    "dieu kien",
    "cac buoc",
    "bao luu",
    "xac nhan sinh vien",
    "mien giam hoc phi",
    "rut hoc phan",
    "hoc lai",
    "cai thien diem",
    "thuc tap",
    "hoan nghia vu hoc tap",
}

KNOWLEDGE_KEYWORDS = {
    "dang ky hoc phan",
    "hoc bong",
    "hoc vu",
    "quy che",
    "so tay sinh vien",
    "giay xac nhan",
    "bao luu",
    "thuc tap",
    "mien giam hoc phi",
    "rut hoc phan",
    "hoc lai",
    "tuyen sinh",
}

COURSE_CATALOG_KEYWORDS = {
    "mon hoc",
    "hoc phan",
    "chuong trinh dao tao",
    "tin chi",
    "tien quyet",
    "ngon ngu giang day",
    "hoc ky",
    "cu nhan",
    "ky su",
}


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_marks.replace("đ", "d").replace("Đ", "D").lower().strip()


def _extract_human_text(message: HumanMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content

    parts: list[str] = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
    return "\n".join(parts).strip()


def _has_attachment_signal(message: HumanMessage) -> bool:
    content = message.content
    if isinstance(content, list):
        return True
    text = _normalize_text(_extract_human_text(message))
    return "tep dinh kem" in text or "anh de ban phan tich" in text


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_casual_message(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact in GREETING_PHRASES


def _tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"router_{uuid4().hex}",
        "name": name,
        "args": args,
        "type": "tool_call",
    }


def _looks_like_course_code(text: str) -> bool:
    return bool(re.search(r"\b[a-z]{2,}[a-z0-9]*\d[\d.a-z]*\b", text))


def route_human_message(message: HumanMessage) -> IntentRoute:
    """Route a user turn into an intent and optional forced tool calls."""
    raw_text = _extract_human_text(message)
    normalized_text = _normalize_text(raw_text)
    has_attachment = _has_attachment_signal(message)

    if _is_casual_message(normalized_text):
        return IntentRoute(
            intent="casual",
            reason="short greeting or conversational opener",
            force_tool_calls=[],
            system_hint="Nguoi dung dang hoi chao hoac tro chuyen thong thuong. Tra loi tu nhien, khong can goi tool neu khong can thiet.",
        )

    if _contains_any(normalized_text, COURSE_CATALOG_KEYWORDS) or _looks_like_course_code(normalized_text):
        return IntentRoute(
            intent="course_catalog",
            reason="curriculum or course catalog lookup",
            force_tool_calls=[_tool_call("search_course_catalog", {"query": raw_text, "top_k": 5})],
            system_hint="Nguoi dung dang tra cuu mon hoc, hoc ky, tin chi, tien quyet hoac chuong trinh dao tao. Uu tien ket qua course catalog thay vi knowledge chung.",
        )

    if _contains_any(normalized_text, FORM_KEYWORDS) and _contains_any(
        normalized_text,
        PROCEDURE_KEYWORDS | KNOWLEDGE_KEYWORDS,
    ):
        return IntentRoute(
            intent="form_fill",
            reason="explicit form/template creation request",
            force_tool_calls=[_tool_call("generate_form", {"topic": raw_text, "requirements": raw_text})],
            system_hint="Nguoi dung dang muon mo hoac tao bieu mau. Sau khi co ket qua tool, huong dan ngan gon va de xuat mo bieu mau.",
        )

    if _contains_any(normalized_text, PROCEDURE_KEYWORDS):
        return IntentRoute(
            intent="procedure_workflow",
            reason="administrative procedure question",
            force_tool_calls=[_tool_call("build_procedure_workflow", {"request": raw_text})],
            system_hint="Nguoi dung dang hoi thu tuc hanh chinh. Sau khi co workflow, can tra loi ro dieu kien, ho so, cac buoc va don vi lien he.",
        )

    if _contains_any(normalized_text, TUITION_KEYWORDS):
        return IntentRoute(
            intent="tuition_lookup",
            reason="tuition or tabular fee lookup request",
            force_tool_calls=[_tool_call("search_student_knowledge", {"query": raw_text, "top_k": 5})],
            system_hint="Nguoi dung dang tra cuu hoc phi. Uu tien cac ket qua bang bieu va neu co nhieu he dao tao thi neu ro he nao dang duoc nhac den.",
        )

    if has_attachment and not _contains_any(normalized_text, KNOWLEDGE_KEYWORDS | TUITION_KEYWORDS):
        return IntentRoute(
            intent="attachment_qa",
            reason="question primarily grounded in current-turn attachments",
            force_tool_calls=[],
            system_hint="Nguoi dung dang hoi dua tren tep dinh kem cua luot hien tai. Uu tien phan tich tep dinh kem truoc, chi goi knowledge tool neu cau hoi co lien quan den quy dinh cua truong.",
        )

    if _contains_any(normalized_text, KNOWLEDGE_KEYWORDS) or "?" in raw_text:
        return IntentRoute(
            intent="knowledge_qa",
            reason="school knowledge question",
            force_tool_calls=[_tool_call("search_student_knowledge", {"query": raw_text, "top_k": 4})],
            system_hint="Nguoi dung dang hoi thong tin hoc vu hoac hanh chinh. Sau khi co ket qua knowledge, tra loi ngan gon va co nguon tham khao.",
        )

    if has_attachment:
        return IntentRoute(
            intent="attachment_qa",
            reason="generic attachment-driven query",
            force_tool_calls=[],
            system_hint="Nguoi dung co gui tep dinh kem. Uu tien noi dung tep dinh kem khi tra loi.",
        )

    return IntentRoute(
        intent="casual",
        reason="fallback conversational route",
        force_tool_calls=[],
        system_hint=None,
    )
