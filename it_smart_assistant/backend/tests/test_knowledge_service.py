"""Tests for generated knowledge retrieval helpers."""

from __future__ import annotations

import json

from app.knowledge.service import KnowledgeDocument, StudentKnowledgeBase


def test_search_reads_generated_chunks(tmp_path):
    """Generated chunk files should be searchable like static documents."""
    static_dir = tmp_path / "static"
    generated_dir = tmp_path / "generated"
    static_dir.mkdir()
    generated_dir.mkdir()

    (static_dir / "sample.json").write_text(
        json.dumps(
            {
                "id": "sample-static",
                "title": "Cau hoi mau",
                "category": "FAQ",
                "summary": "Tai lieu mac dinh",
                "content": "Noi dung chung",
                "source_url": "",
                "keywords": ["faq"],
            }
        ),
        encoding="utf-8",
    )

    (generated_dir / "tuition.json").write_text(
        json.dumps(
            {
                "document_id": "hoc-phi",
                "title": "Quy dinh hoc phi",
                "category": "Hoc Phi",
                "source_url": "",
                "source_path": "knowledge_raw/hoc_phi/qd_hoc_phi.pdf",
                "page_count": 4,
                "status": "needs_review",
                "chunks": [
                    {
                        "chunk_id": "hoc-phi-chunk-001",
                        "section_title": "Muc thu",
                        "summary": "Hoc phi duoc nop theo hoc ky.",
                        "content": "Sinh vien phai nop hoc phi theo hoc ky va theo dung han thong bao.",
                        "page_from": 1,
                        "page_to": 1,
                        "keywords": ["hoc phi"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    knowledge_base = StudentKnowledgeBase.from_sources(
        static_documents_dir=static_dir,
        generated_chunks_dir=generated_dir,
    )

    results = knowledge_base.search("hoc phi theo hoc ky", top_k=3)

    assert results
    assert results[0]["source_id"] == "hoc-phi-chunk-001"
    assert results[0]["source_kind"] == "chunk"
    assert results[0]["page_from"] == 1
    assert results[0]["source_path"] == "knowledge_raw/hoc_phi/qd_hoc_phi.pdf"


def test_search_reads_generated_table_rows(tmp_path):
    """Generated table rows should be searchable as structured knowledge."""
    static_dir = tmp_path / "static"
    generated_dir = tmp_path / "generated"
    tables_dir = tmp_path / "tables"
    static_dir.mkdir()
    generated_dir.mkdir()
    tables_dir.mkdir()

    (tables_dir / "tuition-table.json").write_text(
        json.dumps(
            {
                "document_id": "hoc-phi-2025",
                "title": "Hoc phi nam hoc 2025 2026",
                "category": "Hoc Phi",
                "source_url": "",
                "source_path": "knowledge_raw/hoc_phi/hoc_phi_2025.pdf",
                "tables": [
                    {
                        "table_id": "hoc-phi-2025-table-01",
                        "title": "I. Muc thu hoc phi dao tao dai hoc he chinh quy",
                        "page_from": 2,
                        "page_to": 2,
                        "rows": [
                            {
                                "row_id": "1",
                                "label": "Cac lop khoi nganh III",
                                "amount_text": "448.869 dong / 1 tin chi",
                                "amount_value": 448869,
                                "page_from": 2,
                                "page_to": 2,
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    knowledge_base = StudentKnowledgeBase.from_sources(
        static_documents_dir=static_dir,
        generated_chunks_dir=generated_dir,
        generated_tables_dir=tables_dir,
    )

    results = knowledge_base.search("hoc phi khoi nganh iii", top_k=3)

    assert results
    assert results[0]["source_kind"] == "table_row"
    assert results[0]["source_document_id"] == "hoc-phi-2025"
    assert results[0]["section_title"] == "I. Muc thu hoc phi dao tao dai hoc he chinh quy"


def test_tuition_query_defaults_to_chinh_quy_when_query_is_ambiguous():
    """Ambiguous tuition questions should rank regular undergraduate rows above cao hoc rows."""
    knowledge_base = StudentKnowledgeBase(
        [
            KnowledgeDocument(
                id="cao-hoc-row",
                title="Hoc phi nam hoc 2025 2026",
                category="Hoc Phi",
                summary="Muc hoc phi dao tao cao hoc - Khoi nganh V",
                content="Muc hoc phi dao tao cao hoc. Khoi nganh V. 23.125.000 dong.",
                source_url="",
                keywords=["Hoc Phi", "cao hoc", "Khoi nganh V", "23.125.000 dong"],
                source_kind="table_row",
                section_title="Muc hoc phi dao tao cao hoc",
                page_from=3,
                page_to=3,
                source_path="knowledge_raw/hoc_phi/cao_hoc.pdf",
            ),
            KnowledgeDocument(
                id="chinh-quy-row",
                title="Hoc phi nam hoc 2025 2026",
                category="Hoc Phi",
                summary="Muc thu hoc phi dao tao dai hoc he chinh quy - Cac lop khoi nganh V",
                content="Muc thu hoc phi dao tao dai hoc he chinh quy. Cac lop khoi nganh V. 526.174 dong.",
                source_url="",
                keywords=["Hoc Phi", "chinh quy", "Khoi nganh V", "526.174 dong"],
                source_kind="table_row",
                section_title="Muc thu hoc phi dao tao dai hoc he chinh quy",
                page_from=2,
                page_to=2,
                source_path="knowledge_raw/hoc_phi/chinh_quy.pdf",
            ),
        ]
    )

    results = knowledge_base.search("hoc phi khoi nganh V bao nhieu", top_k=2)

    assert results
    assert results[0]["source_id"] == "chinh-quy-row"


def test_tuition_query_respects_explicit_cao_hoc_track():
    """Explicit cao hoc questions should rank cao hoc rows above default chinh quy rows."""
    knowledge_base = StudentKnowledgeBase(
        [
            KnowledgeDocument(
                id="cao-hoc-row",
                title="Hoc phi nam hoc 2025 2026",
                category="Hoc Phi",
                summary="Muc hoc phi dao tao cao hoc - Khoi nganh V",
                content="Muc hoc phi dao tao cao hoc. Khoi nganh V. 23.125.000 dong.",
                source_url="",
                keywords=["Hoc Phi", "cao hoc", "Khoi nganh V", "23.125.000 dong"],
                source_kind="table_row",
                section_title="Muc hoc phi dao tao cao hoc",
                page_from=3,
                page_to=3,
                source_path="knowledge_raw/hoc_phi/cao_hoc.pdf",
            ),
            KnowledgeDocument(
                id="chinh-quy-row",
                title="Hoc phi nam hoc 2025 2026",
                category="Hoc Phi",
                summary="Muc thu hoc phi dao tao dai hoc he chinh quy - Cac lop khoi nganh V",
                content="Muc thu hoc phi dao tao dai hoc he chinh quy. Cac lop khoi nganh V. 526.174 dong.",
                source_url="",
                keywords=["Hoc Phi", "chinh quy", "Khoi nganh V", "526.174 dong"],
                source_kind="table_row",
                section_title="Muc thu hoc phi dao tao dai hoc he chinh quy",
                page_from=2,
                page_to=2,
                source_path="knowledge_raw/hoc_phi/chinh_quy.pdf",
            ),
        ]
    )

    results = knowledge_base.search("hoc phi cao hoc khoi nganh V bao nhieu", top_k=2)

    assert results
    assert results[0]["source_id"] == "cao-hoc-row"
