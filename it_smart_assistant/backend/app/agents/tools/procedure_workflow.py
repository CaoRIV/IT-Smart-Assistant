from __future__ import annotations

import re
import unicodedata
from typing import Any

from langchain_core.tools import tool

from app.agents.tools.form_generator import _find_admin_form
from app.knowledge.service import get_student_knowledge_base


PROCEDURE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "bao_luu_hoc_tap",
        "title": "Thủ tục bảo lưu học tập",
        "summary": "Hướng dẫn sinh viên xin tạm ngừng học theo học kỳ hoặc năm học.",
        "keywords": ["bảo lưu", "tạm ngừng học", "nghỉ học tạm thời"],
        "eligibility": [
            "Sinh viên có nhu cầu tạm ngừng học tập theo quy định của nhà trường.",
            "Cần có lý do rõ ràng và nộp hồ sơ trong thời gian xử lý được cho phép.",
        ],
        "required_documents": [
            "Đơn xin bảo lưu học tập",
            "Tài liệu chứng minh lý do nếu có",
            "Thẻ sinh viên hoặc giấy tờ nhân thân để đối chiếu khi cần",
        ],
        "steps": [
            "Kiểm tra điều kiện bảo lưu và mốc thời gian nộp hồ sơ.",
            "Điền đầy đủ thông tin vào đơn xin bảo lưu.",
            "Nộp đơn và tài liệu kèm theo cho đơn vị phụ trách học vụ.",
            "Theo dõi kết quả phê duyệt và lưu bản xác nhận.",
        ],
        "contact_office": "Phòng Đào tạo hoặc bộ phận học vụ khoa",
        "form_topic": "đơn xin bảo lưu học tập",
    },
    {
        "id": "xac_nhan_sinh_vien",
        "title": "Thủ tục xin giấy xác nhận sinh viên",
        "summary": "Hướng dẫn xin giấy xác nhận sinh viên phục vụ vay vốn, hồ sơ hành chính hoặc các nhu cầu khác.",
        "keywords": ["xác nhận sinh viên", "giấy xác nhận", "vay vốn"],
        "eligibility": [
            "Sinh viên đang theo học tại trường và cần giấy xác nhận cho mục đích hợp lệ.",
        ],
        "required_documents": [
            "Đơn xin xác nhận sinh viên",
            "Thông tin mục đích sử dụng giấy xác nhận",
        ],
        "steps": [
            "Chọn đúng mục đích xin xác nhận.",
            "Điền đầy đủ thông tin sinh viên và mục đích sử dụng.",
            "Nộp đơn cho đơn vị hành chính hoặc công tác sinh viên.",
            "Nhận kết quả theo lịch hẹn của nhà trường.",
        ],
        "contact_office": "Phòng Công tác sinh viên hoặc bộ phận hành chính sinh viên",
        "form_topic": "đơn xin xác nhận sinh viên",
    },
    {
        "id": "mien_giam_hoc_phi",
        "title": "Thủ tục xin miễn giảm học phí",
        "summary": "Hướng dẫn lập hồ sơ đề nghị xem xét miễn giảm học phí theo đối tượng ưu tiên.",
        "keywords": ["miễn giảm học phí", "hỗ trợ học phí", "học phí ưu tiên"],
        "eligibility": [
            "Sinh viên thuộc đối tượng được xem xét miễn giảm học phí theo quy định.",
            "Có tài liệu chứng minh đối tượng, chính sách hỗ trợ hoặc hoàn cảnh.",
        ],
        "required_documents": [
            "Đơn xin miễn giảm học phí",
            "Tài liệu chứng minh đối tượng chính sách",
            "Minh chứng học phí hoặc thông báo học phí nếu cần",
        ],
        "steps": [
            "Rà soát điều kiện và minh chứng cần nộp.",
            "Điền đơn xin miễn giảm học phí.",
            "Nộp đơn và hồ sơ chứng minh cho phòng tài chính hoặc công tác sinh viên.",
            "Theo dõi kết quả phê duyệt và mức hỗ trợ được áp dụng.",
        ],
        "contact_office": "Phòng Tài chính - Kế toán và đơn vị công tác sinh viên",
        "form_topic": "đơn xin miễn giảm học phí",
    },
    {
        "id": "rut_hoc_phan",
        "title": "Thủ tục xin rút học phần",
        "summary": "Hướng dẫn sinh viên xin rút học phần đã đăng ký trong học kỳ.",
        "keywords": ["rút học phần", "hủy môn", "rút môn học"],
        "eligibility": [
            "Sinh viên đang trong thời gian được phép rút học phần theo quy định.",
        ],
        "required_documents": [
            "Đơn xin rút học phần",
            "Thông tin học phần muốn rút",
        ],
        "steps": [
            "Kiểm tra hạn cuối rút học phần.",
            "Xác định mã học phần, tên học phần và lý do rút.",
            "Điền đơn xin rút học phần và nộp đến bộ phận học vụ.",
            "Theo dõi cập nhật trên hệ thống đăng ký học phần.",
        ],
        "contact_office": "Phòng Đào tạo hoặc bộ phận học vụ khoa",
        "form_topic": "đơn xin rút học phần",
    },
    {
        "id": "hoc_lai_cai_thien",
        "title": "Thủ tục đăng ký học lại hoặc cải thiện điểm",
        "summary": "Hướng dẫn lập yêu cầu học lại hoặc cải thiện điểm cho học phần.",
        "keywords": ["học lại", "cải thiện điểm", "đăng ký học lại"],
        "eligibility": [
            "Sinh viên có học phần cần học lại hoặc muốn cải thiện điểm theo quy định.",
        ],
        "required_documents": [
            "Đơn xin học lại hoặc cải thiện điểm",
            "Thông tin học phần cần đăng ký",
        ],
        "steps": [
            "Xác định học phần, học kỳ và mục tiêu học lại hoặc cải thiện.",
            "Điền đơn đăng ký học lại/cải thiện điểm.",
            "Nộp đơn theo quy trình học vụ và theo dõi kết quả phê duyệt.",
            "Hoàn thành học phí và lịch học nếu được chấp thuận.",
        ],
        "contact_office": "Phòng Đào tạo hoặc bộ phận học vụ khoa",
        "form_topic": "đơn xin học lại cải thiện điểm",
    },
    {
        "id": "dang_ky_thuc_tap",
        "title": "Thủ tục đăng ký thực tập",
        "summary": "Hướng dẫn sinh viên đăng ký thông tin thực tập và đơn vị thực tập.",
        "keywords": ["đăng ký thực tập", "thực tập", "đơn thực tập"],
        "eligibility": [
            "Sinh viên đã đến giai đoạn thực tập theo chương trình đào tạo.",
        ],
        "required_documents": [
            "Đơn đăng ký thực tập",
            "Thông tin đơn vị thực tập và người hướng dẫn",
        ],
        "steps": [
            "Xác định đơn vị thực tập và thông tin liên hệ.",
            "Điền đơn đăng ký thực tập.",
            "Nộp đơn cho khoa hoặc bộ môn phụ trách thực tập.",
            "Theo dõi phân công hướng dẫn và các mốc nộp báo cáo.",
        ],
        "contact_office": "Khoa, bộ môn hoặc đơn vị phụ trách thực tập",
        "form_topic": "đơn đăng ký thực tập",
    },
    {
        "id": "hoan_nghia_vu_hoc_tap",
        "title": "Thủ tục xin hoãn nghĩa vụ học tập",
        "summary": "Hướng dẫn sinh viên lập đề nghị hoãn nghĩa vụ học tập theo trường hợp phù hợp.",
        "keywords": ["hoãn nghĩa vụ học tập", "gia hạn học tập", "hoãn nghĩa vụ"],
        "eligibility": [
            "Sinh viên có lý do hợp lệ và thuộc trường hợp được xem xét.",
        ],
        "required_documents": [
            "Đơn xin hoãn nghĩa vụ học tập",
            "Tài liệu chứng minh lý do nếu có",
        ],
        "steps": [
            "Đối chiếu điều kiện và thủ tục theo quy định hiện hành.",
            "Điền đơn xin hoãn nghĩa vụ học tập.",
            "Nộp hồ sơ cho phòng đào tạo hoặc bộ phận học vụ.",
            "Theo dõi kết quả phê duyệt và thời hạn được gia hạn.",
        ],
        "contact_office": "Phòng Đào tạo hoặc bộ phận học vụ khoa",
        "form_topic": "đơn xin hoãn nghĩa vụ học tập",
    },
]


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_marks.replace("đ", "d").replace("Đ", "D").lower().strip()


def _tokenize(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", _normalize_text(value)) if token}


def _match_procedure(query: str) -> dict[str, Any] | None:
    query_tokens = _tokenize(query)
    normalized_query = _normalize_text(query)
    best_match: dict[str, Any] | None = None
    best_score = 0

    for procedure in PROCEDURE_CATALOG:
        candidate_tokens = _tokenize(
            " ".join([procedure["title"], procedure["summary"], *procedure["keywords"]])
        )
        score = len(query_tokens & candidate_tokens) * 3
        normalized_title = _normalize_text(procedure["title"])
        if normalized_title and normalized_title in normalized_query:
            score += 12
        for keyword in procedure["keywords"]:
            normalized_keyword = _normalize_text(keyword)
            if normalized_keyword and normalized_keyword in normalized_query:
                score += 8 if len(normalized_keyword.split()) >= 2 else 2
        if score > best_score:
            best_score = score
            best_match = procedure

    if best_score == 0:
        return None

    return best_match


def _build_sources(query: str) -> list[dict[str, Any]]:
    hits = get_student_knowledge_base().search(query, top_k=3)
    sources: list[dict[str, Any]] = []
    for hit in hits:
        sources.append(
            {
                "title": hit["title"],
                "source_kind": hit["source_kind"],
                "section_title": hit.get("section_title"),
                "page_from": hit.get("page_from"),
                "page_to": hit.get("page_to"),
                "source_url": hit.get("source_url"),
            }
        )
    return sources


@tool
def build_procedure_workflow(request: str) -> dict[str, Any]:
    """Build a structured administrative workflow for common student procedures."""
    matched = _match_procedure(request)
    if not matched:
        return {
            "matched": False,
            "message": "Không tìm thấy thủ tục phù hợp trong bộ quy trình hiện tại.",
        }

    matched_form = _find_admin_form(matched["form_topic"], request)
    return {
        "matched": True,
        "procedure_id": matched["id"],
        "title": matched["title"],
        "summary": matched["summary"],
        "eligibility": matched["eligibility"],
        "required_documents": matched["required_documents"],
        "steps": matched["steps"],
        "contact_office": matched["contact_office"],
        "matched_form": matched_form,
        "sources": _build_sources(request),
    }
