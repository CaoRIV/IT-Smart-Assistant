from __future__ import annotations

import re
import unicodedata
from typing import List

from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.knowledge.admin_store import list_forms


class FormField(BaseModel):
    id: str = Field(..., description="Unique identifier for the field")
    label: str = Field(..., description="Human-readable label for the field")
    type: str = Field(..., description="Type of input: text, textarea, date, number, email")


class FormTemplate(BaseModel):
    template_id: str | None = Field(default=None, description="Admin template ID if matched")
    title: str = Field(..., description="Display title of the form")
    description: str = Field(default="", description="Short form description")
    template: str = Field(..., description="Markdown content with {{placeholders}}")
    fields: List[FormField] = Field(..., description="Fields that the student needs to fill")


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_marks.replace("đ", "d").replace("Đ", "D").lower().strip()


def _tokenize(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", _normalize_text(value)) if token}


def _build_template_markdown(title: str, description: str, fields: list[dict[str, str]]) -> str:
    lines = [f"# {title}"]
    if description:
        lines.append("")
        lines.append(description)
    lines.append("")
    for field in fields:
        lines.append(f"- **{field['label']}:** {{{{{field['id']}}}}}")
    lines.append("")
    lines.append("Sinh viên cam kết thông tin trên là đúng sự thật.")
    return "\n".join(lines)


def _find_admin_form(topic: str, requirements: str) -> dict | None:
    search_text = f"{topic} {requirements}".strip()
    search_tokens = _tokenize(search_text)
    normalized_search = _normalize_text(search_text)
    best_match: dict | None = None
    best_score = 0

    for form in list_forms():
        normalized_title = _normalize_text(form.title)
        normalized_category = _normalize_text(form.category)
        normalized_description = _normalize_text(form.description)
        normalized_keywords = [_normalize_text(keyword) for keyword in form.keywords]
        candidate_tokens = _tokenize(" ".join([form.title, form.category, form.description, *form.keywords]))

        score = len(search_tokens & candidate_tokens) * 3
        if normalized_title and normalized_title in normalized_search:
            score += 12
        if normalized_category and normalized_category in normalized_search:
            score += 4
        for keyword in normalized_keywords:
            if not keyword:
                continue
            if keyword in normalized_search:
                score += 8 if len(keyword.split()) >= 2 else 2
        if normalized_description and normalized_description in normalized_search:
            score += 2

        if score > best_score:
            best_score = score
            best_match = form.model_dump()

    if not best_match or best_score == 0:
        return None

    fields = [
        {
            "id": field["name"],
            "label": field["label"],
            "type": field["type"],
        }
        for field in best_match["fields"]
    ]

    return {
        "template_id": best_match["id"],
        "title": best_match["title"],
        "description": best_match["description"],
        "template": _build_template_markdown(
            best_match["title"],
            best_match["description"],
            fields,
        ),
        "fields": fields,
    }


@tool
def generate_form(topic: str, requirements: str = "") -> dict:
    """Generate or retrieve a form template for student administrative requests."""
    matched_form = _find_admin_form(topic, requirements)
    if matched_form:
        return matched_form

    provider = settings.LLM_PROVIDER.lower()

    if provider == "google":
        if not settings.GOOGLE_API_KEY:
            return {"error": "GOOGLE_API_KEY is required when LLM_PROVIDER=google"}

        llm = ChatGoogleGenerativeAI(
            model=settings.AI_MODEL,
            temperature=0.2,
            google_api_key=settings.GOOGLE_API_KEY,
        )
    else:
        if not settings.OPENAI_API_KEY:
            return {"error": "OPENAI_API_KEY is required when LLM_PROVIDER=openai"}

        llm = ChatOpenAI(
            model=settings.AI_MODEL,
            temperature=0.2,
            api_key=settings.OPENAI_API_KEY,
        )

    structured_llm = llm.with_structured_output(FormTemplate)

    prompt = f"""
    You are an expert administrative assistant. Create a student-facing form template for: "{topic}".
    Additional requirements: "{requirements}"

    Return a JSON object with:
    1. template_id: null
    2. title: the form title
    3. description: a short description
    4. template: the form content in Markdown using {{field_id}} placeholders
    5. fields: the list of fields to fill
    """

    try:
        result = structured_llm.invoke(prompt)
        return result.model_dump()
    except Exception as e:
        return {"error": str(e)}
